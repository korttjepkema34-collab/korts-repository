"""Safe note viewing and editing for the private vault.

Scope is owned by the path: a user may read/edit notes only under the projects they are allowed,
plus shared/ (read; editing shared requires the owner role). Every save keeps the previous text
under vault/.history/ (hidden folders are never indexed or sent to models)."""
from __future__ import annotations
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from .core import SCOPES, safe_path, note_record, _frontmatter

LINK_RE = re.compile(r'\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]')
MAX_NOTE_BYTES = 400_000


def _scope_of(rel):
    parts = Path(rel).parts
    if not parts or parts[0] not in SCOPES:
        raise ValueError('Notes live under shared/, personal/, business/ or game/')
    return parts[0]


def check_access(rel, projects, write=False, owner=False):
    scope = _scope_of(rel)
    if scope == 'shared':
        if write and not owner:
            raise PermissionError('Only the owner edits shared notes')
        return scope
    if scope not in projects:
        raise PermissionError('No access to that project')
    return scope


def _visible(vault, projects):
    for scope in ('shared', *[p for p in projects if p in SCOPES]):
        base = vault / scope
        if not base.is_dir():
            continue
        for p in sorted(base.rglob('*.md')):
            rel = p.relative_to(vault)
            if p.is_symlink() or any(part.startswith('.') for part in rel.parts):
                continue
            yield rel.as_posix(), p


def list_notes(vault, projects, query='', limit=300):
    vault = Path(vault).resolve()
    out = []
    q = query.lower().strip()
    for rel, p in _visible(vault, projects):
        if p.stat().st_size > MAX_NOTE_BYTES:
            continue
        text = p.read_text(encoding='utf-8', errors='replace')
        if q and q not in text.lower() and q not in rel.lower():
            continue
        rec = note_record(rel, _scope_of(rel), text)
        out.append({'path': rel, 'title': p.stem, 'scope': rec['scope'], 'subproject': rec['subproject'],
                    'status': rec['status'], 'kind': rec['kind'], 'producer': rec['producer'],
                    'updated': rec['note_updated'], 'conflicts': bool(rec['metadata_errors'])})
        if len(out) >= limit:
            break
    return out


def backlinks(vault, projects, rel):
    target = Path(rel).stem.lower()
    target_path = rel.lower().removesuffix('.md')
    hits = []
    for other, p in _visible(Path(vault).resolve(), projects):
        if other == rel:
            continue
        for link in LINK_RE.findall(p.read_text(encoding='utf-8', errors='replace')):
            name = link.strip().lower().removesuffix('.md')
            if name == target or name == target_path or name.endswith('/' + target):
                hits.append(other)
                break
    return hits


def history_dir(vault, rel):
    return Path(vault) / '.history' / rel


def revisions(vault, rel):
    d = history_dir(vault, rel)
    return sorted((p.name for p in d.glob('*.md')), reverse=True) if d.is_dir() else []


def read(vault, projects, rel):
    check_access(rel, projects)
    p = safe_path(vault, rel)
    if p.suffix != '.md' or not p.is_file():
        raise ValueError('Unknown note')
    text = p.read_text(encoding='utf-8', errors='replace')
    rec = note_record(rel, _scope_of(rel), text)
    meta, body = _frontmatter(text)
    links = sorted(set(l.strip() for l in LINK_RE.findall(text)))
    return {'path': rel, 'text': text, 'body': body, 'metadata': meta, 'status': rec['status'],
            'producer': rec['producer'], 'sources': rec['sources'], 'reviewer': rec['reviewer'],
            'supersedes': rec['supersedes'], 'metadata_errors': rec['metadata_errors'],
            'digest': hashlib.sha256(text.encode()).hexdigest(), 'links': links,
            'backlinks': backlinks(vault, projects, rel), 'revisions': revisions(vault, rel)}


def _set_meta(text, updates):
    meta, body = _frontmatter(text)
    lines = []
    if text.startswith('---\n') and text.find('\n---\n', 4) > 0:
        header = text[4:text.find('\n---\n', 4)].splitlines()
        seen = set()
        for line in header:
            key = line.split(':', 1)[0].strip().lower().replace('-', '_') if ':' in line else None
            if key in updates:
                if updates[key] is not None:
                    lines.append(key + ': ' + str(updates[key]))
                seen.add(key)
            else:
                lines.append(line)
        for k, v in updates.items():
            if k not in seen and v is not None:
                lines.append(k + ': ' + str(v))
    else:
        lines = [k + ': ' + str(v) for k, v in updates.items() if v is not None]
    return '---\n' + '\n'.join(lines) + '\n---\n' + body


