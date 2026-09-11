"""Offline tests for the persistent runner, owner controls, events, GPU gaming mode, cloud evidence
checks, health monitoring and backup/restore."""
import json
import os
import sqlite3
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from assistant import state, control, gpu, backup, health
from assistant.core import Store, PROJECTS
from assistant.models import Cloud, CloudUnavailable, parse_json
from assistant.runner import Runner, process_task, runnable, recover
from test_assistant import FakeCloud

REVIEW_OK = {'approved': True, 'checks': [{'criterion': 'one line', 'passed': True, 'evidence': 'A line.'}]}
PLAN = {'jobs': [{'id': 'j1', 'worker': 'writer', 'brief': 'Draft a line', 'acceptance': ['one line'], 'depends_on': []}]}


def grant(store):
    for p in PROJECTS:
        state.grant_cloud_consent(store.db, p, 'test')


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.s = Store(self.root)
        grant(self.s)
        self.cfg = {'allow_cloud_context': {p: True for p in PROJECTS}, 'max_worker_attempts': 2,
                    'poll_seconds': 0, 'retry_base_seconds': 60}
        self.profiles = {'writer': {'description': 'Writer', 'projects': list(PROJECTS), 'adapter': 'ollama-draft',
                                    'skills': [], 'instructions': 'x', 'endpoint': 'http://127.0.0.1:11434'}}

    def tearDown(self):
        self.s.close()
        self.tmp.cleanup()

    def run_steps(self, tid, cloud, n, worker=lambda *a: 'A line.'):
        for _ in range(n):
            process_task(self.s, self.s.get(tid), self.cfg, self.profiles, cloud=cloud, worker_call=worker)


