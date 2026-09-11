# Start here: cloud-led personal, business and game assistant

Status: a tested local foundation and setup package, not a certified turnkey autonomous studio.
Read [ACCEPTANCE.md](ACCEPTANCE.md) for exactly what is implemented and what still needs live
qualification/integration. Do not start the old local-led studio loop. Its entry point is disabled
because its local fallback and automatic approval behavior conflict with the current requirements.

## 1. What you are installing

- A custom native Python desktop interface (`assistant/desktop.py`). No hosting subscription.
- A persistent controller: cloud plans, local workers, cloud review, bounded repair, reports.
- Isolated code candidates and configurable verification commands. No automatic merge/deploy.
- An Obsidian-compatible private vault plus SQLite full-text retrieval and a read-only MCP server.
- Editable worker profiles for personal help, business operations/UI/backend, and game production.
- Existing Reaper's Relics code, game/world/style bibles and legacy media tool implementations remain.

The current controller handles text drafts and code candidates. Image/audio adapters remain gated
until their tool setup and cloud review are integrated; their profiles visibly block instead of
claiming prose is an asset. The migration checklist names the remaining work.

## 2. Before installing — both machines

Record free disk space, current NVIDIA driver (gaming PC only), Python/Ollama/Claude Code versions,
and Tailscale device names. No new GPU or purchases. Hardware is listed in [HARDWARE.md](HARDWARE.md).
Use separate folders for source, private runtime, and large models. Suggested:

| Purpose | Location |
|---|---|
| Personal GitHub checkout | `C:\studio` |
| Private notes, config, SQLite, reports, candidate workspaces | `%USERPROFILE%\KortAssistant` |
| Downloaded model files | Ollama's default folder or an explicitly selected data drive |
| Native media tools | `C:\studio-tools` |

Install these from their official sources:

1. [Git for Windows](https://git-scm.com/downloads/win).
2. [Python](https://www.python.org/downloads/windows/), 3.11+ including Tcl/Tk (desktop UI), pip and PATH.
3. [Ollama for Windows](https://ollama.com/download/windows).
4. [Claude Code](https://code.claude.com/docs/en/setup), native Windows install; Git Bash may be required
   by the installed version. Follow its official setup prerequisites. No Claude subscription purchase.
5. [Tailscale](https://tailscale.com/download/windows), sign both PCs into the intended tailnet.
6. [Obsidian](https://obsidian.md/download), server first; optional on gaming PC.

Core assistant runtime uses Python's standard library: no Redis, Forgejo, Docker, vector database,
or paid Obsidian service is necessary. Legacy game/media components have their own dependencies.

## 3. Clone the correct GitHub project

In PowerShell, select a new empty folder:

```powershell
git clone --branch main https://github.com/korttjepkema34-collab/korts-repository.git C:\studio
cd C:\studio
powershell -ExecutionPolicy Bypass -File scripts\setup-assistant.ps1 -Role server -PullModels
.\.venv\Scripts\python.exe -m unittest discover -s tests/assistant -v
```

The consolidated setup is now on `main`. The script is rerunnable: it preserves edited private
config and vault notes. `-PullModels` is explicit because
model downloads take disk/bandwidth. On the gaming PC use the same clone and `-Role gpu -PullModels`.

Default candidate models: server `qwen3.5:4b`; GPU `qwen3.5:9b`. They are candidates, not a claim
of best performance. No local model ever becomes the coordinator. See [MODELS.md](MODELS.md).

Check each local model in its own terminal:

```powershell
ollama list
ollama run qwen3.5:4b "Return one short sentence explaining your assigned worker role."
```

On the GPU use `qwen3.5:9b` instead. Watch `ollama ps` and Task Manager's GPU memory during a real
prompt. Start with the profiles' 8K context and one heavy GPU job. This context is for our bounded
worker API calls; full Claude Code repository sessions can need substantially more context.

## 4. Connect the GPU worker without exposing Ollama publicly

The first version executes bounded worker requests from the server. Use standard Windows OpenSSH
port forwarding over Tailscale; do not assume Tailscale SSH's server feature runs on Windows.

1. Install/enable Windows OpenSSH Server on the gaming PC using Microsoft's
   [OpenSSH setup](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse).
2. Start `sshd`, set its service startup as appropriate, and configure key-based access for a
   dedicated local worker account. Restrict inbound SSH to the server's Tailscale address.
3. Leave gaming PC Ollama on `127.0.0.1:11434`.
4. From the server, verify `ssh <windows-worker-user>@<gaming-pc-tailscale-ip>`; confirm the host key
   against the gaming PC before trusting it. Never disable host-key checking.
5. Open the tunnel on the server and keep that terminal alive:

```powershell
ssh -N -L 127.0.0.1:11435:127.0.0.1:11434 -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 <windows-worker-user>@<gaming-pc-tailscale-ip>
Invoke-RestMethod http://127.0.0.1:11435/api/tags
```

The second command runs in another terminal. Default GPU profiles use this port. No SSH key or
machine address belongs in the public repo. If forwarding fails, GPU-dependent tasks retry within
the configured budget, then block; server/cloud work on other tasks can continue.

The old media daemon and new Ollama jobs do not share a proven cross-process GPU scheduler yet.
Do not run them simultaneously. For gaming, pause the assistant, wait for the active call to finish,
then unload the local model with `ollama stop qwen3.5:9b` on the gaming PC.

## 5. Configure free cloud leadership

Edit `%USERPROFILE%\KortAssistant\config.json`, not the example in Git. Start with one route.
The example names `qwen/qwen3-coder:free` as a candidate and leaves `qualified:false` deliberately.

For OpenRouter:

1. Use the account with your existing higher free allowance. No new credit purchase.
2. Create a key, disable auto-top-up, and use only explicit `:free` routes.
3. Set the key in the server user's environment through Windows Environment Variables; reopen
   PowerShell afterward. Do not paste it into Git or screenshots.
4. Confirm the chosen model still exists with zero pricing. The adapter independently rechecks the
   live catalog before invocation and rejects nonzero/unknown pricing and missing models.
5. Test the Claude Code/OpenRouter combination following [MODELS.md](MODELS.md). Mark a route
   `qualified:true` only after its live tests pass. If it fails, select a different free cloud route;
   never replace leadership with a local model.

The `OPENROUTER_API_KEY` environment variable is required. The controller pins Claude model aliases
to the chosen free model, clears inherited paid-provider settings, disables arbitrary planning tools,
and never supplies a paid fallback. Verify provider activity during qualification: the local usage
counter measures CLI invocations, not necessarily every internal provider request. Your OpenRouter
account is authoritative for the 1,000-request allowance shared with other apps.

Optional Ollama-cloud route shape (replace placeholder only after checking your account):

```json
{"provider":"ollama-cloud","model":"YOUR-ELIGIBLE-MODEL:cloud","qualified":false,"included_usage_confirmed":false}
```

Use `ollama signin` on the server, check actual free included allowance, ensure no paid extra-usage
path is enabled, test the model, then set both flags true. The controller can validate cloud model
naming and your explicit allowance confirmation; it cannot independently verify your Ollama account
billing balance. Do not configure this route unless you have confirmed the free-only setup.

Set `allow_cloud_context.game` true only when you are ready to send the game goal and scoped notes
to the cloud provider. Personal and business start disabled until you choose their shareable context.
This affects sending to model providers, not GitHub publication.

## 6. Initialize the brain

Open Obsidian → **Open folder as vault** → `%USERPROFILE%\KortAssistant\vault`.
Follow [MEMORY.md](MEMORY.md) to add facts, decisions, lessons and sources. The setup seeds shared
rules and copies the existing game/world/style bibles. It does not overwrite later local edits.

```powershell
.\.venv\Scripts\python.exe -m assistant.run index
.\.venv\Scripts\python.exe -m assistant.run search game "Keep day night" --subproject reapers-relics
```

Confirm a business-only note cannot appear in a game search. SQLite indexes are rebuildable; the
Markdown files are the durable human-readable knowledge. Back up the entire private runtime folder
while the runner is stopped. GitHub is not the live task database.

## 7. Personalize workers and run the first task

Edit `%USERPROFILE%\KortAssistant\workers.json`. See [WORKERS.md](WORKERS.md).
Start with a simple narrative/operations draft, not a major rewrite or an overnight production change.

```powershell
.\.venv\Scripts\python.exe -m assistant.run doctor
.\.venv\Scripts\python.exe -m assistant.run add game "Draft three short weapon descriptions consistent with the world bible." --subproject reapers-relics
.\.venv\Scripts\python.exe -m assistant.run run --once
.\.venv\Scripts\python.exe -m assistant.run status
```

Each pass advances a task by one phase: cloud plan, worker output, cloud review, final bookkeeping.
Repeat `run --once` until you can inspect a cloud-approved draft or a concrete blocker. This phase
separation makes interruption/recovery observable. A cloud failure preserves the artifact for review.

Open the desktop UI:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-assistant.ps1 -Desktop
```

Use Tasks & evidence, Knowledge, and Workers & setup. The UI is an initial native control panel,
not the final visual design. It does not yet show a streaming chat conversation or edit every field
inline; worker/config edits open in your normal editor. See [UI-DESIGN.md](UI-DESIGN.md).

## 8. Enable isolated code candidates

Read [CODE-AND-GAME.md](CODE-AND-GAME.md) first. Set the relevant `code_projects` entry:

- `source`: absolute path of an existing clean, committed project checkout.
- `allowed_prefixes`: permitted source directories only.
- `context_files`: exact relevant source files; small enough for the local model.
- `checks`: trusted argument arrays for actual validation, not model-generated shell commands.
- `execution_enabled`: true only after running those checks manually in a disposable clone.

The controller clones committed source into the private runtime, removes its remote, applies only
allowed file replacements, captures the diff and check output, and asks the cloud reviewer. A
passing candidate remains outside the original project. No production deployment occurs.

Python/Node/Godot tests execute code; a Git clone is file isolation, not an OS sandbox. Run agent
checks in a dedicated account or VM without business credentials and with only intended access.
The default keeps execution disabled until that environment and commands are configured.

## 9. Overnight operation and recovery

> **New (2026-09-11 branch):** the persistent runner service, dashboard, gaming mode, backups and
> monitoring are described in [OPERATIONS.md](OPERATIONS.md). The notes below about `runner.lock`
> describe the older bounded run; the lock is now a lease that recovers from crashes by itself.

Only after all core acceptance checks pass:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-assistant.ps1 -Hours 8
```

The deadline is checked between steps; an in-flight model call may last up to its timeout beyond
the deadline. Pause works after the current step. One runner lock prevents two controllers from
executing the same local jobs. If the process crashes, confirm it is stopped before removing
`runner.lock`; task state survives. Draft generation can repeat after interruption, but no external
messages, merges or deployments are repeated by this controller.

For scheduled runs, use Windows Task Scheduler with the same user, the checkout as working
directory, and the start script. First test while logged in; later test reboot/login behavior,
Ollama startup, SSH tunnel availability and account environment. A scheduled headless process
cannot guarantee desktop game captures; visible Godot checks require an interactive session.
Do not mark Task Scheduler installed until it has actually run on the server.

## 10. GitHub updates and returning later

Read [GITHUB.md](GITHUB.md). Stop the runner, preserve edits, then:

```powershell
.\.venv\Scripts\python.exe -m assistant.sync
.\.venv\Scripts\python.exe -m unittest discover -s tests/assistant -v
```

The sync helper fetches and fast-forwards the current branch only, checks the expected personal
remote, and refuses dirty checkouts or an active runner. It never uploads the private vault.
Read the changed instructions before restarting. The server can read code/docs locally when
GitHub is offline. Keep the repository, private vault, and live database as separate responsibilities.

## 11. Media, business integrations and final readiness

Finish the explicitly tracked gates in [ASSETS.md](ASSETS.md), [INTEGRATIONS.md](INTEGRATIONS.md)
and [ACCEPTANCE.md](ACCEPTANCE.md). No instructions or empty profiles count as tested integrations.
The actual provider accounts, two Windows machines, private business checkout, Godot rendering,
GPU generation and overnight reboot behavior cannot be verified from this repository-writing session.

## OpenRouter model discovery and evaluation

Use `python -m assistant.catalog refresh`, then evaluate selected free IDs and inspect their
Obsidian model cards. Enable `catalog_routing` only after qualification. Full commands, behavior
and limitations: [OPENROUTER-ROUTING.md](OPENROUTER-ROUTING.md).
