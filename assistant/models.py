"""Free-only cloud leadership through Claude Code; bounded local Ollama workers."""
from __future__ import annotations
import json
import os
import subprocess
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse

class CloudUnavailable(RuntimeError): pass

def request_json(url, payload=None, headers=None, timeout=120):
    req=Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                headers={'Content-Type':'application/json', **(headers or {})})
    with urlopen(req,timeout=timeout) as res: return json.load(res)

def validate_route(route):
    provider=route.get('provider'); model=route.get('model','')
    if route.get('qualified') is not True:
        raise ValueError('Cloud route must pass qualification before unattended use')
    if provider=='openrouter':
        if not model.endswith(':free'): raise ValueError('Only explicit :free OpenRouter models allowed')
    elif provider=='ollama-cloud':
        if not (model.endswith('-cloud') or model.endswith(':cloud')):
            raise ValueError('Ollama leadership requires a cloud model')
        if route.get('included_usage_confirmed') is not True:
            raise ValueError('Confirm included free allowance and disable paid extra usage first')
    else: raise ValueError('Leadership must use an approved free cloud provider')

def verify_free_catalog(model, catalog):
    entry=next((m for m in catalog.get('data',[]) if m.get('id')==model),None)
    if not entry: raise ValueError('Free model missing from live catalog')
    prices=entry.get('pricing',{})
    if not {'prompt','completion'} <= prices.keys(): raise ValueError('Unknown pricing')
    for value in prices.values():
        try:
            amount=Decimal(str(value))
            if not amount.is_finite() or amount != 0: raise ValueError('Nonzero or unknown model pricing')
        except InvalidOperation as e: raise ValueError('Unknown pricing') from e

def claude_env(route):
    # Do not inherit alternative providers, model aliases or paid Anthropic authentication.
    env={k:v for k,v in os.environ.items() if not k.startswith(('ANTHROPIC_', 'CLAUDE_CODE_', 'CLAUDE_CONFIG_DIR'))}
    model=route['model']
    env['ANTHROPIC_API_KEY']=''
    if route['provider']=='openrouter':
        token=os.environ.get('OPENROUTER_API_KEY','')
        if not token: raise CloudUnavailable('OPENROUTER_API_KEY is not set')
        env['ANTHROPIC_BASE_URL']='https://openrouter.ai/api'
        env['ANTHROPIC_AUTH_TOKEN']=token
    else:
        env['ANTHROPIC_BASE_URL']='http://127.0.0.1:11434'
        env['ANTHROPIC_AUTH_TOKEN']='ollama'
    for tier in ('FABLE','OPUS','SONNET','HAIKU'):
        env['ANTHROPIC_DEFAULT_'+tier+'_MODEL']=model
    env['ANTHROPIC_MODEL']=model
    env['ANTHROPIC_SMALL_FAST_MODEL']=model
    env['CLAUDE_CODE_SUBAGENT_MODEL']=model
    env['CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC']='1'
    return env

def parse_json(text):
    text=text.strip()
    if text.startswith('```'):
        text='\n'.join(text.splitlines()[1:-1])
    return json.loads(text)

def openrouter_ask(model, prompt, timeout=120, max_tokens=4096):
    token=os.environ.get('OPENROUTER_API_KEY','')
    if not token: raise CloudUnavailable('OPENROUTER_API_KEY is not set')
    response=request_json('https://openrouter.ai/api/v1/chat/completions',{
        'model':model,'stream':False,'temperature':0,'max_tokens':max_tokens,
        'provider':{'allow_fallbacks':False},
        'reasoning':{'effort':'none','exclude':True},
        'usage':{'include':True},
        'messages':[{'role':'system','content':'Return only the requested result. Do not claim evidence that was not supplied.'},
                    {'role':'user','content':prompt}],
    },{'Authorization':'Bearer '+token,'HTTP-Referer':'http://127.0.0.1/assistant.html',
       'X-Title':'Korts Assistant'},timeout=timeout)
    usage=response.get('usage') or {}
    if 'cost' not in usage: raise CloudUnavailable('OpenRouter response did not report cost')
    verify_zero_reported_cost({'total_cost_usd':usage['cost']})
    actual=str(response.get('model',''))
    if actual not in (model,model.removesuffix(':free')):
        raise CloudUnavailable('OpenRouter returned a different model than requested')
    choices=response.get('choices') or []
    if not choices: raise CloudUnavailable('OpenRouter returned no response choice')
    content=(choices[0].get('message',{}).get('content') or '').strip()
    if not content: raise CloudUnavailable('OpenRouter returned no visible content')
    return parse_json(content),{'provider':'openrouter','model':model,'actual_model':actual,'cost_usd':usage['cost']}

