"""Direction files are a role's standing rules, and models may only be swapped for approved ones."""
import json
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

from assistant import benchmark
from assistant.models import (REPO, effective_instructions, local_profile_fingerprint,
                              local_request, local_qualified)

ROLES = REPO / 'config/assistant/roles'
WORKERS = json.loads((REPO / 'config/assistant/workers.json').read_text(encoding='utf-8'))


class DirectionFileTests(unittest.TestCase):
    def test_every_specialist_has_a_direction_file_that_exists(self):
        missing = [n for n, p in WORKERS.items()
                   if isinstance(p, dict) and not (REPO / p.get('direction', 'nope')).is_file()]
        self.assertEqual(missing, [], 'specialists without a readable direction file')

    def test_direction_replaces_the_inline_instruction(self):
        profile = WORKERS['debugger']
        self.assertNotIn('instructions', profile, 'two sources of truth for the same rules')
        text = effective_instructions(profile)
        self.assertIn('Debugger', text)
        self.assertIn('Hard rules', text)

    def test_direction_reaches_the_model_as_the_system_prompt(self):
        _url, payload, _timeout = local_request(WORKERS['operations'], 'hello')
        system = payload['messages'][0]['content']
        self.assertEqual(system, effective_instructions(WORKERS['operations']))
        self.assertIn('Never send a message', system)

    def test_inline_instructions_still_work_without_a_direction(self):
        self.assertEqual(effective_instructions({'instructions': 'be brief'}), 'be brief')

    def test_direction_paths_cannot_escape_the_repository(self):
        for bad in ('../secrets.md', '/etc/passwd', 'config/assistant/workers.json'):
            with self.assertRaises(ValueError):
                effective_instructions({'direction': bad, 'instructions': 'x'})

    def test_editing_a_direction_changes_the_fingerprint(self):
        """Rules that are never re-evidenced are not rules, so an edit must cost qualification."""
        profile = dict(WORKERS['debugger'])
        before = local_profile_fingerprint(profile)
        edited = dict(profile)
        edited.pop('direction')
        edited['instructions'] = 'something else entirely'
        self.assertNotEqual(before, local_profile_fingerprint(edited))


class ModelSwitchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.profile = {'endpoint': 'http://127.0.0.1:11434', 'model': 'a:4b',
                        'instructions': 'sys', 'num_ctx': 8192, 'num_predict': 1024,
                        'approved_models': ['a:4b', 'b:9b']}
        (self.root / 'workers.json').write_text(json.dumps({'ops': self.profile}), encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def report(self, model, passed=True, age_days=0):
        profile = dict(self.profile, model=model)
        at = datetime.fromtimestamp(time.time() - age_days * 86400, timezone.utc)
        d = self.root / 'reports' / 'benchmarks'
        d.mkdir(parents=True, exist_ok=True)
        (d / ('ops-%s.json' % model.replace(':', '-'))).write_text(json.dumps({
            'model': model, 'num_ctx': 8192, 'passed': passed,
            'at': at.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'profile_fingerprint': local_profile_fingerprint(profile)}), encoding='utf-8')

    def test_only_approved_models_are_accepted(self):
        with self.assertRaises(ValueError):
            benchmark.switch_model(self.root, 'ops', 'untrusted:70b')
        with self.assertRaises(ValueError):
            benchmark.switch_model(self.root, 'nobody', 'a:4b')
        saved = json.loads((self.root / 'workers.json').read_text(encoding='utf-8'))
        self.assertEqual(saved['ops']['model'], 'a:4b', 'a refused switch must change nothing')

    def test_switching_without_evidence_leaves_the_role_unqualified(self):
        out = benchmark.switch_model(self.root, 'ops', 'b:9b')
        self.assertEqual(out['model'], 'b:9b')
        self.assertIs(out['qualified'], False)
        self.assertNotIn('qualification', out)
        self.assertFalse(local_qualified(out))

    def test_switching_onto_evidenced_model_restores_qualification(self):
        self.report('b:9b')
        out = benchmark.switch_model(self.root, 'ops', 'b:9b')
        self.assertIs(out['qualified'], True)
        self.assertTrue(local_qualified(out))

    def test_stale_or_failing_evidence_does_not_count(self):
        self.report('b:9b', passed=False)
        self.assertIs(benchmark.switch_model(self.root, 'ops', 'b:9b')['qualified'], False)
        self.report('b:9b', passed=True, age_days=30)
        self.assertIs(benchmark.switch_model(self.root, 'ops', 'b:9b')['qualified'], False)

    def test_evidence_for_another_model_does_not_transfer(self):
        self.report('a:4b')
        self.assertIs(benchmark.switch_model(self.root, 'ops', 'b:9b')['qualified'], False)
        self.assertIs(benchmark.switch_model(self.root, 'ops', 'a:4b')['qualified'], True)


class OneModelPerMachineTests(unittest.TestCase):
    """A machine holds one model, so the endpoint is the unit that gets switched."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        gpu = {'endpoint': 'http://127.0.0.1:11435', 'model': 'a:9b', 'instructions': 'sys',
               'num_ctx': 8192, 'num_predict': 1024, 'approved_models': ['a:9b', 'b:9b']}
        cpu = {'endpoint': 'http://127.0.0.1:11434', 'model': 'small:4b', 'instructions': 'sys',
               'num_ctx': 8192, 'num_predict': 1024, 'approved_models': ['small:4b']}
        self.workers = {'ui': dict(gpu), 'sprites': dict(gpu), 'ops': dict(cpu)}
        self.write()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self):
        (self.root / 'workers.json').write_text(json.dumps(self.workers), encoding='utf-8')

    def saved(self):
        return json.loads((self.root / 'workers.json').read_text(encoding='utf-8'))

    def test_switching_one_specialist_moves_its_whole_machine(self):
        out = benchmark.switch_model(self.root, 'ui', 'b:9b')
        saved = self.saved()
        self.assertEqual(saved['ui']['model'], 'b:9b')
        self.assertEqual(saved['sprites']['model'], 'b:9b', 'left two models on one machine')
        self.assertEqual(out['moved'], ['sprites', 'ui'])

    def test_other_machines_are_left_alone(self):
        benchmark.switch_model(self.root, 'ui', 'b:9b')
        self.assertEqual(self.saved()['ops']['model'], 'small:4b')

    def test_a_switch_the_machine_cannot_take_changes_nothing(self):
        """If one specialist on the machine has not approved the model, nobody moves."""
        self.workers['sprites']['approved_models'] = ['a:9b']
        self.write()
        with self.assertRaises(ValueError):
            benchmark.switch_model(self.root, 'ui', 'b:9b')
        saved = self.saved()
        self.assertEqual(saved['ui']['model'], 'a:9b')
        self.assertEqual(saved['sprites']['model'], 'a:9b')

    def test_each_specialist_is_qualified_on_its_own_evidence(self):
        """Moving together is a hardware fact; being trusted is still earned per role."""
        d = self.root / 'reports' / 'benchmarks'
        d.mkdir(parents=True, exist_ok=True)
        profile = dict(self.workers['ui'], model='b:9b')
        (d / 'ui-new.json').write_text(json.dumps({
            'model': 'b:9b', 'num_ctx': 8192, 'passed': True,
            'at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'profile_fingerprint': local_profile_fingerprint(profile)}), encoding='utf-8')
        out = benchmark.switch_model(self.root, 'ui', 'b:9b')
        saved = self.saved()
        self.assertIs(saved['ui']['qualified'], True)
        self.assertIs(saved['sprites']['qualified'], False)
        self.assertEqual(out['unqualified'], ['sprites'])


class ApprovedModelTests(unittest.TestCase):
    def test_every_machine_offers_one_model_to_all_of_its_specialists(self):
        """Two specialists on a machine must agree on what it may run, or no switch is possible."""
        by_endpoint = {}
        for name, p in WORKERS.items():
            if isinstance(p, dict) and p.get('endpoint'):
                by_endpoint.setdefault(p['endpoint'].rstrip('/'), []).append((name, p))
        self.assertTrue(by_endpoint, 'no local machines configured')
        for endpoint, rows in by_endpoint.items():
            models = {p.get('model') for _, p in rows}
            self.assertEqual(len(models), 1, endpoint + ' is split across models: ' + str(models))
            approved = {tuple(p.get('approved_models') or ()) for _, p in rows}
            self.assertEqual(len(approved), 1, endpoint + ' specialists approve different models')


if __name__ == '__main__':
    unittest.main()
