# Operations: runner, dashboard, gaming mode, backups and monitoring

Status: integrated and tested in a disposable Windows runtime on branch
`assistant/server-web-integration` (2026-09-11). The older adapter is still live on the server;
follow the first-run checklist before trusting the replacement unattended.

## The two PCs and their services

| Machine | Service | How it runs | Notes |
|---|---|---|---|
| Server (i7-10700K, 96 GB, no GPU) | Task runner `python -m assistant.runner` | Scheduled task `KortAssistant-Runner`, at logon, restarts on failure | One runner per runtime (SQLite lease); a second copy exits |
| Server | Dashboard `python -m assistant.web serve` | Scheduled task `KortAssistant-Dashboard` | Loopback by default; Tailscale IP only if you run `assistant.web bind` |
| Server | GPU tunnel `scripts/gpu-tunnel.ps1` | Scheduled task `KortAssistant-GpuTunnel` | Server 127.0.0.1:11435 → gaming PC Ollama 127.0.0.1:11434, reconnects with back-off |
| Server | Ollama with `qwen3.5:4b` | Ollama's own service | CPU worker roles (`device: cpu`) |
| Gaming PC (RTX 3080 Ti 12 GB) | Ollama with `qwen3.5:9b` | Ollama's own service | GPU roles (`device: gpu`); unloaded by gaming mode |

Install the scheduled tasks (review the script first):

```powershell
.\scripts\install-runner-service.ps1 -Dashboard -Tunnel -TunnelTarget <user>@<gaming-pc-tailscale-ip>
Start-ScheduledTask -TaskName KortAssistant-Runner
```

`-Uninstall` removes them; task state is untouched. The old `start-assistant.ps1 -Hours 8`
bounded run still works and now uses the same runner.

## What the runner guarantees

- **Persistent:** keeps running until stopped; each pass processes every runnable task one step.
- **Resume after restart:** state is in SQLite after every step. A job interrupted mid-call is
  re-run on restart (the attempt counts) and recorded as a `resume` event. Verified by
  `scripts/synthetic_e2e.py` with a hard kill (-9).
- **No duplicate execution:** a global runner lease plus a per-task lease. A crashed runner's lease
  is taken over when its process is gone or the lease expires (15 min).
- **Bounded retries and cooldowns:** cloud outages and worker failures back off 1, 2, 4 … 60 minutes
  (`retry_base_seconds`, `retry_max_seconds`), then the task blocks after `max_task_retries` and a
  mailbox item is created. Owner retry/repair gives a fresh bounded attempt budget without
  overwriting earlier artifacts.
- **Dependencies:** jobs inside a task run in plan order; tasks can depend on other tasks in the
  same project (`--after <task-id>`). Cross-project dependencies are refused. A cancelled or
  rejected dependency blocks the dependent task.
- **Isolation:** every task, event, note, artifact, mailbox item and dashboard response is scoped to
  one project. Cloud context for a project needs **both** `allow_cloud_context` in `config.json`
  **and** an audited grant: `python -m assistant.run consent game --grant` (or the System tab).
- **Records:** every cloud call stores provider, requested model, the model(s) that actually served
  it, cost evidence, duration, outcome and prompt/result digests (not the text) in `invocations`.

## Cloud cost and model enforcement

For each OpenRouter call the controller:

1. refuses routes not marked `qualified` or not ending in `:free`, and re-checks the live catalog
   price (prompt and completion must be exactly zero);
2. reads the key's cumulative usage from `GET /api/v1/key` before and after the call;
   **the result is discarded if usage changed or could not be read** (`rejected_cost_*`);
3. **discards the result if any model other than the pinned one served it**, or if Claude Code
   returned no model-usage evidence (`rejected_model_*`);
4. applies a cooldown to the route on failure: exponential, 5× longer for rate limits (HTTP 429),
   30 minutes for a policy rejection; other qualified routes are tried in order;
5. rechecks every configured route's price and catalog fingerprint every `catalog_recheck_hours`
   and raises a mailbox item when a price becomes nonzero or the catalog entry changes.

Claude Code's own `total_cost_usd` is an estimate from Anthropic prices and is only recorded.

