import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from assistant.core import Store, safe_path
from assistant.models import Cloud, CloudUnavailable, validate_route, verify_free_catalog, claude_env
from assistant.run import step, validate_plan, approved_review

class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.store=Store(self.root)
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def test_scope_and_reindex_delete(self):
        vault=self.root/'vault'
        for scope in ('shared','business','game','personal'):
            (vault/scope).mkdir(parents=True);(vault/scope/'a.md').write_text('dragon '+scope)
        self.store.index(vault)
        hits=self.store.search('game','dragon')
        self.assertEqual({h['scope'] for h in hits},{'shared','game'})
        (vault/'game/a.md').unlink();self.store.index(vault)
        self.assertEqual({h['scope'] for h in self.store.search('game','dragon')},{'shared'})
    def test_query_does_not_accept_fts_operators(self):
        self.assertEqual(self.store.search('game','" OR * --'),[])
    def test_traversal(self):
        for rel in ('../outside','/etc/passwd','C:\\outside','a/../../b','.'):
            with self.assertRaises(ValueError):safe_path(self.root,rel)
    def test_restart_preserves_task(self):
        tid=self.store.create('business','Draft a procedure')
        self.store.update(tid,'awaiting_cloud',{'attempt':1})
        other=Store(self.root)
        try:self.assertEqual(other.get(tid)['data']['attempt'],1)
        finally:other.close()
    def test_daily_cap_persists_across_connections(self):
        self.store.reserve_call('openrouter',1);other=Store(self.root)
        try:
            with self.assertRaises(RuntimeError):other.reserve_call('openrouter',1)
        finally:other.close()
    def test_unknown_project(self):
        with self.assertRaises(ValueError):self.store.create('other','x')
    def test_symlink_not_indexed(self):
        vault=self.root/'vault';(vault/'game').mkdir(parents=True)
        outside=self.root/'secret.md';outside.write_text('dragon secret')
        try:(vault/'game/link.md').symlink_to(outside)
        except OSError:self.skipTest('Symlink privilege unavailable')
        self.assertEqual(self.store.index(vault),0)