def save(vault, projects, rel, text, actor, expected_digest=None, owner=False):
    """Write a note, preserving the previous revision. Refuses stale edits (digest mismatch) and
    scope changes made through frontmatter."""
    scope = check_access(rel, projects, write=True, owner=owner)
    if len(text.encode()) > MAX_NOTE_BYTES:
        raise ValueError('Note too large')
    p = safe_path(vault, rel)
    if p.suffix != '.md':
        raise ValueError('Notes must be Markdown files')
    old = p.read_text(encoding='utf-8') if p.exists() else None
    if old is not None and expected_digest and hashlib.sha256(old.encode()).hexdigest() != expected_digest:
        raise ValueError('The note changed since you opened it; reload before saving')
    meta, _ = _frontmatter(text)
    if meta.get('project', scope) != scope:
        raise ValueError('Project metadata must match the note folder')
    today = datetime.now(timezone.utc).date().isoformat()
    updates = {'updated_date': today}
    status = meta.get('status', 'proposed').lower()
    if status == 'approved':
        if owner:
            # The owner re-approves exactly what was saved.
            updates['approved_revision'] = hashlib.sha256(_frontmatter(text)[1].encode()).hexdigest()
            updates['producer'] = meta.get('producer') or actor
            updates['note_id'] = meta.get('note_id') or rel.removesuffix('.md').replace('/', '-')
            updates['sources'] = meta.get('sources') or 'owner edit'
        else:
            updates['status'] = 'proposed'   # a non-owner edit cannot stay approved
    text = _set_meta(text, updates)
    if old is not None:
        h = history_dir(vault, rel)
        h.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        (h / (stamp + '.md')).write_text(old, encoding='utf-8')
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')
    return hashlib.sha256(text.encode()).hexdigest()


def read_revision(vault, projects, rel, revision):
    check_access(rel, projects)
    safe_path(vault, rel)
    if not re.fullmatch(r'\d{8}T\d{6}\d*Z\.md', revision):
        raise ValueError('Unknown revision')
    p = history_dir(vault, rel) / revision
    if not p.is_file():
        raise ValueError('Unknown revision')
    return p.read_text(encoding='utf-8', errors='replace')


def set_status(vault, projects, rel, status, actor, owner=False, reason='', superseded_by=''):
    """Mark a note superseded or disputed (or restore it to proposed) with a recorded reason."""
    if status not in ('superseded', 'disputed', 'proposed'):
        raise ValueError('Status must be superseded, disputed or proposed')
    note = read(vault, projects, rel)
    updates = {'status': status, 'status_reason': reason.replace('\n', ' ')[:300] or None,
               'status_by': actor}
    if status == 'superseded':
        if not superseded_by:
            raise ValueError('Name the note that replaces this one')
        check_access(superseded_by, projects)
        if _scope_of(superseded_by) != _scope_of(rel):
            raise ValueError('A note can only be superseded within its own scope')
        updates['superseded_by'] = superseded_by
        new = read(vault, projects, superseded_by)
        save(vault, projects, superseded_by,
             _set_meta(new['text'], {'supersedes': note['metadata'].get('note_id') or rel}),
             actor, new['digest'], owner)
    return save(vault, projects, rel, _set_meta(note['text'], updates), actor, note['digest'], owner)


def propose_skill(vault, projects, rel, actor, owner=False):
    """Turn an approved lesson into a skill *proposal*. Promotion into repository skills stays a
    reviewed pull request; this only prepares the draft privately."""
    note = read(vault, projects, rel)
    if note['status'] != 'approved':
        raise ValueError('Only approved knowledge can be proposed as a skill')
    scope = _scope_of(rel)
    # Same folder keeps the same path-owned project/subproject boundary.
    target = (Path(rel).parent / (Path(rel).stem + '.skill-proposal.md')).as_posix()
    text = ('---\nkind: skill-proposal\nstatus: proposed\nproducer: ' + actor + '\nsources: ' + rel +
            '\nproject: ' + scope + '\n---\n# Skill proposal: ' + Path(rel).stem + '\n\n'
            'Review before promotion. Promotion into the repository requires a reviewed pull request and '
            'must not include private details.\n\n' + note['body'])
    if safe_path(vault, target).exists():
        raise ValueError('A proposal already exists for this note')
    save(vault, projects, target, text, actor, owner=owner)
    return target
