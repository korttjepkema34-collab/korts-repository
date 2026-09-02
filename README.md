# Godot AI Game Dev Team

A self-hosted, mostly-free "AI game studio" that builds a game in **Godot 4** using a team of
specialised AI workers, running across two machines on a private Tailscale network.

> **If you are an AI model reading this repo:** start with [`AGENTS.md`](AGENTS.md). It explains
> the project, the machines, your role options, and the rules. The `docs/` folder holds the full
> design and every decision made so far.

## The idea in one paragraph

One **orchestrator** model acts as the studio lead. It reads the task board, breaks work into
jobs, and dispatches them to specialised **workers**: a coder (GDScript + scenes via a Godot MCP
server), a 2D artist (ComfyUI), a 3D artist (TRELLIS / Hunyuan3D), an audio worker (ACE-Step /
Stable Audio Open), and a reviewer (vision model that checks output against the style bible).
The human owner is the creative director and final QA. Nothing ships without their sign-off.

## The machines

| Name | Role | Hardware | Always on? |
|---|---|---|---|
| `server` | Studio: orchestrator LLM, job queue, git, headless Godot tests, asset library | i7-10700K, 96 GB DDR4, **no GPU yet** (12 GB card planned) | Yes |
| `gpu` | Contractor: GPU asset generation, Godot editor + MCP | Ryzen 9 7900X, 32 GB DDR5, **RTX 3080 Ti 12 GB** | No, it is also the gaming PC |

They talk over **Tailscale**. The server never pushes work at the gaming PC; it puts jobs on a
queue and the GPU worker pulls them whenever it is online and not in gaming mode.

## Repo map

```
AGENTS.md            <- read this first if you are an AI
CLAUDE.md            <- pointer to AGENTS.md for Claude Code
docs/                <- vision, hardware, architecture, models, setup guides, decision log
agents/              <- one markdown file per team role (system prompts / subagent definitions)
shared/              <- job schema shared by orchestrator and worker
server/              <- docker-compose + orchestrator for the always-on server
worker/              <- GPU worker daemon for the gaming PC
game/                <- the Godot 4 project (placeholder until the first prototype)
style/               <- style bible + reference images every art prompt must include
tasks/               <- file-based task board: backlog / in-progress / done
assets/              <- generated assets: incoming / approved / rejected (synced, not in git)
scripts/             <- wake-on-LAN, Tailscale ACL example, helpers
```

## Quick start

1. Read `docs/06-setup-server.md` and bring up the server stack with `docker compose up -d`.
2. Read `docs/07-setup-gpu-worker.md` and start `worker/worker.py` on the gaming PC.
3. Drop a task file into `tasks/backlog/` and watch the orchestrator turn it into jobs.

## Status

**Scaffold stage.** The architecture, docs, role definitions, job schema, queue, worker loop
and orchestrator skeleton exist. Model tags need verifying against the current Ollama library,
the ComfyUI / TRELLIS / ACE-Step handlers are thin wrappers that need real workflows wired in,
and the Godot project has not been created yet. See `docs/open-questions.md`.