class RunnerTests(Base):
    def test_single_runner_lease(self):
        r1 = Runner(self.cfg, self.s, profiles_loader=lambda: self.profiles)
        r1.start()
        other = Store(self.root)
        try:
            r2 = Runner(self.cfg, other, profiles_loader=lambda: self.profiles)
            with self.assertRaises(RuntimeError):
                r2.start()
        finally:
            other.close()
            r1.stop()
        self.assertFalse((self.root / 'runner.lock').exists())

    def test_dead_local_runner_lease_is_reclaimed(self):
        with self.s.db:
            self.s.db.execute("INSERT INTO leases VALUES ('runner','old',999999999,?,?,?,?)",
                              (__import__('socket').gethostname(), state.iso(), state.iso(),
                               state.iso(state.utcnow() + timedelta(hours=1))))
        r = Runner(self.cfg, self.s, profiles_loader=lambda: self.profiles)
        r.start()
        r.stop()

    def test_task_lease_prevents_duplicate_step(self):
        tid = self.s.create('game', 'Draft')
        self.assertTrue(state.acquire_lease(self.s.db, 'task:' + tid, 'someone-else', 600))
        out = process_task(self.s, self.s.get(tid), self.cfg, self.profiles, cloud=FakeCloud([]))
        self.assertEqual(out, 'leased')
        self.assertEqual(self.s.get(tid)['status'], 'planned')

    def test_full_pipeline_through_runner_and_mailbox(self):
        tid = self.s.create('game', 'Draft a dialogue')
        cloud = FakeCloud([PLAN, REVIEW_OK])
        r = Runner(self.cfg, self.s, profiles_loader=lambda: self.profiles, cloud=cloud,
                   worker_call=lambda *a: 'A line.', sleep=lambda s: None)
        r.maintenance = lambda: None
        r.start()
        try:
            for _ in range(4):
                r.pass_once()
        finally:
            r.stop()
        self.assertEqual(self.s.get(tid)['status'], 'draft_ready')
        mail = state.mailbox_items(self.s.db, ['game'])
        self.assertEqual([m['priority'] for m in mail], ['review'])
        kinds = [e['kind'] for e in state.events_since(self.s.db, ['game'])['events']]
        for k in ('task.created', 'plan.start', 'assign', 'work.start', 'handoff', 'review.start',
                  'review.accepted', 'task.draft_ready'):
            self.assertIn(k, kinds)

    def test_cloud_outage_uses_bounded_cooldown_then_blocks(self):
        tid = self.s.create('game', 'Draft')
        self.cfg['max_task_retries'] = 2
        down = FakeCloud([CloudUnavailable('x')] * 10)
        self.run_steps(tid, down, 1)
        t = self.s.get(tid)
        self.assertEqual(t['status'], 'awaiting_cloud')
        self.assertEqual(t['data']['retry']['count'], 1)
        self.assertFalse(runnable(self.s, t))   # cooling down
        for _ in range(2):
            t = self.s.get(tid)
            t['data']['retry']['next_at'] = state.iso(state.utcnow() - timedelta(seconds=1))
            self.s.save_data(tid, t['data'])
            self.run_steps(tid, down, 1)
        self.assertEqual(self.s.get(tid)['status'], 'blocked')
        self.assertEqual(state.mailbox_items(self.s.db, ['game'])[0]['priority'], 'blocked')

    def test_progress_resets_retry_counter(self):
        tid = self.s.create('game', 'Draft')
        self.run_steps(tid, FakeCloud([CloudUnavailable('x')]), 1)
        t = self.s.get(tid)
        t['data']['retry']['next_at'] = state.iso(state.utcnow() - timedelta(seconds=1))
        self.s.save_data(tid, t['data'])
        self.run_steps(tid, FakeCloud([PLAN]), 1)
        self.assertNotIn('retry', self.s.get(tid)['data'])

    def test_task_dependencies_order_and_isolation(self):
        first = self.s.create('game', 'First')
        second = self.s.create('game', 'Second', after=[first])
        with self.assertRaises(ValueError):
            self.s.create('business', 'Cross project', after=[first])
        self.assertFalse(runnable(self.s, self.s.get(second)))
        self.assertEqual(self.s.get(second)['status'], 'waiting_dependency')
        self.s.update(first, 'draft_ready', {})
        self.assertTrue(runnable(self.s, self.s.get(second)))
        self.assertEqual(self.s.get(second)['status'], 'planned')

    def test_cancelled_dependency_blocks_dependent(self):
        first = self.s.create('game', 'First')
        second = self.s.create('game', 'Second', after=[first])
        control.cancel(self.s, 'kort', PROJECTS, first)
        self.assertFalse(runnable(self.s, self.s.get(second)))
        self.assertEqual(self.s.get(second)['status'], 'blocked')

    def test_resume_after_interruption(self):
        tid = self.s.create('game', 'Draft')
        self.run_steps(tid, FakeCloud([PLAN]), 1)
        t = self.s.get(tid)
        t['data']['jobs'][0]['status'] = 'running'
        t['data']['jobs'][0]['attempts'] = 1
        self.s.update(tid, 'working', t['data'])
        state.set_worker_state(self.s.db, 'writer', 'working', 'game', tid, 'j1')
        self.assertEqual(recover(self.s), 1)
        self.assertEqual(state.worker_states(self.s.db)['writer']['state'], 'idle')
        self.run_steps(tid, FakeCloud([REVIEW_OK]), 3)
        self.assertEqual(self.s.get(tid)['status'], 'draft_ready')
        self.assertEqual(self.s.get(tid)['data']['jobs'][0]['attempts'], 2)

    def test_consent_required_per_project(self):
        state.grant_cloud_consent(self.s.db, 'business', 'kort', False)
        tid = self.s.create('business', 'Draft')
        self.run_steps(tid, FakeCloud([]), 1)
        self.assertEqual(self.s.get(tid)['status'], 'blocked')
        self.assertIn('consent', self.s.get(tid)['data']['blocker'])

    def test_pause_setting_stops_passes(self):
        tid = self.s.create('game', 'Draft')
        control.pause(self.s, 'kort')
        r = Runner(self.cfg, self.s, profiles_loader=lambda: self.profiles, cloud=FakeCloud([]))
        r.start()
        try:
            self.assertEqual(r.pass_once(), 0)
        finally:
            r.stop()
        self.assertEqual(self.s.get(tid)['status'], 'planned')
        control.resume(self.s, 'kort')
        self.assertFalse(state.is_paused(self.s.db))


