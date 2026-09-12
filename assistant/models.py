"""Free-only cloud leadership through Claude Code; bounded local Ollama workers."""
from __future__ import annotations
import json
import os
import subprocess
import time
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
    """Parse a model's JSON answer, recovering common small-model formatting faults.

    Accepted recoveries: code fences anywhere, leading/trailing prose, a <think> block, and
    trailing commas. Anything else still fails, so a malformed answer is a repairable error rather
    than a silently guessed result."""
    if not isinstance(text,str): raise ValueError('Model output is not text')
    text=text.strip()
    try: return json.loads(text)
    except ValueError: pass
    import re
    text=re.sub(r'<think>.*?</think>','',text,flags=re.S).strip()
    fence=re.search(r'```(?:json)?\s*\n(.*?)\n```',text,flags=re.S)
    if fence: text=fence.group(1).strip()
    decoder=json.JSONDecoder()
    for i,ch in enumerate(text):
        if ch not in '{[': continue
        candidate=text[i:]
        for attempt in (candidate, re.sub(r',(\s*[}\]])',r'\1',candidate)):
            try: return decoder.raw_decode(attempt)[0]
            except ValueError: continue
        break  # only the first JSON-looking start is considered; no guessing deeper
    raise ValueError('Model output is not valid JSON')

class RouteRejected(CloudUnavailable):
    """A call completed but its evidence failed policy (substitution or cost); result discarded."""
    def __init__(self, outcome, message):
        super().__init__(message); self.outcome=outcome

RATE_LIMIT_MARKERS=('429','rate limit','rate-limit','too many requests','quota')

def openrouter_key_usage(fetch=None):
    """Return the key's cumulative usage (credits) from /api/v1/key, or raise.

    A `limit` of null there means the key has no credit limit configured on OpenRouter; it is not
    an error and not evidence of free usage. Usage deltas are the cost evidence used here."""
    fetch=fetch or request_json
    token=os.environ.get('OPENROUTER_API_KEY','')
    if not token: raise CloudUnavailable('OPENROUTER_API_KEY is not set')
    data=fetch('https://openrouter.ai/api/v1/key',headers={'Authorization':'Bearer '+token},timeout=30)
    info=data.get('data',data) if isinstance(data,dict) else {}
    usage=Decimal(str(info.get('usage')))
    if not usage.is_finite(): raise ValueError('Unknown key usage')
    return usage, {'limit': info.get('limit'), 'is_free_tier': info.get('is_free_tier'),
                   'limit_remaining': info.get('limit_remaining')}

def check_models(route, wrapper, require_evidence=True):
    """Every model that actually served the request must be the pinned model."""
    usage=wrapper.get('modelUsage')
    actual=sorted(usage.keys()) if isinstance(usage,dict) else []
    if not actual and require_evidence:
        raise RouteRejected('rejected_model_missing','No model usage evidence returned')
    substituted=[m for m in actual if m!=route['model']]
    if substituted:
        raise RouteRejected('rejected_model_substitution','Unexpected model served the request')
    return actual

