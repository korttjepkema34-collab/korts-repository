> **Current assistant setup (2026-09-09):** Read [the current setup guide](docs/assistant/SETUP.md). Cloud models lead and approve; local models never take over. No new GPU or paid inference is planned. The older game studio loop below is preserved for migration, not approved for unattended operation under the current requirements.

# AGENTS.md - read me first

You are looking at the shared repository for an **AI-run game development team** building a game
in **Godot 4**. This file tells you what the project is, what machines exist, what roles you can
take, and the rules that apply to every role.

## 1. What we are building

A small studio made of AI workers, coordinated by one orchestrator model, supervised by a human
owner (the creative director). The goal is for the AI team to do most of the production work:
GDScript and scenes, 32 px sprites, tiles and buildings, the 2D lighting layer, music and
sound effects, and sprite animation. The human sets direction, reviews, and approves.

The game is **Reaper's Relics**, a 2.5D pixel-art online RPG: day scavenging and building,
night hordes, Elden Ring-style bosses, a persistent shared hub called the Keep, built as a scope
ladder towards an MMO. Near-future feudal dystopia, medieval cyberpunk. Read
`docs/10-game-design.md` before any gameplay, rendering or netcode work, `docs/14-world-bible.md`
before inventing any name, place, enemy or line of dialogue, and `style/style-bible.md` before
making or judging any art. The approved look is `style/references/mock-day.png` and `mock-night.png`. The first milestone is a playable two-player prototype on a
dedicated server. See `docs/01-vision.md`.

## 2. Current architecture (supersedes older studio documents)

Read `docs/assistant/SETUP.md`, `DECISIONS.md`, and `ACCEPTANCE.md` in that directory.
The server has an i7-10700K, 96 GB RAM, Windows, **no dedicated GPU**. The gaming PC has
Ryzen 9 7900X, 32 GB RAM, RTX 3080 Ti 12 GB. No additional GPU is planned.

Cloud models always plan and review through Claude Code. Only explicitly free qualified routes
are allowed. If unavailable, persist work and wait; never use a local leader or paid fallback.
The current `assistant/` runtime uses SQLite, private Markdown memory, and serial worker jobs;
local Ollama workers connect through localhost or a Tailscale SSH tunnel. Editable role profiles
are in `config/assistant/workers.json`, copied to the private runtime on initialization.
The old Redis/media studio remains migration material; do not run its supervisor unattended.

Personal and business notes, credentials, reports, and generated outputs stay out of this PUBLIC
repository. Preserve scope boundaries. A draft is not an implementation; a tested candidate is
not an integrated change. Record actual test evidence before cloud approval. Preserve existing
game, world, and art bibles. New integration work must meet `docs/assistant/ACCEPTANCE.md`.

## 5. Rules for every role

1. **Server-authoritative gameplay, always.** Clients send inputs; the server simulates. See `docs/10-game-design.md`.
2. **Godot 4 only.** GDScript 2.0 syntax. Never emit Godot 3 code. See `docs/09-godot-conventions.md`.
3. **Every art and audio prompt includes the style bible.** `style/style-bible.md` plus the
   references in `style/references/`. Consistency beats individual quality.
4. **Never write directly into `assets/approved/`.** Generated output goes to `assets/incoming/`.
   Only the reviewer moves things to `approved/` or `rejected/`.
5. **Never commit to `main`.** Work on a branch named `<role>/<task-id>-<slug>`. Integration requires configured tests and cloud review; current runtime does not auto-merge.
6. **Generated binaries do not go in git.** Changes to the studio's own code (`server/`, `worker/`, `shared/`, `scripts/`) merge only when `pytest tests` passes; add a test for every bug fixed. `assets/` is synced with Syncthing. Only source,
   config, docs, and the Godot project's own small resources are committed.
7. **Log decisions.** Anything that changes architecture, model choice, or conventions gets a line
   in `docs/decisions.md`. If you are unsure whether something is decided, check there first.
8. **Check licences** before a generated asset ships. Note the generator and its licence in the
   asset's sidecar `.json`.
9. **Never wait for the human.** The studio runs unattended for days. When you would have asked
   a question, take the most conservative reasonable answer, log it in `docs/decisions.md`
   marked "(auto)", and continue. Stop affected jobs when required cloud review, permission, or verification is unavailable; report blockers and continue independent work. Never spend money or expose services outside the tailnet. See `docs/12-autonomy.md`.
10. **Verify before claiming.** Run the tests, open the scene, look at the image. Report what
   actually happened, including failures.

## 6. Where things are

- Research behind the model picks and the prior art we learned from: `docs/20-research-notes.md`
- Godot snippets that are known to work: `docs/18-godot4-cookbook.md`; exact API lookup via the coder's `search_godot_api`
- How the repo helps small models, and the Claude Code skills in `.claude/skills/`: `docs/19-helping-weak-models.md`
- Gameplay systems (loop rules, building, weapons, armor, classes, workers): `docs/17-gameplay-systems.md`
- Item data is generated: edit `scripts/gen_items.py`, never `game/data/{weapons,armor,classes,rarities}.json`
- Task board: `tasks/backlog`, `tasks/in-progress`, `tasks/done` (one markdown file per task)
- Decision log: `docs/decisions.md`
- Open questions for the human: `docs/open-questions.md` (read on return; nothing blocks on them)
- Free cloud escalation ladder (Ollama Cloud, OpenRouter): `docs/24-cloud-escalation.md`
- Safety nets (supervision, healing, incidents, the engineer with rollback): `docs/23-safety-nets.md`; open incidents in `incidents/`
- Human setup, in order, with a preflight check: `START-HERE.md`, `scripts/doctor.py`
- Progress: `PROGRESS.md`, `reports/`, `tasks/deferred/` (the human's to-do list)
- Server stack: `server/docker-compose.yml`
- GPU worker: `worker/worker.py`, config in `worker/config.yaml`
- Shared job schema: `shared/jobs.py`
- Training: `training/` (recipes), `data/traces/` (labelled history), `docs/15-training.md`