def verify_zero_reported_cost(wrapper):
    """Reject responses when Claude Code reports any charge or unreadable cost."""
    reported=[]
    if 'total_cost_usd' in wrapper: reported.append(wrapper['total_cost_usd'])
    usage=wrapper.get('modelUsage',{})
    if usage is None: usage={}
    if not isinstance(usage,dict): raise CloudUnavailable('Claude Code returned invalid cost data')
    for details in usage.values():
        if not isinstance(details,dict): raise CloudUnavailable('Claude Code returned invalid cost data')
        if 'costUSD' in details: reported.append(details['costUSD'])
    for value in reported:
        try:
            amount=Decimal(str(value))
        except InvalidOperation as e:
            raise CloudUnavailable('Claude Code returned unreadable cost data') from e
        if not amount.is_finite() or amount != 0:
            raise CloudUnavailable('Claude Code reported nonzero inference cost')

class Cloud:
    def __init__(self, config, store): self.config,self.store=config,store
    def ask(self, prompt):
        errors=[]
        routes=self.config['cloud_routes']
        if self.config.get('catalog_routing') is True:
            from .catalog import ranked_routes
            try: routes=ranked_routes(self.store.root,self.config)
            except Exception as e:
                raise CloudUnavailable('Catalog refresh or evaluation data unavailable') from e
        for route in routes:
            provider=route.get('provider','unknown')
            try:
                validate_route(route)
                if provider=='openrouter':
                    verify_free_catalog(route['model'],request_json('https://openrouter.ai/api/v1/models'))
                self.store.reserve_call(provider,int(self.config['daily_caps'][provider]))
                if provider=='openrouter':
                    return openrouter_ask(route['model'],prompt,
                        timeout=int(self.config.get('cloud_timeout_seconds',120)),
                        max_tokens=int(self.config.get('cloud_max_tokens',4096)))
                env=claude_env(route)
                cwd=self.store.root/'control'; cwd.mkdir(exist_ok=True)
                # Deliberately no arbitrary tools in planning/review: controller executes validated jobs.
                cmd=[self.config.get('claude_bin','claude'), '--bare', '-p', '--model',route['model'],
                     '--output-format','json','--tools','', '--setting-sources','',
                     '--strict-mcp-config','--mcp-config','{"mcpServers":{}}', '--max-turns','1',
                     '--max-budget-usd','0']
                p=subprocess.run(cmd,input=prompt,cwd=cwd,env=env,capture_output=True,
                    text=True,encoding='utf-8',timeout=int(self.config.get('cloud_timeout_seconds',600)))
                if p.returncode: raise CloudUnavailable('Claude Code failed; run the documented account/compatibility check')
                wrapper=json.loads(p.stdout)
                if wrapper.get('is_error') or wrapper.get('subtype') not in ('success',None):
                    raise CloudUnavailable('Claude Code did not complete successfully')
                verify_zero_reported_cost(wrapper)
                result=parse_json(wrapper.get('result',''))
                return result, {'provider':provider,'model':route['model']}
            except Exception as e:
                # Avoid logging CLI stderr or keys. Full model outputs stay in private runtime only.
                errors.append(provider+': '+type(e).__name__)
        raise CloudUnavailable('No qualified free cloud route completed: '+', '.join(errors))

def local_ask(worker, prompt):
    base=worker['endpoint'].rstrip('/')
    parsed=urlparse(base)
    if parsed.scheme!='http' or parsed.hostname not in ('127.0.0.1','localhost'):
        raise ValueError('Use a local Ollama endpoint or localhost SSH tunnel')
    model=worker['model']
    if model.endswith(('-cloud',':cloud')): raise ValueError('Local worker cannot silently use cloud')
    data=request_json(base+'/api/chat',{'model':model,'stream':False,
        'think':worker.get('think',False),
        'messages':[{'role':'system','content':worker['instructions']}, {'role':'user','content':prompt}],
        'options':{'num_ctx':worker.get('num_ctx',8192),'num_predict':4096}},timeout=600)
    return data['message']['content']
