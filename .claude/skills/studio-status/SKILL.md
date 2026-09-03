---
name: studio-status
description: Report what the unattended studio has done: progress, queue, tasks, deferred items, recent commits. Use when asked "what happened", "status", "progress", or on return after days away.
---
1. Read `PROGRESS.md` and the newest file in `reports/`.
2. List `tasks/in-progress/`, `tasks/deferred/` (the human's to-do list) and the last 5 of `tasks/done/`.
3. If Redis is reachable: `redis-cli -a $REDIS_PASSWORD LLEN jobs:image` etc., and `GET worker:gpu:status`.
4. `git log --oneline -20`.
5. Summarise in this order: blocked/deferred items first, then what got done, then what is running now. Quote the reasons from task files verbatim; do not soften them.
