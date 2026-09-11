import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from assistant.core import Store, safe_path, validate_subproject
from assistant.models import (Cloud, CloudUnavailable, validate_route, verify_free_catalog,
                              verify_zero_reported_cost, claude_env)
from assistant.run import step, validate_plan, approved_review, init

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
        tid=self.store.create('business','Draft a procedure','mountain-men')
        self.store.update(tid,'awaiting_cloud',{'attempt':1})
        other=Store(self.root)
        try:
            self.assertEqual(other.get(tid)['data']['attempt'],1)
            self.assertEqual(other.get(tid)['subproject'],'mountain-men')
        finally:other.close()
    def test_existing_task_database_migrates_without_data_loss(self):
        self.store.close()
        db=sqlite3.connect(self.root/'state.sqlite')
        db.execute('DROP TABLE tasks')
        db.execute('''CREATE TABLE tasks (id TEXT PRIMARY KEY, project TEXT NOT NULL,
            goal TEXT NOT NULL, status TEXT NOT NULL, data TEXT NOT NULL, updated TEXT NOT NULL)''')
        db.execute("INSERT INTO tasks VALUES ('old','game','Keep task','planned','{}','then')")
        db.commit();db.close()
        self.store=Store(self.root)
        task=self.store.get('old')
        self.assertEqual(task['goal'],'Keep task');self.assertEqual(task['subproject'],'')
    def test_daily_cap_persists_across_connections(self):
        self.store.reserve_call('openrouter',1);other=Store(self.root)
        try:
            with self.assertRaises(RuntimeError):other.reserve_call('openrouter',1)
        finally:other.close()
    def test_unknown_project(self):
        with self.assertRaises(ValueError):self.store.create('other','x')
    def test_invalid_subproject_rejected(self):
        for value in ('../other','other/project','other project','x'*65):
            with self.assertRaises(ValueError):validate_subproject(value)
    def test_symlink_not_indexed(self):
        vault=self.root/'vault';(vault/'game').mkdir(parents=True)
        outside=self.root/'secret.md';outside.write_text('dragon secret')
        try:(vault/'game/link.md').symlink_to(outside)
        except OSError:self.skipTest('Symlink privilege unavailable')
        self.assertEqual(self.store.index(vault),0)

    def test_subproject_scope_cannot_retrieve_sibling(self):
        vault=self.root/'vault'
        for folder,label in [('shared','shared'),('business','project'),
                             ('business/mountain-men','mountain'),('business/other-company','other')]:
            p=vault/folder;p.mkdir(parents=True,exist_ok=True)
            (p/'note.md').write_text('sharedword '+label)
        self.store.index(vault)
        hits=self.store.search('business','sharedword',subproject='mountain-men',limit=20)
        self.assertEqual({h['subproject'] for h in hits},{'', 'mountain-men'})
        self.assertNotIn('business/other-company/note.md',{h['path'] for h in hits})

    def test_status_provenance_and_history_are_preserved(self):
        vault=self.root/'vault';folder=vault/'business'/'mountain-men';folder.mkdir(parents=True)
        approved='''---
note_id: pricing-v2
project: business
subproject: mountain-men
status: approved
kind: specification
producer: Kort
sources: owner decision 2026-09-09
observed_date: 2026-09-09
updated_date: 2026-09-09
evidence_ids: task-123
reviewer: Judge
approved_revision: rev-2
supersedes: pricing-v1
---
specialtoken approved price
'''
        proposed=approved.replace('pricing-v2','pricing-draft').replace('status: approved','status: proposed').replace('approved price','proposed price')
        superseded=approved.replace('pricing-v2','pricing-v1').replace('status: approved','status: superseded').replace('approved price','old price')
        (folder/'approved.md').write_text(approved);(folder/'proposed.md').write_text(proposed)
        (folder/'old.md').write_text(superseded)
        self.store.index(vault)
        hits=self.store.search('business','specialtoken',subproject='mountain-men',limit=20)
        self.assertEqual([h['status'] for h in hits],['approved','proposed'])
        self.assertEqual(hits[0]['note_id'],'pricing-v2');self.assertEqual(hits[0]['producer'],'Kort')
        self.assertEqual(hits[0]['approved_revision'],'rev-2')
        history=self.store.search('business','specialtoken',subproject='mountain-men',limit=20,include_history=True)
        self.assertEqual([h['status'] for h in history],['approved','proposed','superseded'])

    def test_metadata_cannot_move_note_to_sibling_scope(self):
        vault=self.root/'vault';folder=vault/'business'/'mountain-men';folder.mkdir(parents=True)
        (folder/'bad.md').write_text('''---
project: game
subproject: other-company
status: approved
---
boundarytoken
''')
        self.store.index(vault)
        self.assertEqual(self.store.search('business','boundarytoken',subproject='other-company'),[])
        hit=self.store.search('business','boundarytoken',subproject='mountain-men')[0]
        self.assertEqual(hit['status'],'disputed');self.assertTrue(hit['metadata_errors'])

    def test_approval_label_without_provenance_is_disputed(self):
        vault=self.root/'vault';folder=vault/'business';folder.mkdir(parents=True)
        (folder/'claim.md').write_text('''---
status: approved
---
claimtoken
''')
        self.store.index(vault)
        hit=self.store.search('business','claimtoken')[0]
        self.assertEqual(hit['status'],'disputed')
        self.assertIn('approved knowledge requires identity, producer, source and revision',
                      hit['metadata_errors'])

    def test_init_marks_canonical_game_knowledge_approved(self):
        installed=self.root/'installed'
        with patch.dict(os.environ,{'ASSISTANT_HOME':str(installed)}):init()
        seeded=Store(installed)
        try:
            hits=seeded.search('game','Keep',subproject='reapers-relics',limit=20)
            game_specs=[h for h in hits if h['path'].startswith('game/') and h['kind']=='specification']
            self.assertTrue(game_specs);self.assertEqual({h['status'] for h in game_specs},{'approved'})
            self.assertTrue(all(h['approved_revision'] for h in game_specs))
        finally:seeded.close()

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
    def test_reported_cost_must_be_zero(self):
        verify_zero_reported_cost({'total_cost_usd':0,'modelUsage':{'x:free':{'costUSD':'0'}}})
        for wrapper in ({'total_cost_usd':0.00219},
                        {'modelUsage':{'x:free':{'costUSD':'unknown'}}},
                        {'modelUsage':[]}):
            with self.assertRaises(CloudUnavailable):verify_zero_reported_cost(wrapper)
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

    def test_task_subproject_pins_cloud_and_worker_retrieval(self):
        self.s.close();self.tmp.cleanup()
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(self.tmp.name)
        self.tid=self.s.create('business','scopeword','alpha')
        vault=Path(self.tmp.name)/'vault'
        for sub,secret in [('alpha','alpha-secret'),('beta','beta-secret')]:
            p=vault/'business'/sub;p.mkdir(parents=True)
            (p/'note.md').write_text('scopeword '+secret)
        self.s.index(vault)
        self.cfg={'allow_cloud_context':{'business':True},'max_worker_attempts':2}
        self.profiles={'writer':{'description':'Writer','projects':['business'],
            'adapter':'ollama-draft','skills':[]}}
        self.plan={'jobs':[{'id':'j1','worker':'writer','brief':'scopeword',
            'acceptance':['one line'],'depends_on':[]}]}
        prompts=[]
        class RecordingCloud:
            def ask(_,prompt):
                prompts.append(prompt)
                return self.plan,{'provider':'openrouter','model':'test:free'}
        self.go(RecordingCloud())
        self.assertIn('alpha-secret',prompts[0]);self.assertNotIn('beta-secret',prompts[0])
        worker_prompts=[]
        self.go(FakeCloud([]),lambda profile,prompt:worker_prompts.append(prompt) or 'draft')
        self.assertIn('alpha-secret',worker_prompts[0]);self.assertNotIn('beta-secret',worker_prompts[0])

if __name__=='__main__':unittest.main()