class ControlTests(Base):
    def ready(self):
        tid = self.s.create('game', 'Draft')
        self.run_steps(tid, FakeCloud([PLAN, REVIEW_OK]), 4)
        self.assertEqual(self.s.get(tid)['status'], 'draft_ready')
        return tid

    def test_cancel_cannot_be_overwritten_by_runner(self):
        tid = self.s.create('game', 'Draft')
        control.cancel(self.s, 'kort', PROJECTS, tid)
        self.assertFalse(self.s.update(tid, 'working', {}))
        self.assertEqual(self.s.get(tid)['status'], 'cancelled')

    def test_approve_binds_digests_and_is_audited(self):
        tid = self.ready()
        control.decide(self.s, 'kort', PROJECTS, tid, True, 'looks good')
        t = self.s.get(tid)
        self.assertEqual(t['status'], 'owner_approved')
        self.assertIn('j1', t['data']['owner_decision']['artifact_digests'])
        self.assertEqual(state.audit_rows(self.s.db, PROJECTS)[0]['action'], 'task.approve')
        self.assertEqual(state.mailbox_items(self.s.db, PROJECTS), [])

    def test_repair_with_instructions_reaches_worker(self):
        tid = self.ready()
        control.request_repair(self.s, 'kort', PROJECTS, tid, 'j1', 'Make it rhyme')
        prompts = []
        self.run_steps(tid, FakeCloud([]), 1, worker=lambda p, prompt: prompts.append(prompt) or 'A rhyme.')
        self.assertIn('Make it rhyme', prompts[0])
        job = self.s.get(tid)['data']['jobs'][0]
        self.assertEqual(job['attempts'], 2)
        self.assertTrue(job['artifact'].endswith('j1-2.md'))

    def test_retry_keeps_artifact_numbering(self):
        tid = self.s.create('game', 'Draft')
        self.run_steps(tid, FakeCloud([PLAN]), 1)
        def fail(*a):
            raise RuntimeError('down')
        self.run_steps(tid, FakeCloud([]), 1, fail)
        t = self.s.get(tid)
        t['data'].pop('retry', None)
        self.s.save_data(tid, t['data'])
        self.run_steps(tid, FakeCloud([]), 1, fail)
        self.assertEqual(self.s.get(tid)['data']['jobs'][0]['status'], 'blocked')
        control.retry(self.s, 'kort', PROJECTS, tid)
        self.s.update(tid, 'working', self.s.get(tid)['data'])
        self.run_steps(tid, FakeCloud([]), 1)
        job = self.s.get(tid)['data']['jobs'][0]
        self.assertEqual(job['attempts'], 3)
        self.assertEqual(job['status'], 'awaiting_review')

    def test_cross_project_control_denied(self):
        tid = self.s.create('business', 'Private')
        with self.assertRaises(ValueError):
            control.cancel(self.s, 'guest', ['game'], tid)
        with self.assertRaises(control.Forbidden):
            control.add_task(self.s, 'guest', ['game'], 'business', 'x')


class EventTests(Base):
    def test_events_are_scoped_and_contain_no_private_detail(self):
        a = self.s.create('business', 'SECRET-GOAL')
        self.s.update(a, 'blocked', {}, detail='C:/Users/kort/secret/path failed')
        self.s.create('game', 'Visible')
        game_events = state.events_since(self.s.db, ['game'])['events']
        self.assertTrue(all(e['project'] in ('game', 'system') for e in game_events))
        blob = json.dumps(state.events_since(self.s.db, PROJECTS))
        self.assertNotIn('SECRET-GOAL', blob)
        self.assertNotIn('secret/path', blob)

    def test_cursor_gap_requests_resync(self):
        for i in range(5):
            state.emit(self.s.db, 'game', 'x', 'msg')
        with self.s.db:
            self.s.db.execute('DELETE FROM sevents WHERE id < 4')
        self.assertTrue(state.events_since(self.s.db, ['game'], cursor=1)['resync'])
        self.assertFalse(state.events_since(self.s.db, ['game'], cursor=4)['resync'])

    def test_event_history_is_bounded(self):
        old = state.EVENT_HISTORY_LIMIT
        state.EVENT_HISTORY_LIMIT = 100
        try:
            for i in range(450):
                state.emit(self.s.db, 'game', 'x', 'm')
            count = self.s.db.execute('SELECT COUNT(*) FROM sevents').fetchone()[0]
            self.assertLessEqual(count, 350)
        finally:
            state.EVENT_HISTORY_LIMIT = old

    def test_mailbox_is_idempotent(self):
        a = state.mail(self.s.db, 'game', 'blocked', 'S', 'b1', task_id='t', dedupe_key='k')
        b = state.mail(self.s.db, 'game', 'blocked', 'S', 'b2', task_id='t', dedupe_key='k')
        self.assertEqual(a, b)
        self.assertEqual(len(state.mailbox_items(self.s.db, ['game'])), 1)


