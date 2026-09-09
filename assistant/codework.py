"""Code candidates in isolated clones, with human-configured check commands.
No merge/push/deploy. Never execute test commands invented by the model.
"""
import json
import subprocess
from pathlib import Path
from .core import safe_path
from .models import parse_json


def git(root,*args):
    p=subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True,encoding='utf-8',timeout=120)
    if p.returncode:raise RuntimeError('Git workspace operation failed: '+p.stderr[:300])
    return p.stdout


def prepare(root, tid, jid, settings):
    if settings.get('execution_enabled') is not True:
        raise ValueError('Code execution is disabled for this project; configure its trusted checks first')
    source=Path(settings['source']).expanduser().resolve()
    git(source,'rev-parse','--show-toplevel')
    dest=Path(root)/'workspaces'/tid/jid
    if not dest.exists():
        dest.parent.mkdir(parents=True,exist_ok=True)
        p=subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(source),str(dest)],capture_output=True,text=True,timeout=120)
        if p.returncode:raise RuntimeError('Could not clone source into isolated workspace')
        revision=git(source,'rev-parse','HEAD').strip()
        git(dest,'checkout','--detach',revision)
        git(dest,'switch','-c','assistant/'+jid)
        # Remove remote to keep a worker workspace from publishing accidentally.
        git(dest,'remote','remove','origin')
    return dest


def permitted(path,settings):
    return (any(path.startswith(prefix) for prefix in settings.get('allowed_prefixes',[]))
            and not any(part.startswith('.') for part in Path(path).parts)
            and Path(path).suffix in {'.py','.gd','.tscn','.tres','.ts','.tsx','.js','.jsx','.css','.html','.json','.md'})


def context(workspace,settings,max_chars=45000):
    result=[];used=0
    for rel in settings.get('context_files',[]):
        p=safe_path(workspace,rel)
        if not permitted(rel,settings):raise ValueError('Context file outside configured scope')
        body=p.read_text(encoding='utf-8') if p.exists() else '(new file)'
        used+=len(body)
        if used>max_chars:raise ValueError('Configured context too large; split the task')
        result.append({'path':rel,'content':body})
    return result


def apply_candidate(workspace,text,settings):
    data=parse_json(text)
    if not isinstance(data,dict) or not isinstance(data.get('files'),list) or not 1<=len(data['files'])<=12:
        raise ValueError('Code worker must return 1-12 files in a JSON files array')
    writes=[];seen=set()
    for f in data['files']:
        rel=f.get('path','');body=f.get('content')
        if not isinstance(rel,str) or not permitted(rel,settings) or rel in seen:
            raise ValueError('Invalid, duplicate or out-of-scope file')
        seen.add(rel);p=safe_path(workspace,rel)
        if not isinstance(body,str) or len(body.encode())>100000:raise ValueError('Invalid file body')
        writes.append((p,body))
    for p,body in writes:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body,encoding='utf-8')
    git(workspace,'add','--',*[f['path'] for f in data['files']])
    diff=git(workspace,'diff','--cached','--no-ext-diff')
    if not diff.strip():raise ValueError('Code worker made no changes')
    if len(diff)>60000:raise ValueError('Diff exceeds review limit; split the task')
    return diff


def check_candidate(workspace,settings):
    commands=settings.get('checks',[])
    if not commands:raise ValueError('No verification commands configured; cannot claim code is verified')
    results=[]
    for command in commands:
        if not isinstance(command,list) or not command or not all(isinstance(x,str) for x in command):
            raise ValueError('Checks must be argv arrays; no shell strings')
        argv=[part.replace('{workspace}',str(workspace)) for part in command]
        try:
            p=subprocess.run(argv,cwd=workspace,capture_output=True,text=True,encoding='utf-8',
                timeout=int(settings.get('check_timeout_seconds',300)),shell=False)
            results.append({'argv':argv,'passed':p.returncode==0,'exit_code':p.returncode,'output':(p.stdout+p.stderr)[-12000:]})
        except (OSError,subprocess.TimeoutExpired) as e:
            results.append({'argv':argv,'passed':False,'error':type(e).__name__})
    return results


def unchanged(workspace, expected_diff):
    """A review must describe the exact tested candidate, not later edits."""
    return (git(workspace,'diff','--cached','--no-ext-diff') == expected_diff
            and not git(workspace,'diff','--no-ext-diff').strip())
