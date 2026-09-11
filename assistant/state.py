"""Durable controller state beyond tasks: settings, leases, mailbox, audit, sanitized events,
cloud invocation records, route health and GPU leases. Everything lives in the private SQLite
database next to the task table. Nothing here performs network or model calls."""
from __future__ import annotations
import hashlib
import json
import os
import socket
import uuid
from datetime import datetime, timedelta, timezone

EVENT_HISTORY_LIMIT = 5000          # bounded sanitized event history kept in SQLite
AUDIT_DETAIL_LIMIT = 2000
WORKER_STATES = ('idle', 'working', 'waiting', 'offline', 'blocked', 'unavailable')

SCHEMA = '''
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS leases (
  name TEXT PRIMARY KEY, owner TEXT NOT NULL, pid INTEGER, host TEXT,
  acquired TEXT NOT NULL, heartbeat TEXT NOT NULL, expires TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS mailbox (
  id TEXT PRIMARY KEY, dedupe_key TEXT UNIQUE, task_id TEXT, project TEXT NOT NULL,
  priority TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL, status TEXT NOT NULL,
  created TEXT NOT NULL, updated TEXT NOT NULL, response TEXT, responded_by TEXT, responded_at TEXT);
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY, at TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
  project TEXT, task_id TEXT, ok INTEGER NOT NULL, detail TEXT);
CREATE TABLE IF NOT EXISTS sevents (
  id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, project TEXT NOT NULL,
  task_id TEXT, job_id TEXT, worker TEXT, kind TEXT NOT NULL, message TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS worker_state (
  worker TEXT PRIMARY KEY, state TEXT NOT NULL, project TEXT, task_id TEXT, job_id TEXT,
  updated TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS invocations (
  id TEXT PRIMARY KEY, at TEXT NOT NULL, task_id TEXT, job_id TEXT, purpose TEXT,
  provider TEXT NOT NULL, requested_model TEXT NOT NULL, actual_models TEXT,
  cost_reported TEXT, cost_evidence TEXT, duration_ms INTEGER, outcome TEXT NOT NULL,
  prompt_digest TEXT, result_digest TEXT);
CREATE TABLE IF NOT EXISTS route_state (
  route TEXT PRIMARY KEY, provider TEXT NOT NULL, model TEXT NOT NULL,
  cooldown_until TEXT, failures INTEGER NOT NULL DEFAULT 0, last_ok TEXT,
  last_check TEXT, last_error TEXT, pricing_ok INTEGER);
CREATE TABLE IF NOT EXISTS gpu_lease (
  resource TEXT PRIMARY KEY, holder TEXT NOT NULL, kind TEXT NOT NULL,
  acquired TEXT NOT NULL, expires TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL, project TEXT NOT NULL, role TEXT NOT NULL,
  author TEXT, text TEXT NOT NULL, at TEXT NOT NULL);
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(text, content='messages', content_rowid='id');
CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
  INSERT INTO messages_fts(rowid, text) VALUES (new.id, new.text); END;
CREATE TABLE IF NOT EXISTS attachments (
  id TEXT PRIMARY KEY, task_id TEXT NOT NULL, project TEXT NOT NULL, name TEXT NOT NULL, kind TEXT NOT NULL,
  size INTEGER NOT NULL, sha256 TEXT NOT NULL, at TEXT NOT NULL, by TEXT);
CREATE TABLE IF NOT EXISTS health (
  name TEXT PRIMARY KEY, ok INTEGER NOT NULL, detail TEXT, checked TEXT NOT NULL,
  last_ok TEXT);
'''


def utcnow():
    return datetime.now(timezone.utc)


def iso(dt=None):
    return (dt or utcnow()).isoformat()


def parse(ts):
    try:
        return datetime.fromisoformat(ts) if ts else None
    except (TypeError, ValueError):
        return None


def ensure_schema(db):
    db.executescript(SCHEMA)
    db.commit()


