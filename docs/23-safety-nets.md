> **Setup migration notice:** For the personal/business/game assistant, [assistant/SETUP.md](assistant/SETUP.md) and [assistant/DECISIONS.md](assistant/DECISIONS.md) supersede older model, hardware, autonomy and installation choices below. Game design remains preserved.

# 23 - Safety nets: how the studio stays up and fixes itself

Four layers, from cheapest to most powerful. Each one writes down what it did.

## 1. Supervision: nothing stays dead

- `server/supervise.ps1` (Task Scheduler runs this, not the orchestrator directly) restarts the
  orchestrator whenever it exits, with backoff. `worker/run.ps1` does the same for the GPU worker.
- The orchestrator writes `reports/health.json` every cycle: uptime, cycles, errors in the last
  hour, queue depth, open incidents. The doctor and the daily report read it.

## 2. Healing: dependencies get restarted

- Every cycle probes Ollama and Redis. Unreachable for 2 minutes: the loop runs
  `OLLAMA_START_CMD` / `REDIS_START_CMD` from `server/.env` (at most once per 10 minutes).
  Still down after 30 minutes: an incident is opened with a plan for the human.
- Without Redis the loop only writes health. Without Ollama it does bookkeeping only (results,
  closing tasks) and plans nothing, so no work is lost and nothing is invented.
- The GPU worker probes ComfyUI and the audio API before claiming their job kinds. A tool that is
  down gets its `*_start_cmd` from `worker/config.yaml`; its jobs wait on the queue instead of
  failing. The heartbeat says which tools are down.
- Git sanity at every cycle start: a stuck merge is aborted, a leftover coder branch is
  abandoned and the tree returns to main clean.
- Disk below the floor: new work pauses and a disk incident names what to delete.

## 3. Incidents: problems are written down with a diagnosis and a plan

`incidents/<date>-<kind>-<slug>.md`, one per problem, sections Detected / Diagnosis / Plan /
Attempts / Resolution. Opened automatically for:

| Kind | Trigger |
|---|---|
| `studio-bug` | the orchestrator cycle raised the same error 3 times in an hour (with the traceback) |
| `infra` | Ollama or Redis unreachable for 30 minutes |
| `disk` | free space under `MIN_FREE_GB` |

Deduplicated by signature; repeats bump a counter. Open incidents are listed at the bottom of
`PROGRESS.md` and pushed with the daily checkpoint. Resolved automatically when the cause clears
(infra) or the fix merges (studio-bug).

## 4. The engineer: the studio fixes its own code, behind a gate, with rollback

For each open `studio-bug` incident, once per cycle, up to 3 attempts:

1. The engineer (escalation or GPU model) reads the incident and the traceback, works on a branch
   with file tools restricted to `server/`, `worker/`, `shared/`, `scripts/`, `tests/`. It cannot
   touch the game, the role prompts or the docs.
2. Gate: every Python file compiles and `pytest tests` passes. It is told to add a test that would
   have caught the bug.
3. On green it merges to main, records the previous commit in `reports/last_good.txt`, writes
   `RESTART_REQUESTED`, and the loop exits with code 3.
4. The supervisor restarts the loop. If the loop dies again within 5 minutes without writing a
   fresh health file, the supervisor reverts the merge (or resets to the recorded commit),
   appends a line to `incidents/ROLLBACKS.md`, and restarts the known-good version.
5. After 3 failed attempts the incident's Plan says "needs a human" and stays open.

`ENGINEER_ENABLED=0` turns layer 4 off; layers 1-3 still run.

## Notifications (optional, free)

Set `NOTIFY_URL` to an ntfy topic and subscribe in the ntfy app: a daily one-liner, and a push
when an incident opens, a fix merges, or the engineer gives up.

## What is still only a human's

- A dead machine, a dead disk, a driver update that breaks CUDA, a Windows reboot that did not
  auto-login. The health file's timestamp going stale is the signal; the doctor names the cause.
- A bug in the game's design rather than its code. Playtest reports and deferred tasks show it.
- A wrong fix that passes the tests. The tests are the safety net; adding one per bug is the rule.

