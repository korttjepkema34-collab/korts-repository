# AGENTS.md - read me first

You are looking at the shared repository for an **AI-run game development team** building a game
in **Godot 4**. This file tells you what the project is, what machines exist, what roles you can
take, and the rules that apply to every role.

## 1. What we are building

A small studio made of AI workers, coordinated by one orchestrator model, supervised by a human
owner (the creative director). The goal is for the AI team to do most of the production work:
GDScript and scenes, 2D sprites and backgrounds, 3D models, music and sound effects, and
eventually animation. The human sets direction, reviews, and approves.

The game itself is not decided yet. The first milestone is a **playable prototype** produced
end to end by the pipeline, to prove the team works. See `docs/01-vision.md`.

## 2. The two machines

| Hostname | What it is | Runs |
|---|---|---|
| `server` | Home server, i7-10700K, 96 GB DDR4, no GPU (12 GB card planned), Linux + Docker, always on | Ollama (orchestrator LLM), Redis job queue, Forgejo git, headless Godot for tests/exports, asset library, this repo's orchestrator |
| `gpu` | Gaming PC, Ryzen 9 7900X, 32 GB DDR5, RTX 3080 Ti 12 GB VRAM, Windows, online when not gaming | GPU worker daemon, ComfyUI, TRELLIS/Hunyuan3D, ACE-Step, Godot editor + Godot MCP server, optional coder LLM when the GPU is idle |

Connected over **Tailscale**. Use Tailscale hostnames or IPs, never public addresses.
Full details: `docs/02-hardware.md`.

## 3. How work flows

```
human writes task  ->  tasks/backlog/*.md
orchestrator (server) reads task, plans, emits jobs  ->  Redis queue
GPU worker (gpu) pulls job when online and not gaming  ->  runs tool  ->  writes to assets/incoming/
reviewer (server, vision model) checks output vs style bible  ->  assets/approved/ or rejected/
coder (gpu or server) edits game/ via Godot MCP, commits to a branch
headless Godot (server) runs tests  ->  orchestrator merges or sends back
human reviews milestone  ->  tasks/done/
```

Key rule: **the server never calls the gaming PC directly.** It enqueues. The GPU worker pulls.
If the gaming PC is off or in gaming mode, jobs wait. The orchestrator keeps doing CPU-side work.

Details: `docs/03-architecture.md`. Job format: `docs/08-job-schema.md` and `shared/jobs.py`.

## 4. Roles you can take

Each role has a system prompt in `agents/`. Load the one you are acting as.

| Role | File | Where it runs | Model tier |
|---|---|---|---|
| Orchestrator / studio lead | `agents/orchestrator.md` | server (CPU, MoE model) | large MoE, needs planning + tool calling |
| Coder | `agents/coder.md` | gpu when idle, else server | strongest coder that fits |
| 2D artist | `agents/artist-2d.md` | gpu (ComfyUI), later server too | small LLM + SDXL/FLUX |
| 3D artist | `agents/artist-3d.md` | gpu (TRELLIS / Hunyuan3D) | small LLM + 3D model |
| Audio | `agents/audio.md` | gpu (ACE-Step, Stable Audio Open), later server | small LLM + audio model |
| Reviewer / QA | `agents/reviewer.md` | server (vision model) | vision-language model |

Model picks and alternatives: `docs/04-models.md`.

## 5. Rules for every role

1. **Godot 4 only.** GDScript 2.0 syntax. Never emit Godot 3 code. See `docs/09-godot-conventions.md`.
2. **Every art, 3D, and audio prompt includes the style bible.** `style/style-bible.md` plus the
   references in `style/references/`. Consistency beats individual quality.
3. **Never write directly into `assets/approved/`.** Generated output goes to `assets/incoming/`.
   Only the reviewer moves things to `approved/` or `rejected/`.
4. **Never commit to `main`.** Work on a branch named `<role>/<task-id>-<slug>`. The orchestrator
   merges after headless tests pass.
5. **Generated binaries do not go in git.** `assets/` is synced with Syncthing. Only source,
   config, docs, and the Godot project's own small resources are committed.
6. **Log decisions.** Anything that changes architecture, model choice, or conventions gets a line
   in `docs/decisions.md`. If you are unsure whether something is decided, check there first.
7. **Check licences** before a generated asset ships. Note the generator and its licence in the
   asset's sidecar `.json`.
8. **Ask the human** for anything that changes the game's design direction, spends money, or
   exposes a service outside the tailnet. Everything else, do it and log it.
9. **Verify before claiming.** Run the tests, open the scene, look at the image. Report what
   actually happened, including failures.

## 6. Where things are

- Task board: `tasks/backlog`, `tasks/in-progress`, `tasks/done` (one markdown file per task)
- Decision log: `docs/decisions.md`
- Open questions for the human: `docs/open-questions.md`
- Server stack: `server/docker-compose.yml`
- GPU worker: `worker/worker.py`, config in `worker/config.yaml`
- Shared job schema: `shared/jobs.py`