class PolicyTests(unittest.TestCase):
    def test_local_leader_rejected(self):
        with self.assertRaises(ValueError):validate_route({'provider':'local','model':'qwen3.5:4b','qualified':True})
    def test_paid_rejected(self):
        with self.assertRaises(ValueError):validate_route({'provider':'openrouter','model':'paid/model','qualified':True})
    def test_unqualified_rejected(self):
        with self.assertRaises(ValueError):validate_route({'provider':'openrouter','model':'x/y:free','qualified':False})
    def test_ollama_must_be_cloud_and_free_confirmed(self):
        for model,confirmed in [('local:9b',True),('x:cloud',False)]:
            with self.assertRaises(ValueError):validate_route({'provider':'ollama-cloud','model':model,'qualified':True,'included_usage_confirmed':confirmed})
        validate_route({'provider':'ollama-cloud','model':'x:cloud','qualified':True,'included_usage_confirmed':True})
    def test_catalog_checks_all_prices(self):
        valid={'data':[{'id':'x:free','pricing':{'prompt':'0','completion':'0','request':'0'}}]}
        verify_free_catalog('x:free',valid)
        valid['data'][0]['pricing']['request']='0.01'
        with self.assertRaises(ValueError):verify_free_catalog('x:free',valid)
        with self.assertRaises(ValueError):verify_free_catalog('missing:free',valid)
    def test_missing_and_nan_pricing_rejected(self):
        for prices in ({},{'prompt':'0','completion':'NaN'}):
            with self.assertRaises(ValueError):verify_free_catalog('x:free',{'data':[{'id':'x:free','pricing':prices}]})
    def test_env_removes_paid_provider_and_pins_aliases(self):
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':'paid','CLAUDE_CODE_USE_BEDROCK':'1','OPENROUTER_API_KEY':'test'}):
            e=claude_env({'provider':'openrouter','model':'x:free'})
        self.assertEqual(e['ANTHROPIC_API_KEY'],'');self.assertNotIn('CLAUDE_CODE_USE_BEDROCK',e)
        for tier in ('FABLE','OPUS','SONNET','HAIKU'):self.assertEqual(e['ANTHROPIC_DEFAULT_'+tier+'_MODEL'],'x:free')
    def test_empty_cloud_routes_fail_without_local_call(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(d)
            try:
                with self.assertRaises(CloudUnavailable):Cloud({'cloud_routes':[]},s).ask('plan')
            finally:s.close()
    def test_plan_dependency_cycle_rejected(self):
        with self.assertRaises(ValueError):validate_plan({'jobs':[{'id':'a','worker':'w','brief':'x','acceptance':['a'],'depends_on':['a']}]},{'w':{}})
    def test_review_requires_exact_boolean_and_evidence(self):
        for r in ({},{'approved':'true','checks':[]},{'approved':True,'checks':[{'criterion':'a','passed':True,'evidence':''}]}):
            self.assertFalse(approved_review(r,['a']))
        self.assertTrue(approved_review({'approved':True,'checks':[{'criterion':'a','passed':True,'evidence':'artifact paragraph 1'}]},['a']))

class FakeCloud:
    def __init__(self,answers):self.answers=iter(answers)
    def ask(self,prompt):
        value=next(self.answers)
        if isinstance(value,Exception):raise value
        return value,{'provider':'openrouter','model':'test:free'}

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(self.tmp.name)
        self.tid=self.s.create('game','Draft a dialogue')
        self.cfg={'allow_cloud_context':{'game':True},'max_worker_attempts':2}
        self.profiles={'writer':{'description':'Writer','projects':['game'],'adapter':'ollama-draft','skills':[]}}
        self.plan={'jobs':[{'id':'j1','worker':'writer','brief':'Draft a line','acceptance':['one line'],'depends_on':[]}]}
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def go(self,cloud,worker=lambda *a:'A line.'):
        step(self.s,self.s.get(self.tid),self.cfg,self.profiles,cloud=cloud,worker_call=worker)
    def test_plan_worker_review_and_restart(self):
        cloud=FakeCloud([self.plan,{'approved':True,'checks':[{'criterion':'one line','passed':True,'evidence':'A line.'}]}])
        self.go(cloud);self.go(cloud)
        self.assertEqual(self.s.get(self.tid)['data']['jobs'][0]['status'],'awaiting_review')
        self.go(cloud);self.go(cloud)
        self.assertEqual(self.s.get(self.tid)['status'],'draft_ready')
    def test_cloud_outage_keeps_artifact_pending_review(self):
        cloud=FakeCloud([self.plan,CloudUnavailable('down')]);self.go(cloud);self.go(cloud);self.go(cloud)
        t=self.s.get(self.tid)
        self.assertEqual(t['status'],'awaiting_cloud');self.assertEqual(t['data']['jobs'][0]['status'],'awaiting_review')
        self.assertTrue(Path(t['data']['jobs'][0]['artifact']).exists())
    def test_tampering_blocks_review(self):
        cloud=FakeCloud([self.plan]);self.go(cloud);self.go(cloud)
        Path(self.s.get(self.tid)['data']['jobs'][0]['artifact']).write_text('changed')
        self.go(cloud);self.assertEqual(self.s.get(self.tid)['data']['jobs'][0]['status'],'blocked')
    def test_bad_review_requests_repair(self):
        cloud=FakeCloud([self.plan,{'approved':False,'repairs':['shorten']}]);self.go(cloud);self.go(cloud);self.go(cloud)
        self.assertEqual(self.s.get(self.tid)['data']['jobs'][0]['status'],'repair_requested')
    def test_cloud_context_disabled_does_not_send(self):
        self.cfg['allow_cloud_context']['game']=False
        self.go(FakeCloud([]));self.assertEqual(self.s.get(self.tid)['status'],'blocked')
    def test_unconfigured_media_does_not_fake_output(self):
        self.profiles['writer']['adapter']='unconfigured-media';c=FakeCloud([self.plan]);self.go(c);self.go(c)
        self.assertEqual(self.s.get(self.tid)['data']['jobs'][0]['status'],'blocked')
    def test_worker_failure_is_bounded(self):
        c=FakeCloud([self.plan]);self.go(c)
        def fail(*a):raise RuntimeError('offline')
        self.go(c,fail);self.go(c,fail)
        self.assertEqual(self.s.get(self.tid)['data']['jobs'][0]['status'],'blocked')
    def test_unknown_worker_blocks(self):
        self.plan['jobs'][0]['worker']='invented';self.go(FakeCloud([self.plan]))
        self.assertEqual(self.s.get(self.tid)['status'],'blocked')

if __name__=='__main__':unittest.main()
