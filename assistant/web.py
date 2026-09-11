"""Private dashboard: task controls, live workforce view, mailbox, knowledge and system health.

Security model (see docs/assistant/DASHBOARD.md):
* Binds to loopback by default; a Tailscale address (100.64.0.0/10 or fd7a:115c:a1e0::/48) is the
  only other permitted bind. 0.0.0.0 and LAN/public addresses are refused.
* Password mode requires a session cookie (HttpOnly, SameSite=Strict) with idle and absolute
  expiry. An explicit open-access mode is available for the owner's private server page; it
  grants the configured local identity owner access without storing or requesting a password.
* Every mutation is POST, requires the per-session CSRF token header, an allowed Origin and an
  allowed Host (DNS-rebinding protection), and is written to the audit table.
* Each user has an explicit project list; every task, event, note, artifact and mailbox response
  is filtered by it. System controls (pause, gaming, cloud consent, backup) are owner-only.
* Responses never contain raw task JSON or private filesystem paths.
"""
from __future__ import annotations
import getpass
import hashlib
import hmac
import ipaddress
import json
import re
import secrets
import sys
import threading
import time
from datetime import timedelta
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from . import state, control, notes
from .core import Store, PROJECTS, runtime_root

STATIC = Path(__file__).resolve().parent / 'web_static'
OFFICE_TEMPLATE = Path(__file__).resolve().parents[1] / 'config' / 'assistant' / 'office.json'
COOKIE = 'ka_session'
MAX_BODY = 3_000_000   # allows one 2 MB attachment as base64
MAX_STREAMS = 8
PATH_RE = re.compile(r'([A-Za-z]:[\\/][^\s"\'`]*|/(?:home|Users|root|tmp|mnt|var|etc)/[^\s"\'`]*|\\\\[^\s"\'`]+)')

WEB_SCHEMA = '''
CREATE TABLE IF NOT EXISTS web_sessions (
  token_hash TEXT PRIMARY KEY, user TEXT NOT NULL, csrf TEXT NOT NULL, created TEXT NOT NULL,
  last_seen TEXT NOT NULL, expires TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS web_login_failures (user TEXT, ip TEXT, at TEXT);
'''


# ------------------------------------------------------------------ configuration and users

def config_path(root=None):
    return Path(root or runtime_root()) / 'dashboard.json'


def load_config(root=None):
    p = config_path(root)
    cfg = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    cfg.setdefault('users', {})
    cfg.setdefault('host', '127.0.0.1')
    cfg.setdefault('port', 8765)
    cfg.setdefault('session_hours', 12)
    cfg.setdefault('idle_minutes', 120)
    cfg.setdefault('extra_origins', [])
    cfg.setdefault('open_access', False)
    cfg.setdefault('open_user', 'kort')
    return cfg


def save_config(cfg, root=None):
    p = config_path(root)
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(cfg, indent=2), encoding='utf-8')
    tmp.replace(p)


def hash_password(password, salt=None, iterations=600_000):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), iterations).hex()
    return {'salt': salt, 'iterations': iterations, 'hash': digest}


def verify_password(user, password):
    if not user or 'hash' not in user:
        hash_password(password, iterations=600_000)  # equalize timing for unknown users
        return False
    calc = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(user['salt']), user['iterations']).hex()
    return hmac.compare_digest(calc, user['hash'])


def validate_bind(host):
    if host in ('127.0.0.1', 'localhost', '::1'):
        return
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        raise ValueError('Bind to 127.0.0.1 or this machine\'s Tailscale IP address')
    if ip in ipaddress.ip_network('100.64.0.0/10') or ip in ipaddress.ip_network('fd7a:115c:a1e0::/48'):
        return
    raise ValueError('Refusing to listen on %s: only loopback or a Tailscale address is allowed' % host)


def allowed_hosts(cfg):
    port = cfg['port']
    hosts = {'127.0.0.1:%d' % port, 'localhost:%d' % port, '[::1]:%d' % port}
    if cfg['host'] not in ('127.0.0.1', 'localhost', '::1'):
        hosts.add('%s:%d' % (cfg['host'], port))
    for origin in cfg.get('extra_origins', []):
        hosts.add(urlparse(origin).netloc)
    return hosts


