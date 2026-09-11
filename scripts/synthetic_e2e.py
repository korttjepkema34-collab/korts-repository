"""Process-level synthetic acceptance run. No real model, provider or private data is used.

It starts the real runner as a separate process against a throwaway runtime, with:
  * a fake `claude` executable that answers planning/review prompts in Claude Code's JSON format,
  * a fake Ollama HTTP server for the local worker,
then checks: planning, work, review rejection and repair, completion, cancellation, pause,
forced kill (-9) and restart without duplicate work or lost results, a second runner being refused,
mailbox items, and backup/restore into a clean folder.

Run on the server after setup:  python scripts/synthetic_e2e.py
Exit code 0 means every check passed; results are printed. Nothing touches your real runtime."""
from __future__ import annotations
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

FAKE_CLAUDE = r'''
import json, sys, pathlib, time
args = sys.argv[1:]
model = args[args.index('--model') + 1]
prompt = sys.stdin.read()
state = pathlib.Path(__file__).with_name('fake_state.json')
seen = json.loads(state.read_text()) if state.exists() else {}
def out(result):
    print(json.dumps({"subtype": "success", "is_error": False, "result": json.dumps(result),
                      "modelUsage": {model: {"inputTokens": 1}}, "total_cost_usd": 0}))
if 'AVAILABLE WORKER PROFILES' in prompt:
    time.sleep(0.5)
    out({"assumptions": ["synthetic"], "jobs": [
        {"id": "a", "worker": "writer", "brief": "first part", "acceptance": ["mentions alpha"], "depends_on": []},
        {"id": "b", "worker": "writer", "brief": "second part", "acceptance": ["mentions beta"], "depends_on": ["a"]}]})
else:
    data = json.loads(prompt[prompt.rindex('\n{'):])
    job = data['job']
    key = data['goal'][:20] + ':' + job['id']
    seen[key] = seen.get(key, 0) + 1
    state.write_text(json.dumps(seen))
    reject = 'REPAIR' in data['goal'] and seen[key] == 1
    out({"approved": not reject, "checks": [{"criterion": c, "passed": not reject,
         "evidence": "synthetic check of artifact"} for c in job['acceptance']],
         "repairs": ["add the missing word"] if reject else [], "cause": "synthetic"})
'''


class FakeOllama(BaseHTTPRequestHandler):
    calls = 0
    def log_message(self, *a):
        pass
    def _json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass   # the runner was killed mid-request on purpose
    def do_GET(self):
        self._json({'version': 'synthetic'} if self.path == '/api/version' else {'models': []})
    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0)
        payload = json.loads(self.rfile.read(n) or b'{}')
        if self.path == '/api/chat':
            FakeOllama.calls += 1
            time.sleep(1.5)   # long enough to be interrupted
            text = payload['messages'][1]['content']
            self._json({'message': {'content': 'Draft with alpha and beta. ' + ('(repaired)' if 'repair' in text else '')},
                        'eval_count': 5, 'eval_duration': 1e8})
        else:
            self._json({})