def openrouter_ask(model, prompt, timeout=120, max_tokens=4096, fetch=None):
    fetch = fetch or request_json
    token=os.environ.get('OPENROUTER_API_KEY','')
    if not token: raise CloudUnavailable('OPENROUTER_API_KEY is not set')
    response=fetch('https://openrouter.ai/api/v1/chat/completions',{
        'model':model,'stream':False,'temperature':0,'max_tokens':max_tokens,
        'provider':{'allow_fallbacks':False},
        'reasoning':{'effort':'none','exclude':True},
        'usage':{'include':True},
        'messages':[{'role':'system','content':'Return only the requested result. Do not claim evidence that was not supplied.'},
                    {'role':'user','content':prompt}],
    },{'Authorization':'Bearer '+token,'HTTP-Referer':'http://127.0.0.1/assistant.html',
       'X-Title':'Korts Assistant'},timeout=timeout)
    usage=response.get('usage') or {}
    if 'cost' not in usage:
        # An envelope carrying neither usage nor any finish_reason is an unfinished generation, not a
        # cost-policy violation; OpenRouter returns one intermittently (observed repeatedly on a cold
        # route). Reporting it as a rejection applied the 30-minute policy cooldown and, with a single
        # configured route, took cloud leadership offline for up to an hour after one transient blip.
        # Treat it as a normal outage so it retries on the short backoff. The content is still refused,
        # because its cost was never verified.
        if not any((choice or {}).get('finish_reason') for choice in (response.get('choices') or [])):
            raise CloudUnavailable('OpenRouter returned an incomplete generation without usage')
        raise RouteRejected('rejected_cost_missing', 'OpenRouter response did not report cost')
    try:
        verify_zero_reported_cost({'total_cost_usd':usage['cost']})
    except CloudUnavailable as exc:
        raise RouteRejected('rejected_cost_nonzero', str(exc)) from exc
    actual=str(response.get('model',''))
    if not actual:
        raise RouteRejected('rejected_model_missing', 'OpenRouter response did not identify the serving model')
    if actual not in (model,model.removesuffix(':free')):
        raise RouteRejected('rejected_model_substitution', 'OpenRouter returned a different model than requested')
    choices=response.get('choices') or []
    if not choices: raise CloudUnavailable('OpenRouter returned no response choice')
    content=(choices[0].get('message',{}).get('content') or '').strip()
    if not content: raise CloudUnavailable('OpenRouter returned no visible content')
    return parse_json(content),{'provider':'openrouter','model':model,'actual_models':[actual],
                                'cost_usd':usage['cost'],
                                'cost_evidence':{'method':'response_usage','delta':str(usage['cost'])}}

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
    def __init__(self, config, store, fetch=None, runner=None):
        self.config,self.store=config,store
        self.fetch=fetch or request_json
        self.runner=runner or subprocess.run
        self.context={}
    def _record(self, route, outcome, started, prompt, required=False, **extra):
        from .state import record_invocation
        try:
            record_invocation(self.store.db, route.get('provider','unknown'), route.get('model','unknown'), outcome,
                duration_ms=int((time.monotonic()-started)*1000), prompt=prompt,
                task_id=self.context.get('task_id'), job_id=self.context.get('job_id'),
                purpose=self.context.get('purpose'), **extra)
        except Exception:
            if required:
                raise
    def ask(self, prompt):
        from .state import route_available, route_result
        errors=[]
        routes=self.config['cloud_routes']
        if self.config.get('catalog_routing') is True:
            from .catalog import ranked_routes
            try: routes=ranked_routes(self.store.root,self.config)
            except Exception as e:
                raise CloudUnavailable('Catalog refresh or evaluation data unavailable') from e
        require_cost=self.config.get('require_zero_cost_evidence',True)
        for route in routes:
            provider=route.get('provider','unknown')
            started=time.monotonic()
            try:
                validate_route(route)
                if hasattr(self.store,'db') and not route_available(self.store.db,route):
                    errors.append(provider+': cooldown');continue
                if provider=='openrouter':
                    verify_free_catalog(route['model'],self.fetch('https://openrouter.ai/api/v1/models'))
                self.store.reserve_call(provider,int(self.config['daily_caps'][provider]))
                if provider=='openrouter':
                    result, evidence = openrouter_ask(route['model'], prompt,
                        timeout=int(self.config.get('cloud_timeout_seconds',120)),
                        max_tokens=int(self.config.get('cloud_max_tokens',4096)), fetch=self.fetch)
                    self._record(route, 'ok', started, prompt, required=True,
                        actual_models=evidence['actual_models'], cost_evidence=evidence['cost_evidence'],
                        result=json.dumps(result))
                    route_result(self.store.db, route, True)
                    return result, evidence
                env=claude_env(route)
                cwd=self.store.root/'control'; cwd.mkdir(exist_ok=True)
                # Deliberately no arbitrary tools in planning/review: controller executes validated jobs.
                cmd=[self.config.get('claude_bin','claude'), '--bare', '-p', '--model',route['model'],
                     '--output-format','json','--tools','', '--setting-sources','',
                     '--strict-mcp-config','--mcp-config','{"mcpServers":{}}', '--max-turns','1',
                     '--max-budget-usd','0']
                p=self.runner(cmd,input=prompt,cwd=cwd,env=env,capture_output=True,
                    text=True,encoding='utf-8',timeout=int(self.config.get('cloud_timeout_seconds',600)))
                try: wrapper=json.loads(p.stdout or '{}')
                except ValueError: wrapper={}
                text=(str(wrapper.get('result',''))+' '+(p.stderr or '')[-2000:]).lower()
                if p.returncode or wrapper.get('is_error') or wrapper.get('subtype') not in ('success',None):
                    limited=any(m in text for m in RATE_LIMIT_MARKERS)
                    self._record(route,'rate_limited' if limited else 'failed',started,prompt)
                    route_result(self.store.db,route,False,'rate limited' if limited else 'call failed',rate_limited=limited)
                    raise CloudUnavailable('Claude Code did not complete successfully')
                verify_zero_reported_cost(wrapper)
                actual=check_models(route,wrapper,self.config.get('require_model_evidence',True))
                evidence={'method':'none'}
                result=parse_json(wrapper.get('result',''))
                # Claude Code's total_cost_usd is its own price estimate, not the provider's bill; it is recorded only.
                self._record(route,'ok',started,prompt,required=True,actual_models=actual,
                    cost_reported={'claude_code_estimate_usd':wrapper.get('total_cost_usd')},
                    cost_evidence=evidence,result=wrapper.get('result',''))
                route_result(self.store.db,route,True)
                return result, {'provider':provider,'model':route['model'],'actual_models':actual,'cost_evidence':evidence}
            except RouteRejected as e:
                self._record(route,e.outcome,started,prompt,actual_models=None,
                    cost_evidence={'reason':str(e)})
                route_result(self.store.db,route,False,e.outcome,base_seconds=1800)
                errors.append(provider+': '+e.outcome)
            except Exception as e:
                # Avoid logging CLI stderr or keys. Full model outputs stay in private runtime only.
                limited=any(m in str(e).lower() for m in RATE_LIMIT_MARKERS)
                outcome='rate_limited' if limited else 'failed'
                self._record(route,outcome,started,prompt)
                route_result(self.store.db,route,False,outcome,rate_limited=limited)
                errors.append(provider+': '+type(e).__name__)
        raise CloudUnavailable('No qualified free cloud route completed: '+', '.join(errors))

def local_ask(worker, prompt):
    base=worker['endpoint'].rstrip('/')
    parsed=urlparse(base)
    if parsed.scheme!='http' or parsed.hostname not in ('127.0.0.1','localhost'):
        raise ValueError('Use a local Ollama endpoint or localhost SSH tunnel')
    model=worker['model']
    if model.endswith(('-cloud',':cloud')): raise ValueError('Local worker cannot silently use cloud')
    num_predict=int(worker.get('num_predict',4096))
    # A CPU-only role measured ~6.8 tokens/second, so a full num_predict answer needs ~600 s there:
    # the previous fixed 600 s timeout cut those off just before they finished. Scale with the
    # budget the role is actually allowed to produce, and let a slow role raise it explicitly.
    timeout=int(worker.get('timeout_seconds',max(600,num_predict//4)))
    data=request_json(base+'/api/chat',{'model':model,'stream':False,
        'think':worker.get('think',False),
        'keep_alive':worker.get('keep_alive','10m'),
        'messages':[{'role':'system','content':worker['instructions']}, {'role':'user','content':prompt}],
        'options':{'num_ctx':worker.get('num_ctx',8192),'num_predict':num_predict}},timeout=timeout)
    return data['message']['content']