def allowed_origins(cfg):
    return {'http://' + h for h in allowed_hosts(cfg)} | {'https://' + h for h in allowed_hosts(cfg)} | \
        set(cfg.get('extra_origins', []))


# ------------------------------------------------------------------ sanitizing

def redact(value):
    """Remove filesystem paths (Windows, POSIX, UNC) from any string that goes to the browser."""
    if isinstance(value, str):
        return PATH_RE.sub('[path]', value)
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    return value


def task_summary(t):
    jobs = t['data'].get('jobs', [])
    counts = {}
    for j in jobs:
        counts[j['status']] = counts.get(j['status'], 0) + 1
    return {'id': t['id'], 'project': t['project'], 'subproject': t['subproject'], 'goal': t['goal'][:300],
            'status': t['status'], 'updated': t['updated'], 'jobs': counts, 'after': t['data'].get('after', []),
            'retry': t['data'].get('retry'), 'waiting': sorted({j['waiting'] for j in jobs if j.get('waiting')})}


def _review(review):
    if not isinstance(review, dict):
        return None
    checks = [{'criterion': str(c.get('criterion', ''))[:500], 'passed': c.get('passed') is True,
               'evidence': str(c.get('evidence', ''))[:2000]}
              for c in review.get('checks', []) if isinstance(c, dict)][:20]
    return redact({'approved': review.get('approved') is True, 'checks': checks,
                   'cause': str(review.get('cause', ''))[:1500] if review.get('cause') else None,
                   'repairs': [str(r)[:800] for r in review.get('repairs', [])][:10]
                   if isinstance(review.get('repairs'), list) else [],
                   'summary': str(review.get('summary', ''))[:1500] if review.get('summary') else None})


def _route(route):
    if not isinstance(route, dict):
        return None
    return {k: route.get(k) for k in ('provider', 'model', 'actual_models', 'device') if route.get(k) is not None}


def task_detail(store, t, profiles, projects):
    data = t['data']
    deps = []
    for dep in data.get('after', []):
        try:
            other = store.get(dep)
            deps.append({'id': dep, 'goal': other['goal'][:120], 'status': other['status']}
                        if other['project'] in projects else {'id': dep, 'status': 'unknown'})
        except ValueError:
            deps.append({'id': dep, 'status': 'missing'})
    jobs = []
    for j in data.get('jobs', []):
        prof = profiles.get(j.get('worker'), {})
        jobs.append(redact({
            'id': j['id'], 'worker': j.get('worker'), 'worker_name': prof.get('name', j.get('worker')),
            'brief': j.get('brief', '')[:4000], 'acceptance': j.get('acceptance', []),
            'depends_on': j.get('depends_on', []), 'status': j.get('status'), 'attempts': j.get('attempts', 0),
            'max_attempts': j.get('max_attempts'), 'waiting': j.get('waiting'), 'reason': j.get('reason'),
            'last_error': j.get('last_error'), 'has_artifact': bool(j.get('artifact')),
            'code': bool(j.get('workspace')), 'checks_passed': j.get('checks_passed'),
            'test_results': [{'command': ' '.join(map(str, r.get('argv', [])))[:300], 'passed': r.get('passed') is True,
                              'output': str(r.get('output', r.get('error', '')))[-2000:]}
                             for r in j.get('test_results', []) if isinstance(r, dict)][:20],
            'review': _review(j.get('review')), 'review_rounds': len(j.get('review_history', [])),
            'owner_instructions': j.get('owner_instructions', []),
            'execution_route': _route(j.get('execution_route')), 'review_route': _route(j.get('review_route'))}))
    return {**task_summary(t), 'goal': t['goal'], 'dependencies': deps, 'job_list': jobs,
            'blocker': redact(data.get('blocker')), 'export': data.get('export'),
            'questions': data.get('questions', []), 'assumptions': data.get('assumptions', []),
            'confirm_plan': bool(data.get('confirm_plan')),
            'has_code': any(j.get('workspace') for j in data.get('jobs', [])), 'last_error': redact(data.get('last_error')),
            'plan_route': _route(data.get('plan_route')), 'owner_decision': redact(data.get('owner_decision')),
            'integration_review': _review((data.get('integration_review') or {}).get('review')),
            'invocations': [{k: v for k, v in i.items() if k != 'task_id'}
                            for i in state.invocations(store.db, 50, t['id'])],
            'events': [dict(zip(('id', 'at', 'kind', 'message', 'job_id', 'worker'), e)) for e in store.db.execute(
                'SELECT id,at,kind,message,job_id,worker FROM sevents WHERE task_id=? ORDER BY id DESC LIMIT 60',
                (t['id'],)).fetchall()]}


