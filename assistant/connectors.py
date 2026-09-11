"""Business connector policy gate (email, calendar, accounting, storage, project tools).

No service is implemented or enabled here. This module is the gate every future connector must
pass through:
  * each connector is declared in the private runtime file connectors.json with explicit read
    scopes, write actions, allowed projects and the name of the environment variable holding its
    credential (the credential itself never enters the repository, SQLite, logs or the browser),
  * a connector is unusable until enabled AND qualified (its failure and account-expiry tests
    were run and recorded),
  * every external write needs a mailbox approval bound to the exact action payload; approvals
    are consumed once, so a restart cannot repeat an external effect,
  * every read/write attempt and result is written to the audit log.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from . import state

TEMPLATE = {
    'example-email': {
        'kind': 'email', 'enabled': False, 'qualified': False, 'projects': ['business'],
        'credential_env': 'KORT_EMAIL_TOKEN',
        'read_scopes': ['list_unread_subjects'], 'write_actions': ['create_draft'],
        'notes': 'Template only. Drafts are created, never sent. Define exact scopes before enabling.'}
}


class ConnectorDenied(PermissionError):
    pass


def load(root):
    p = Path(root) / 'connectors.json'
    if not p.exists():
        return {}
    data = json.loads(p.read_text(encoding='utf-8'))
    return data if isinstance(data, dict) else {}


def _connector(root, name, project):
    c = load(root).get(name)
    if not c:
        raise ConnectorDenied('Unknown connector')
    if c.get('enabled') is not True or c.get('qualified') is not True:
        raise ConnectorDenied('Connector is disabled until its qualification passes')
    if project not in c.get('projects', []):
        raise ConnectorDenied('Connector is not authorized for this project')
    if not os.environ.get(c.get('credential_env', '') or '_missing_'):
        raise ConnectorDenied('Connector credential is not configured (or has expired)')
    return c


def authorize_read(store, name, project, scope, actor):
    try:
        c = _connector(store.root, name, project)
        if scope not in c.get('read_scopes', []):
            raise ConnectorDenied('Read scope not granted')
    except ConnectorDenied as e:
        state.audit(store.db, actor, 'connector.read.denied', False, project=project, detail=name + ':' + str(e))
        raise
    state.audit(store.db, actor, 'connector.read', True, project=project, detail=name + ':' + scope)
    return c


def action_digest(name, action, payload):
    return hashlib.sha256(json.dumps([name, action, payload], sort_keys=True).encode()).hexdigest()


def request_write(store, name, project, action, payload, task_id, actor):
    """Create (idempotently) a mailbox approval for one exact external write."""
    c = _connector(store.root, name, project)
    if action not in c.get('write_actions', []):
        raise ConnectorDenied('Write action not granted')
    digest = action_digest(name, action, payload)
    mid = state.mail(store.db, project, 'review', 'Approve external action: %s %s' % (name, action),
                     'The assistant wants to perform this external change:\n' + json.dumps(payload, indent=2)[:3000] +
                     '\nAnswer "approve ' + digest[:12] + '" to allow it once.', task_id=task_id,
                     dedupe_key='connector:' + digest)
    state.audit(store.db, actor, 'connector.write.requested', True, project=project, task_id=task_id,
                detail=name + ':' + action + ':' + digest[:12])
    return digest


def consume_approval(store, name, project, action, payload, actor):
    """Return True exactly once for an owner-approved write; later calls return False."""
    digest = action_digest(name, action, payload)
    row = store.db.execute("SELECT id,response,status FROM mailbox WHERE dedupe_key=?", ('connector:' + digest,)).fetchone()
    if not row or row[2] != 'answered' or (row[1] or '').strip().lower() != 'approve ' + digest[:12]:
        return False
    with store.db:
        cur = store.db.execute("UPDATE mailbox SET status='resolved', updated=? WHERE id=? AND status='answered'",
                               (state.iso(), row[0]))
    if cur.rowcount != 1:
        return False
    state.audit(store.db, actor, 'connector.write.approved', True, project=project, detail=name + ':' + action)
    return True


def record_result(store, name, project, action, ok, detail, actor):
    state.audit(store.db, actor, 'connector.write.' + ('ok' if ok else 'failed'), ok, project=project,
                detail=(name + ':' + action + ':' + str(detail))[:500])
