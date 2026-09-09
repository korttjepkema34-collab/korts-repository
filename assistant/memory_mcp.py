"""Small read-only stdio MCP server. Each process is restricted to one project."""
import json
import os
import sys
from .core import Store, PROJECTS

def dispatch(message, store, project):
    if project not in PROJECTS: raise ValueError('ASSISTANT_PROJECT must select one project')
    method=message.get('method');rid=message.get('id')
    if rid is None:return None
    result={}
    if method=='initialize':
        result={'protocolVersion':message.get('params',{}).get('protocolVersion','2024-11-05'),
                'capabilities':{'tools':{}},'serverInfo':{'name':'kort-memory','version':'0.1.0'}}
    elif method=='tools/list':
        result={'tools':[{'name':'memory_search','description':'Search '+project+' and shared notes; returns source paths and text.',
            'inputSchema':{'type':'object','properties':{'query':{'type':'string'}},'required':['query'],'additionalProperties':False}}]}
    elif method=='tools/call':
        params=message.get('params',{})
        if params.get('name')!='memory_search':
            return {'jsonrpc':'2.0','id':rid,'error':{'code':-32602,'message':'Unknown tool'}}
        query=params.get('arguments',{}).get('query')
        if not isinstance(query,str):
            return {'jsonrpc':'2.0','id':rid,'error':{'code':-32602,'message':'query must be text'}}
        result={'content':[{'type':'text','text':json.dumps(store.search(project,query))}]}
    elif method!='ping':
        return {'jsonrpc':'2.0','id':rid,'error':{'code':-32601,'message':'Unknown method'}}
    return {'jsonrpc':'2.0','id':rid,'result':result}

def main():
    project=os.environ.get('ASSISTANT_PROJECT','game');store=Store()
    try:
        for line in sys.stdin:
            if len(line)>1000000:continue
            try:reply=dispatch(json.loads(line),store,project)
            except Exception:reply={'jsonrpc':'2.0','id':None,'error':{'code':-32600,'message':'Invalid request'}}
            if reply is not None:print(json.dumps(reply),flush=True)
    finally:store.close()
if __name__=='__main__':main()