# ------------------------------------------------------------------ HTTP handler

class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class App:
    def __init__(self, root=None, profiles_loader=None):
        self.root = Path(root or runtime_root())
        self.cfg = load_config(self.root)
        validate_bind(self.cfg['host'])
        self.hosts = allowed_hosts(self.cfg)
        self.origins = allowed_origins(self.cfg)
        self.open_csrf = secrets.token_urlsafe(24)
        self.streams = threading.BoundedSemaphore(MAX_STREAMS)
        if profiles_loader is None:
            def profiles_loader():
                p = self.root / 'workers.json'
                return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
        self.profiles_loader = profiles_loader
        s = self.store()
        s.db.executescript(WEB_SCHEMA)
        s.close()

    def store(self):
        s = Store(self.root)
        s.db.executescript(WEB_SCHEMA)
        return s

    def office(self):
        path = self.root / 'office.json'
        try:
            data = json.loads((path if path.exists() else OFFICE_TEMPLATE).read_text(encoding='utf-8'))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}


class Handler(BaseHTTPRequestHandler):
    app: App = None
    server_version = 'KortAssistant'
    sys_version = ''

    def log_message(self, fmt, *args):  # no request logging of query strings or cookies
        pass

    # ---- low level
    def _send(self, status, body=b'', ctype='application/json', headers=None):
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; "
                         "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; "
                         "form-action 'self'")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def _json(self, obj, status=200, headers=None):
        self._send(status, json.dumps(obj, default=str).encode(), headers=headers)

    def _body(self):
        n = int(self.headers.get('Content-Length') or 0)
        if n > MAX_BODY:
            raise ApiError(413, 'Request too large')
        raw = self.rfile.read(n) if n else b'{}'
        try:
            data = json.loads(raw or b'{}')
        except ValueError:
            raise ApiError(400, 'Invalid JSON')
        if not isinstance(data, dict):
            raise ApiError(400, 'Expected an object')
        return data

    def _client_ip(self):
        return self.client_address[0]

    def _check_host(self):
        if self.headers.get('Host') not in self.app.hosts:
            raise ApiError(421, 'Host not allowed')

    def _check_origin(self):
        origin = self.headers.get('Origin')
        if origin is None or origin not in self.app.origins:
            raise ApiError(403, 'Origin not allowed')
        if self.headers.get('Sec-Fetch-Site') not in (None, 'same-origin', 'none'):
            raise ApiError(403, 'Cross-site request refused')

    def _session(self, store, required=True):
        if self.app.cfg.get('open_access'):
            return {'user': str(self.app.cfg.get('open_user') or 'kort')[:64],
                    'csrf': self.app.open_csrf, 'projects': list(PROJECTS), 'owner': True,
                    'token_hash': None, 'open_access': True}
        cookie = SimpleCookie(self.headers.get('Cookie') or '')
        token = cookie[COOKIE].value if COOKIE in cookie else None
        if not token:
            if required:
                raise ApiError(401, 'Sign in required')
            return None
        th = hashlib.sha256(token.encode()).hexdigest()
        row = store.db.execute('SELECT user,csrf,last_seen,expires FROM web_sessions WHERE token_hash=?',
                               (th,)).fetchone()
        now = state.utcnow()
        if not row or state.parse(row[3]) <= now or \
                state.parse(row[2]) + timedelta(minutes=self.app.cfg['idle_minutes']) <= now:
            if row:
                with store.db:
                    store.db.execute('DELETE FROM web_sessions WHERE token_hash=?', (th,))
            if required:
                raise ApiError(401, 'Session expired; sign in again')
            return None
        user = self.app.cfg['users'].get(row[0])
        if not user:
            raise ApiError(401, 'Unknown user')
        with store.db:
            store.db.execute('UPDATE web_sessions SET last_seen=? WHERE token_hash=?', (state.iso(), th))
        projects = [p for p in user.get('projects', []) if p in PROJECTS]
        return {'user': row[0], 'csrf': row[1], 'projects': projects, 'owner': user.get('role') == 'owner',
                'token_hash': th, 'open_access': False}

    def _require_csrf(self, sess):
        sent = self.headers.get('X-CSRF-Token') or ''
        if not hmac.compare_digest(sent, sess['csrf']):
            raise ApiError(403, 'Missing or invalid CSRF token')

    # ---- dispatch
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        self._dispatch('GET')

    def do_POST(self):
        self._dispatch('POST')

    def _dispatch(self, method):
        store = None
        try:
            self._check_host()
            url = urlparse(self.path)
            path = url.path
            query = {k: v[-1] for k, v in parse_qs(url.query).items()}
            if method == 'GET' and (path == '/' or path.startswith('/static/')):
                return self._static(path)
            if not path.startswith('/api/'):
                raise ApiError(404, 'Not found')
            store = self.app.store()
            if method == 'POST':
                self._check_origin()
                body = self._body()
                if path == '/api/login':
                    return self._login(store, body)
                sess = self._session(store)
                self._require_csrf(sess)
                return self._post(store, sess, path, body)
            sess = self._session(store, required=path != '/api/me')
            if path == '/api/me':
                return self._json({'signed_in': bool(sess), 'user': sess and sess['user'],
                                   'projects': sess and sess['projects'], 'owner': bool(sess and sess['owner']),
                                   'csrf': sess and sess['csrf'],
                                   'open_access': bool(sess and sess.get('open_access'))})
            if path == '/api/stream':
                store.close()
                store = None
                return self._stream(sess, query)
            return self._get(store, sess, path, query)
        except ApiError as e:
            self._json({'error': str(e)}, e.status)
        except PermissionError as e:
            self._json({'error': str(e) or 'Not allowed'}, 403)
        except (ValueError, KeyError) as e:
            self._json({'error': redact(str(e))[:300]}, 400)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as e:
            self._json({'error': 'Internal error (' + type(e).__name__ + ')'}, 500)
        finally:
            if store is not None:
                store.close()

    def _static(self, path):
        name = 'index.html' if path == '/' else path[len('/static/'):]
        if not re.fullmatch(r'[a-z0-9-]+\.(html|js|css|svg)', name):
            raise ApiError(404, 'Not found')
        p = STATIC / name
        if not p.is_file():
            raise ApiError(404, 'Not found')
        ctype = {'html': 'text/html; charset=utf-8', 'js': 'text/javascript; charset=utf-8',
                 'css': 'text/css; charset=utf-8', 'svg': 'image/svg+xml'}[name.rsplit('.', 1)[1]]
        self._send(200, p.read_bytes(), ctype)

    # ---- auth
    def _login(self, store, body):
        if self.app.cfg.get('open_access'):
            raise ApiError(400, 'Password sign-in is disabled for this dashboard')
        name = str(body.get('user', ''))[:64]
        password = str(body.get('password', ''))[:256]
        ip = self._client_ip()
        since = state.iso(state.utcnow() - timedelta(minutes=15))
        failures = store.db.execute('SELECT COUNT(*) FROM web_login_failures WHERE (user=? OR ip=?) AND at>=?',
                                    (name, ip, since)).fetchone()[0]
        if failures >= 5:
            state.audit(store.db, name or '?', 'login.locked', False, detail='ip ' + ip)
            raise ApiError(429, 'Too many failed sign-ins; wait 15 minutes')
        user = self.app.cfg['users'].get(name)
        if not verify_password(user, password):
            with store.db:
                store.db.execute('INSERT INTO web_login_failures VALUES (?,?,?)', (name, ip, state.iso()))
            state.audit(store.db, name or '?', 'login', False, detail='ip ' + ip)
            raise ApiError(401, 'Wrong user name or password')
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(24)
        now = state.utcnow()
        with store.db:
            store.db.execute('DELETE FROM web_sessions WHERE expires<=?', (state.iso(now),))
            store.db.execute('INSERT INTO web_sessions VALUES (?,?,?,?,?,?)',
                             (hashlib.sha256(token.encode()).hexdigest(), name, csrf, state.iso(now), state.iso(now),
                              state.iso(now + timedelta(hours=self.app.cfg['session_hours']))))
            store.db.execute('DELETE FROM web_login_failures WHERE user=?', (name,))
        state.audit(store.db, name, 'login', True, detail='ip ' + ip)
        cookie = '%s=%s; HttpOnly; SameSite=Strict; Path=/; Max-Age=%d' % (
            COOKIE, token, int(self.app.cfg['session_hours'] * 3600))
        if self.app.cfg.get('secure_cookie'):
            cookie += '; Secure'
        self._json({'ok': True, 'csrf': csrf}, headers={'Set-Cookie': cookie})

    # ---- reads
    def _get(self, store, sess, path, q):
        projects = sess['projects']
        profiles = self.app.profiles_loader()
        if path == '/api/overview':
            return self._json(overview(store, sess, profiles, self.app.office()))
        if path == '/api/tasks':
            want = q.get('project')
            tasks = [task_summary(t) for t in store.list() if t['project'] in projects
                     and (not want or t['project'] == want)]
            return self._json({'tasks': tasks[:500]})
        m = re.fullmatch(r'/api/tasks/([0-9a-f]{32})', path)
        if m:
            t = store.get(m.group(1))
            if t['project'] not in projects:
                raise ApiError(404, 'Unknown task')
            return self._json(task_detail(store, t, profiles, projects))
        m = re.fullmatch(r'/api/tasks/([0-9a-f]{32})/artifact/([A-Za-z0-9]+)', path)
        if m:
            return self._artifact(store, sess, m.group(1), m.group(2), q.get('download') == '1')
        m = re.fullmatch(r'/api/tasks/([0-9a-f]{32})/messages', path)
        if m:
            t = store.get(m.group(1))
            if t['project'] not in projects:
                raise ApiError(404, 'Unknown task')
            from .conversation import list_attachments
            return self._json({'messages': redact(state.task_messages(store.db, t['id'])),
                               'attachments': list_attachments(store.db, t['id'])})
        if path == '/api/search':
            return self._json({'results': redact(state.search_messages(store.db, projects, q.get('q', '')))})
        if path == '/api/events':
            return self._json(state.events_since(store.db, projects, int(q.get('cursor') or 0)))
        if path == '/api/mailbox':
            return self._json({'items': redact(state.mailbox_items(store.db, projects,
                                                                   q.get('all') == '1'))})
        if path == '/api/audit':
            return self._json({'rows': redact(state.audit_rows(store.db, projects, 200))})
        if path == '/api/notes':
            return self._json({'notes': notes.list_notes(self.app.root / 'vault', projects, q.get('q', ''))})
        if path == '/api/note':
            n = notes.read(self.app.root / 'vault', projects, q.get('path', ''))
            return self._json(n)
        if path == '/api/note/revision':
            return self._json({'text': notes.read_revision(self.app.root / 'vault', projects, q.get('path', ''),
                                                           q.get('revision', ''))})
        raise ApiError(404, 'Not found')

    def _artifact(self, store, sess, tid, jid, download):
        t = store.get(tid)
        if t['project'] not in sess['projects']:
            raise ApiError(404, 'Unknown task')
        job = next((j for j in t['data'].get('jobs', []) if j['id'] == jid), None)
        if not job or not job.get('artifact'):
            raise ApiError(404, 'No artifact')
        base = (self.app.root / 'artifacts' / tid).resolve()
        p = Path(job['artifact']).resolve()
        if base not in p.parents or not p.is_file():
            raise ApiError(404, 'No artifact')
        raw = p.read_bytes()
        verified = hashlib.sha256(raw).hexdigest() == job.get('digest')
        headers = {'X-Digest-Verified': 'yes' if verified else 'NO'}
        if download:
            headers['Content-Disposition'] = 'attachment; filename="%s-%s-%s.md"' % (tid[:8], jid, job.get('attempts'))
        state.audit(store.db, 'web:' + sess['user'], 'artifact.' + ('download' if download else 'view'), True,
                    project=t['project'], task_id=tid, detail='job ' + jid)
        self._send(200, raw[:5_000_000], 'text/plain; charset=utf-8', headers)

    # ---- mutations
    def _post(self, store, sess, path, body):
        actor = 'web:' + sess['user']
        projects = sess['projects']
        owner = sess['owner']
        vault = self.app.root / 'vault'

        def owner_only():
            if not owner:
                state.audit(store.db, actor, 'denied:' + path, False)
                raise ApiError(403, 'Owner only')

        try:
            if path == '/api/logout':
                if sess['token_hash']:
                    with store.db:
                        store.db.execute('DELETE FROM web_sessions WHERE token_hash=?', (sess['token_hash'],))
                state.audit(store.db, actor, 'logout', True)
                return self._json({'ok': True}, headers={'Set-Cookie': COOKIE + '=; Max-Age=0; Path=/'})
            if path == '/api/control/pause':
                owner_only(); control.pause(store, actor); return self._json({'ok': True})
            if path == '/api/control/resume':
                owner_only(); control.resume(store, actor); return self._json({'ok': True})
            if path == '/api/control/gaming':
                owner_only()
                return self._json(redact(control.gaming(store, actor, bool(body.get('on')), self.app.profiles_loader(),
                                                        bool(body.get('cancel_active')))))
            if path == '/api/control/consent':
                owner_only()
                control.consent(store, actor, str(body.get('project')), bool(body.get('grant')))
                return self._json({'ok': True})
            if path == '/api/control/backup':
                owner_only()
                from . import backup
                target = backup.create(self.app.root)
                state.audit(store.db, actor, 'backup.create', True, detail=target.name)
                return self._json({'ok': True, 'file': target.name})
            if path == '/api/tasks':
                after = body.get('after') or []
                if not isinstance(after, list):
                    raise ValueError('after must be a list of task IDs')
                tid = control.add_task(store, actor, projects, str(body.get('project')), str(body.get('goal', '')),
                                       str(body.get('subproject', '')), [str(a) for a in after],
                                       confirm_plan=bool(body.get('confirm_plan')))
                return self._json({'id': tid})
            m = re.fullmatch(r'/api/tasks/([0-9a-f]{32})/(cancel|retry|approve|reject|repair)', path)
            if m:
                tid, action = m.groups()
                if action == 'cancel':
                    control.cancel(store, actor, projects, tid)
                elif action == 'retry':
                    control.retry(store, actor, projects, tid)
                elif action in ('approve', 'reject'):
                    control.decide(store, actor, projects, tid, action == 'approve', str(body.get('note', '')))
                else:
                    control.request_repair(store, actor, projects, tid, str(body.get('job', '')),
                                           str(body.get('instructions', '')))
                return self._json({'ok': True})
            m = re.fullmatch(r'/api/tasks/([0-9a-f]{32})/(messages|attachments|plan)', path)
            if m:
                from . import conversation
                tid, kind = m.groups()
                if kind == 'messages':
                    return self._json({'result': conversation.owner_message(store, actor, projects, tid,
                                                                            str(body.get('text', '')))})
                if kind == 'attachments':
                    return self._json({'id': conversation.add_attachment(store, actor, projects, tid,
                                                                         str(body.get('name', '')),
                                                                         str(body.get('content', '')))})
                conversation.approve_plan(store, actor, projects, tid, bool(body.get('approve')),
                                          str(body.get('note', '')))
                return self._json({'ok': True})
            m = re.fullmatch(r'/api/tasks/([0-9a-f]{32})/export', path)
            if m:
                owner_only()
                from . import export
                from .run import configuration
                result = export.export(store, configuration(), m.group(1), actor)
                return self._json({'ok': True, 'applies': result['applies'], 'patches': result['patches'],
                                   'base': result['base'], 'head': result['head']})
            m = re.fullmatch(r'/api/mailbox/([0-9a-f]{32})/answer', path)
            if m:
                control.answer_mail(store, actor, projects, m.group(1), str(body.get('response', '')))
                return self._json({'ok': True})
            if path == '/api/note':
                rel = str(body.get('path', ''))
                digest = notes.save(vault, projects, rel, str(body.get('text', '')), sess['user'],
                                    body.get('digest'), owner)
                state.audit(store.db, actor, 'note.save', True, project=rel.split('/')[0], detail=rel)
                store.index(vault)
                return self._json({'ok': True, 'digest': digest})
            if path == '/api/note/status':
                rel = str(body.get('path', ''))
                notes.set_status(vault, projects, rel, str(body.get('status', '')), sess['user'], owner,
                                 str(body.get('reason', '')), str(body.get('superseded_by', '')))
                state.audit(store.db, actor, 'note.status.' + str(body.get('status')), True,
                            project=rel.split('/')[0], detail=rel)
                store.index(vault)
                return self._json({'ok': True})
            if path == '/api/note/propose-skill':
                rel = str(body.get('path', ''))
                target = notes.propose_skill(vault, projects, rel, sess['user'], owner)
                state.audit(store.db, actor, 'note.propose_skill', True, project=rel.split('/')[0], detail=target)
                return self._json({'ok': True, 'path': target})
        except (ValueError, PermissionError, control.Forbidden) as e:
            state.audit(store.db, actor, 'failed:' + path, False, detail=redact(str(e)))
            raise
        raise ApiError(404, 'Not found')

    # ---- server-sent events
    def _stream(self, sess, q):
        if not self.app.streams.acquire(blocking=False):
            raise ApiError(503, 'Too many open dashboards')
        try:
            cursor = int(self.headers.get('Last-Event-ID') or q.get('cursor') or 0)
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(b'retry: 3000\n\n')
            deadline = time.monotonic() + 25   # short-lived; the browser reconnects with Last-Event-ID
            while time.monotonic() < deadline:
                store = self.app.store()
                try:
                    if not self._session(store, required=False):
                        self.wfile.write(b'event: auth\ndata: {}\n\n')
                        return
                    batch = state.events_since(store.db, sess['projects'], cursor, 200)
                finally:
                    store.close()
                if batch['resync']:
                    self.wfile.write(('event: resync\ndata: {"latest": %d}\n\n' % batch['latest']).encode())
                    cursor = batch['latest']
                for e in batch['events']:
                    cursor = e['id']
                    self.wfile.write(('id: %d\nevent: evt\ndata: %s\n\n' % (e['id'], json.dumps(e))).encode())
                self.wfile.write(('event: beat\ndata: {"at": "%s", "cursor": %d}\n\n' % (state.iso(), cursor)).encode())
                self.wfile.flush()
                time.sleep(1.0)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            self.app.streams.release()


