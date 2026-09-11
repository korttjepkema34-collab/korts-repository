# Overnight work log — 2026-09-11 (for Kort's review)

Branch: `assistant/overnight-runtime`, based on `main` at 02dcc28. **Not merged, not pushed to
GitHub by the assistant** (the session had no write access to the repository; the branch was
delivered as a git bundle and patch). Nothing ran on either PC. No provider account, model or
private data was used; every result below comes from offline tests and synthetic runs.

How to review: read [OPERATIONS.md](OPERATIONS.md), then run on the server in a *test* runtime:
`python -m unittest discover -s tests/assistant -v` and `python scripts/synthetic_e2e.py`.

## Verification actually performed (Linux sandbox)

- Assistant unit suite: **126 passed** (68 before this branch). New: `test_runtime.py`
  (runner, controls, events, GPU/gaming, cloud evidence, backup/health, conversations,
  connectors, benchmark, privacy guard), `test_web.py` (real HTTP server: auth, CSRF, origin,
  host, lockout, session expiry, project isolation, redaction, artifacts, notes), and an export
  test in `test_integration.py`.
- `scripts/synthetic_e2e.py`: **12/12** — real runner process, fake `claude` and fake Ollama:
  plan → work → review rejection → repair → acceptance, cancel, second runner refused, kill -9
  mid-job and resume without lost artifacts, pause, backup and restore to a clean folder.
- Dashboard rendered in headless Chromium at 1400 px and 390 px with synthetic data; no console
  errors after fixing a CSP violation. Screenshots were delivered with this log.
- `python -m compileall`, `git diff --check`, private-data scan of every tracked file: passed.
- **Not run:** legacy `pytest tests` (package index blocked in the sandbox; no legacy code changed),
  Windows, Tailscale, real Ollama, real OpenRouter/Claude Code, real Obsidian vault.

## Checklist status

Legend: **Done offline** = implemented + tested here, still needs a live check on your PCs.
**Needs you / hardware** = cannot be done from this session. **Left for review** = deliberately
not done because it needs your decision.

### 1. Core task runtime — done offline
Persistent runner (`assistant/runner.py`), scheduled-task installer (not installed), resume after
restart, runner + per-task leases, bounded retries with cooldowns, task-to-task dependencies,
project isolation, audited per-project cloud consent, invocation records (provider, requested and
actual model, cost evidence, duration, digests). *Needs you:* install and reboot test on the server.

### 2. Dashboard task controls — done offline
Pause/resume, cancel, retry, approve/reject results, repair with written instructions, plans and
assignments, dependencies, review evidence and failures, text/code artifact preview and download,
service/connection health, mailbox notifications (+ optional browser notifications).