# ---------------------------------------------------------------- settings

def get_setting(db, key, default=None):
    row = db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
    if not row:
        return default
    try:
        return json.loads(row[0])
    except ValueError:
        return default


def set_setting(db, key, value):
    with db:
        db.execute('INSERT INTO settings VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET '
                   'value=excluded.value, updated=excluded.updated', (key, json.dumps(value), iso()))


def is_paused(db):
    return bool(get_setting(db, 'paused', False))


def cloud_consent(db, project):
    """Explicit, audited owner permission to send a project's context to cloud models."""
    value = get_setting(db, 'cloud_consent:' + project)
    return isinstance(value, dict) and value.get('granted') is True


# ---------------------------------------------------------------- leases

def _pid_alive(pid):
    if not pid:
        return False
    if os.name == 'nt':
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))  # QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return code.value == 259  # STILL_ACTIVE
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def acquire_lease(db, name, owner, ttl_seconds=300):
    """Atomically take a named lease. An existing lease is reclaimed only when it has expired,
    or when it belongs to this host and its process is gone. Returns True on success."""
    now = utcnow()
    host = socket.gethostname()
    db.execute('BEGIN IMMEDIATE')
    try:
        row = db.execute('SELECT owner,pid,host,expires FROM leases WHERE name=?', (name,)).fetchone()
        if row and row[0] != owner:
            expired = (parse(row[3]) or now) <= now
            dead_local = row[2] == host and not _pid_alive(row[1])
            if not expired and not dead_local:
                db.rollback()
                return False
        db.execute('INSERT INTO leases VALUES (?,?,?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET '
                   'owner=excluded.owner,pid=excluded.pid,host=excluded.host,acquired=excluded.acquired,'
                   'heartbeat=excluded.heartbeat,expires=excluded.expires',
                   (name, owner, os.getpid(), host, iso(now), iso(now),
                    iso(now + timedelta(seconds=ttl_seconds))))
        db.commit()
        return True
    except BaseException:
        db.rollback()
        raise


def renew_lease(db, name, owner, ttl_seconds=300):
    now = utcnow()
    with db:
        cur = db.execute('UPDATE leases SET heartbeat=?, expires=? WHERE name=? AND owner=?',
                         (iso(now), iso(now + timedelta(seconds=ttl_seconds)), name, owner))
    return cur.rowcount == 1


def release_lease(db, name, owner):
    with db:
        db.execute('DELETE FROM leases WHERE name=? AND owner=?', (name, owner))


def lease_info(db, name):
    row = db.execute('SELECT owner,pid,host,acquired,heartbeat,expires FROM leases WHERE name=?',
                     (name,)).fetchone()
    return dict(zip(('owner', 'pid', 'host', 'acquired', 'heartbeat', 'expires'), row)) if row else None


# ---------------------------------------------------------------- audit

def audit(db, actor, action, ok=True, project=None, task_id=None, detail=''):
    with db:
        db.execute('INSERT INTO audit(at,actor,action,project,task_id,ok,detail) VALUES (?,?,?,?,?,?,?)',
                   (iso(), str(actor)[:80], str(action)[:80], project, task_id, int(bool(ok)),
                    str(detail)[:AUDIT_DETAIL_LIMIT]))


def audit_rows(db, projects, limit=100):
    marks = ','.join('?' * len(projects)) or "''"
    rows = db.execute(f'SELECT at,actor,action,project,task_id,ok,detail FROM audit '
                      f'WHERE project IS NULL OR project IN ({marks}) ORDER BY id DESC LIMIT ?',
                      (*projects, int(limit))).fetchall()
    return [dict(zip(('at', 'actor', 'action', 'project', 'task_id', 'ok', 'detail'), r)) for r in rows]


# ---------------------------------------------------------------- sanitized events

