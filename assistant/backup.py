"""Backup and restore of the private runtime.

A backup is one zip with a manifest of SHA-256 hashes: a consistent SQLite snapshot (online
backup API, safe while the runner is active), the vault, artifacts, reports and the editable
profiles/config. Credentials are never included: API keys live in environment variables and the
dashboard password file (dashboard.json) is excluded. Restore only targets an empty folder and
verifies hashes and SQLite integrity before reporting success."""
from __future__ import annotations
import hashlib
import json
import sqlite3
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from . import state

INCLUDE_DIRS = ('vault', 'artifacts', 'reports')
INCLUDE_FILES = ('workers.json', 'config.json', 'office.json')
EXCLUDED_NAMES = ('dashboard.json',)   # credentials: never copied


def _sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def source_revision():
    try:
        repo = Path(__file__).resolve().parents[1]
        return subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'], capture_output=True,
                              text=True, timeout=10).stdout.strip() or None
    except Exception:
        return None


def create(root, dest_dir=None, keep=14):
    root = Path(root).resolve()
    dest_dir = Path(dest_dir or root / 'backups')
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    target = dest_dir / ('backup-' + stamp + '.zip')
    manifest = {'created': state.iso(), 'source_revision': source_revision(), 'files': {}}
    with tempfile.TemporaryDirectory() as tmp:
        snap = Path(tmp) / 'state.sqlite'
        src = sqlite3.connect(root / 'state.sqlite')
        out = sqlite3.connect(snap)
        try:
            src.backup(out)
        finally:
            out.close()
            src.close()
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as z:
            z.write(snap, 'state.sqlite')
            manifest['files']['state.sqlite'] = _sha(snap)
            for name in INCLUDE_FILES:
                p = root / name
                if p.is_file():
                    z.write(p, name)
                    manifest['files'][name] = _sha(p)
            for d in INCLUDE_DIRS:
                base = root / d
                if not base.is_dir():
                    continue
                for p in sorted(base.rglob('*')):
                    if not p.is_file() or p.is_symlink() or p.name in EXCLUDED_NAMES:
                        continue
                    rel = p.relative_to(root).as_posix()
                    z.write(p, rel)
                    manifest['files'][rel] = _sha(p)
            z.writestr('manifest.json', json.dumps(manifest, indent=2))
    backups = sorted(dest_dir.glob('backup-*.zip'))
    for old in backups[:-keep] if keep else []:
        old.unlink()
    db = sqlite3.connect(root / 'state.sqlite')
    try:
        state.ensure_schema(db)
        state.set_setting(db, 'backup.last', {'at': manifest['created'], 'file': target.name,
                                              'files': len(manifest['files'])})
    finally:
        db.close()
    return target


def _safe_member(name):
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or ':' in name or '\\' in name:
        raise ValueError('Unsafe path in backup: ' + name)
    return p


def verify(archive):
    with zipfile.ZipFile(archive) as z:
        manifest = json.loads(z.read('manifest.json'))
        for name, expected in manifest['files'].items():
            _safe_member(name)
            if hashlib.sha256(z.read(name)).hexdigest() != expected:
                raise ValueError('Hash mismatch for ' + name)
    return manifest


def restore(archive, target):
    """Restore into an empty or new folder; never over a live runtime."""
    target = Path(target).resolve()
    if target.exists() and any(target.iterdir()):
        raise ValueError('Restore target must be empty; stop the runner and restore to a new folder')
    manifest = verify(archive)
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for name in manifest['files']:
            dest = target.joinpath(*_safe_member(name).parts)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(name))
    db = sqlite3.connect(target / 'state.sqlite')
    try:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Restored database failed integrity check')
        tasks = db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]
    finally:
        db.close()
    return {'restored_to': str(target), 'files': len(manifest['files']), 'tasks': tasks,
            'source_revision': manifest.get('source_revision')}


def age_hours(db):
    last = state.get_setting(db, 'backup.last')
    at = state.parse(last.get('at')) if isinstance(last, dict) else None
    return None if at is None else (state.utcnow() - at).total_seconds() / 3600


def main(argv=None):
    import argparse
    from .core import runtime_root
    p = argparse.ArgumentParser(description='Back up or restore the private assistant runtime')
    sub = p.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('create')
    c.add_argument('--dest')
    c.add_argument('--keep', type=int, default=14)
    v = sub.add_parser('verify')
    v.add_argument('archive')
    r = sub.add_parser('restore')
    r.add_argument('archive')
    r.add_argument('target')
    a = p.parse_args(argv)
    if a.cmd == 'create':
        print(create(runtime_root(), a.dest, a.keep))
    elif a.cmd == 'verify':
        print(json.dumps(verify(a.archive), indent=2)[:4000])
    else:
        print(json.dumps(restore(a.archive, a.target), indent=2))


if __name__ == '__main__':
    main()
