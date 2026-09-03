# Reaper's Relics · AI game dev team

A self-hosted, mostly-free "AI game studio" that builds a game in **Godot 4** using a team of
specialised AI workers, running across two machines on a private Tailscale network.

> **If you are an AI model reading this repo:** start with [`AGENTS.md`](AGENTS.md). It explains
> the project, the machines, your role options, and the rules. The `docs/` folder holds the full
> design and every decision made so far.

## The game

**Reaper's Relics**, a 2.5D pixel-art online RPG. By day you scavenge and build. By night the
Wired come in their hundreds. Survivor.io hordes, Stardew's look and daylight loop, Elden Ring
bosses and stamina, Minecraft-style building, one day/night clock. Near-future feudal dystopia:
medieval cyberpunk. Design in `docs/10-game-design.md`, world in `docs/14-world-bible.md`, the
approved look in `style/references/mock-day.png` and `mock-night.png`.

## The idea in one paragraph

One **orchestrator** model acts as the studio lead. It reads the task board, breaks work into
jobs, and dispatches them to specialised **workers**: a coder (GDScript + scenes via a Godot MCP
server), a 2D artist (ComfyUI), an audio worker (ACE-Step / Stable Audio Open), and a reviewer (vision model that checks output against the style bible).
The human owner is the creative director and final QA. Nothing ships without their sign-off.

## The machines

| Name | Role | Hardware | Always on? |
|---|---|---|---|
| `server` | Studio: orchestrator LLM, job queue, git, headless Godot tests, asset library, dedicated game server | i7-10700K, 96 GB DDR4, **no GPU yet** (12 GB card planned), Windows | Yes |
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
game/                <- the Godot 4 project (minimal skeleton; task 003 adds the full layout)
style/               <- style bible + reference images every art prompt must include
tasks/               <- file-based task board: backlog / in-progress / done
assets/              <- generated assets: incoming / approved / rejected (synced, not in git)
                        plus training/datasets and training/models (same sync)
data/                <- traces, retrieval index, fetched docs (server-only, not in git)
training/            <- dataset builders, fine-tune recipes, eval, reviewer server
scripts/             <- wake-on-LAN, Tailscale ACL example, override/train/activate helpers
```

## Quick start

1. Read `docs/06-setup-server.md` and bring up the server stack with `docker compose up -d`.
2. Read `docs/07-setup-gpu-worker.md` and start `worker/worker.py` on the gaming PC.
3. Drop a task file into `tasks/backlog/` and watch the orchestrator turn it into jobs.

## Unattended mode

Turn it on and walk away. The orchestrator plans, delegates, reviews, retries, defers, generates
its own backlog, and writes a daily report to `PROGRESS.md`. Nothing waits for a human. Setup
checklist: `docs/13-before-you-walk-away.md`. Contract: `docs/12-autonomy.md`.

## Self-improvement

The studio records every coder run (with its gate result) and every reviewer verdict, gives
the coder a retrieval tool over the Godot 4 docs, and can fine-tune a style LoRA, a coder and a
reviewer on its own approved work using the gaming PC. Nothing activates itself. How it works:
`docs/15-training.md`. What to do: `docs/16-when-you-get-home.md`.

## Status

**Ready for first run, pending setup.** The unattended loop, the file-based coder with a headless
gate and playtest proofs, the rubric reviewer with deterministic checks, the GPU worker with
palette post-processing, retrieval over the engine reference and Godot docs, traces, the training
recipes, the world and style bibles, the item generator, the eval set and the bootstrap scripts
are all in the repo. Nothing has run against a real Godot or ComfyUI yet: task 001 (queue smoke
test) and task 003 (verify the skeleton) exist to prove them. Setup order: `docs/13-before-you-walk-away.md`,
then `docs/16-when-you-get-home.md` for the learning loop. Research and reasoning behind the
choices: `docs/20-research-notes.md`.
