import unittest
import json
import test_assistant
import test_codework
from assistant.models import CloudUnavailable
from assistant.core import Store
from assistant.run import step

class CloudDraftTests(unittest.TestCase):
    setUp=test_assistant.PipelineTests.setUp
    tearDown=test_assistant.PipelineTests.tearDown
    def go(self,cloud):
        self.profiles['writer'].update(adapter='cloud-draft',instructions='Write dialogue.')
        step(self.s,self.s.get(self.tid),self.cfg,self.profiles,cloud,lambda *a:self.fail('Local fallback called'))
    def test_execution_requires_separate_review(self):
        cloud=test_assistant.FakeCloud([self.plan,{'draft':'Hello'}, {'approved':True,'checks':[{'criterion':'one line','passed':True,'evidence':'Hello'}]}])
        self.go(cloud);self.go(cloud)
        job=self.s.get(self.tid)['data']['jobs'][0]
        self.assertEqual(job['status'],'awaiting_review');self.assertEqual(job['execution_route']['provider'],'openrouter')
        self.go(cloud);self.go(cloud);self.assertEqual(self.s.get(self.tid)['status'],'draft_ready')
    def test_outage_resumes_without_local_or_attempt_loss(self):
        cloud=test_assistant.FakeCloud([self.plan,CloudUnavailable('offline'),{'draft':'Recovered'}])
        self.go(cloud);self.go(cloud)
        t=self.s.get(self.tid);self.assertEqual(t['status'],'awaiting_cloud');self.assertEqual(t['data']['jobs'][0]['attempts'],0)
        self.go(cloud);self.assertEqual(self.s.get(self.tid)['data']['jobs'][0]['status'],'awaiting_review')
    def test_malformed_draft_blocks(self):
        cloud=test_assistant.FakeCloud([self.plan,{'approved':True}]);self.go(cloud);self.go(cloud)
        self.assertEqual(self.s.get(self.tid)['status'],'blocked')
    def test_project_disclosure_gate_applies(self):
        self.cfg['allow_cloud_context']['game']=False
        self.go(test_assistant.FakeCloud([]));self.assertEqual(self.s.get(self.tid)['status'],'blocked')

class CloudCodeTests(unittest.TestCase):
    setUp=test_codework.CandidateTests.setUp
    tearDown=test_codework.CandidateTests.tearDown
    def test_real_checks_and_integration(self):
        store=Store(self.root/'runtime');tid=store.create('game','Change value');[__import__('assistant.state',fromlist=['x']).grant_cloud_consent(store.db,x,'test') for x in ('personal','business','game')]
        config={'allow_cloud_context':{'game':True},'code_projects':{'game':self.settings}}
        profiles={'engineer':{'adapter':'cloud-code','instructions':'Implement code.','description':'Hard code','projects':['game'],'skills':[]}}
        criterion='Combined implementation satisfies the user goal and all job acceptance criteria'
        approve=lambda c:{'approved':True,'checks':[{'criterion':c,'passed':True,'evidence':'Actual check and diff'}]}
        cloud=test_assistant.FakeCloud([{'jobs':[{'id':'a','worker':'engineer','brief':'change value','acceptance':['value two'],'depends_on':[]}]},
            {'files':[{'path':'game/main.py','content':'value = 2\n'}]},approve('value two'),approve(criterion)])
        try:
            for _ in range(6):step(store,store.get(tid),config,profiles,cloud,lambda *a:self.fail('Local worker called'))
            task=store.get(tid);self.assertEqual(task['status'],'draft_ready')
            job=task['data']['jobs'][0];self.assertTrue(job['checks_passed']);self.assertIn('integration',job)
            self.assertEqual((self.source/'game/main.py').read_text(),'value = 1\n')
        finally:store.close()
