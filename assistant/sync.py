"""Pull-only GitHub refresh between runs. Never uploads the private vault."""
from pathlib import Path
import subprocess
from .run import REPO
from .core import runtime_root

def git(*args):
    p=subprocess.run(['git','-C',str(REPO),*args],capture_output=True,text=True)
    if p.returncode:raise RuntimeError(p.stderr.strip() or 'Git command failed')
    return p.stdout.strip()

def main():
    if (runtime_root()/'runner.lock').exists():raise RuntimeError('Stop the runner before changing its code')
    if git('status','--porcelain'):raise RuntimeError('Checkout has edits; commit or preserve them before updating')
    remote=git('remote','get-url','origin')
    accepted=('https://github.com/korttjepkema34-collab/korts-repository.git','git@github.com:korttjepkema34-collab/korts-repository.git')
    if remote not in accepted:raise RuntimeError('Origin is not the expected personal GitHub repository')
    branch=git('branch','--show-current')
    if not branch:raise RuntimeError('Detached HEAD; select the intended branch first')
    git('fetch','origin');git('merge','--ff-only','origin/'+branch)
    print('Updated to '+git('rev-parse','HEAD')+'. Run tests before restarting. Private vault was not uploaded.')
if __name__=='__main__':main()
