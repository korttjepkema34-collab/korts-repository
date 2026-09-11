"""Owner control actions. Every action is validated, scoped to the actor's projects and audited.

The dashboard and CLI both call these functions; nothing here talks to models. Approval of a
draft records Kort's decision only: it never merges, deploys or publishes anything."""
from __future__ import annotations
from . import state
from .core import PROJECTS

CANCELLABLE = ('planned', 'working', 'awaiting_cloud', 'waiting_dependency', 'blocked', 'draft_ready',
               'needs_input', 'awaiting_plan_approval')


def store_config_attempts(store):
    try:
        from .run import configuration
        return configuration().get('max_worker_attempts', 3)
    except Exception:
        return 3


class Forbidden(PermissionError):
    pass


def _task(store, tid, projects):
    task = store.get(tid)
    if task['project'] not in projects:
        # Same message as a missing task so IDs from other projects cannot be probed.
        raise ValueError('Unknown task')
    return task


def _done(store, actor, action, task=None, detail=''):
    state.audit(store.db, actor, action, True, project=task['project'] if task else None,
                task_id=task['id'] if task else None, detail=detail)


def pause(store, actor):
    state.set_setting(store.db, 'paused', True)
    state.emit(store.db, 'system', 'assistant.paused', 'Assistant paused by owner')
    _done(store, actor, 'pause')


def resume(store, actor):
    state.set_setting(store.db, 'paused', False)
    (store.root / 'PAUSE').unlink(missing_ok=True)
    state.emit(store.db, 'system', 'assistant.resumed', 'Assistant resumed by owner')
    _done(store, actor, 'resume')


def add_task(store, actor, projects, project, goal, subproject='', after=None, confirm_plan=False):
    if project not in projects:
        raise Forbidden('No access to that project')
    tid = store.create(project, goal, subproject, after=after, confirm_plan=confirm_plan)
    state.post_message(store.db, tid, project, 'owner', goal, actor)
    _done(store, actor, 'task.add', store.get(tid))
    return tid


def cancel(store, actor, projects, tid):
    task = _task(store, tid, projects)
    if task['status'] not in CANCELLABLE:
        raise ValueError('Task cannot be cancelled from status ' + task['status'])
    data = task['data']
    data['cancelled'] = {'by': actor, 'at': state.iso(), 'previous_status': task['status']}
    store.update(tid, 'cancelled', data, 'Cancelled by owner', force=True)
    state.resolve_mail_for_task(store.db, tid, 'Cancelled', actor)
    _done(store, actor, 'task.cancel', task)


def retry(store, actor, projects, tid):
    """Retry blocked jobs with a fresh attempt budget; the repair history is preserved."""
    task = _task(store, tid, projects)
    if task['status'] not in ('blocked', 'awaiting_cloud', 'working', 'planned'):
        raise ValueError('Only blocked or waiting tasks can be retried')
    data = task['data']
    data.pop('blocker', None)
    data.pop('retry', None)
    for job in data.get('jobs', []):
        if job['status'] == 'blocked':
            job.setdefault('retry_history', []).append({'at': state.iso(), 'by': actor,
                                                         'attempts': job.get('attempts'),
                                                         'reason': job.get('reason')})
            job['status'] = 'pending'
            # Keep counting attempts (artifact names include the attempt number) but allow a
            # fresh bounded budget from here.
            job['max_attempts'] = job.get('attempts', 0) + int(store_config_attempts(store))
            job.pop('reason', None)
    store.update(tid, 'working' if data.get('jobs') else 'planned', data, 'Owner requested retry', force=True)
    state.resolve_mail_for_task(store.db, tid, 'Retried', actor)
    _done(store, actor, 'task.retry', task)


def decide(store, actor, projects, tid, approve, note=''):
    """Record Kort's approval or rejection of a review-ready result."""
    task = _task(store, tid, projects)
    if task['status'] != 'draft_ready':
        raise ValueError('Only review-ready results can be approved or rejected')
    data = task['data']
    # Bind the decision to the exact artifacts that were reviewed.
    data['owner_decision'] = {'approved': bool(approve), 'by': actor, 'at': state.iso(), 'note': note[:2000],
                              'artifact_digests': {j['id']: j.get('digest') for j in data.get('jobs', [])}}
    status = 'owner_approved' if approve else 'owner_rejected'
    store.update(tid, status, data, 'Owner ' + ('approved' if approve else 'rejected') + ' the result', force=True)
    state.resolve_mail_for_task(store.db, tid, 'Approved' if approve else 'Rejected', actor)
    _done(store, actor, 'task.approve' if approve else 'task.reject', task)


def request_repair(store, actor, projects, tid, job_id, instructions):
    """Send one job back to its specialist with Kort's written instructions."""
    task = _task(store, tid, projects)
    instructions = (instructions or '').strip()
    if not instructions or len(instructions) > 4000:
        raise ValueError('Repair instructions are required (up to 4000 characters)')
    if task['status'] not in ('draft_ready', 'blocked', 'working', 'owner_rejected'):
        raise ValueError('Task is not in a repairable state')
    data = task['data']
    job = next((j for j in data.get('jobs', []) if j['id'] == job_id), None)
    if job is None:
        raise ValueError('Unknown job')
    if job.get('workspace') and job['status'] in ('verified_candidate',):
        raise ValueError('Integrated code candidates need a new task; repair would bypass integration evidence')
    job.setdefault('owner_instructions', []).append({'at': state.iso(), 'by': actor, 'text': instructions})
    job['status'] = 'repair_requested'
    job['max_attempts'] = job.get('attempts', 0) + 2  # two owner-directed repair rounds (W5 default)
    data.pop('blocker', None)
    data.pop('owner_decision', None)
    store.update(tid, 'working', data, 'Owner requested a repair', force=True)
    state.emit(store.db, task['project'], 'repair.requested', 'Owner requested a repair',
               task_id=tid, job_id=job_id, worker=job.get('worker'))
    state.resolve_mail_for_task(store.db, tid, 'Repair requested', actor)
    _done(store, actor, 'task.repair', task, detail='job ' + job_id)


def consent(store, actor, project, grant):
    if project not in PROJECTS:
        raise ValueError('Unknown project')
    state.grant_cloud_consent(store.db, project, actor, grant)


def gaming(store, actor, on, profiles, cancel_active=False):
    from . import gpu
    if on:
        return gpu.enter_gaming(store.db, profiles, actor=actor, cancel_active=cancel_active)
    return gpu.exit_gaming(store.db, profiles, actor=actor)


def answer_mail(store, actor, projects, mail_id, response):
    row = store.db.execute('SELECT project,task_id,status FROM mailbox WHERE id=?', (mail_id,)).fetchone()
    if not row or row[0] not in projects:
        raise ValueError('Unknown mailbox item')
    if not response.strip():
        raise ValueError('Response required')
    with store.db:
        store.db.execute("UPDATE mailbox SET status='answered', response=?, responded_by=?, responded_at=?, "
                         'updated=? WHERE id=?', (response[:2000], actor, state.iso(), state.iso(), mail_id))
    state.audit(store.db, actor, 'mailbox.answer', True, project=row[0], task_id=row[1])