def emit(db, project, kind, message, task_id=None, job_id=None, worker=None):
    """Record a display-safe event. Callers pass controller-authored text only, never model
    output, prompts, exception text or file paths."""
    with db:
        cur = db.execute('INSERT INTO sevents(at,project,task_id,job_id,worker,kind,message) '
                         'VALUES (?,?,?,?,?,?,?)',
                         (iso(), project, task_id, job_id, worker, kind[:40], message[:200]))
        if cur.lastrowid % 200 == 0:
            db.execute('DELETE FROM sevents WHERE id <= ?', (cur.lastrowid - EVENT_HISTORY_LIMIT,))
    return cur.lastrowid


def events_since(db, projects, cursor=0, limit=200):
    marks = ','.join('?' * len(projects)) or "''"
    rows = db.execute(f'SELECT id,at,project,task_id,job_id,worker,kind,message FROM sevents '
                      f"WHERE id>? AND (project='system' OR project IN ({marks})) ORDER BY id LIMIT ?",
                      (int(cursor), *projects, max(1, min(int(limit), 500)))).fetchall()
    oldest = db.execute('SELECT MIN(id) FROM sevents').fetchone()[0] or 0
    latest = db.execute('SELECT MAX(id) FROM sevents').fetchone()[0] or 0
    gap = bool(cursor) and oldest > int(cursor) + 1
    keys = ('id', 'at', 'project', 'task_id', 'job_id', 'worker', 'kind', 'message')
    return {'events': [dict(zip(keys, r)) for r in rows], 'latest': latest, 'resync': gap}


def set_worker_state(db, worker, state, project=None, task_id=None, job_id=None):
    if state not in WORKER_STATES:
        raise ValueError('Unknown worker state')
    with db:
        db.execute('INSERT INTO worker_state VALUES (?,?,?,?,?,?) ON CONFLICT(worker) DO UPDATE SET '
                   'state=excluded.state,project=excluded.project,task_id=excluded.task_id,'
                   'job_id=excluded.job_id,updated=excluded.updated',
                   (worker, state, project, task_id, job_id, iso()))


def worker_states(db):
    rows = db.execute('SELECT worker,state,project,task_id,job_id,updated FROM worker_state').fetchall()
    return {r[0]: dict(zip(('worker', 'state', 'project', 'task_id', 'job_id', 'updated'), r)) for r in rows}


# ---------------------------------------------------------------- mailbox

PRIORITIES = ('urgent', 'blocked', 'review', 'fyi')


def mail(db, project, priority, subject, body, task_id=None, dedupe_key=None):
    """Idempotent: an open item with the same key is updated instead of duplicated."""
    if priority not in PRIORITIES:
        raise ValueError('Unknown mailbox priority')
    key = dedupe_key or (str(task_id) + ':' + subject)
    now = iso()
    with db:
        row = db.execute('SELECT id,status FROM mailbox WHERE dedupe_key=?', (key,)).fetchone()
        if row and row[1] in ('open', 'reopened'):
            db.execute('UPDATE mailbox SET body=?, priority=?, updated=? WHERE id=?',
                       (body[:4000], priority, now, row[0]))
            return row[0]
        if row:  # resolved earlier; reopen with history preserved in audit
            db.execute("UPDATE mailbox SET body=?,priority=?,status='reopened',updated=?,response=NULL,"
                       'responded_by=NULL,responded_at=NULL WHERE id=?', (body[:4000], priority, now, row[0]))
            return row[0]
        mid = uuid.uuid4().hex
        db.execute('INSERT INTO mailbox VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   (mid, key, task_id, project, priority, subject[:200], body[:4000], 'open',
                    now, now, None, None, None))
        return mid


def resolve_mail_for_task(db, task_id, response, actor):
    with db:
        db.execute("UPDATE mailbox SET status='resolved', response=?, responded_by=?, responded_at=?, "
                   "updated=? WHERE task_id=? AND status IN ('open','reopened')",
                   (response[:2000], actor, iso(), iso(), task_id))


