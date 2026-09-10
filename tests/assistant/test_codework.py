import json
import sys
import tempfile
import unittest
from pathlib import Path
from assistant import codework
from assistant.core import Store
from assistant.memory_mcp import dispatch

class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.source=self.root/'source';self.source.mkdir()
        codework.git(self.source,'init');codework.git(self.source,'config','user.email','test@example.invalid')
        codework.git(self.source,'config','user.name','Test')
        (self.source/'game').mkdir();(self.source/'game/main.py').write_text('value = 1\n')
        codework.git(self.source,'add','.');codework.git(self.source,'commit','-m','initial')
        self.settings={'source':str(self.source),'execution_enabled':True,'allowed_prefixes':['game/'],
            'context_files':['game/main.py'],'checks':[[sys.executable,'-c','assert open("game/main.py").read() == "value = 2\\n"']]}
    def tearDown(self):self.tmp.cleanup()
    def prepare(self):return codework.prepare(self.root,'task','job',self.settings)
    def candidate(self,w):return codework.apply_candidate(w,json.dumps({'files':[{'path':'game/main.py','content':'value = 2\n'}]}),self.settings)
    def test_candidate_isolated_and_checks_real(self):
        w=self.prepare();diff=self.candidate(w)
        self.assertIn('+value = 2',diff)
        self.assertEqual((self.source/'game/main.py').read_text(),'value = 1\n')
        self.assertEqual(codework.git(w,'remote').strip(),'')
        self.assertTrue(codework.check_candidate(w,self.settings)[0]['passed'])
        self.assertTrue(codework.unchanged(w,diff))
    def test_test_failure_is_not_success(self):
        w=self.prepare()
        self.assertFalse(codework.check_candidate(w,self.settings)[0]['passed'])
    def test_unstaged_tamper_blocks(self):
        w=self.prepare();diff=self.candidate(w);(w/'game/main.py').write_text('value = 9\n')
        self.assertFalse(codework.unchanged(w,diff))
    def test_staged_tamper_blocks(self):
        w=self.prepare();diff=self.candidate(w);(w/'game/main.py').write_text('value = 9\n');codework.git(w,'add','.')
        self.assertFalse(codework.unchanged(w,diff))
    def test_out_of_scope_and_traversal(self):
        w=self.prepare()
        for path in ('game/../../outside.py','server/main.py','.git/config','game/.secret.py'):
            with self.assertRaises(ValueError):codework.apply_candidate(w,json.dumps({'files':[{'path':path,'content':'bad'}]}),self.settings)
    def test_no_checks_cannot_verify(self):
        with self.assertRaises(ValueError):codework.check_candidate(self.prepare(),{'checks':[]})
    def test_disabled_cannot_execute(self):
        with self.assertRaises(ValueError):codework.prepare(self.root,'task','job',{})

class McpTests(unittest.TestCase):
    def test_protocol_and_scope(self):
        with tempfile.TemporaryDirectory() as root:
            s=Store(Path(root))
            try:
                for scope in ('game','business'):
                    p=Path(root)/'vault'/scope;p.mkdir(parents=True);(p/'a.md').write_text('dragon '+scope)
                s.index(Path(root)/'vault')
                self.assertIsNone(dispatch({'jsonrpc':'2.0','method':'notifications/initialized'},s,'game'))
                self.assertEqual(dispatch({'id':1,'method':'initialize','params':{'protocolVersion':'2025-03-26'}},s,'game')['result']['protocolVersion'],'2025-03-26')
                reply=dispatch({'id':2,'method':'tools/call','params':{'name':'memory_search','arguments':{'query':'dragon','project':'business'}}},s,'game')
                self.assertEqual({r['scope'] for r in json.loads(reply['result']['content'][0]['text'])},{'game'})
                self.assertIn('error',dispatch({'id':3,'method':'tools/call','params':{'name':'memory_write'}},s,'game'))
            finally:s.close()

    def test_protocol_pins_subproject_from_process_configuration(self):
        with tempfile.TemporaryDirectory() as root:
            for sub in ('alpha','beta'):
                p=Path(root)/'vault'/'business'/sub;p.mkdir(parents=True)
                (p/'a.md').write_text('uniquetoken '+sub)
            s=Store(root)
            try:
                s.index(Path(root)/'vault')
                request={'id':2,'method':'tools/call','params':{'name':'memory_search',
                    'arguments':{'query':'uniquetoken','subproject':'beta'}}}
                reply=dispatch(request,s,'business','alpha')
                hits=json.loads(reply['result']['content'][0]['text'])
                self.assertEqual({h['subproject'] for h in hits},{'alpha'})
            finally:s.close()
