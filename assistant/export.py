"""Hand an owner-approved code result back to Kort as a patch with a rollback point.

The assistant never merges, pushes, deploys or publishes. After Kort approves a task whose code
passed configured checks and combined cloud review, this module:
  1. verifies the approved integration revision is unchanged,
  2. writes a git patch series and bundle into the private runtime (exports/<task>/),
  3. checks whether the patch still applies to the source checkout's *current* HEAD
     (conflict detection) inside a throwaway clone, never touching the real checkout,
  4. records the rollback point (the base revision) and exact commands in README.txt.
Applying the patch to the real repository stays a manual, reviewed step."""
from __future__ import annotations
import json
import subprocess
import tempfile
from pathlib import Path
from . import state
from .codework import git


def export(store, config, tid, actor='owner'):
    task = store.get(tid)
    if task['status'] != 'owner_approved':
        raise ValueError('Only results you approved can be exported')
    data = task['data']
    review = data.get('integration_review') or {}
    if not any(j.get('workspace') for j in data.get('jobs', [])):
        raise ValueError('This task produced no code')
    settings = config['code_projects'][task['project']]
    workspace = store.root / 'workspaces' / tid / '_integration'
    head = git(workspace, 'rev-parse', 'HEAD').strip()
    if review.get('revision') != head:
        raise ValueError('Integration revision changed after review; do not export')
    if git(workspace, 'status', '--porcelain', '--untracked-files=no').strip():
        raise ValueError('Integration workspace has uncommitted changes')
    base = git(workspace, 'config', '--local', '--get', 'assistant.base').strip()
    out = store.root / 'exports' / tid
    out.mkdir(parents=True, exist_ok=True)
    patches = git(workspace, 'format-patch', '--no-stat', '-o', str(out), base + '..' + head).split()
    branch = git(workspace, 'rev-parse', '--abbrev-ref', 'HEAD').strip()
    git(workspace, 'bundle', 'create', str(out / 'result.bundle'), branch, '^' + base)
    source = Path(settings['source']).expanduser().resolve()
    current = git(source, 'rev-parse', 'HEAD').strip()
    applies, detail = True, 'Source is still at the reviewed base revision.'
    if current != base:
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / 'check'
            subprocess.run(['git', 'clone', '--no-hardlinks', '--quiet', str(source), str(clone)], check=True,
                           capture_output=True, timeout=300)
            check = subprocess.run(['git', '-C', str(clone), 'apply', '--check', *patches],
                                   capture_output=True, text=True, timeout=120)
            applies = check.returncode == 0
            detail = ('Source moved on since review, but the patch still applies cleanly. Re-run checks after applying.'
                      if applies else 'CONFLICT: the source changed and the patch does not apply. Create a new task '
                      'from the current source; do not hand-merge unreviewed changes.')
    readme = [
        'Owner-approved assistant result for task ' + tid,
        'Reviewed base revision (rollback point): ' + base,
        'Reviewed result revision: ' + head,
        'Source HEAD at export: ' + current,
        detail, '',
        'Apply (in your own checkout, on a new branch):',
        '  git switch -c assistant-result-' + tid[:8] + ' ' + base,
        '  git am ' + ' '.join(Path(p).name for p in patches),
        'Then run the project checks yourself before merging.', '',
        'Roll back (before merge): git switch - && git branch -D assistant-result-' + tid[:8],
        'Roll back (after merge):  git revert <merge or commit ids above>', '',
        'Nothing has been merged, pushed, deployed or published by the assistant.']
    (out / 'README.txt').write_text('\n'.join(readme) + '\n', encoding='utf-8')
    record = {'at': state.iso(), 'base': base, 'head': head, 'source_head': current, 'applies': applies,
              'patches': [Path(p).name for p in patches]}
    data['export'] = record
    store.update(tid, 'owner_approved', data, 'Exported approved patch for manual integration', force=True)
    state.audit(store.db, actor, 'task.export', True, project=task['project'], task_id=tid,
                detail=json.dumps({'applies': applies}))
    return {'folder': str(out), **record}