def mailbox_items(db, projects, include_resolved=False):
    marks = ','.join('?' * len(projects)) or "''"
    clause = '' if include_resolved else "AND status IN ('open','reopened')"
    rows = db.execute(f'SELECT id,task_id,project,priority,subject,body,status,created,updated,response '
                      f"FROM mailbox WHERE (project='system' OR project IN ({marks})) {clause} ORDER BY "
                      "CASE priority WHEN 'urgent' THEN 0 WHEN 'blocked' THEN 1 WHEN 'review' THEN 2 ELSE 3 END,"
                      ' updated DESC LIMIT 200', tuple(projects)).fetchall()
    keys = ('id', 'task_id', 'project', 'priority', 'subject', 'body', 'status', 'created', 'updated', 'response')
    return [dict(zip(keys, r)) for r in rows]


# ---------------------------------------------------------------- cloud invocations and routes

def digest(text):
    return hashlib.sha256((text or '').encode('utf-8', 'replace')).hexdigest()


def record_invocation(db, provider, requested_model, outcome, actual_models=None, cost_reported=None,
                      cost_evidence=None, duration_ms=None, task_id=None, job_id=None, purpose=None,
                      prompt=None, result=None):
    with db:
        db.execute('INSERT INTO invocations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   (uuid.uuid4().hex, iso(), task_id, job_id, purpose, provider, requested_model,
                    json.dumps(actual_models) if actual_models is not None else None,
                    json.dumps(cost_reported) if cost_reported is not None else None,
                    json.dumps(cost_evidence) if cost_evidence is not None else None,
                    duration_ms, outcome[:200], digest(prompt) if prompt else None,
                    digest(result) if result else None))


def invocations(db, limit=100, task_id=None):
    sql = ('SELECT at,task_id,job_id,purpose,provider,requested_model,actual_models,cost_reported,'
           'cost_evidence,duration_ms,outcome FROM invocations')
    args = ()
    if task_id:
        sql += ' WHERE task_id=?'
        args = (task_id,)
    rows = db.execute(sql + ' ORDER BY at DESC LIMIT ?', (*args, int(limit))).fetchall()
    keys = ('at', 'task_id', 'job_id', 'purpose', 'provider', 'requested_model', 'actual_models',
            'cost_reported', 'cost_evidence', 'duration_ms', 'outcome')
    out = []
    for r in rows:
        item = dict(zip(keys, r))
        for k in ('actual_models', 'cost_reported', 'cost_evidence'):
            item[k] = json.loads(item[k]) if item[k] else None
        out.append(item)
    return out


def route_key(route):
    return route.get('provider', '?') + ':' + route.get('model', '?')


def route_available(db, route):
    row = db.execute('SELECT cooldown_until FROM route_state WHERE route=?', (route_key(route),)).fetchone()
    until = parse(row[0]) if row else None
    return until is None or until <= utcnow()


def route_result(db, route, ok, error='', rate_limited=False, base_seconds=60, max_seconds=3600):
    """Success clears failures. Failure applies an exponential cooldown; rate limits start longer."""
    key = route_key(route)
    now = utcnow()
    row = db.execute('SELECT failures FROM route_state WHERE route=?', (key,)).fetchone()
    failures = 0 if ok else (row[0] if row else 0) + 1
    cooldown = None
    if not ok:
        seconds = min(max_seconds, base_seconds * (2 ** (failures - 1)) * (5 if rate_limited else 1))
        cooldown = iso(now + timedelta(seconds=seconds))
    with db:
        db.execute('INSERT INTO route_state(route,provider,model,cooldown_until,failures,last_ok,last_check,last_error) '
                   'VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(route) DO UPDATE SET cooldown_until=excluded.cooldown_until,'
                   'failures=excluded.failures,last_ok=COALESCE(excluded.last_ok,route_state.last_ok),'
                   'last_check=excluded.last_check,last_error=excluded.last_error',
                   (key, route.get('provider', '?'), route.get('model', '?'), cooldown, failures,
                    iso(now) if ok else None, iso(now), None if ok else error[:200]))


