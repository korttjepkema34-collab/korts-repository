# Task board

One markdown file per task. Move files between folders; git history is the audit trail.

- `backlog/` - not started. The orchestrator picks the lowest `priority:` number first.
- `in-progress/` - being worked. The orchestrator appends log lines at the bottom.
- `done/` - finished and accepted by the human.

Filename: `<id>-<slug>.md`, e.g. `007-player-idle-sprite.md`. IDs are zero-padded and unique.

Template:

```markdown
# 007 Player idle sprite
priority: 3
roles: artist-2d, reviewer
depends_on: 003

## Goal
One sentence.

## Acceptance
- Bullet list the reviewer can check.

## Notes
Anything the workers need: references, sizes, constraints.
```

A task the orchestrator cannot progress gets `BLOCKED: <reason>` appended and stays in
`in-progress/` until a human edits it.
