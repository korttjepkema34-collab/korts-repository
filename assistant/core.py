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
KNOWLEDGE_STATUSES = ('proposed', 'reviewed', 'approved', 'superseded', 'disputed')
SUBPROJECT_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$')

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

def validate_subproject(value):
    value = '' if value is None else str(value).strip()
    if value and not SUBPROJECT_RE.fullmatch(value):
        raise ValueError('Subproject must be a simple name up to 64 characters')
    return value

def _frontmatter(text):
    """Parse the deliberately small metadata subset used by vault notes."""
    if not text.startswith('---\n'):
        return {}, text
    end = text.find('\n---\n', 4)
    if end < 0:
        return {}, text
    values = {}
    for line in text[4:end].splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        key = key.strip().lower().replace('-', '_')
        value = value.strip().strip('"\'')
        values[key] = value
    return values, text[end + 5:]

def note_record(relative, scope, text):
    """Return path-owned scope metadata; note text can never widen its own access."""
    metadata, body = _frontmatter(text)
    errors = []
    parts = Path(relative).parts
    path_subproject = parts[1] if scope != 'shared' and len(parts) > 2 else ''
    claimed_project = metadata.get('project', scope)
    if claimed_project != scope:
        errors.append('project metadata does not match the vault path')
    claimed_subproject = metadata.get('subproject', path_subproject)
    try:
        claimed_subproject = validate_subproject(claimed_subproject)
    except ValueError:
        claimed_subproject = path_subproject
        errors.append('invalid subproject metadata')
    if path_subproject and claimed_subproject != path_subproject:
        errors.append('subproject metadata does not match the vault path')
    subproject = path_subproject or claimed_subproject
    status = metadata.get('status', 'proposed').lower()
    if status not in KNOWLEDGE_STATUSES:
        status = 'disputed'; errors.append('unknown knowledge status')
    if status == 'reviewed' and not metadata.get('reviewer'):
        errors.append('reviewed knowledge requires reviewer provenance')
    if status == 'approved':
        required = ('note_id','producer','sources','approved_revision')
        if any(not metadata.get(field) for field in required):
            errors.append('approved knowledge requires identity, producer, source and revision')
    if errors:
        status = 'disputed'
    return {
        'note_id': metadata.get('note_id') or relative,
        'scope': scope,
        'subproject': subproject,
        'status': status,
        'kind': metadata.get('kind', 'note'),
        'producer': metadata.get('producer') or metadata.get('author', 'unknown'),
        'sources': metadata.get('sources', ''),
        'observed_date': metadata.get('observed_date', ''),
        'note_updated': metadata.get('updated_date', ''),
        'evidence_ids': metadata.get('evidence_ids', ''),
        'reviewer': metadata.get('reviewer', ''),
        'approved_revision': metadata.get('approved_revision', ''),
        'supersedes': metadata.get('supersedes', ''),
        'metadata_errors': errors,
        'body': body,
    }

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
          status TEXT NOT NULL, data TEXT NOT NULL, updated TEXT NOT NULL,
          subproject TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY, task_id TEXT, at TEXT, kind TEXT, detail TEXT);
        CREATE TABLE IF NOT EXISTS usage (day TEXT, provider TEXT, calls INTEGER,
          PRIMARY KEY(day,provider));
        ''')
        columns = {row[1] for row in self.db.execute('PRAGMA table_info(tasks)')}
        if 'subproject' not in columns:
            self.db.execute("ALTER TABLE tasks ADD COLUMN subproject TEXT NOT NULL DEFAULT ''")
        note_columns = [row[1] for row in self.db.execute('PRAGMA table_info(notes)')]
        expected = ['path','scope','subproject','note_id','status','kind','producer','sources',
                    'observed_date','note_updated','evidence_ids','reviewer','approved_revision',
                    'supersedes','metadata_errors','digest','body']
        if note_columns and note_columns != expected:
            self.db.execute('DROP TABLE notes')
        self.db.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS notes USING fts5(
          path UNINDEXED, scope UNINDEXED, subproject UNINDEXED, note_id UNINDEXED,
          status UNINDEXED, kind UNINDEXED, producer UNINDEXED, sources UNINDEXED,
          observed_date UNINDEXED, note_updated UNINDEXED, evidence_ids UNINDEXED,
          reviewer UNINDEXED, approved_revision UNINDEXED, supersedes UNINDEXED,
          metadata_errors UNINDEXED, digest UNINDEXED, body)''')
        self.db.commit()

    def close(self): self.db.close()

    def create(self, project, goal, subproject=''):
        if project not in PROJECTS or not goal.strip() or len(goal) > 30000:
            raise ValueError('Valid project and nonempty goal up to 30000 characters required')
        subproject = validate_subproject(subproject)
        tid = uuid.uuid4().hex
        with self.db:
            self.db.execute('''INSERT INTO tasks
                (id,project,goal,status,data,updated,subproject) VALUES (?,?,?,?,?,?,?)''',
                (tid, project, goal, 'planned', '{}', now(), subproject))
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
                record = note_record(rel, scope, text)
                for start in range(0, len(record['body']), 2400):
                    chunks.append((rel,scope,record['subproject'],record['note_id'],record['status'],
                        record['kind'],record['producer'],record['sources'],
                        record['observed_date'],record['note_updated'],record['evidence_ids'],
                        record['reviewer'],record['approved_revision'],record['supersedes'],
                        json.dumps(record['metadata_errors']),digest,record['body'][start:start+2800]))
        # Replace transactionally: removed notes disappear and readers never see a half index.
        with self.db:
            self.db.execute('DELETE FROM notes')
            self.db.executemany('INSERT INTO notes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', chunks)
        return len(chunks)

    def search(self, project, query, limit=6, subproject='', include_history=False):
        if project not in PROJECTS: raise ValueError('Unknown project')
        subproject = validate_subproject(subproject)
        words = re.findall(r'\w+', query, re.UNICODE)[:24]
        if not words: return []
        expression = ' OR '.join('"'+w+'"' for w in words)
        rows = self.db.execute('''SELECT path,scope,subproject,note_id,status,kind,producer,
                sources,observed_date,note_updated,evidence_ids,reviewer,approved_revision,
                supersedes,metadata_errors,digest,body FROM notes
              WHERE notes MATCH ?
                AND (scope='shared' OR (scope=? AND (?='' OR subproject='' OR subproject=?)))
                AND (?=1 OR status!='superseded')
              ORDER BY CASE status WHEN 'approved' THEN 0 WHEN 'reviewed' THEN 1
                WHEN 'proposed' THEN 2 WHEN 'disputed' THEN 3 ELSE 4 END, rank LIMIT ?''',
                (expression,project,subproject,subproject,int(bool(include_history)),max(1,min(limit,20))))
        results=[]
        for row in rows:
            item=dict(row);item['metadata_errors']=json.loads(item['metadata_errors']);results.append(item)
        return results

    def report(self):
        lines = ['# Assistant report', '', 'Generated: '+now(), '',
            'Cloud-approved drafts are not deployed changes or verified game builds.', '']
        for t in self.list():
            label=t['project']+('/'+t['subproject'] if t['subproject'] else '')
            lines += ['## '+label+' / '+t['id'][:8],
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
