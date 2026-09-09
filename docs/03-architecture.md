> **Setup migration notice:** For the personal/business/game assistant, [assistant/SETUP.md](assistant/SETUP.md) and [assistant/DECISIONS.md](assistant/DECISIONS.md) supersede older model, hardware, autonomy and installation choices below. Game design remains preserved.

# 03 - Architecture

## Overview

```
SERVER (always on, CPU + 96 GB)                GAMING PC (GPU, sometimes busy)
+---------------------------------+            +---------------------------------+
| Ollama  (orchestrator + reviewer|            | worker.py  (pulls jobs)          |
|          + small coder models)  |            |   handlers: comfyui, acestep,    |
| Redis   (job queue + results)   |<--pull-----|             stub                 |
| Forgejo (git server, web UI)    |            | ComfyUI        :8188             |
| orchestrator.py (task loop)     |            | Godot editor + MCP (optional)    |
| Godot: headless gate + windowed |
| screenshots for visual review   |            | ACE-Step API   :8190             |
| Syncthing (assets/ folder)      |<--sync---->| Syncthing (assets/ folder)       |
| dashboard (Tailscale Serve)     |            |                                  |
+---------------------------------+            | gaming-mode toggle               |
        |  WoL magic packet over LAN --------> +---------------------------------+
```

All traffic goes over Tailscale. Nothing is exposed to the internet.

## Principles

1. **Pull, don't push.** The server enqueues jobs in Redis. The GPU worker pulls with a blocking
   pop when it is online and not in gaming mode. If the gaming PC is off, jobs wait. The
   orchestrator never blocks on the GPU.
2. **One resident generative model per GPU.** The worker loads a model, runs a batch of jobs of
   that type, unloads, moves to the next type. Jobs carry a `kind` so they can be grouped.
3. **Code in git, binaries in a synced folder.** The Godot project and all config live in this
   repo (hosted on the server's Forgejo, mirrored to GitHub). Generated assets live in
   `assets/` which Syncthing keeps identical on both machines and which is git-ignored.
4. **File-based task board.** `tasks/backlog`, `tasks/in-progress`, `tasks/done`. One markdown
   file per task. Humans and models can both read and write it. Git history is the audit trail.
5. **Reviewer gates everything.** Generated output lands in `assets/incoming/`. Only the reviewer
   moves it to `approved/` or `rejected/`, writing a sidecar JSON with the verdict and reason.
6. **Branch per job, merge after tests.** The coder commits to `coder/<task-id>-<slug>`. The
   orchestrator runs headless Godot tests on the server and merges on green.

## Components

### Server

| Component | Purpose | Port (Tailscale) |
|---|---|---|
| Ollama | Serves the orchestrator, reviewer, and fallback coder models | 11434 |
| Redis | Job queue (`jobs:<kind>` lists), results (`results` list), heartbeat keys | 6379 |
| Forgejo | Git hosting with web UI; this repo's origin for the two machines | 3000 |
| orchestrator | Python loop: read task board, call LLM, emit jobs, consume results, merge | none |
| godot-headless | `godot --headless` container for running gdUnit4/GUT tests and exports | none |
| Syncthing | Two-way sync of `assets/` | 8384 (UI), 22000 |
| dashboard | Optional. Simple status page via `tailscale serve` | 443 |

### Gaming PC

| Component | Purpose | Port |
|---|---|---|
| worker.py | Pulls jobs from Redis, dispatches to handlers, posts results | none |
| ComfyUI | 2D sprites, backgrounds, concept art | 8188 |
| ACE-Step / Stable Audio API wrapper | Music and SFX | 8190 |
| Godot editor + MCP server | Coder agent's hands inside the editor | per MCP server |
| gaming-mode toggle | A file (`worker/GAMING_MODE`) or tray script; worker pauses and frees VRAM | none |
| training venv | `train` jobs: kohya SDXL LoRA, Unsloth QLoRA for coder and reviewer (`training/`) | none |
| serve_reviewer.py | Optional, once a reviewer fine-tune exists: OpenAI-compatible endpoint | 8191 |

### Wake-on-LAN

The server and gaming PC share a LAN. When the queue has jobs and no worker heartbeat has been
seen for N minutes, the orchestrator sends a magic packet (`server/orchestrator/wake.py`; `scripts/wake_gpu.py` does the same by hand). The worker is set to start on
boot. Gaming mode is a manual toggle so a wake never interrupts a game already running.

## Data flow for one art job

1. Human writes `tasks/backlog/007-player-idle-sprite.md`.
2. Orchestrator reads it, loads `agents/artist-2d.md` and `style/style-bible.md`, produces a job
   JSON (`kind: image`, prompt, negative prompt, reference images, size, output name).
3. Job pushed to Redis list `jobs:image`.
4. Worker pops it, calls ComfyUI with the project's workflow, saves PNG to
   `assets/incoming/007-player-idle-sprite/`, pushes result JSON to `results`.
5. Orchestrator sees the result, dispatches the reviewer (vision model on server) with the image
   and the style bible.
6. Reviewer writes verdict; file moves to `approved/` or `rejected/` with a sidecar JSON.
7. If rejected, orchestrator re-queues with the reviewer's notes appended to the prompt, up to a
   retry limit. Then it escalates to the human.
8. If approved, the coder gets a follow-up job to import it into the Godot project.

## Data flow for self-improvement

1. Every coder run writes its transcript and gate result to `data/traces/coder/`; every verdict
   goes to `data/traces/reviewer/verdicts.jsonl`; your corrections (`scripts/override.py`) to
   `overrides.jsonl`.
2. Daily, with `AUTO_TRAIN=1` (or by hand with `scripts/enqueue_train.py`), the server builds a
   dataset into `assets/training/datasets/<name>/` and queues a `train` job.
3. The GPU worker runs the recipe, writes the model to `assets/training/models/<name>/`.
4. The orchestrator records it and logs a decision. You activate it (`scripts/activate_model.py`)
   after `training/eval_coder.py` or your own eyes say it is better. See `docs/15-training.md`.

## Failure handling

- Worker crashes mid-job: jobs are moved to `jobs:<kind>:processing` on pop and restored if no
  completion within a timeout (Redis reliable-queue pattern).
- GPU OOM: handler returns an error result; orchestrator retries with a smaller variant
  (lower resolution, fewer candidates) before deferring.
- Model writes Godot 3 code: headless tests fail on parse; result feeds back to the coder with the
  error text. After 3 failures, escalate to the human.

## Security

- Tailscale ACL restricts Redis, Ollama, Forgejo to the two machine nodes. Example in
  `scripts/tailscale-acl.example.json`.
- Redis has a password (see `server/.env.example`). Bind to the Tailscale IP only.
- No service is exposed via Tailscale Funnel or port forwarding.

