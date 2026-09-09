"""Local state and Obsidian-compatible retrieval. No network or model dependency."""
from __future__ import annotations
import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECTS = ('personal', 'business', 'game')
SCOPES = ('shared', *PROJECTS)

def now():
    return datetime.now(timezone.utc).isoformat()

def runtime_root():
    # Outside the Git checkout by default, including private vault contents and all artifacts.
    return Path(os.environ.get('ASSISTANT_HOME', str(Path.home() / 'KortAssistant'))).expanduser().resolve()

def safe_path(root, relative):
    root = Path(root).resolve()
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts or ':' in str(rel) or '\\' in str(rel):
        raise ValueError('Expected a relative path without traversal')
    target = (root / rel).resolve()
    if root not in target.parents:
        raise ValueError('Path escapes root')
    return target

class Store:
    def __init__(self, root=None):
        self.root = Path(root or runtime_root()).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / 'state.sqlite', timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS tasks (
          id TEXT PRIMARY KEY, project TEXT NOT NULL, goal TEXT NOT NULL,
          status TEXT NOT NULL, data TEXT NOT NULL, updated TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY, task_id TEXT, at TEXT, kind TEXT, detail TEXT);
        CREATE TABLE IF NOT EXISTS usage (day TEXT, provider TEXT, calls INTEGER,
          PRIMARY KEY(day,provider));
        CREATE VIRTUAL TABLE IF NOT EXISTS notes USING fts5(path UNINDEXED, scope UNINDEXED, digest UNINDEXED, body);
        ''')
        self.db.commit()

    def close(self): self.db.close()

    def create(self, project, goal):
        if project not in PROJECTS or not goal.strip() or len(goal) > 30000:
            raise ValueError('Valid project and nonempty goal up to 30000 characters required')
        tid = uuid.uuid4().hex
        with self.db:
            self.db.execute('INSERT INTO tasks VALUES (?,?,?,?,?,?)',
                (tid, project, goal, 'planned', '{}', now()))
            self.db.execute('INSERT INTO events(task_id,at,kind,detail) VALUES (?,?,?,?)',
                (tid, now(), 'created', 'User goal recorded'))
        return tid

    def get(self, tid):
        row = self.db.execute('SELECT * FROM tasks WHERE id=?', (tid,)).fetchone()
        if not row: raise ValueError('Unknown task')
        result = dict(row); result['data'] = json.loads(result['data']); return result

    def list(self):
        return [self.get(r[0]) for r in self.db.execute('SELECT id FROM tasks ORDER BY updated DESC')]

    def update(self, tid, status, data, detail=''):
        self.get(tid)
        with self.db:
            self.db.execute('UPDATE tasks SET status=?,data=?,updated=? WHERE id=?',
                (status, json.dumps(data), now(), tid))
            self.db.execute('INSERT INTO events(task_id,at,kind,detail) VALUES (?,?,?,?)',
                (tid, now(), status, detail[:8000]))

    def reserve_call(self, provider, cap):
        day = datetime.now(timezone.utc).date().isoformat()
        try:
            self.db.execute('BEGIN IMMEDIATE')
            row = self.db.execute('SELECT calls FROM usage WHERE day=? AND provider=?', (day,provider)).fetchone()
            used = row[0] if row else 0
            if used >= cap: raise RuntimeError('Configured cloud allowance reached; wait for cloud')
            self.db.execute('INSERT INTO usage VALUES (?,?,?) ON CONFLICT(day,provider) DO UPDATE SET calls=excluded.calls',
                (day,provider,used+1))
            self.db.commit()
        except BaseException:
            self.db.rollback(); raise

    def index(self, vault):
        vault = Path(vault).resolve(); chunks = []
        for scope in SCOPES:
            for p in sorted((vault / scope).rglob('*.md')):
                if p.is_symlink() or vault not in p.resolve().parents: continue
                if any(part.startswith('.') for part in p.relative_to(vault).parts): continue
                if p.stat().st_size > 1_000_000: continue
                text = p.read_text(encoding='utf-8')
                digest = hashlib.sha256(text.encode()).hexdigest()
                rel = p.relative_to(vault).as_posix()
                for start in range(0, len(text), 2400):
                    chunks.append((rel,scope,digest,text[start:start+2800]))
        # Replace transactionally: removed notes disappear and readers never see a half index.
        with self.db:
            self.db.execute('DELETE FROM notes')
            self.db.executemany('INSERT INTO notes VALUES (?,?,?,?)', chunks)
        return len(chunks)

    def search(self, project, query, limit=6):
        if project not in PROJECTS: raise ValueError('Unknown project')
        words = re.findall(r'\w+', query, re.UNICODE)[:24]
        if not words: return []
        expression = ' OR '.join('"'+w+'"' for w in words)
        rows = self.db.execute('SELECT path,scope,digest,body FROM notes WHERE notes MATCH ? AND scope IN (?,?) ORDER BY rank LIMIT ?',
                (expression,project,'shared',max(1,min(limit,20))))
        return [dict(r) for r in rows]

    def report(self):
        lines = ['# Assistant report', '', 'Generated: '+now(), '',
            'Cloud-approved drafts are not deployed changes or verified game builds.', '']
        for t in self.list():
            lines += ['## '+t['project']+' / '+t['id'][:8],
                'Status: '+t['status'], '', t['goal'], '']
            for job in t['data'].get('jobs',[]):
                review=job.get('review',{})
                lines += ['### Job '+job['id']+' / '+job['status'],
                    '- Cause: '+str(review.get('cause','Unknown; no confirmed diagnosis recorded.')),
                    '- Prevention / skill suggestions: '+json.dumps(review.get('prevention',[])),
                    '- Repairs / human follow-up: '+json.dumps(review.get('repairs',[])),
                    '- Artifact: '+str(job.get('artifact','No artifact yet')), '']
            for key in ('blocker','last_error','review','jobs'):
                if t['data'].get(key):
                    lines += ['### '+key, '```json', json.dumps(t['data'][key],indent=2), '```', '']
        p=self.root/'reports'/('report-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'.md')
        p.parent.mkdir(exist_ok=True); p.write_text('\n'.join(lines),encoding='utf-8'); return p
