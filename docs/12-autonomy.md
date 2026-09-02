# 12 - Unattended operation

The owner turns the studio on and comes back days later. No input in between. This document is
the contract for how the system behaves in that mode. Every role file assumes it.

## Principles

1. **Never wait for a human.** A question that would have gone to the owner gets the most
   conservative reasonable answer, is written to `docs/decisions.md` with "(auto)" and the run
   continues. The owner reads the log on return and can reverse anything.
2. **Never get stuck on one thing.** Every job has an attempt cap. Every task has a coder-run cap.
   A task that exhausts its caps moves to `tasks/deferred/` and the studio moves on. Deferred
   tasks are retried once a day with the slow escalation model.
3. **Never run out of work.** When the backlog is empty and nothing is in progress, the
   orchestrator generates the next few tasks from `docs/10-game-design.md`, capped per day so a
   bad day does not produce a hundred junk tasks.
4. **Never depend on the gaming PC for code.** The coder runs on the server with headless Godot
   and file edits. Art, 3D, and audio wait for the GPU box; code and planning never do.
5. **Latency does not matter, correctness does.** In unattended mode the escalation model can be
   the biggest model that fits in RAM even at a few tokens per second. Slow and right beats fast
   and wrong when nobody is waiting.
6. **Leave a trail.** Every decision and outcome is appended to the task file. A daily report goes
   to `reports/YYYY-MM-DD.md` and `PROGRESS.md`. The task board and reports are committed and
   pushed daily so the story is in git even if the server dies.

## Rails (env vars in `server/.env`)

| Rail | Default | What it prevents |
|---|---|---|
| `max_attempts` per job | 3 | Infinite regeneration of an asset the reviewer keeps rejecting |
| `MAX_CODER_RUNS_PER_TASK` | 3 | The coder rewriting the same file forever |
| `MAX_INFLIGHT_JOBS` | 12 | Flooding the GPU queue while the gaming PC is off |
| `MAX_GENERATED_TASKS_PER_DAY` | 10 | Runaway self-planning |
| `STALE_JOB_SECONDS` | 5400 | A job lost when the worker died mid-run staying "running" forever |
| `MIN_FREE_GB` | 20 | Filling the disk with candidates |
| Ollama `OLLAMA_MAX_LOADED_MODELS` | 2 | RAM thrash between orchestrator and reviewer models |

## What the owner finds on return

- `PROGRESS.md` at the repo root: latest report. `reports/` has one per day.
- `tasks/done/`: what got finished, with the log of every job inside each file.
- `tasks/deferred/`: what the studio could not do on its own, with the reason. This is the
  owner's to-do list.
- `assets/approved/`: everything that passed review. `assets/rejected/`: what did not, with the
  reason in each sidecar.
- `git log`: the coder's merges and the daily checkpoints.
- `docs/decisions.md`: any "(auto)" decisions the orchestrator made on the owner's behalf.

## Known limits of unattended mode today

- Audio and 3D results are auto-approved on existence. The reviewer only judges images so far.
- The reviewer is a small local vision model. It will let some drift through and reject some
  good work. The attempt cap keeps that bounded.
- The coder has no editor. It cannot build complex scenes visually; it writes `.tscn` files as
  text. Simple scenes are fine. Complex UI will be rough until an MCP-driven session polishes it.
- If Ollama dies, the loop logs errors every cycle and keeps trying. Nothing is lost; the queue
  and state are on disk.