def overview(store, sess, profiles, office=None):
    from . import gpu
    db = store.db
    states = state.worker_states(db)
    workforce = []
    display_workers = (office or {}).get('workers', {})
    for name, p in profiles.items():
        if not set(p.get('projects', [])) & set(sess['projects']):
            continue
        s = states.get(name, {})
        current = s.get('state')
        if current is None:
            # Missing instrumentation is unknown, and untested roles are not "idle".
            current = 'idle' if p.get('qualified') is True or str(p.get('adapter', '')).startswith('cloud') \
                else 'unavailable'
        task = s.get('task_id') if s.get('project') in sess['projects'] else None
        display = display_workers.get(name, {}) if isinstance(display_workers.get(name, {}), dict) else {}
        workforce.append({'id': name, 'name': p.get('name', name), 'adapter': p.get('adapter'),
                          'device': gpu.device_of(p), 'model': p.get('model'), 'state': current,
                          'task_id': task, 'job_id': s.get('job_id') if task else None, 'updated': s.get('updated'),
                          'qualified': p.get('qualified') is True,
                          'projects': sorted(set(p.get('projects', [])) & set(sess['projects'])),
                          'display': redact({k: str(display.get(k, ''))[:40] for k in ('callsign', 'room', 'palette')})})
    for special in ('orchestrator', 'reviewer'):
        s = states.get(special, {})
        task = s.get('task_id') if s.get('project') in sess['projects'] else None
        display = display_workers.get(special, {}) if isinstance(display_workers.get(special, {}), dict) else {}
        workforce.insert(0 if special == 'orchestrator' else 1,
                         {'id': special, 'name': special.title() + ' (cloud)', 'adapter': 'cloud', 'device': 'cloud',
                          'state': s.get('state', 'idle'), 'task_id': task,
                          'job_id': s.get('job_id') if task else None, 'updated': s.get('updated'),
                          'qualified': True, 'projects': sorted(sess['projects']),
                          'display': redact({k: str(display.get(k, ''))[:40] for k in ('callsign', 'room', 'palette')})})
    runner = state.lease_info(db, 'runner')
    beat = state.parse(state.get_setting(db, 'runner.heartbeat'))
    runner_state = 'offline'
    if runner and beat and (state.utcnow() - beat).total_seconds() < 180:
        runner_state = 'running'
    elif runner:
        runner_state = 'stale'
    day = state.utcnow().date().isoformat()
    usage = [dict(zip(('provider', 'calls'), r)) for r in
             db.execute('SELECT provider, calls FROM usage WHERE day=?', (day,)).fetchall()]
    since = state.iso(state.utcnow() - timedelta(hours=24))
    outcomes = [dict(zip(('provider', 'model', 'outcome', 'count'), r)) for r in db.execute(
        'SELECT provider, requested_model, outcome, COUNT(*) FROM invocations WHERE at>=? GROUP BY 1,2,3',
        (since,)).fetchall()]
    consent = {p: state.cloud_consent(db, p) for p in sess['projects']}
    return {'paused': state.is_paused(db) or (store.root / 'PAUSE').exists(), 'gaming': gpu.gaming(db),
            'gpu_lease': bool(gpu.lease_holder(db)), 'runner': runner_state,
            'runner_heartbeat': beat.isoformat() if beat else None,
            'workforce': workforce, 'health': redact(state.health_rows(db)), 'routes': redact(state.routes(db)),
            'usage_today': usage, 'invocations_24h': outcomes, 'consent': consent,
            'mailbox_open': len(state.mailbox_items(db, sess['projects'])),
            'latest_event': db.execute('SELECT MAX(id) FROM sevents').fetchone()[0] or 0,
            'server_time': state.iso()}


