# AGENTS.md - read me first

You are looking at the shared repository for an **AI-run game development team** building a game
in **Godot 4**. This file tells you what the project is, what machines exist, what roles you can
take, and the rules that apply to every role.

## 1. What we are building

A small studio made of AI workers, coordinated by one orchestrator model, supervised by a human
owner (the creative director). The goal is for the AI team to do most of the production work:
GDScript and scenes, 2D sprites, tiles and backgrounds, music and sound effects, and 2D
animation. The human sets direction, reviews, and approves.

The game is a **2D pixel-art online RPG**: a story campaign playable solo or co-op on a
persistent shared world, built as a scope ladder towards an MMO. Read `docs/10-game-design.md`
before any gameplay or netcode work. The first milestone is a playable two-player prototype on a
dedicated server. See `docs/01-vision.md`.

## 2. The two machines

| Hostname | What it is | Runs |
|---|---|---|
| `server` | Home server, i7-10700K, 96 GB DDR4, no GPU (12 GB card planned), **Windows**, always on | Ollama (native), Redis + Forgejo (Docker Desktop), Syncthing (native), orchestrator (native Python), headless Godot for tests, dedicated game server later |
| `gpu` | Gaming PC, Ryzen 9 7900X, 32 GB DDR5, RTX 3080 Ti 12 GB VRAM, Windows, online when not gaming | GPU worker daemon, ComfyUI, ACE-Step, optional Godot editor for interactive sessions |

Connected over **Tailscale**. Use Tailscale hostnames or IPs, never public addresses.
Full details: `docs/02-hardware.md`.

## 3. How work flows

```
human writes task  ->  tasks/backlog/*.md
orchestrator (server) reads task, plans, emits jobs  ->  Redis queue
GPU worker (gpu) pulls job when online and not gaming  ->  runs tool  ->  writes to assets/incoming/
reviewer (server, vision model) checks output vs style bible  ->  assets/approved/ or rejected/
coder (server, in-process) edits game/ with file tools, headless Godot gate  ->  merged or retried
task closes  ->  tasks/done/ (all jobs passed) or tasks/deferred/ (caps hit; retried daily)
backlog empty  ->  orchestrator generates next tasks from docs/10-game-design.md
daily  ->  reports/YYYY-MM-DD.md + PROGRESS.md, committed and pushed
```

Key rules: **the server never calls the gaming PC directly** (it enqueues, the worker pulls), and
**the studio never waits for a human** (`docs/12-autonomy.md`). Code and planning continue when
the gaming PC is off; only art and audio wait for it.

Details: `docs/03-architecture.md`. Job format: `docs/08-job-schema.md` and `shared/jobs.py`.

## 4. Roles you can take

Each role has a system prompt in `agents/`. Load the one you are acting as.

| Role | File | Where it runs | Model tier |
|---|---|---|---|
| Orchestrator / studio lead | `agents/orchestrator.md` | server (CPU, MoE model) | large MoE, needs planning + tool calling |
| Coder | `agents/coder.md` | **server** (file tools + headless gate + windowed screenshots + optional editor MCP) | strongest coder that fits in RAM |
| 2D artist | `agents/artist-2d.md` | gpu (ComfyUI), later server too | small LLM + SDXL/FLUX |
| Audio | `agents/audio.md` | gpu (ACE-Step, Stable Audio Open), later server | small LLM + audio model |
| Reviewer / QA | `agents/reviewer.md` | server (vision model) | vision-language model |

Model picks and alternatives: `docs/04-models.md`.

## 5. Rules for every role

1. **Server-authoritative gameplay, always.** Clients send inputs; the server simulates. See `docs/10-game-design.md`.
2. **Godot 4 only.** GDScript 2.0 syntax. Never emit Godot 3 code. See `docs/09-godot-conventions.md`.
3. **Every art and audio prompt includes the style bible.** `style/style-bible.md` plus the
   references in `style/references/`. Consistency beats individual quality.
4. **Never write directly into `assets/approved/`.** Generated output goes to `assets/incoming/`.
   Only the reviewer moves things to `approved/` or `rejected/`.
5. **Never commit to `main`.** Work on a branch named `<role>/<task-id>-<slug>`. The orchestrator
   merges after headless tests pass.
6. **Generated binaries do not go in git.** `assets/` is synced with Syncthing. Only source,
   config, docs, and the Godot project's own small resources are committed.
7. **Log decisions.** Anything that changes architecture, model choice, or conventions gets a line
   in `docs/decisions.md`. If you are unsure whether something is decided, check there first.
8. **Check licences** before a generated asset ships. Note the generator and its licence in the
   asset's sidecar `.json`.
9. **Never wait for the human.** The studio runs unattended for days. When you would have asked
   a question, take the most conservative reasonable answer, log it in `docs/decisions.md`
   marked "(auto)", and continue. The only hard stops are spending money and exposing a service
   outside the tailnet: never do either; defer the task instead. See `docs/12-autonomy.md`.
10. **Verify before claiming.** Run the tests, open the scene, look at the image. Report what
   actually happened, including failures.

## 6. Where things are

- Task board: `tasks/backlog`, `tasks/in-progress`, `tasks/done` (one markdown file per task)
- Decision log: `docs/decisions.md`
- Open questions for the human: `docs/open-questions.md` (read on return; nothing blocks on them)
- Progress: `PROGRESS.md`, `reports/`, `tasks/deferred/` (the human's to-do list)
- Server stack: `server/docker-compose.yml`
- GPU worker: `worker/worker.py`, config in `worker/config.yaml`
- Shared job schema: `shared/jobs.py`
