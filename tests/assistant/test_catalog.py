import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from assistant.catalog import refresh, inventory, evaluate, ranked_routes, card_path, save, SUITE
from assistant.core import now

def entry(model='test/model:free',price='0'):
    return {'id':model,'pricing':{'prompt':price,'completion':'0'},'architecture':{'input_modalities':['text']}}

class CatalogTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def refresh(self,rows=None):return refresh(self.root,lambda *a,**k:{'data':rows or [entry()]})
    def test_free_filter_unknown_and_paid(self):
        rows=[entry(),entry('other/zero'),entry('paid/x:free','1'),{'id':'missing:free'},entry('bad:free','NaN')]
        data=self.refresh(rows)['data'];self.assertEqual(len(data),2)
        self.assertTrue(data[0]['route_supported']);self.assertFalse(data[1]['route_supported'])
    def test_cache_reused(self):
        self.refresh()
        self.assertEqual(len(inventory(self.root,fetch=lambda *a,**k:self.fail('Unexpected fetch'))['data']),1)
    def test_stale_failure_not_used(self):
        data=self.refresh();data['at']='2000-01-01T00:00:00+00:00';save(self.root/'models/catalog.json',data)
        with self.assertRaises(OSError):inventory(self.root,fetch=lambda *a,**k:(_ for _ in ()).throw(OSError()))
    def test_invalid_fetch_preserves_previous(self):
        self.refresh()
        with self.assertRaises(ValueError):refresh(self.root,lambda *a,**k:{'error':'bad'})
        self.assertEqual(len(inventory(self.root)['data']),1)
    def test_removed_model_replaces_inventory(self):
        self.refresh();self.refresh([entry('new:free')])
        self.assertEqual(inventory(self.root)['data'][0]['id'],'new:free')
    def test_evaluation_records_failure_without_promoting(self):
        self.refresh();config={'cloud_routes':[]}
        class Fake:
            def __init__(self,c,s):assert c['catalog_routing'] is False
            def ask(self,p):return {},{'model':'test/model:free'}
        result=evaluate(self.root,config,'test/model:free',Fake)
        self.assertFalse(result['passed']);self.assertEqual(config,{'cloud_routes':[]})
        self.assertTrue(list((self.root/'vault/shared/models').glob('*.md')))
        self.assertTrue(list((self.root/'models/evaluations').glob('*.json')))
    def test_unsupported_free_candidate_cannot_evaluate(self):
        self.refresh([entry('other/zero')])
        with self.assertRaises(ValueError):evaluate(self.root,{},'other/zero')
    def test_rank_requires_qualification_and_current_evidence(self):
        data=self.refresh();model='test/model:free';route={'provider':'openrouter','model':model,'qualified':True}
        config={'cloud_routes':[route]};self.assertEqual(ranked_routes(self.root,config),[])
        card={'at':now(),'passed':True,'suite':SUITE,'fingerprint':data['data'][0]['fingerprint'],'cases':[{'seconds':1}]}
        save(card_path(self.root,model),card);self.assertEqual(ranked_routes(self.root,config),[route])
        route['qualified']=False;self.assertEqual(ranked_routes(self.root,config),[])
        route['qualified']=True;card['fingerprint']='changed';save(card_path(self.root,model),card)
        self.assertEqual(ranked_routes(self.root,config),[])
    def test_model_adapter_uses_ranked_routes(self):
        from assistant.models import Cloud,CloudUnavailable
        from assistant.core import Store
        s=Store(self.root)
        try:
            with patch('assistant.catalog.ranked_routes',return_value=[]) as rank:
                with self.assertRaises(CloudUnavailable):Cloud({'cloud_routes':[{'provider':'local'}],'catalog_routing':True},s).ask('goal')
                rank.assert_called_once()
        finally:s.close()
    def test_expired_or_failed_evidence_excluded(self):
        data=self.refresh();model='test/model:free';config={'cloud_routes':[{'provider':'openrouter','model':model,'qualified':True}]}
        for at,passed in [('2000-01-01T00:00:00+00:00',True),(now(),False)]:
            save(card_path(self.root,model),{'at':at,'passed':passed,'suite':SUITE,'fingerprint':data['data'][0]['fingerprint'],'cases':[{'seconds':1}]})
            self.assertEqual(ranked_routes(self.root,config),[])
    def test_successful_evaluation_retains_all_evidence(self):
        self.refresh()
        class Fake:
            def __init__(self,c,s):pass
            def ask(self,p):return {'ok':True},{'model':'test/model:free'}
        with patch('assistant.qualify.CASES',[('test','prompt',lambda x:x['ok'])]):
            card=evaluate(self.root,{},'test/model:free',Fake)
        self.assertTrue(card['passed']);self.assertEqual(card['observed_strengths'],['test'])
        self.assertEqual(card['cases'][0]['response'],{'ok':True})