def serve(root=None):
    app = App(root)
    if not app.cfg.get('open_access') and not app.cfg['users']:
        raise SystemExit('No dashboard users. Run: python -m assistant.web user add <name> --owner')
    Handler.app = app
    httpd = ThreadingHTTPServer((app.cfg['host'], app.cfg['port']), Handler)
    httpd.daemon_threads = True
    print('Dashboard on http://%s:%d (Ctrl+C to stop)' % (app.cfg['host'], app.cfg['port']))
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description='Private assistant dashboard')
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('serve')
    u = sub.add_parser('user')
    usub = u.add_subparsers(dest='action', required=True)
    add = usub.add_parser('add')
    add.add_argument('name')
    add.add_argument('--projects', default=','.join(PROJECTS))
    add.add_argument('--owner', action='store_true')
    rm = usub.add_parser('remove')
    rm.add_argument('name')
    h = sub.add_parser('bind')
    h.add_argument('host')
    h.add_argument('--port', type=int)
    access = sub.add_parser('access')
    access.add_argument('mode', choices=('open', 'password'))
    access.add_argument('--user', default='kort')
    a = p.parse_args(argv)
    if a.cmd == 'serve':
        return serve()
    cfg = load_config()
    if a.cmd == 'bind':
        validate_bind(a.host)
        cfg['host'] = a.host
        if a.port:
            cfg['port'] = a.port
        save_config(cfg)
        print('Dashboard will listen on %s:%d' % (cfg['host'], cfg['port']))
        return
    if a.cmd == 'access':
        cfg['open_access'] = a.mode == 'open'
        cfg['open_user'] = str(a.user)[:64] or 'kort'
        save_config(cfg)
        print('Dashboard access is %s%s' %
              (a.mode, ' as ' + cfg['open_user'] if a.mode == 'open' else ''))
        return
    if a.action == 'remove':
        cfg['users'].pop(a.name, None)
        save_config(cfg)
        return
    projects = [x for x in a.projects.split(',') if x]
    if any(x not in PROJECTS for x in projects):
        raise SystemExit('Projects must be among ' + ', '.join(PROJECTS))
    password = getpass.getpass('Password for %s (12+ characters): ' % a.name)
    if len(password) < 12 or password != getpass.getpass('Repeat: '):
        raise SystemExit('Passwords must match and be at least 12 characters')
    cfg['users'][a.name] = {**hash_password(password), 'projects': projects,
                            'role': 'owner' if a.owner else 'member'}
    save_config(cfg)
    print('Saved user %s with projects %s' % (a.name, ', '.join(projects)))


if __name__ == '__main__':
    main(sys.argv[1:])
