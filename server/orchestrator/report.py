"""Daily progress report in reports/YYYY-MM-DD.md, plus a rolling PROGRESS.md at the repo root."""
from __future__ import annotations

import time
from pathlib import Path

from . import gitops, traces


def write(repo: Path, state, queue_depths: dict, worker_alive: bool, events: list[str]) -> None:
    day = time.strftime("%Y-%m-%d")
    jobs = state.data["jobs"].values()
    counts = {}
    for j in jobs:
        counts[j.get("status", "?")] = counts.get(j.get("status", "?"), 0) + 1
    done = sorted(p.name for p in (repo / "tasks" / "done").glob("*.md"))
    deferred = sorted(p.name for p in (repo / "tasks" / "deferred").glob("*.md"))
    inprog = sorted(p.name for p in (repo / "tasks" / "in-progress").glob("*.md"))
    approved = sum(1 for p in (repo / "assets" / "approved").rglob("*") if p.is_file() and p.suffix != ".json" and not p.name.startswith("."))
    _, log = gitops.git(repo, "log", "--since=1.day", "--oneline")
    tc = traces.counts(repo)
    body = f"""# Progress report {day}

| | |
|---|---|
| Worker online now | {'yes' if worker_alive else 'no'} |
| Queue depths | {queue_depths} |
| Jobs by status (all time) | {counts} |
| Approved assets | {approved} |
| Tasks done | {len(done)} |
| Tasks in progress | {len(inprog)} |
| Tasks deferred | {len(deferred)} |
| Training data | coder runs {tc['coder_runs']} ({tc['coder_passed']} passed), reviewer verdicts {tc['verdicts']}, your verdicts {tc['overrides']} |

## Done
{chr(10).join('- ' + d for d in done) or '- none yet'}

## In progress
{chr(10).join('- ' + d for d in inprog) or '- none'}

## Deferred (retried once a day with the escalation model)
{chr(10).join('- ' + d for d in deferred) or '- none'}

## Commits in the last day
```
{log or '(none)'}
```

## Events today
{chr(10).join('- ' + e for e in events[-200:]) or '- none'}
"""
    (repo / "reports" / f"{day}.md").write_text(body)
    (repo / "PROGRESS.md").write_text("# Latest progress\n\nSee `reports/` for the daily history.\n\n" + body)