### 3. Workforce events — done offline (plain view, not the pixel office)
Sanitized lifecycle events (fixed messages only), assignment/work/handoff/review/repair/completion,
handoff animation, six states, restore from SQLite after reload, animation isolated from execution,
bounded server history (5000) and client memory (300), SSE reconnect + resync + stale banner.
*Left for review:* the approved pixel-art office (issue #2, Stage B) is still not built; the
authority docs ask for owner review between workforce stages — this branch is that review point.

### 4. Cloud routing — partly done offline
Done: model-substitution rejection, missing/nonzero cost rejection (OpenRouter key usage delta),
rate-limit cooldowns, periodic price + catalog-change recheck, cloud usage/availability in the
dashboard, explanation of `limit: null` (no credit cap on the key; see OPERATIONS.md — also the
50 vs 1000 free requests/day rule). *Needs you:* Ling stays primary in your private config (I did
not see it — it is not in GitHub), fallback qualification, Nemotron/Inkling re-evaluation all need
live calls: `python -m assistant.catalog evaluate <model>` / `python -m assistant.qualify`.

### 5. Local workers — tooling done offline
Benchmark + qualification tool (latency, memory/VRAM, tested context, long prompt, malformed
output), JSON recovery, keep-alive warm-up/unload, unqualified roles shown unavailable and not run.
*Needs you:* actually run it against `qwen3.5:4b` on the server and `qwen3.5:9b` on the gaming PC;
per-role instruction tuning should follow those results.

### 6. Gaming-mode GPU controls — done offline
Stop new GPU work, finish-or-cancel, unload via Ollama, VRAM confirmation, resume, exclusive GPU
lease shared with future media tools, tunnel reconnect script, tunnel/GPU health in the dashboard.
*Needs you:* test with the real card, sleep and shutdown.

### 7. Code-work workflows — partly done offline
Existing isolated candidates + checks + cloud review kept; added owner-approved patch export with
rollback point and conflict detection, and a harmless sample project generator.
*Needs you:* configure the real game checkout and business repositories and their check commands
(execution stays disabled until you do), then run the sample project first.

### 8. Memory and knowledge — done offline
Scoped note viewing/editing in the dashboard with revision history and stale-edit protection,
sources/status display, supersede, dispute, links/backlinks, reviewed memory-to-skill *proposal*,
backup/restore test, leak guard (`scripts/check_private_leak.py`, `.githooks/pre-commit`, and the
runtime refuses to live inside the checkout). *Left for review:* retention rules (how long to keep
reports, artifacts, history) — defaults: 14 backups, 200 pass reports; nothing else is deleted.

### 9. Media pipeline — not started (by design)
Only the exclusive GPU lease exists. ComfyUI install, workflows, sprite/audio tools and visual
review need the gaming PC and licence decisions. Media roles remain disabled.

### 10. Chat — done offline
Per-task conversations, plan confirmation with assumptions and acceptance criteria, clarifying
questions (task waits in `needs_input`), SSE status updates, safe attachments (type/size/magic
checks), image attachments stored but explicitly *not* shown to models until a vision route is
qualified, per-job revision requests, internal evidence kept out of the conversation, persisted,
searchable.

### 11. Authentication — done offline
All items implemented and tested except live Tailscale restriction (bind is limited to loopback or
a Tailscale address; ACL still needs to be applied by you).

### 12. Business connectors — gate only
Policy gate implemented and tested; no connector implemented or enabled. Each service needs your
decision on exact read/write scope.

### 13. Backups — done offline (except scheduling)
Vault, SQLite, artifacts, reports; credentials excluded; clean-folder restore tested; rollback and
known-good revisions documented; disk and backup-age warnings. *Left for review:* automatic nightly
backups and an off-machine copy destination.

### 14. Monitoring — done offline
Health checks with last-success times, log rotation, repeated-failure and cost alerts, catalog
change monitoring, disk/memory pressure, daily report, controlled update process (no auto-update).

### 15. Acceptance testing — synthetic only
Synthetic E2E, cancellation, retry, malformed output, review rejection/repair, isolation,
unauthorized access and backup restore are covered offline. Everything involving real reboots,
the gaming PC, real cloud outage, dashboard-on/off inference comparison, multi-hour and overnight
runs must happen on your machines.

### 16. Documentation and release — partly done
New: OPERATIONS.md (both PCs, services, controls, privacy, cost enforcement, gaming mode, backups),
this log, ACCEPTANCE/VERIFICATION/DECISIONS updates. *Left for review:* pull request, merge, release
tag and recording the installed release — those need your approval.

## Decisions for you

1. **Cloud consent is now required in two places** (config + audited grant). After updating, run
   `python -m assistant.run consent <project> --grant` for each project you allow, or tasks block.
2. **`require_qualified_workers: true`** in the template means local roles do nothing until you
   benchmark + qualify them. Your existing private config does not have the key, so old behavior
   continues there until you add it. Decide which you want.
3. **Plan confirmation** is on by default in the dashboard's add form ("show me the plan first").
4. **`daily_caps.openrouter`**: 1000 assumes you bought ≥10 credits; otherwise set 50.
5. The dashboard is a new network service — keep it on loopback until you have reviewed it.
6. Retention and automatic backup schedule (see 8 and 13).
