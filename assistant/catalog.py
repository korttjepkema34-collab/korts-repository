"""Free OpenRouter inventory and measured smoke evaluations. No automatic promotion."""
import argparse
import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .core import Store, now
from .models import Cloud, request_json, verify_free_catalog

URL='https://openrouter.ai/api/v1/models'
SUITE='leadership-smoke-v1'

def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(data,indent=2),encoding='utf-8');temporary.replace(path)

def fingerprint(entry):
    fields={k:entry.get(k) for k in ('id','architecture','context_length','supported_parameters','pricing')}
    return hashlib.sha256(json.dumps(fields,sort_keys=True).encode()).hexdigest()

def refresh(root,fetch=request_json):
    headers={}
    if os.environ.get('OPENROUTER_API_KEY'):headers['Authorization']='Bearer '+os.environ['OPENROUTER_API_KEY']
    catalog=fetch(URL,headers=headers,timeout=30)
    if not isinstance(catalog,dict) or not isinstance(catalog.get('data'),list):raise ValueError('Malformed model catalog')
    rows=[]
    for entry in catalog['data']:
        if not isinstance(entry,dict) or not isinstance(entry.get('id'),str):continue
        try:verify_free_catalog(entry['id'],{'data':[entry]})
        except (ValueError,TypeError,AttributeError):continue
        rows.append({**entry,'route_supported':entry['id'].endswith(':free'),'fingerprint':fingerprint(entry)})
    snapshot={'at':now(),'source':URL,'data':rows}
    save(Path(root)/'models/catalog.json',snapshot)
    return snapshot

def inventory(root,max_age=86400,fetch=request_json):
    path=Path(root)/'models/catalog.json'
    try:
        data=json.loads(path.read_text(encoding='utf-8'))
        age=(datetime.now(timezone.utc)-datetime.fromisoformat(data['at'])).total_seconds()
        if 0<=age<max_age:return data
    except (OSError,ValueError,KeyError,TypeError):pass
    # Do not silently use stale data after a failed refresh.
    return refresh(root,fetch)

def card_path(root,model):
    return Path(root)/'models/cards'/(hashlib.sha256(model.encode()).hexdigest()+'.json')

def evaluate(root,config,model,cloud_factory=Cloud):
    from .qualify import CASES
    snapshot=inventory(root)
    entry=next((e for e in snapshot['data'] if e['id']==model and e['route_supported']),None)
    if entry is None:raise ValueError('Model is not a supported free catalog candidate')
    trial=dict(config);trial['catalog_routing']=False
    trial['cloud_routes']=[{'provider':'openrouter','model':model,'qualified':True}]
    store=Store(root);results=[]
    try:
        cloud=cloud_factory(trial,store)
        for name,prompt,predicate in CASES:
            start=time.monotonic()
            try:
                response,route=cloud.ask(prompt)
                results.append({'case':name,'passed':bool(predicate(response)),'response':response,'route':route,'seconds':time.monotonic()-start})
            except Exception as e:
                results.append({'case':name,'passed':False,'error':type(e).__name__,'seconds':time.monotonic()-start})
    finally:store.close()
    card={'model':model,'at':now(),'suite':SUITE,'fingerprint':entry['fingerprint'],
          'passed':all(x['passed'] for x in results),'cases':results,
          'observed_strengths':[x['case'] for x in results if x['passed']],
          'observed_failures':[x['case'] for x in results if not x['passed']],
          'unknown':['production coding quality','vision','tax reasoning','long-horizon autonomy'],
          'note':'Small synthetic smoke suite; not general intelligence ranking or authorization.'}
    save(Path(root)/'models/evaluations'/(uuid.uuid4().hex+'.json'),card)
    save(card_path(root,model),card)
    note=Path(root)/'vault/shared/models'/(hashlib.sha256(model.encode()).hexdigest()+'.md')
    note.parent.mkdir(parents=True,exist_ok=True)
    note.write_text('# Model evaluation: '+model+'\n\nSynthetic tests only; no private task data.\n\n```json\n'+json.dumps(card,indent=2)+'\n```\n',encoding='utf-8')
    return card

def ranked_routes(root,config):
    """Only explicitly qualified routes with fresh matching evidence can lead."""
    snapshot=inventory(root);entries={e['id']:e for e in snapshot['data']}
    ranked=[];alternatives=[]
    for route in config['cloud_routes']:
        if route.get('qualified') is not True:continue
        if route.get('provider')!='openrouter':
            alternatives.append(route);continue
        entry=entries.get(route['model'])
        if not entry or not entry['route_supported']:continue
        try:
            card=json.loads(card_path(root,route['model']).read_text(encoding='utf-8'))
            age=(datetime.now(timezone.utc)-datetime.fromisoformat(card['at'])).total_seconds()
            if not (0<=age<30*86400 and card['passed'] is True and card['suite']==SUITE
                    and card['fingerprint']==entry['fingerprint']):continue
            latency=sum(c['seconds'] for c in card['cases'])/len(card['cases'])
            ranked.append((latency,route))
        except (OSError,KeyError,TypeError,ValueError,ZeroDivisionError):continue
    # All admitted candidates passed the same suite; latency only breaks that tie.
    return [r for _,r in sorted(ranked,key=lambda pair:pair[0])]+alternatives

def main():
    from .run import configuration
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('refresh');sub.add_parser('list');sub.add_parser('rank')
    e=sub.add_parser('evaluate');e.add_argument('model')
    args=p.parse_args();s=Store();root=s.root;s.close()
    if args.command=='refresh':result=refresh(root)
    elif args.command=='list':result=inventory(root)
    elif args.command=='evaluate':result=evaluate(root,configuration(),args.model)
    else:result=ranked_routes(root,configuration())
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