class GpuTests(Base):
    def setUp(self):
        super().setUp()
        self.profiles['coder'] = {'description': 'Coder', 'projects': ['game'], 'adapter': 'ollama-draft',
                                  'skills': [], 'instructions': 'x', 'endpoint': 'http://127.0.0.1:11435',
                                  'model': 'qwen3.5:9b'}
        self.loaded = [{'name': 'qwen3.5:9b', 'size_vram': 9_000_000_000}]

    def fetch(self, url, payload=None, timeout=10):
        if url.endswith('/api/ps'):
            return {'models': list(self.loaded)}
        if url.endswith('/api/generate') and payload.get('keep_alive') == 0:
            self.loaded = [m for m in self.loaded if m['name'] != payload['model']]
            return {}
        if url.endswith('/api/version'):
            return {'version': '0.test'}
        raise AssertionError(url)

    def test_gaming_unloads_and_confirms_vram(self):
        report = gpu.enter_gaming(self.s.db, self.profiles, fetch=self.fetch)
        self.assertEqual(report['vram'], 'released')
        self.assertFalse(gpu.acquire(self.s.db, 'job'))
        self.assertEqual(state.worker_states(self.s.db)['coder']['state'], 'unavailable')
        gpu.exit_gaming(self.s.db, self.profiles, fetch=self.fetch)
        self.assertTrue(gpu.acquire(self.s.db, 'job'))

    def test_unconfirmed_unload_is_reported(self):
        def broken(url, payload=None, timeout=10):
            raise OSError('tunnel down')
        self.assertEqual(gpu.enter_gaming(self.s.db, self.profiles, fetch=broken)['vram'], 'unconfirmed')

    def test_active_job_keeps_lease_until_it_finishes(self):
        self.assertTrue(gpu.acquire(self.s.db, 'task:1'))
        report = gpu.enter_gaming(self.s.db, self.profiles, fetch=self.fetch)
        self.assertEqual(report['vram'], 'waiting_for_active_job')
        report = gpu.enter_gaming(self.s.db, self.profiles, fetch=self.fetch, cancel_active=True)
        self.assertEqual(report['vram'], 'waiting_for_active_job')
        self.assertIsNotNone(gpu.lease_holder(self.s.db))
        self.assertFalse(report['cancel_requested'])

    def test_exclusive_lease_between_llm_and_media(self):
        self.assertTrue(gpu.acquire(self.s.db, 'llm-job', 'llm'))
        self.assertFalse(gpu.acquire(self.s.db, 'comfy-job', 'media'))
        gpu.release(self.s.db, 'llm-job')
        self.assertTrue(gpu.acquire(self.s.db, 'comfy-job', 'media'))

    def test_gaming_mode_job_waits_without_spending_attempts(self):
        plan = {'jobs': [{'id': 'j1', 'worker': 'coder', 'brief': 'b', 'acceptance': ['one line'], 'depends_on': []}]}
        tid = self.s.create('game', 'Draft')
        self.run_steps(tid, FakeCloud([plan]), 1)
        state.set_setting(self.s.db, 'gaming_mode', True)
        calls = []
        self.run_steps(tid, FakeCloud([]), 3, worker=lambda *a: calls.append(1) or 'x')
        job = self.s.get(tid)['data']['jobs'][0]
        self.assertEqual((job['attempts'], job['status'], job['waiting']), (0, 'pending', 'gaming'))
        self.assertEqual(calls, [])

    def test_offline_tunnel_job_waits(self):
        from assistant import run
        prof = self.profiles['coder']
        reason = run.local_gate(self.s, self.cfg, prof, 'coder', 'game', 't', 'j',
                                health=lambda e: (False, 'URLError'))
        self.assertEqual(reason, 'offline')
        self.assertEqual(state.worker_states(self.s.db)['coder']['state'], 'offline')

    def test_unqualified_role_is_unavailable_when_required(self):
        from assistant import run
        self.cfg['require_qualified_workers'] = True
        self.assertEqual(run.local_gate(self.s, self.cfg, self.profiles['writer'], 'writer', 'game', 't', 'j'),
                         'unqualified')
        self.profiles['writer']['qualified'] = True
        self.assertIsNone(run.local_gate(self.s, self.cfg, self.profiles['writer'], 'writer', 'game', 't', 'j'))


