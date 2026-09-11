"""Refuse commits that could leak private assistant data into the public repository.

Checks staged (or given) files for: files from the private runtime (state.sqlite, vault notes
with personal/business scope metadata, dashboard.json, artifacts, backups), API-key patterns and
private-key blocks. Run by .githooks/pre-commit (enable once: git config core.hooksPath .githooks)
and by the test suite against the whole tree."""
from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BLOCKED_NAMES = {'state.sqlite', 'state.sqlite-wal', 'state.sqlite-shm', 'dashboard.json', 'runner.lock'}
BLOCKED_PARTS = {'KortAssistant', 'artifacts', 'backups', '.history'}
SECRET_PATTERNS = [
    re.compile(r'sk-or-v1-[0-9a-f]{20,}'),                       # OpenRouter keys
    re.compile(r'sk-ant-[A-Za-z0-9_-]{20,}'),                     # Anthropic keys
    re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}'),                    # GitHub tokens
    re.compile(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----'),
    re.compile(r'(?i)(?:api[_-]?key|token|password)\s*[:=]\s*["\'][^"\'\s]{16,}["\']'),
]
PRIVATE_SCOPE = re.compile(r'(?m)^project:\s*(personal|business)\s*$')
TEMPLATE_DIRS = ('memory/',)   # public templates are allowed to declare scope, but must say so


def staged():
    out = subprocess.run(['git', '-C', str(REPO), 'diff', '--cached', '--name-only', '--diff-filter=ACMR'],
                         capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line]


def problems(paths):
    found = []
    for rel in paths:
        p = REPO / rel
        parts = set(Path(rel).parts)
        if Path(rel).name in BLOCKED_NAMES or parts & BLOCKED_PARTS:
            found.append((rel, 'private runtime file'))
            continue
        if not p.is_file() or p.stat().st_size > 2_000_000:
            continue
        try:
            text = p.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        for pat in SECRET_PATTERNS:
            if pat.search(text) and 'tests/' not in rel and 'check_private_leak' not in rel:
                found.append((rel, 'looks like a credential'))
                break
        header = text[4:text.find('\n---\n', 4)] if text.startswith('---\n') and '\n---\n' in text[4:] else ''
        if rel.endswith('.md') and PRIVATE_SCOPE.search(header):  # the file's own frontmatter only
            if not rel.startswith(TEMPLATE_DIRS) or 'template: true' not in text:
                found.append((rel, 'note declares personal/business scope; private notes belong in the vault'))
    return found


def main(argv):
    paths = argv or staged()
    found = problems(paths)
    for rel, why in found:
        print('BLOCKED %s: %s' % (rel, why))
    if found:
        print('Private data must stay in the runtime folder (outside this public repository).')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