def route_pricing(db, route, ok, error=''):
    key = route_key(route)
    with db:
        db.execute('INSERT INTO route_state(route,provider,model,failures,last_check,pricing_ok,last_error) '
                   'VALUES (?,?,?,0,?,?,?) ON CONFLICT(route) DO UPDATE SET last_check=excluded.last_check,'
                   'pricing_ok=excluded.pricing_ok,last_error=COALESCE(excluded.last_error,route_state.last_error)',
                   (key, route.get('provider', '?'), route.get('model', '?'), iso(), int(bool(ok)),
                    None if ok else error[:200]))


def routes(db):
    rows = db.execute('SELECT route,provider,model,cooldown_until,failures,last_ok,last_check,last_error,'
                      'pricing_ok FROM route_state ORDER BY route').fetchall()
    keys = ('route', 'provider', 'model', 'cooldown_until', 'failures', 'last_ok', 'last_check',
            'last_error', 'pricing_ok')
    return [dict(zip(keys, r)) for r in rows]


# ---------------------------------------------------------------- health records

def record_health(db, name, ok, detail=''):
    now = iso()
    with db:
        db.execute('INSERT INTO health VALUES (?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET ok=excluded.ok,'
                   'detail=excluded.detail,checked=excluded.checked,'
                   'last_ok=COALESCE(excluded.last_ok,health.last_ok)',
                   (name, int(bool(ok)), str(detail)[:300], now, now if ok else None))


def health_rows(db):
    rows = db.execute('SELECT name,ok,detail,checked,last_ok FROM health ORDER BY name').fetchall()
    return [dict(zip(('name', 'ok', 'detail', 'checked', 'last_ok'), r)) for r in rows]


def grant_cloud_consent(db, project, actor, granted=True):
    set_setting(db, 'cloud_consent:' + project, {'granted': bool(granted), 'by': actor, 'at': iso()})
    audit(db, actor, 'cloud_consent.' + ('grant' if granted else 'revoke'), True, project=project)


# ---------------------------------------------------------------- task conversations

MESSAGE_ROLES = ('owner', 'assistant')


def post_message(db, task_id, project, role, text, author=None):
    """User-facing conversation only. Internal evidence (prompts, raw reviews) never goes here."""
    if role not in MESSAGE_ROLES:
        raise ValueError('Unknown message role')
    text = (text or '').strip()
    if not text or len(text) > 8000:
        raise ValueError('Message must be 1-8000 characters')
    with db:
        cur = db.execute('INSERT INTO messages(task_id,project,role,author,text,at) VALUES (?,?,?,?,?,?)',
                         (task_id, project, role, author, text, iso()))
    return cur.lastrowid


def task_messages(db, task_id, limit=500):
    rows = db.execute('SELECT id,role,author,text,at FROM messages WHERE task_id=? ORDER BY id LIMIT ?',
                      (task_id, limit)).fetchall()
    return [dict(zip(('id', 'role', 'author', 'text', 'at'), r)) for r in rows]


def search_messages(db, projects, query, limit=50):
    import re as _re
    words = _re.findall(r'\w+', query or '', _re.UNICODE)[:12]
    if not words or not projects:
        return []
    expr = ' OR '.join('"' + w + '"' for w in words)
    marks = ','.join('?' * len(projects))
    rows = db.execute(f'SELECT m.id,m.task_id,m.project,m.role,m.text,m.at FROM messages_fts f '
                      f'JOIN messages m ON m.id=f.rowid WHERE messages_fts MATCH ? AND m.project IN ({marks}) '
                      f'ORDER BY rank LIMIT ?', (expr, *projects, int(limit))).fetchall()
    return [dict(zip(('id', 'task_id', 'project', 'role', 'text', 'at'), r)) for r in rows]
