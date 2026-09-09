import hashlib
import json
import sys
from pathlib import Path
import unittest
import test_codework
from unittest.mock import patch
from assistant import codework
from assistant.core import Store
from assistant.run import step

class IntegrationTests(unittest.TestCase):
    setUp=test_codework.CandidateTests.setUp
    tearDown=test_codework.CandidateTests.tearDown
    def approved(self,jid,body='value = 2\n'):
        w=codework.prepare_integrated(self.root,'task',jid,self.settings)
        diff=codework.apply_candidate(w,json.dumps({'files':[{'path':'game/main.py','content':body}]}),self.settings)
        artifact=self.root/(jid+'.json');text=json.dumps({'diff':diff});artifact.write_text(text)
        return {'id':jid,'status':'awaiting_integration','checks_passed':True,'workspace':str(w),
                'artifact':str(artifact),'digest':hashlib.sha256(text.encode()).hexdigest()}
    def test_downstream_inherits_and_original_untouched(self):
        job=self.approved('backend');codework.integrate(self.root,'task',job,self.settings)
        w=codework.prepare_integrated(self.root,'task','ui',self.settings)
        self.assertEqual((w/'game/main.py').read_text(),'value = 2\n')
        self.assertEqual((self.source/'game/main.py').read_text(),'value = 1\n')
    def test_stale_worker_blocked(self):
        a=self.approved('a');b=self.approved('b','value = 3\n')
        codework.integrate(self.root,'task',a,self.settings)
        with self.assertRaisesRegex(ValueError,'stale'):codework.integrate(self.root,'task',b,self.settings)
    def test_idempotent_recovery(self):
        a=self.approved('a');first=codework.integrate(self.root,'task',a,self.settings)
        second=codework.integrate(self.root,'task',a,self.settings)
        self.assertEqual(first,second)
    def test_modified_artifact_blocks(self):
        a=self.approved('a');Path(a['artifact']).write_text('{}')
        with self.assertRaises(ValueError):codework.integrate(self.root,'task',a,self.settings)
    def test_unapproved_blocks(self):
        a=self.approved('a');a['status']='awaiting_review'
        with self.assertRaises(ValueError):codework.integrate(self.root,'task',a,self.settings)
    def test_source_advances_task_remains_pinned(self):
        codework.task_workspace(self.root,'task',self.settings)
        (self.source/'game/main.py').write_text('value = 99\n');codework.git(self.source,'add','.')
        codework.git(self.source,'commit','-m','other work')
        w=codework.prepare_integrated(self.root,'task','a',self.settings)
        self.assertEqual((w/'game/main.py').read_text(),'value = 1\n')
    def test_pipeline_inherits_then_combined_review(self,final_approved=True):
        store=Store(self.root/'runtime');tid=store.create('game','Implement backend then UI')
        profiles={'coder':{'adapter':'code-sandbox','projects':['game'],'description':'code','skills':[]}}
        config={'allow_cloud_context':{'game':True},'code_projects':{'game':self.settings},'max_worker_attempts':3}
        calls=[]
        class Cloud:
            def ask(_,prompt):
                calls.append(prompt)
                if 'AVAILABLE WORKER PROFILES' in prompt:
                    return {'jobs':[{'id':'a','worker':'coder','brief':'backend','acceptance':['works'],'depends_on':[]},
                        {'id':'b','worker':'coder','brief':'ui','acceptance':['works'],'depends_on':['a']}]},{}
                criterion='Combined implementation satisfies the user goal and all job acceptance criteria' if 'combined_checks' in prompt else 'works'
                accepted=final_approved if 'combined_checks' in prompt else True
                return {'approved':accepted,'checks':[{'criterion':criterion,'passed':accepted,'evidence':'configured checks and diff'}]},{}
        outputs=[]
        def worker(profile,prompt):
            outputs.append(prompt)
            if len(outputs)==2:self.assertIn('value = 2',prompt)
            # Second job creates a consumer; backend check must still pass.
            f={'path':'game/main.py','content':'value = 2\n'} if len(outputs)==1 else {'path':'game/ui.py','content':'from main import value\n'}
            return json.dumps({'files':[f]})
        try:
            for _ in range(12):step(store,store.get(tid),config,profiles,Cloud(),worker)
            result=store.get(tid);self.assertEqual(result['status'],'draft_ready' if final_approved else 'blocked')
            self.assertIn('integration_review',result['data']);self.assertIn('combined_diff',calls[-1])
            self.assertEqual(len(outputs),2)
        finally:store.close()
    def test_resume_after_commit_before_fetch(self):
        a=self.approved('a');real_git=codework.git
        def fail_fetch(root,*args):
            if args[0]=='fetch':raise RuntimeError('interrupted')
            return real_git(root,*args)
        with patch('assistant.codework.git',side_effect=fail_fetch):
            with self.assertRaises(RuntimeError):codework.integrate(self.root,'task',a,self.settings)
        result=codework.integrate(self.root,'task',a,self.settings)
        self.assertEqual((Path(result['workspace'])/'game/main.py').read_text(),'value = 2\n')
    def test_combined_failure_not_ready(self):
        a=self.approved('a');codework.integrate(self.root,'task',a,self.settings)
        a['status']='verified_candidate';a['depends_on']=[];a['integration']={'revision':'fixture'}
        store=Store(self.root);tid=store.create('game','combined goal')
        # Use the same task workspace ID for this persisted task.
        workspace=codework.task_workspace(self.root,tid,self.settings)
        a['workspace']=str(workspace)
        store.update(tid,'working',{'jobs':[a]})
        config={'allow_cloud_context':{'game':True},'code_projects':{'game':self.settings}}
        class Cloud:
            def ask(self,p):raise AssertionError('Failed combined checks must not ask for approval')
        try:
            step(store,store.get(tid),config,{},Cloud())
            self.assertEqual(store.get(tid)['status'],'blocked')
            self.assertFalse(store.get(tid)['data']['integration_review']['approved'])
        finally:store.close()

    def test_combined_cloud_rejection_blocks_completion(self):
        self.test_pipeline_inherits_then_combined_review(final_approved=False)
