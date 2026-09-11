"""Persistent task runner.

Runs as a long-lived service (Windows Task Scheduler at logon/boot, see
scripts/install-runner-service.ps1) or for a bounded number of hours. Guarantees:

* one active runner per runtime (SQLite lease with heartbeat; a crashed runner's lease is
  reclaimed after expiry or when its local process is gone),
* one step per task at a time (per-task lease), so no job is executed twice concurrently,
* interrupted work resumes from persisted task state after a restart,
* bounded retries with exponential cooldowns per task,
* cross-task dependencies inside one project,
* global pause, cancellation and owner decisions honored between steps,
* mailbox items for blocked tasks and review-ready results.
"""
from __future__ import annotations
import json
import logging
import logging.handlers
import os
import time
import uuid
from datetime import timedelta
from . import state
from .core import Store, now

log = logging.getLogger('assistant.runner')

TERMINAL = ('draft_ready', 'blocked', 'cancelled', 'owner_approved', 'owner_rejected',
            'needs_input', 'awaiting_plan_approval')   # the last two wait for Kort, not the runner
DEPENDENCY_DONE = ('draft_ready', 'owner_approved')
DEPENDENCY_FAILED = ('cancelled', 'owner_rejected')
LEASE_TTL = 900   # longer than one bounded model call plus margin