class CloudEvidenceTests(Base):
    ROUTE = {'provider': 'openrouter', 'model': 'inclusionai/ling-test:free', 'qualified': True}

    def cloud(self, wrapper, usage=(0, 0), returncode=0, stderr=''):
        def fetch(url, payload=None, headers=None, timeout=30):
            if url.endswith('/models'):
                return {'data': [{'id': self.ROUTE['model'], 'pricing': {'prompt': '0', 'completion': '0'}}]}
            if url.endswith('/chat/completions'):
                if returncode:
                    raise RuntimeError(stderr or str(wrapper.get('result', 'request failed')))
                return wrapper
            raise AssertionError(url)

        def runner(cmd, **kw):
            return SimpleNamespace(returncode=returncode, stdout=json.dumps(wrapper), stderr=stderr)
        cfg = {'cloud_routes': [dict(self.ROUTE)], 'daily_caps': {'openrouter': 100}}
        os.environ['OPENROUTER_API_KEY'] = 'test-key'
        return Cloud(cfg, self.s, fetch=fetch, runner=runner)

    def tearDown(self):
        os.environ.pop('OPENROUTER_API_KEY', None)
        super().tearDown()

    def ok_wrapper(self, model=None, cost=0):
        return {'model': model or self.ROUTE['model'], 'usage': {'cost': cost},
                'choices': [{'message': {'content': '{"ok": true}'}}]}

    def test_zero_cost_pinned_model_is_accepted_and_recorded(self):
        result, prov = self.cloud(self.ok_wrapper()).ask('p')
        self.assertEqual(result, {'ok': True})
        self.assertEqual(prov['cost_evidence']['delta'], '0')
        rec = state.invocations(self.s.db)[0]
        self.assertEqual((rec['outcome'], rec['actual_models']), ('ok', [self.ROUTE['model']]))
        self.assertEqual(rec['cost_evidence']['method'], 'response_usage')

    def test_model_substitution_rejected(self):
        with self.assertRaises(CloudUnavailable):
            self.cloud(self.ok_wrapper('anthropic/claude-haiku')).ask('p')
        self.assertEqual(state.invocations(self.s.db)[0]['outcome'], 'rejected_model_substitution')
        self.assertFalse(state.route_available(self.s.db, self.ROUTE))

    def test_missing_model_evidence_rejected(self):
        w = self.ok_wrapper()
        w.pop('model')
        with self.assertRaises(CloudUnavailable):
            self.cloud(w).ask('p')

    def test_nonzero_cost_rejected(self):
        with self.assertRaises(CloudUnavailable):
            self.cloud(self.ok_wrapper(cost=0.0001)).ask('p')
        self.assertEqual(state.invocations(self.s.db)[0]['outcome'], 'rejected_cost_nonzero')

    def test_rate_limit_sets_longer_cooldown(self):
        with self.assertRaises(CloudUnavailable):
            self.cloud({}, returncode=1, stderr='Error 429 Too Many Requests').ask('p')
        self.assertEqual(state.invocations(self.s.db)[0]['outcome'], 'rate_limited')
        until = state.parse(state.routes(self.s.db)[0]['cooldown_until'])
        self.assertGreater((until - state.utcnow()).total_seconds(), 200)
        with self.assertRaises(CloudUnavailable) as e:   # cooled-down route is skipped without calling
            self.cloud(self.ok_wrapper()).ask('p')
        self.assertIn('cooldown', str(e.exception))

    def test_structured_output_recovery(self):
        self.assertEqual(parse_json('Here you go:\n```json\n{"a": [1,2,],}\n```'), {'a': [1, 2]})
        with self.assertRaises(ValueError):
            parse_json('I could not do it')


