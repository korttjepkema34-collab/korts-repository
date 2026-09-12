"""Regression checks for production-equivalent, auditable qualification."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from assistant import benchmark, models, run
from assistant.core import Store


PROFILE = {'endpoint': 'http://127.0.0.1:11434', 'model': 'qwen3.5:4b',
           'instructions': 'Return the requested result.', 'adapter': 'ollama-draft',
           'num_ctx': 4096, 'skills': []}


class QualificationReliabilityTests(unittest.TestCase):
    def test_benchmark_sends_same_request_as_production(self):
        for overrides in ({}, {'num_predict': 7000, 'timeout_seconds': 2100, 'think': True}):
            with self.subTest(overrides=overrides):
                profile = dict(PROFILE, **overrides)
                fetch = Mock(return_value={'message': {'content': '{}'}})
                with patch('assistant.models.request_json', fetch):
                    models.local_ask(profile, 'same prompt')
                production = fetch.call_args
                fetch.reset_mock()
                benchmark._chat(profile, 'same prompt', fetch)
                self.assertEqual(fetch.call_args, production)

    def test_changed_persona_cannot_reuse_passing_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = dict(PROFILE)
            fetch = Mock(return_value={'message': {'content': '{}'}})
            with patch('assistant.benchmark.cases', return_value=[('ok', 'prompt', lambda x: True)]):
                report = benchmark.run_role('writer', profile, fetch)
            self.assertTrue(report['passed'])
            self.assertEqual(report['cases'][0]['prompt'], 'prompt')
            self.assertEqual(report['cases'][0]['response'], '{}')
            benchmark.save(report, root)
            profile['instructions'] = 'A different persona.'
            (root / 'workers.json').write_text(json.dumps({'writer': profile}))
            with self.assertRaises(ValueError):
                benchmark.qualify(root, 'writer')

    def test_runtime_rejects_profile_changed_after_qualification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = dict(PROFILE)
            fetch = Mock(return_value={'message': {'content': '{}'}})
            with patch('assistant.benchmark.cases', return_value=[('ok', 'prompt', lambda x: True)]):
                benchmark.save(benchmark.run_role('writer', profile, fetch), root)
            (root / 'workers.json').write_text(json.dumps({'writer': profile}))
            qualified = benchmark.qualify(root, 'writer')
            store = Store(root)
            try:
                config = {'require_qualified_workers': True}
                self.assertIsNone(run.local_gate(store, config, qualified, 'writer', 'game', 't', 'j'))
                for field, value in [('instructions', 'New persona'), ('num_predict', 128),
                                     ('think', True), ('timeout_seconds', 30), ('model', 'other:4b'),
                                     ('endpoint', 'http://localhost:11434'), ('num_ctx', 2048),
                                     ('skills', ['new-skill.md'])]:
                    with self.subTest(field=field):
                        changed = copy.deepcopy(qualified)
                        changed[field] = value
                        self.assertEqual(run.local_gate(store, config, changed, 'writer', 'game', 't', 'j'),
                                         'unqualified')
            finally:
                store.close()

    def test_cloud_evaluation_keeps_randomized_question(self):
        from assistant import catalog
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog.refresh(root, lambda *a, **k: {'data': [
                {'id': 'test/model:free', 'pricing': {'prompt': '0', 'completion': '0'}}]})
            prompts = []

            class Cloud:
                def __init__(self, *args): pass
                def ask(self, prompt):
                    prompts.append(prompt)
                    return {}, {'model': 'test/model:free'}

            report = catalog.evaluate(root, {}, 'test/model:free', Cloud)
            self.assertEqual([case['prompt'] for case in report['cases']], prompts)

    def test_workforce_reports_effective_qualification(self):
        from assistant import web, state
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            try:
                profile = dict(PROFILE, projects=['game'], qualified=True)
                def displayed():
                    return next(w for w in web.overview(store, {'projects': ['game']},
                                {'writer': profile})['workforce'] if w['id'] == 'writer')
                state.set_worker_state(store.db, 'writer', 'idle')
                self.assertFalse(displayed()['qualified'])
                self.assertEqual(displayed()['state'], 'unavailable')
                profile['qualification'] = {'profile_fingerprint': models.local_profile_fingerprint(profile)}
                self.assertTrue(displayed()['qualified'])
                self.assertEqual(displayed()['state'], 'idle')
                profile['instructions'] = 'Edited persona'
                self.assertFalse(displayed()['qualified'])
                self.assertEqual(displayed()['state'], 'unavailable')
            finally:
                store.close()


if __name__ == '__main__':
    unittest.main()
