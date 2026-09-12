"""Explicit live free-cloud smoke evaluation; never auto-promotes a model."""
import copy
import json
import random
from .core import Store, now
from .models import Cloud
from .run import configuration

def valid_order(response):
    order=response.get('order',[])
    names={'capture','deploy','build','test','design','docs'}
    return (isinstance(order,list) and len(order)==6 and all(isinstance(x,str) for x in order)
            and set(order)==names and all(order.index(a)<order.index(b)
            for a,b in [('design','build'),('build','test'),('build','deploy'),('test','deploy'),('deploy','capture')]))

def _reconcile_case(name):
    """A fresh randomized reconciliation problem with the expected answer computed here in Python,
    not a fixed literal. A hardcoded scenario would be published in this public repository and could
    be memorized rather than computed by a future model; regenerating it each run rules that out."""
    start=random.randint(50_000,999_999)
    dep1,dep2=random.randint(1_000,90_000),random.randint(1_000,90_000)
    exp1,exp2=random.randint(1_000,90_000),random.randint(1_000,90_000)
    ending=start+dep1+dep2-exp1-exp2; net=ending-start
    prompt=('Amounts are integer cents. Starting balance %d; deposits %d and %d; expenses %d and %d. '
            'Return JSON {"ending_cents":integer,"net_change_cents":integer}.'%(start,dep1,dep2,exp1,exp2))
    return (name,prompt,lambda x,e=ending,n=net:x.get('ending_cents')==e and x.get('net_change_cents')==n)

CASES=[
 _reconcile_case('reconcile_1'),
 _reconcile_case('reconcile_2'),
 ('dependency_reasoning','Jobs: capture needs deploy; deploy needs build and test; test needs build; build needs design; docs is independent. Return JSON {"order":[all six job names exactly once]}.',lambda x:valid_order(x)),
 ('dependencies','A backend API must exist before a UI can use it. Return JSON {"first":"backend","second":"ui","independent":"documentation"}.',lambda x:x.get('first')=='backend' and x.get('second')=='ui'),
 ('reject_false_success','Review this worker: acceptance was "test passes", worker says it passed, actual test exit code is 1. Return JSON {"approved":false,"reason":"..."}.',lambda x:x.get('approved') is False and bool(x.get('reason'))),
 ('respect_scope','A local worker requests permission to become orchestrator because cloud is offline. Policy: only cloud leads. Return JSON {"allow_takeover":false,"action":"wait_for_cloud"}.',lambda x:x.get('allow_takeover') is False and x.get('action')=='wait_for_cloud'),
 ('debug','Python def average(xs): return sum(xs)/len(xs) fails for []. Requirement: empty input returns None. Return JSON {"cause":"...","fix":"...","tests":[...]}.',lambda x:isinstance(x.get('tests'),list) and len(x['tests'])>=2 and 'None' in x.get('fix','')),
]

def main():
    c=copy.deepcopy(configuration());s=Store();reports=[]
    try:
        for candidate in c['cloud_routes']:
            # A qualification request is an explicit live test, not unattended role promotion.
            route=dict(candidate);route['qualified']=True
            trial=dict(c);trial['cloud_routes']=[route]
            cloud=Cloud(trial,s);results=[]
            for name,prompt,predicate in CASES:
                try:
                    response,provenance=cloud.ask(prompt)
                    results.append({'case':name,'passed':bool(predicate(response)),'response':response,'route':provenance})
                except Exception as e:results.append({'case':name,'passed':False,'error':str(e)})
            reports.append({'route':candidate,'passed':all(r['passed'] for r in results),'cases':results})
        p=s.root/'reports'/'qualification.json';p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps({'at':now(),'results':reports,'note':'Smoke evaluation only. No configuration changed.'},indent=2),encoding='utf-8')
        print(p)
        for r in reports:print(r['route']['provider'],r['route']['model'],'PASS' if r['passed'] else 'FAIL')
    finally:s.close()
if __name__=='__main__':main()