def setup_logging(root):
    logs = root / 'logs'
    logs.mkdir(exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(logs / 'runner.log', maxBytes=2_000_000, backupCount=5,
                                                   encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    root_logger = logging.getLogger('assistant')
    if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root_logger.handlers):
        root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


def dependency_state(store, task):
    """Return 'ready', 'waiting' or 'failed' for a task's cross-task dependencies."""
    worst = 'ready'
    for dep in task['data'].get('after', []):
        try:
            other = store.get(dep)
        except ValueError:
            return 'failed'
        if other['project'] != task['project']:
            return 'failed'
        if other['status'] in DEPENDENCY_FAILED:
            return 'failed'
        if other['status'] not in DEPENDENCY_DONE:
            worst = 'waiting'
    return worst


def cooling(task):
    retry = task['data'].get('retry') or {}
    until = state.parse(retry.get('next_at'))
    return until is not None and until > state.utcnow()


def _job_signature(data):
    return json.dumps([(j.get('id'), j.get('status'), j.get('attempts')) for j in data.get('jobs', [])])


def apply_retry_policy(store, before, config):
    """After one step: reset the retry counter on progress; otherwise back off exponentially and
    block with a mailbox item once the bounded retry budget is spent."""
    after = store.get(before['id'])
    data = after['data']
    failed = after['status'] == 'awaiting_cloud' or any(
        j.get('status') == 'pending' and j.get('last_error') for j in data.get('jobs', []))
    progressed = (after['status'] != before['status'] or
                  _job_signature(after['data']) != _job_signature(before['data']))
    if failed:
        retry = data.get('retry') or {'count': 0}
        retry['count'] = int(retry.get('count', 0)) + 1
        limit = int(config.get('max_task_retries', 8))
        if retry['count'] > limit:
            data['retry'] = retry
            data['blocker'] = 'Retry budget exhausted after repeated cloud/worker failures'
            store.update(after['id'], 'blocked', data, data['blocker'])
            return 'blocked'
        base = int(config.get('retry_base_seconds', 60))
        delay = min(int(config.get('retry_max_seconds', 3600)), base * 2 ** (retry['count'] - 1))
        retry['next_at'] = state.iso(state.utcnow() + timedelta(seconds=delay))
        data['retry'] = retry
        store.save_data(after['id'], data)
        state.emit(store.db, after['project'], 'retry.cooldown', 'Retrying after a cooldown', task_id=after['id'])
        return 'cooldown'
    if progressed and data.get('retry'):
        data.pop('retry', None)
        store.save_data(after['id'], data)
    return 'progress' if progressed else 'idle'


def notify(store, before, after):
    """Mailbox items are idempotent per task and decision type."""
    if after['status'] == before['status']:
        return
    label = after['project'] + ('/' + after['subproject'] if after.get('subproject') else '')
    goal = after['goal'][:140]
    if after['status'] == 'blocked':
        state.mail(store.db, after['project'], 'blocked', 'Task blocked: ' + goal,
                   'A task in ' + label + ' is blocked and needs a decision or retry. Open the task to see the '
                   'recorded blocker, evidence and repair history.', task_id=after['id'],
                   dedupe_key=after['id'] + ':blocked')
    if after['status'] in ('draft_ready', 'blocked'):
        state.post_message(store.db, after['id'], after['project'], 'assistant',
                           'Result is ready for your review. Nothing was merged, deployed or published.'
                           if after['status'] == 'draft_ready' else
                           'I am blocked on this task. Open it to see the reason and evidence; you can retry, '
                           'request a repair or cancel.')
    if after['status'] == 'draft_ready':
        state.mail(store.db, after['project'], 'review', 'Ready for your review: ' + goal,
                   'Cloud review accepted every job. Nothing has been merged, deployed or published. '
                   'Approve, reject or request a repair from the dashboard.', task_id=after['id'],
                   dedupe_key=after['id'] + ':review')


def process_task(store, task, config, profiles, cloud=None, worker_call=None):
    from .run import step
    from .models import local_ask
    owner = 'step:' + uuid.uuid4().hex
    name = 'task:' + task['id']
    if not state.acquire_lease(store.db, name, owner, LEASE_TTL):
        return 'leased'
    try:
        before = store.get(task['id'])
        if before['status'] in TERMINAL:
            return 'terminal'
        result = step(store, before, config, profiles, cloud=cloud, worker_call=worker_call or local_ask)
        outcome = apply_retry_policy(store, before, config)
        notify(store, before, store.get(task['id']))
        return 'waiting' if result == 'waiting' and outcome == 'idle' else outcome
    finally:
        state.release_lease(store.db, name, owner)


def runnable(store, task):
    if task['status'] in TERMINAL or cooling(task):
        return False
    dep = dependency_state(store, task)
    if dep == 'failed':
        data = task['data']
        data['blocker'] = 'A task this depends on was cancelled, rejected or is missing'
        store.update(task['id'], 'blocked', data, data['blocker'])
        notify(store, task, store.get(task['id']))
        return False
    if dep == 'waiting':
        if task['status'] != 'waiting_dependency':
            store.update(task['id'], 'waiting_dependency', task['data'], 'Waiting for dependency tasks')
        return False
    if task['status'] == 'waiting_dependency':
        store.update(task['id'], 'planned' if not task['data'].get('jobs') else 'working', task['data'],
                     'Dependencies satisfied')
    return True


def recover(store):
    """Called once at startup: mark resumption of interrupted jobs and reset display state."""
    resumed = 0
    for task in store.list():
        for job in task['data'].get('jobs', []):
            if job.get('status') == 'running':
                resumed += 1
                state.emit(store.db, task['project'], 'resume', 'Resuming work interrupted by a restart',
                           task_id=task['id'], job_id=job['id'], worker=job.get('worker'))
    with store.db:
        store.db.execute("UPDATE worker_state SET state='idle', task_id=NULL, job_id=NULL "
                         "WHERE state IN ('working','waiting')")
        store.db.execute('DELETE FROM gpu_lease')  # held only by a dead process after a restart
    return resumed


def ordered(tasks):
    # Oldest updated first so one busy task cannot starve the others.
    return sorted(tasks, key=lambda t: t['updated'])


class Runner:
    def __init__(self, config, store=None, profiles_loader=None, cloud=None, worker_call=None,
                 sleep=time.sleep, clock=time.monotonic):
        self.config = config
        self.store = store or Store()
        from .run import workers
        self.profiles_loader = profiles_loader or workers
        self.cloud = cloud
        self.worker_call = worker_call
        self.sleep = sleep
        self.clock = clock
        self.owner = 'runner:' + uuid.uuid4().hex
        self.lock_file = self.store.root / 'runner.lock'
        self._last_maintenance = None

    # -- lifecycle
    def start(self):
        if not state.acquire_lease(self.store.db, 'runner', self.owner, LEASE_TTL):
            info = state.lease_info(self.store.db, 'runner') or {}
            raise RuntimeError('Another runner is active (pid %s on %s, heartbeat %s)' % (
                info.get('pid'), info.get('host'), info.get('heartbeat')))
        # Legacy lock file kept for tools (assistant.sync) that check it; the lease is authoritative.
        self.lock_file.write_text(str(os.getpid()), encoding='utf-8')
        state.set_setting(self.store.db, 'runner', {'pid': os.getpid(), 'started': now()})
        resumed = recover(self.store)
        state.record_health(self.store.db, 'runner', True, 'started; resumed %d job(s)' % resumed)
        log.info('runner started, resumed %d interrupted job(s)', resumed)

    def stop(self):
        try:
            state.record_health(self.store.db, 'runner', True, 'stopped cleanly')
            state.release_lease(self.store.db, 'runner', self.owner)
        finally:
            self.lock_file.unlink(missing_ok=True)

    def heartbeat(self):
        if not state.renew_lease(self.store.db, 'runner', self.owner, LEASE_TTL):
            raise RuntimeError('Runner lease lost; stopping to avoid duplicate execution')
        state.set_setting(self.store.db, 'runner.heartbeat', now())

    def _report_due(self):
        last = getattr(self, '_last_report', None)
        if last is None or self.clock() - last >= 3600:
            self._last_report = self.clock()
            return True
        return False

    def paused(self):
        return state.is_paused(self.store.db) or (self.store.root / 'PAUSE').exists()

    # -- work
    def maintenance(self):
        """Index notes, run cheap health checks, daily report. Failures never stop task work."""
        if self._last_maintenance and self.clock() - self._last_maintenance < 300:
            return
        self._last_maintenance = self.clock()
        try:
            self.store.index(self.store.root / 'vault')
        except Exception as e:
            log.warning('vault index failed: %s', type(e).__name__)
        try:
            from . import health
            health.run_checks(self.store, self.config, self.profiles_loader())
            health.daily_report_if_due(self.store)
        except Exception as e:
            log.warning('health checks failed: %s', type(e).__name__)

    def pass_once(self):
        """Process each runnable task at most one step. Returns number of steps that progressed."""
        progressed = 0
        profiles = self.profiles_loader()
        for task in ordered(self.store.list()):
            if self.paused():
                break
            self.heartbeat()
            if not runnable(self.store, task):
                continue
            outcome = process_task(self.store, self.store.get(task['id']), self.config, profiles,
                                   cloud=self.cloud, worker_call=self.worker_call)
            if outcome == 'progress':
                progressed += 1
        return progressed

    def run(self, hours=None, once=False):
        deadline = None if hours is None else self.clock() + hours * 3600
        announced_pause = False
        self.start()
        try:
            while True:
                self.heartbeat()
                if self.paused():
                    if not announced_pause:
                        state.emit(self.store.db, 'system', 'assistant.paused', 'Assistant paused by owner')
                        announced_pause = True
                    if once or hours is not None and (self.store.root / 'PAUSE').exists():
                        break  # legacy bounded runs stop on the PAUSE file, as before
                    self.sleep(int(self.config.get('poll_seconds', 60)))
                    continue
                announced_pause = False
                self.maintenance()
                progressed = self.pass_once()
                if progressed or once or self._report_due():
                    try:
                        self.store.report()
                    except OSError as e:
                        log.warning('report failed: %s', type(e).__name__)
                if once or (deadline is not None and self.clock() >= deadline):
                    break
                # Keep going quickly while work is flowing; otherwise poll.
                self.sleep(2 if progressed else int(self.config.get('poll_seconds', 60)))
        finally:
            self.stop()


def main(argv=None):
    import argparse
    from .run import configuration
    p = argparse.ArgumentParser(description='Persistent assistant task runner')
    p.add_argument('--hours', type=float, default=None, help='Stop after this many hours (default: run until stopped)')
    p.add_argument('--once', action='store_true')
    a = p.parse_args(argv)
    config = configuration()
    store = Store()
    setup_logging(store.root)
    Runner(config, store).run(hours=a.hours, once=a.once)


if __name__ == '__main__':
    main()