**Why OpenRouter shows the key `limit` as `null`:** OpenRouter documents `limit` as "credit limit
for the key, or null if unlimited" — `null` just means no spending cap is set on that key. It is
not an error and does not prove calls are free. To add a cap, edit the key on openrouter.ai →
Keys and set a credit limit (verify afterwards that `:free` models still answer with that limit).
Also note OpenRouter's documented free-model limits: 20 requests/minute, and **50 `:free`
requests/day unless the account has bought at least 10 credits (then 1000/day)**. Set
`daily_caps.openrouter` to match your account (the template's 1000 assumes the higher tier). Each
cost check records `is_free_tier` so you can see which applies.

## Dashboard

```powershell
python -m assistant.web user add kort --owner          # prompts for a 12+ character password
python -m assistant.web access open --user kort        # private server page without a login prompt
python -m assistant.web access password                # restore password/session mode
python -m assistant.web serve                          # http://127.0.0.1:8765
python -m assistant.web bind 100.x.y.z                 # optional: your server's Tailscale IP only
```

The Tjepkema deployment uses explicit open access at the owner's request. Anyone who can open that
private server page receives owner controls, so access depends on the existing LAN/tailnet boundary.
The backend still refuses public/LAN wildcard binds and listens on the server's Tailscale address.
Every change remains a POST with a process-scoped CSRF token, allowed Origin and Host
(DNS-rebinding protection); 5 failed sign-ins lock for 15 minutes; strict Content-Security-Policy;
no raw task JSON or filesystem paths are sent (paths are replaced by `[path]`); every control action
and denial is in the audit log. Password mode retains PBKDF2 hashes, HttpOnly SameSite=Strict
cookies, 12 h absolute / 2 h idle expiry, and sign-in rate limiting. Binding to `0.0.0.0` or a
LAN/public address is refused. Other users
(`--projects game`) see only their projects and cannot use system controls. Restrict the port in
the Tailscale ACL as well (`scripts/tailscale-acl.example.json`).

| Tab | Controls |
|---|---|
| Header | Runner / cloud / GPU tunnel / disk / backup status with last-success times; Pause/Resume; Gaming mode; notifications |
| Tasks | Add (with "show me the plan first"), dependencies, conversation, attachments, search; cancel, retry, approve/reject plan, approve/reject result, request repair per job with written instructions, preview/download artifacts (digest verified), review evidence, check output, failure reasons, cloud call records, timeline, export patch |
| Workforce | Every role with state idle / working / waiting / offline / blocked / unavailable from real events; handoff animation (disabled with reduced motion); recent activity |
| Needs you | Mailbox: blocked tasks, questions, plans and results waiting for you, health alerts |
| Knowledge | Scoped note list/search, view, edit with revision history and stale-edit protection, status/provenance, supersede, dispute, links/backlinks, propose an approved lesson as a skill |
| System | Health checks, cloud routes (price verified, cooldowns), 24 h call outcomes, cloud-context consent, audit log, backup now |

The live view uses server-sent events with cursor resume; after a gap it resynchronizes from
SQLite. A missing heartbeat shows a "stale" banner. The dashboard is a separate process: closing
it or a browser error cannot affect the runner. The Office landing page is a real-state pixel
workspace; its clearly labeled Preview mode is browser-only and never changes runner state.

## Gaming mode

`python -m assistant.run gaming on` (or the header button):

1. New GPU work stops immediately (jobs wait without spending attempts).
2. Active GPU work keeps the GPU lease until its HTTP request exits. `--cancel-active` is retained
   for compatibility but reports that an in-flight request cannot be killed safely.
3. Every model loaded on GPU endpoints is unloaded through Ollama (`keep_alive: 0`).
4. `/api/ps` is re-read; VRAM is reported **released** only when no model remains, otherwise
   **unconfirmed** (e.g. the PC was already asleep).

`gaming off` checks the tunnel endpoint and marks GPU roles idle or offline. Sleep, shutdown and
reconnect of the gaming PC are handled by the tunnel script's reconnect loop plus the runner's
endpoint check (GPU jobs wait while offline). One exclusive `gpu` lease covers Ollama and all
future media tools, so they can never load the card at the same time.

## Code results: approval, export and rollback

Code candidates are built in isolated clones with configured checks and cloud review (unchanged).
When you approve such a result, **Export patch** (or `python -m assistant.run export <task>`) writes
`exports/<task>/` in the private runtime with patch files, a git bundle and a README containing the
reviewed base revision (the rollback point), apply and rollback commands. It checks in a throwaway
clone whether the patch still applies to your repository's current HEAD and reports a conflict
instead of merging. Nothing is ever merged, pushed, deployed or published by the assistant.
Try it first with `python scripts/make_sample_project.py <empty folder>`.

## Backups and recovery

```powershell
python -m assistant.backup create            # zip in <runtime>\backups, keeps 14
python -m assistant.backup verify <zip>
python -m assistant.backup restore <zip> <new empty folder>
```

Included: SQLite (online-consistent snapshot), vault with revision history, artifacts, reports,
`workers.json`, `config.json`, plus the source revision. Excluded: `dashboard.json` (password hashes)
and all API keys (they live in environment variables). Restore refuses non-empty targets, verifies
every hash and SQLite integrity. To switch to a restored runtime: stop the scheduled tasks, point
`ASSISTANT_HOME` at the restored folder (or rename folders), start the runner, open the dashboard.
Health raises "Backup is overdue" after `backup_max_age_hours` (36). Copy backups to another disk.

**Known-good revisions:** each backup records the source commit. To roll back source, stop the
tasks, `git switch --detach <commit>` in the checkout, run the unit tests, start again.

## Monitoring

`python -m assistant.run health` (also every 5 minutes inside the runner) records: runner heartbeat,
disk free (`min_free_disk_gb`), memory (if `psutil` is installed), backup age, server and GPU
endpoints, cloud catalog/price, blocked-task count and cost/substitution rejections — each with last
success time. Alerts become mailbox items. A daily report is written after 07:00 local time to
`reports/daily-YYYY-MM-DD.md`. Logs rotate (`logs/runner.log`, 5 × 2 MB); per-pass reports keep 200.

**Controlled updates:** nothing updates source or models automatically. Update with
`python -m assistant.sync` (refuses while the runner is active), run the unit tests and
`python scripts/synthetic_e2e.py`, then restart. New models are used only after
`python -m assistant.benchmark run <role>` passes and you run `python -m assistant.benchmark qualify <role>`.

## Local worker qualification

`python -m assistant.benchmark run` measures each local role with real requests: cold-load time,
resident memory and VRAM, latency, tokens/second, JSON compliance, a long prompt at ~70% of
`num_ctx` with recall of a planted fact, and output under "explain first" pressure. Reports go to
`reports/benchmarks/`. `qualify <role>` sets `qualified: true` in your private `workers.json` only
when the newest benchmark for the same model and context passed within 7 days. With
`require_qualified_workers: true` (template default) unqualified local roles show **unavailable**
and their jobs wait instead of running. Local answers go through JSON recovery (code fences,
surrounding prose, `<think>` blocks, trailing commas); anything else becomes a repairable failure.

## Business connectors

`assistant/connectors.py` is the gate every future connector must use; no service is implemented.
Declare each one in the private `connectors.json` with exact read scopes, write actions, projects and
the environment variable holding its credential. It stays unusable until `enabled` and `qualified`
are both true and its credential is present (expired/missing credentials are refused). Every
external write needs your mailbox approval of that exact payload (answer `approve <code>`); the
approval is consumed once so restarts cannot repeat an external effect. All attempts are audited.

## First run on the server (checklist)

### Tjepkema Server page integration

The reviewed deployment package is under `deploy/` and `scripts/deploy-dashboard-wsl.sh`. It keeps
the existing homepage's **My Assistant** link, redirects `/assistant.html` to `/assistant/`, and
reverse-proxies that path to the assistant's Tailscale-only listener at
`100.72.202.38:8772`. Static files, API calls, downloads and SSE use the `/assistant/` base path;
nginx does not claim the site-wide `/api` or `/static` routes.

The script requires the exact approved commit, refuses a dirty or different checkout, runs the
assistant tests, compilation, privacy scan and synthetic recovery test before changing services,
backs up the old systemd/nginx/assistant-page files, initializes the runtime without overwriting
private configuration, enables the owner-approved passwordless `kort` access mode, installs separate runner
and dashboard services, validates nginx, reloads it, and probes both the direct and proxied pages.
The nginx container's reachability to the target address and the configuration syntax were checked
before review. Do not run the script until the owner approves the prepared commit.

1. `git fetch` and check out this branch in a **copy** of the runtime first
   (`$env:ASSISTANT_HOME="$HOME\KortAssistant-test"`), run `python -m assistant.run init`.
2. `python -m unittest discover -s tests/assistant -v` and `python scripts/synthetic_e2e.py`.
3. Grant consent per project, open the dashboard, and try every control. If password mode is later
   restored, create the dashboard user first.
4. `python -m assistant.benchmark run` for the 4B (server) and, with the tunnel up, the 9B roles.
5. Gaming mode on/off with the 9B loaded; watch Task Manager VRAM.
6. Put the gaming PC to sleep, confirm GPU roles go offline and come back.
7. Reboot the server; confirm the runner and dashboard start and resume.
8. Back up, restore to a new folder, open the restored dashboard.
9. Only then point the scheduled tasks at the real runtime.
