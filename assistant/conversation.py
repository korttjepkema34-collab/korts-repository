"""Task conversations, clarifying questions, plan confirmation and safe attachments.

Owner messages are stored per task and are searchable. When the orchestrator asks clarifying
questions, the task waits in `needs_input`; the owner's reply becomes a recorded clarification and
the task is re-planned. When a task asks for plan confirmation, the plan (assumptions, jobs and
acceptance criteria) waits in `awaiting_plan_approval` until the owner approves it."""
from __future__ import annotations
import base64
import hashlib
import re
import uuid
from pathlib import Path
from . import state

TEXT_TYPES = {'.txt', '.md', '.csv', '.json'}
IMAGE_TYPES = {'.png', '.jpg', '.jpeg', '.webp'}
MAX_ATTACHMENT = 2_000_000
NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9 ._-]{0,80}$')
IMAGE_MAGIC = {b'\x89PNG': '.png', b'\xff\xd8\xff': '.jpg', b'RIFF': '.webp'}


def plan_summary(data):
    lines = []
    if data.get('assumptions'):
        lines.append('Assumptions: ' + '; '.join(data['assumptions']))
    for j in data.get('jobs', []):
        lines.append('- %s → %s: %s (done when: %s)%s' % (
            j['id'], j['worker'], j['brief'][:300], '; '.join(j['acceptance'])[:300],
            ' [after ' + ', '.join(j['depends_on']) + ']' if j['depends_on'] else ''))
    return '\n'.join(lines)


def owner_message(store, actor, projects, tid, text):
    """Record an owner message; answer pending questions or queue an artifact-specific revision."""
    task = store.get(tid)
    if task['project'] not in projects:
        raise ValueError('Unknown task')
    state.post_message(store.db, tid, task['project'], 'owner', text, actor)
    data = task['data']
    if task['status'] == 'needs_input':
        data.setdefault('clarifications', []).append({'at': state.iso(), 'questions': data.pop('questions', []),
                                                      'answer': text.strip()[:4000]})
        data.pop('proposed_plan', None)
        store.update(tid, 'planned', data, 'Owner answered clarifying questions', force=True)
        state.resolve_mail_for_task(store.db, tid, 'Answered', actor)
        state.post_message(store.db, tid, task['project'], 'assistant',
                           'Thanks — I will re-plan with your answer.')
        return 'answered'
    return 'noted'


def approve_plan(store, actor, projects, tid, approve=True, note=''):
    task = store.get(tid)
    if task['project'] not in projects:
        raise ValueError('Unknown task')
    if task['status'] != 'awaiting_plan_approval':
        raise ValueError('This task is not waiting for plan approval')
    data = task['data']
    if approve:
        data['plan_approved'] = {'by': actor, 'at': state.iso(), 'note': note[:1000]}
        store.update(tid, 'working', data, 'Owner approved the plan', force=True)
        state.post_message(store.db, tid, task['project'], 'assistant', 'Plan approved. Starting work.')
    else:
        data.setdefault('clarifications', []).append({'at': state.iso(), 'questions': ['Plan rejected'],
                                                      'answer': note.strip()[:4000] or 'Plan rejected without notes'})
        data.pop('jobs', None)
        store.update(tid, 'planned', data, 'Owner rejected the plan; re-planning', force=True)
        state.post_message(store.db, tid, task['project'], 'assistant', 'Understood — I will make a new plan.')
    state.resolve_mail_for_task(store.db, tid, 'Plan approved' if approve else 'Plan rejected', actor)
    state.audit(store.db, actor, 'plan.approve' if approve else 'plan.reject', True, project=task['project'], task_id=tid)


def attachments_dir(root, tid):
    return Path(root) / 'attachments' / tid


def add_attachment(store, actor, projects, tid, name, content_b64):
    task = store.get(tid)
    if task['project'] not in projects:
        raise ValueError('Unknown task')
    name = (name or '').strip()
    if not NAME_RE.fullmatch(name) or '..' in name:
        raise ValueError('Use a simple file name (letters, numbers, spaces, dot, dash, underscore)')
    ext = Path(name).suffix.lower()
    if ext not in TEXT_TYPES | IMAGE_TYPES:
        raise ValueError('Allowed attachments: ' + ', '.join(sorted(TEXT_TYPES | IMAGE_TYPES)))
    try:
        raw = base64.b64decode(content_b64 or '', validate=True)
    except ValueError:
        raise ValueError('Attachment must be base64 encoded')
    if not raw or len(raw) > MAX_ATTACHMENT:
        raise ValueError('Attachment must be between 1 byte and 2 MB')
    if ext in TEXT_TYPES:
        try:
            raw.decode('utf-8')
        except UnicodeDecodeError:
            raise ValueError('Text attachments must be UTF-8')
        kind = 'text'
    else:
        if not any(raw.startswith(m) for m in IMAGE_MAGIC):
            raise ValueError('File content is not a PNG, JPEG or WebP image')
        kind = 'image'
    aid = uuid.uuid4().hex
    d = attachments_dir(store.root, tid)
    d.mkdir(parents=True, exist_ok=True)
    (d / (aid + ext)).write_bytes(raw)
    with store.db:
        store.db.execute('INSERT INTO attachments VALUES (?,?,?,?,?,?,?,?,?)',
                         (aid, tid, task['project'], name, kind, len(raw), hashlib.sha256(raw).hexdigest(),
                          state.iso(), actor))
    state.audit(store.db, actor, 'attachment.add', True, project=task['project'], task_id=tid, detail=name)
    return aid


def list_attachments(db, tid):
    rows = db.execute('SELECT id,name,kind,size,sha256,at FROM attachments WHERE task_id=? ORDER BY at', (tid,)).fetchall()
    return [dict(zip(('id', 'name', 'kind', 'size', 'sha256', 'at'), r)) for r in rows]


def attachment_context(store, tid, config, limit=20000):
    """Text attachments go to models as data. Images are sent only when a vision-capable route has
    been qualified (config vision_input_qualified); otherwise their absence is stated explicitly."""
    out, used = [], 0
    for a in list_attachments(store.db, tid):
        p = attachments_dir(store.root, tid) / (a['id'] + Path(a['name']).suffix.lower())
        if a['kind'] == 'text' and p.is_file():
            body = p.read_text(encoding='utf-8')[:max(0, limit - used)]
            used += len(body)
            out.append({'name': a['name'], 'kind': 'text', 'content': body})
        elif a['kind'] == 'image':
            out.append({'name': a['name'], 'kind': 'image',
                        'content': None if not config.get('vision_input_qualified') else 'attached',
                        'note': 'Image NOT visible to you: no qualified vision route. Do not describe or judge it.'
                        if not config.get('vision_input_qualified') else 'Image supplied separately.'})
    return out
