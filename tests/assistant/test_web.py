"""Dashboard security and behavior tests against a real HTTP server on loopback."""
import http.client
import json
import tempfile
import threading
import unittest
from datetime import timedelta
from http.server import ThreadingHTTPServer
from pathlib import Path
from assistant import web, state, control
from assistant.core import Store, PROJECTS
from test_runtime import FakeCloud, PLAN, REVIEW_OK, grant
from assistant.runner import process_task


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cfg = web.load_config(cls.root)
        cfg['users'] = {'kort': {**web.hash_password('correct horse battery', iterations=1000),
                                 'projects': list(PROJECTS), 'role': 'owner'},
                        'helper': {**web.hash_password('helper password 1', iterations=1000),
                                   'projects': ['game'], 'role': 'member'}}
        cfg['port'] = 0
        web.save_config(cfg, cls.root)
        cls.profiles = {'writer': {'name': 'Writer', 'description': 'W', 'projects': list(PROJECTS),
                                   'adapter': 'ollama-draft', 'skills': [], 'instructions': 'x',
                                   'endpoint': 'http://127.0.0.1:11434', 'model': 'qwen3.5:4b'}}
        app = web.App(cls.root, profiles_loader=lambda: cls.profiles)
        cls.httpd = ThreadingHTTPServer(('127.0.0.1', 0), type('H', (web.Handler,), {'app': app}))
        cls.port = cls.httpd.server_address[1]
        app.cfg['port'] = cls.port
        app.hosts = web.allowed_hosts(app.cfg)
        app.origins = web.allowed_origins(app.cfg)
        cls.origin = 'http://127.0.0.1:%d' % cls.port
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        # A finished business task with an artifact whose text contains a private path.
        s = Store(cls.root)
        grant(s)
        cfgr = {'allow_cloud_context': {p: True for p in PROJECTS}, 'max_worker_attempts': 3}
        cls.biz = s.create('business', 'Private invoice fix')
        cloud = FakeCloud([PLAN, REVIEW_OK])
        for _ in range(4):
            process_task(s, s.get(cls.biz), cfgr, cls.profiles, cloud=cloud,
                         worker_call=lambda *a: 'Draft mentions C:\\Users\\kort\\secret\\ledger.xlsx')
        cls.game = s.create('game', 'Game task')
        t = s.get(cls.game)
        s.update(cls.game, 'blocked', {'blocker': 'failed reading /home/kort/private/file.txt'})
        (cls.root / 'vault/business').mkdir(parents=True)
        (cls.root / 'vault/business/prices.md').write_text('---\nstatus: proposed\n---\nbusiness secret [[other]]')
        (cls.root / 'vault/game').mkdir(parents=True)
        (cls.root / 'vault/game/lore.md').write_text('---\nstatus: proposed\n---\ngame lore')
        (cls.root / 'vault/game/other.md').write_text('links to [[lore]]')
        s.close()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.tmp.cleanup()

    def req(self, method, path, body=None, cookie=None, csrf=None, origin='default', host=None):
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        headers = {'Host': host or '127.0.0.1:%d' % self.port}
        if body is not None:
            headers['Content-Type'] = 'application/json'
        if origin == 'default':
            origin = self.origin if method == 'POST' else None
        if origin:
            headers['Origin'] = origin
        if cookie:
            headers['Cookie'] = cookie
        if csrf:
            headers['X-CSRF-Token'] = csrf
        c.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
        r = c.getresponse()
        raw = r.read()
        c.close()
        try:
            data = json.loads(raw)
        except ValueError:
            data = raw.decode('utf-8', 'replace')
        return r.status, data, r

    def login(self, user='kort', password='correct horse battery'):
        status, data, r = self.req('POST', '/api/login', {'user': user, 'password': password})
        self.assertEqual(status, 200, data)
        cookie = r.getheader('Set-Cookie').split(';')[0]
        self.assertIn('HttpOnly', r.getheader('Set-Cookie'))
        self.assertIn('SameSite=Strict', r.getheader('Set-Cookie'))
        return cookie, data['csrf']

    def test_static_page_has_security_headers(self):
        status, body, r = self.req('GET', '/')
        self.assertEqual(status, 200)
        text = body.decode('utf-8') if isinstance(body, bytes) else body
        self.assertIn('The Night Shift', text)
        self.assertIn('SIMULATED PREVIEW', text)
        self.assertIn('id="office-project"', text)
        self.assertIn("script-src 'self'", r.getheader('Content-Security-Policy'))
        self.assertEqual(r.getheader('X-Frame-Options'), 'DENY')
        self.assertEqual(self.req('GET', '/static/../web.py')[0], 404)

    def test_unauthenticated_api_is_refused(self):
        for path in ('/api/overview', '/api/tasks', '/api/tasks/' + self.biz, '/api/notes', '/api/events'):
            self.assertEqual(self.req('GET', path)[0], 401, path)
        self.assertEqual(self.req('POST', '/api/control/pause', {})[0], 401)

    def test_wrong_password_and_lockout(self):
        for _ in range(5):
            self.assertEqual(self.req('POST', '/api/login', {'user': 'ghost', 'password': 'x'})[0], 401)
        self.assertEqual(self.req('POST', '/api/login', {'user': 'ghost', 'password': 'x'})[0], 429)

    def test_csrf_origin_and_host_are_enforced(self):
        cookie, csrf = self.login()
        self.assertEqual(self.req('POST', '/api/control/pause', {}, cookie)[0], 403)            # no CSRF token
        self.assertEqual(self.req('POST', '/api/control/pause', {}, cookie, 'bad')[0], 403)     # wrong token
        self.assertEqual(self.req('POST', '/api/control/pause', {}, cookie, csrf, origin='http://evil.example')[0], 403)
        self.assertEqual(self.req('POST', '/api/control/pause', {}, cookie, csrf, origin=None)[0], 403)
        self.assertEqual(self.req('GET', '/api/overview', cookie=cookie, host='evil.example:80')[0], 421)
        self.assertEqual(self.req('POST', '/api/control/pause', {}, cookie, csrf)[0], 200)
        self.assertEqual(self.req('POST', '/api/control/resume', {}, cookie, csrf)[0], 200)
        s = Store(self.root)
        try:
            actions = [r['action'] for r in state.audit_rows(s.db, PROJECTS, 50)]
        finally:
            s.close()
        self.assertIn('pause', actions)
        self.assertIn('resume', actions)

    def test_project_isolation_for_member(self):
        cookie, csrf = self.login('helper', 'helper password 1')
        overview = self.req('GET', '/api/overview', cookie=cookie)[1]
        self.assertTrue(all(set(w['projects']) <= {'game'} for w in overview['workforce']))
        status, data, _ = self.req('GET', '/api/tasks', cookie=cookie)
        self.assertEqual({t['project'] for t in data['tasks']}, {'game'})
        self.assertEqual(self.req('GET', '/api/tasks/' + self.biz, cookie=cookie)[0], 404)
        self.assertEqual(self.req('GET', '/api/tasks/%s/artifact/j1' % self.biz, cookie=cookie)[0], 404)
        self.assertEqual(self.req('POST', '/api/tasks/%s/cancel' % self.biz, {}, cookie, csrf)[0], 400)
        self.assertEqual(self.req('POST', '/api/tasks', {'project': 'business', 'goal': 'x'}, cookie, csrf)[0], 403)
        self.assertEqual(self.req('GET', '/api/note?path=business/prices.md', cookie=cookie)[0], 403)
        notes = self.req('GET', '/api/notes', cookie=cookie)[1]['notes']
        self.assertTrue(all(not n['path'].startswith('business') for n in notes))
        events = self.req('GET', '/api/events', cookie=cookie)[1]['events']
        self.assertTrue(all(e['project'] in ('game', 'system') for e in events))
        self.assertEqual(self.req('POST', '/api/control/pause', {}, cookie, csrf)[0], 403)   # owner only
        self.assertEqual(self.req('POST', '/api/control/consent', {'project': 'game', 'grant': True}, cookie, csrf)[0], 403)

    def test_no_raw_data_or_private_paths_reach_browser(self):
        cookie, _ = self.login()
        status, detail, _ = self.req('GET', '/api/tasks/' + self.game, cookie=cookie)
        self.assertEqual(status, 200)
        blob = json.dumps(detail)
        self.assertNotIn('/home/kort', blob)
        self.assertIn('[path]', blob)
        biz = self.req('GET', '/api/tasks/' + self.biz, cookie=cookie)[1]
        self.assertNotIn('"data"', json.dumps(biz))
        self.assertNotIn('artifacts', json.dumps(biz))   # artifact file paths are never sent
        self.assertEqual(biz['job_list'][0]['review']['checks'][0]['passed'], True)

    def test_artifact_preview_and_download(self):
        cookie, _ = self.login()
        status, body, r = self.req('GET', '/api/tasks/%s/artifact/j1' % self.biz, cookie=cookie)
        self.assertEqual(status, 200)
        self.assertEqual(r.getheader('X-Digest-Verified'), 'yes')
        self.assertTrue(r.getheader('Content-Type').startswith('text/plain'))
        status, body, r = self.req('GET', '/api/tasks/%s/artifact/j1?download=1' % self.biz, cookie=cookie)
        self.assertIn('attachment', r.getheader('Content-Disposition'))

    def test_owner_controls_round_trip(self):
        cookie, csrf = self.login()
        tid = self.req('POST', '/api/tasks', {'project': 'game', 'goal': 'New thing'}, cookie, csrf)[1]['id']
        self.assertEqual(self.req('POST', '/api/tasks/%s/cancel' % tid, {}, cookie, csrf)[0], 200)
        ov = self.req('GET', '/api/overview', cookie=cookie)[1]
        self.assertIn('workforce', ov)
        writer = next(w for w in ov['workforce'] if w['id'] == 'writer')
        self.assertIn(writer['state'], ('idle', 'unavailable'))
        self.assertEqual(writer['projects'], sorted(PROJECTS))
        inbox = self.req('GET', '/api/mailbox', cookie=cookie)[1]['items']
        self.assertTrue(any(i['priority'] == 'review' for i in inbox))

    def test_note_edit_keeps_history_and_rejects_stale(self):
        cookie, csrf = self.login()
        note = self.req('GET', '/api/note?path=game/lore.md', cookie=cookie)[1]
        self.assertEqual(note['backlinks'], ['game/other.md'])
        ok = self.req('POST', '/api/note', {'path': 'game/lore.md', 'text': note['text'] + '\nmore', 'digest': note['digest']},
                      cookie, csrf)
        self.assertEqual(ok[0], 200, ok[1])
        stale = self.req('POST', '/api/note', {'path': 'game/lore.md', 'text': 'x', 'digest': note['digest']}, cookie, csrf)
        self.assertEqual(stale[0], 400)
        again = self.req('GET', '/api/note?path=game/lore.md', cookie=cookie)[1]
        self.assertEqual(len(again['revisions']), 1)
        self.assertEqual(self.req('POST', '/api/note', {'path': '../escape.md', 'text': 'x'}, cookie, csrf)[0], 400)
        wrong = self.req('POST', '/api/note', {'path': 'game/x.md', 'text': '---\nproject: business\n---\nx'}, cookie, csrf)
        self.assertEqual(wrong[0], 400)

    def test_session_expiry(self):
        cookie, csrf = self.login()
        s = Store(self.root)
        try:
            with s.db:
                s.db.execute('UPDATE web_sessions SET last_seen=?', (state.iso(state.utcnow() - timedelta(days=1)),))
        finally:
            s.close()
        self.assertEqual(self.req('GET', '/api/overview', cookie=cookie)[0], 401)

    def test_bind_validation(self):
        for good in ('127.0.0.1', '100.101.102.103'):
            web.validate_bind(good)
        for bad in ('0.0.0.0', '192.168.1.20', '8.8.8.8', 'example.com'):
            with self.assertRaises(ValueError):
                web.validate_bind(bad)


class OpenAccessWebTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        cfg = web.load_config(self.root)
        cfg.update({'open_access': True, 'open_user': 'kort', 'port': 0})
        web.save_config(cfg, self.root)
        self.app = web.App(self.root, profiles_loader=lambda: {})
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), type('H', (web.Handler,), {'app': self.app}))
        self.port = self.httpd.server_address[1]
        self.app.cfg['port'] = self.port
        self.app.hosts = web.allowed_hosts(self.app.cfg)
        self.app.origins = web.allowed_origins(self.app.cfg)
        self.origin = 'http://127.0.0.1:%d' % self.port
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.tmp.cleanup()

    def req(self, method, path, body=None, csrf=None, origin=None):
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        headers = {'Host': '127.0.0.1:%d' % self.port}
        if body is not None:
            headers['Content-Type'] = 'application/json'
        if origin:
            headers['Origin'] = origin
        if csrf:
            headers['X-CSRF-Token'] = csrf
        c.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
        r = c.getresponse()
        raw = r.read()
        c.close()
        return r.status, json.loads(raw)

    def test_open_access_is_owner_without_cookie_and_keeps_csrf_origin_checks(self):
        status, me = self.req('GET', '/api/me')
        self.assertEqual(status, 200)
        self.assertEqual(me['user'], 'kort')
        self.assertTrue(me['signed_in'])
        self.assertTrue(me['owner'])
        self.assertTrue(me['open_access'])
        self.assertEqual(me['projects'], list(PROJECTS))
        self.assertEqual(self.req('GET', '/api/overview')[0], 200)
        self.assertEqual(self.req('POST', '/api/control/pause', {}, origin=self.origin)[0], 403)
        self.assertEqual(self.req('POST', '/api/control/pause', {}, me['csrf'], 'http://evil.example')[0], 403)
        self.assertEqual(self.req('POST', '/api/control/pause', {}, me['csrf'], self.origin)[0], 200)
        self.assertEqual(self.req('POST', '/api/control/resume', {}, me['csrf'], self.origin)[0], 200)
        self.assertEqual(self.req('POST', '/api/login', {}, origin=self.origin)[0], 400)


if __name__ == '__main__':
    unittest.main()