class BackupHealthTests(Base):
    def test_backup_restore_round_trip_excludes_credentials(self):
        tid = self.s.create('game', 'Keep me')
        (self.root / 'vault/game').mkdir(parents=True)
        (self.root / 'vault/game/note.md').write_text('hello')
        (self.root / 'artifacts' / tid).mkdir(parents=True)
        (self.root / 'artifacts' / tid / 'j1-1.md').write_text('draft')
        (self.root / 'dashboard.json').write_text('{"secret": 1}')
        archive = backup.create(self.root)
        with tempfile.TemporaryDirectory() as target:
            result = backup.restore(archive, Path(target) / 'restored')
            restored = Path(result['restored_to'])
            self.assertEqual(result['tasks'], 1)
            self.assertEqual((restored / 'vault/game/note.md').read_text(), 'hello')
            self.assertFalse((restored / 'dashboard.json').exists())
            other = Store(restored)
            try:
                self.assertEqual(other.get(tid)['goal'], 'Keep me')
            finally:
                other.close()
        self.assertLess(backup.age_hours(self.s.db), 1)

    def test_restore_refuses_nonempty_target_and_tampering(self):
        archive = backup.create(self.root)
        with self.assertRaises(ValueError):
            backup.restore(archive, self.root)
        import zipfile
        tampered = self.root / 'bad.zip'
        with zipfile.ZipFile(archive) as src, zipfile.ZipFile(tampered, 'w') as dst:
            for item in src.infolist():
                data = src.read(item.filename)
                dst.writestr(item, b'x' + data if item.filename == 'config.json' or item.filename == 'state.sqlite' else data)
        with self.assertRaises(ValueError):
            backup.verify(tampered)

    def test_health_checks_record_and_alert(self):
        cfg = dict(self.cfg, min_free_disk_gb=10 ** 9, cloud_routes=[])
        rows = health.run_checks(self.s, cfg, self.profiles, probe=lambda e: (False, 'URLError'),
                                 fetch=lambda *a, **k: {'data': []})
        names = {r['name']: r for r in rows}
        self.assertFalse(names['disk']['ok'])
        self.assertFalse(names['backup']['ok'])
        self.assertFalse(names['endpoint.cpu']['ok'])
        self.assertEqual(state.worker_states(self.s.db)['writer']['state'], 'offline')
        subjects = [m['subject'] for m in state.mailbox_items(self.s.db, [])]
        self.assertIn('Low disk space on the assistant server', subjects)

    def test_price_change_raises_urgent_mail(self):
        cfg = dict(self.cfg, cloud_routes=[{'provider': 'openrouter', 'model': 'm:free'}])
        catalog = {'data': [{'id': 'm:free', 'pricing': {'prompt': '0.000001', 'completion': '0'}}]}
        health.check_cloud(self.s, cfg, fetch=lambda *a, **k: catalog)
        self.assertEqual(state.mailbox_items(self.s.db, [])[0]['priority'], 'urgent')

    def test_report_rotation(self):
        (self.root / 'reports').mkdir()
        for i in range(5):
            (self.root / 'reports' / ('report-%03d.md' % i)).write_text('x')
        health.rotate_reports(self.s, keep=2)
        self.assertEqual(len(list((self.root / 'reports').glob('report-*.md'))), 2)


if __name__ == '__main__':
    unittest.main()


class PrivacyGuardTests(unittest.TestCase):
    def test_repository_contains_no_private_runtime_data(self):
        import subprocess, sys
        repo = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(repo / 'scripts'))
        import check_private_leak
        files = subprocess.run(['git', '-C', str(repo), 'ls-files'], capture_output=True, text=True).stdout.split()
        if not files:
            self.skipTest('not a git checkout')
        self.assertEqual(check_private_leak.problems(files), [])

    def test_guard_blocks_private_files_and_keys(self):
        import sys
        repo = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(repo / 'scripts'))
        import check_private_leak
        self.assertTrue(check_private_leak.problems(['KortAssistant/vault/business/x.md']))
        self.assertTrue(check_private_leak.problems(['state.sqlite']))

    def test_runtime_cannot_live_inside_checkout(self):
        from assistant.core import runtime_root
        repo = Path(__file__).resolve().parents[2]
        old = os.environ.get('ASSISTANT_HOME')
        os.environ['ASSISTANT_HOME'] = str(repo / 'private')
        try:
            with self.assertRaises(ValueError):
                runtime_root()
        finally:
            if old is None:
                os.environ.pop('ASSISTANT_HOME')
            else:
                os.environ['ASSISTANT_HOME'] = old


