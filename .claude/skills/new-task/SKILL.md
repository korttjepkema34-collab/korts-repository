---
name: new-task
description: Write a new task file for the studio's backlog in the format the orchestrator expects. Use when asked to add work, queue a feature, or file a task.
---
1. Next id = highest number across `tasks/*/` + 1, zero-padded to 3 digits. Filename `<id>-<slug>.md`.
2. Template (see `tasks/README.md`): title line `# <id> <Title>`, `priority: N` (1 = first), `roles:` from orchestrator, coder, artist-2d, audio, reviewer, optional `depends_on:`, then `## Goal` (one sentence), `## Acceptance` (bullets a gate or reviewer can check: files, tests, `visual_check` descriptions), `## Notes`.
3. Keep it doable by one or two roles in under an hour of worker time; split otherwise. Art tasks cite `style/references/`. Code tasks name files and tests. Never ask for design decisions inside a task; decide, and log it in `docs/decisions.md`.
4. Stay inside `docs/14-world-bible.md` and `docs/17-gameplay-systems.md`. Do not grow the prototype scope in `docs/10-game-design.md`.