def main():
    results = []
    def check(name, ok, detail=''):
        results.append((name, bool(ok), detail))
        print(('PASS ' if ok else 'FAIL ') + name + (' — ' + detail if detail else ''))

    tmp = Path(tempfile.mkdtemp(prefix='assistant-e2e-'))
    home = tmp / 'runtime'
    home.mkdir()
    bindir = tmp / 'bin'
    bindir.mkdir()
    (bindir / 'fake_claude.py').write_text(FAKE_CLAUDE)
    if os.name == 'nt':
        claude = bindir / 'claude.cmd'
        claude.write_text('@"%s" "%s" %%*\n' % (sys.executable, bindir / 'fake_claude.py'))
    else:
        claude = bindir / 'claude'
        claude.write_text('#!/bin/sh\nexec "%s" "%s" "$@"\n' % (sys.executable, bindir / 'fake_claude.py'))
        claude.chmod(0o755)
    ollama = ThreadingHTTPServer(('127.0.0.1', 0), FakeOllama)
    threading.Thread(target=ollama.serve_forever, daemon=True).start()
    port = ollama.server_address[1]
    config = json.loads((REPO / 'config/assistant/config.example.json').read_text())
    config.update({'claude_bin': str(claude), 'poll_seconds': 1, 'retry_base_seconds': 1,
                   'cloud_routes': [{'provider': 'ollama-cloud', 'model': 'synthetic:cloud', 'qualified': True,
                                     'included_usage_confirmed': True}],
                   'allow_cloud_context': {'personal': True, 'business': True, 'game': True},
                   'min_free_disk_gb': 0})
    (home / 'config.json').write_text(json.dumps(config))
    (home / 'workers.json').write_text(json.dumps({'writer': {
        'name': 'Writer', 'description': 'Writes drafts', 'projects': ['personal', 'business', 'game'],
        'adapter': 'ollama-draft', 'endpoint': 'http://127.0.0.1:%d' % port, 'model': 'synthetic-4b',
        'device': 'cpu', 'qualified': True, 'instructions': 'Write.', 'skills': []}}))
    env = dict(os.environ, ASSISTANT_HOME=str(home), PYTHONPATH=str(REPO))
    py = [sys.executable, '-m']
    def cli(*args):
        return subprocess.run(py + ['assistant.run', *args], cwd=REPO, env=env, capture_output=True, text=True, timeout=60)

    for p in ('personal', 'business', 'game'):
        cli('consent', p, '--grant')
    ok_task = cli('add', 'game', 'Write alpha beta note').stdout.strip()
    repair_task = cli('add', 'business', 'REPAIR path: write alpha beta').stdout.strip()
    cancel_task = cli('add', 'personal', 'This task will be cancelled').stdout.strip()
    check('tasks created', all(len(t) == 32 for t in (ok_task, repair_task, cancel_task)))
    cli('cancel', cancel_task)

    from assistant.core import Store
    def status():
        s = Store(home)
        try:
            return {t['id']: t for t in s.list()}
        finally:
            s.close()

    runner = subprocess.Popen(py + ['assistant.runner'], cwd=REPO, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(3)
    second = subprocess.run(py + ['assistant.runner', '--once'], cwd=REPO, env=env, capture_output=True, text=True, timeout=60)
    check('second runner refused', second.returncode != 0 and 'Another runner is active' in second.stderr)
    # Wait until a worker call is in flight, then kill the runner hard.
    deadline = time.time() + 60
    while time.time() < deadline and FakeOllama.calls < 1:
        time.sleep(0.2)
    time.sleep(0.3)
    if os.name == 'nt':
        runner.kill()
    else:
        runner.send_signal(signal.SIGKILL)
    runner.wait(timeout=30)
    before = status()
    check('runner killed mid-work', any(j['status'] == 'running' for t in before.values() for j in t['data'].get('jobs', [])),
          'a job was left in running state')
    runner = subprocess.Popen(py + ['assistant.runner'], cwd=REPO, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    deadline = time.time() + 240
    while time.time() < deadline:
        st = status()
        if st[ok_task]['status'] == 'draft_ready' and st[repair_task]['status'] == 'draft_ready':
            break
        time.sleep(1)
    st = status()
    check('normal task completed', st[ok_task]['status'] == 'draft_ready', st[ok_task]['status'])
    check('rejected draft repaired then accepted', st[repair_task]['status'] == 'draft_ready' and
          any(len(j.get('review_history', [])) == 2 for j in st[repair_task]['data']['jobs']), st[repair_task]['status'])
    check('cancelled task never ran', st[cancel_task]['status'] == 'cancelled' and not st[cancel_task]['data'].get('jobs'))
    arts = [Path(j['artifact']) for t in st.values() for j in t['data'].get('jobs', []) if j.get('artifact')]
    check('artifacts exist after restart', arts and all(a.exists() for a in arts), '%d artifacts' % len(arts))
    s = Store(home)
    try:
        from assistant import state
        mail = state.mailbox_items(s.db, ['personal', 'business', 'game'])
        check('review mailbox items', sum(1 for m in mail if m['priority'] == 'review') >= 2)
        resumed = s.db.execute("SELECT COUNT(*) FROM sevents WHERE kind='resume'").fetchone()[0]
        check('interruption recorded as resume', resumed >= 1)
        calls = s.db.execute("SELECT COUNT(*), SUM(outcome='ok') FROM invocations").fetchone()
        check('cloud calls recorded with outcome', calls[0] and calls[0] == calls[1], '%s calls' % calls[0])
        state.set_setting(s.db, 'paused', True)
    finally:
        s.close()
    paused_task = cli('add', 'game', 'Added while paused').stdout.strip()
    time.sleep(4)
    check('pause stops new work', status()[paused_task]['status'] == 'planned')
    runner.terminate()
    try:
        runner.wait(timeout=30)
    except subprocess.TimeoutExpired:
        runner.kill()
    backup = subprocess.run(py + ['assistant.backup', 'create'], cwd=REPO, env=env, capture_output=True, text=True, timeout=120)
    archive = backup.stdout.strip()
    restored = tmp / 'restored'
    rest = subprocess.run(py + ['assistant.backup', 'restore', archive, str(restored)], cwd=REPO, env=env,
                          capture_output=True, text=True, timeout=120)
    ok = rest.returncode == 0 and json.loads(rest.stdout)['tasks'] == 4
    check('backup restores to clean folder', ok, rest.stderr[-300:] if not ok else '')
    ollama.shutdown()
    failed = [r for r in results if not r[1]]
    print('\n%d/%d checks passed. Temporary runtime: %s' % (len(results) - len(failed), len(results), tmp))
    if not failed:
        shutil.rmtree(tmp, ignore_errors=True)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