class BenchmarkTests(Base):
    def test_benchmark_measures_and_qualify_requires_pass(self):
        from assistant import benchmark
        prof = dict(self.profiles['writer'], model='qwen3.5:4b', num_ctx=4096)
        answers = {'structured': '{"items":["a","b","c"],"count":3}', 'reasoning': '{"order":["design","build","test"]}',
                   'long_context': 'Sure: {"code":"amber-falcon-42"}', 'malformed_pressure': 'Because exit 1.\n```json\n{"approved": false}\n```'}

        def fetch(url, payload=None, headers=None, timeout=30):
            if url.endswith('/api/generate'):
                return {}
            if url.endswith('/api/ps'):
                return {'models': [{'name': 'qwen3.5:4b', 'size': 4_000_000_000, 'size_vram': 0, 'context_length': 4096}]}
            text = payload['messages'][1]['content']
            key = ('long_context' if 'SECRET CODE' in text else 'structured' if '"count":3' in text
                   else 'reasoning' if 'design' in text else 'malformed_pressure')
            return {'message': {'content': answers[key]}, 'eval_count': 20, 'eval_duration': 1e9, 'prompt_eval_count': 10}
        result = benchmark.run_role('writer', prof, fetch)
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['memory_bytes'], 4_000_000_000)
        (self.root / 'workers.json').write_text(json.dumps({'writer': prof}))
        with self.assertRaises(ValueError):
            benchmark.qualify(self.root, 'writer')
        benchmark.save(result, self.root)
        self.assertTrue(benchmark.qualify(self.root, 'writer')['qualified'])
        answers['long_context'] = '{"code":"wrong"}'
        self.assertFalse(benchmark.run_role('writer', prof, fetch)['passed'])


class ConversationTests(Base):
    def test_questions_wait_for_owner_then_replan_with_answer(self):
        from assistant import conversation
        tid = control.add_task(self.s, 'kort', PROJECTS, 'business', 'Price the spring cleanup package')
        asked = dict(PLAN, questions=['What is the hourly rate?'])
        prompts = []

        class Cloud:
            answers = iter([asked, PLAN])
            def ask(_, prompt):
                prompts.append(prompt)
                return next(Cloud.answers), {'provider': 'openrouter', 'model': 'm:free'}
        self.run_steps(tid, Cloud(), 1)
        t = self.s.get(tid)
        self.assertEqual(t['status'], 'needs_input')
        self.assertNotIn('jobs', t['data'])
        self.run_steps(tid, Cloud(), 1)          # runner does nothing while waiting for Kort
        self.assertEqual(len(prompts), 1)
        self.assertEqual(state.mailbox_items(self.s.db, ['business'])[0]['priority'], 'blocked')
        self.assertEqual(conversation.owner_message(self.s, 'kort', PROJECTS, tid, '$65 per hour'), 'answered')
        self.run_steps(tid, Cloud(), 1)
        self.assertIn('$65 per hour', prompts[1])
        self.assertEqual(self.s.get(tid)['status'], 'working')
        roles = [m['role'] for m in state.task_messages(self.s.db, tid)]
        self.assertEqual(roles[:2], ['owner', 'assistant'])
        self.assertEqual(state.search_messages(self.s.db, ['business'], 'hour')[0]['task_id'], tid)
        self.assertEqual(state.search_messages(self.s.db, ['game'], 'hour'), [])

    def test_plan_confirmation_gate(self):
        from assistant import conversation
        tid = control.add_task(self.s, 'kort', PROJECTS, 'game', 'Draft', confirm_plan=True)
        self.run_steps(tid, FakeCloud([dict(PLAN, assumptions=['Tone is friendly'])]), 1)
        t = self.s.get(tid)
        self.assertEqual(t['status'], 'awaiting_plan_approval')
        self.assertEqual(t['data']['assumptions'], ['Tone is friendly'])
        calls = []
        self.run_steps(tid, FakeCloud([]), 1, worker=lambda *a: calls.append(1) or 'x')
        self.assertEqual(calls, [])
        conversation.approve_plan(self.s, 'kort', PROJECTS, tid, True)
        self.run_steps(tid, FakeCloud([]), 1)
        self.assertEqual(self.s.get(tid)['data']['jobs'][0]['status'], 'awaiting_review')

    def test_attachments_are_validated_and_scoped(self):
        import base64
        from assistant import conversation
        tid = self.s.create('game', 'Draft')
        enc = lambda b: base64.b64encode(b).decode()
        conversation.add_attachment(self.s, 'kort', PROJECTS, tid, 'notes.md', enc(b'# hello'))
        conversation.add_attachment(self.s, 'kort', PROJECTS, tid, 'shot.png', enc(b'\x89PNG\r\n\x1a\n....'))
        for name, content in (('../evil.md', b'x'), ('run.exe', b'MZ'), ('fake.png', b'not an image'),
                              ('bin.txt', b'\xff\xfe\x00')):
            with self.assertRaises(ValueError):
                conversation.add_attachment(self.s, 'kort', PROJECTS, tid, name, enc(content))
        with self.assertRaises(ValueError):
            conversation.add_attachment(self.s, 'guest', ['business'], tid, 'a.md', enc(b'x'))
        ctx = conversation.attachment_context(self.s, tid, {})
        self.assertEqual(ctx[0]['content'], '# hello')
        self.assertIsNone(ctx[1]['content'])
        self.assertIn('NOT visible', ctx[1]['note'])


class ConnectorTests(Base):
    def test_connector_gate(self):
        from assistant import connectors
        conf = {'mail': {'kind': 'email', 'enabled': True, 'qualified': False, 'projects': ['business'],
                         'credential_env': 'TEST_MAIL_TOKEN', 'read_scopes': ['subjects'], 'write_actions': ['create_draft']}}
        (self.root / 'connectors.json').write_text(json.dumps(conf))
        with self.assertRaises(connectors.ConnectorDenied):     # not qualified
            connectors.authorize_read(self.s, 'mail', 'business', 'subjects', 'runner')
        conf['mail']['qualified'] = True
        (self.root / 'connectors.json').write_text(json.dumps(conf))
        with self.assertRaises(connectors.ConnectorDenied):     # credential missing / expired
            connectors.authorize_read(self.s, 'mail', 'business', 'subjects', 'runner')
        os.environ['TEST_MAIL_TOKEN'] = 'x'
        try:
            connectors.authorize_read(self.s, 'mail', 'business', 'subjects', 'runner')
            for bad in (('game', 'subjects'), ('business', 'bodies')):
                with self.assertRaises(connectors.ConnectorDenied):
                    connectors.authorize_read(self.s, 'mail', bad[0], bad[1], 'runner')
            payload = {'to': 'client@example.com', 'subject': 'Quote'}
            digest = connectors.request_write(self.s, 'mail', 'business', 'create_draft', payload, 't1', 'runner')
            self.assertEqual(digest, connectors.request_write(self.s, 'mail', 'business', 'create_draft', payload, 't1', 'runner'))
            self.assertFalse(connectors.consume_approval(self.s, 'mail', 'business', 'create_draft', payload, 'runner'))
            item = state.mailbox_items(self.s.db, ['business'])[0]
            control.answer_mail(self.s, 'kort', PROJECTS, item['id'], 'approve ' + digest[:12])
            self.assertTrue(connectors.consume_approval(self.s, 'mail', 'business', 'create_draft', payload, 'runner'))
            self.assertFalse(connectors.consume_approval(self.s, 'mail', 'business', 'create_draft', payload, 'runner'))
            changed = dict(payload, subject='Other')
            self.assertFalse(connectors.consume_approval(self.s, 'mail', 'business', 'create_draft', changed, 'runner'))
        finally:
            os.environ.pop('TEST_MAIL_TOKEN')
