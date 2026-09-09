> **Setup migration notice:** For the personal/business/game assistant, [assistant/SETUP.md](assistant/SETUP.md) and [assistant/DECISIONS.md](assistant/DECISIONS.md) supersede older model, hardware, autonomy and installation choices below. Game design remains preserved.

# 05 - Team roles

Eight roles: five with prompts that produce work, plus writer, level designer and playtester added 2026-09-04 (see docs/21-levels-writing-playtests.md). Each has a system prompt in `agents/`. The orchestrator is the only one that reads the
task board directly; everyone else receives jobs.

| Role | Responsibilities | Inputs | Outputs | Tools |
|---|---|---|---|---|
| **Orchestrator** | Read tasks, plan, split into jobs, dispatch, consume results, merge branches, escalate to human, maintain decision log | `tasks/backlog/*.md`, `docs/`, results from Redis | Jobs on Redis, task files moved, merges, `docs/decisions.md` entries | Redis, git, headless Godot, LLM |
| **Coder** | GDScript, scenes, resources, imports, tests | Job with spec, `docs/09-godot-conventions.md`, current repo | Commits on `coder/<id>-<slug>` branch, test results | File tools, headless Godot gate + tests, `visual_check` (vision model), `search_docs` (retrieval), optional `mcp_*` editor tools, git |
| **2D artist** | Sprites, tilesets, backgrounds, UI art, concept art | Job with description, style bible, references | PNGs in `assets/incoming/<id>/` + sidecar JSON | ComfyUI (SDXL/FLUX, LoRAs, IP-Adapter) |
| **Audio** | Music tracks, SFX, placeholder voice | Job with mood/tempo/length or SFX description | `.ogg`/`.wav` in `assets/incoming/<id>/` + sidecar | ACE-Step, Stable Audio Open, Kokoro |
| **Trainer** | Fine-tune the style LoRA, coder and reviewer on the studio's own approved work | `train` job with recipe + dataset built on the server | LoRA / merged model in `assets/training/models/` + manifest | kohya sd-scripts, Unsloth, `training/` (docs/15) |
| **Writer** | Dialogue, quests, item flavour, names, signs in the world-bible voice | `text` job with content type and brief | JSON under `game/data/`, validated for voice and shape | orchestrator model, CPU |
| **Level designer** | Map layouts as ASCII with the fixed legend | `level` job with name, size, purpose, required markers | `game/data/maps/<name>.json`, validated for reachability | orchestrator model, CPU |
| **Playtester** | Judge the running build from bot screenshots, telemetry and error logs; file bugs | nightly pass | `reports/playtest-<date>.md`, bug tasks | vision model (cloud rung optional) |
| **Engineer** | Fix the studio's own code when an incident repeats | open `studio-bug` incident | merged fix behind `pytest tests`, restart request | escalation ladder |
| **Reviewer** | QA every generated asset against the style bible; judge the coder's screenshots. Code branches are gated automatically by the headless Godot check in `coder.py`, not by this role | Asset + style bible + references, or a scene screenshot + expectation | Verdict JSON, file moved to `approved/` or `rejected/` | Vision model |

## Escalation ladder

1. Worker fails a job: retry once with the error appended.
2. Reviewer rejects: re-queue with reviewer notes, up to 3 times.
3. Still failing: orchestrator writes the problem to `docs/open-questions.md` and moves the task
   to `tasks/in-progress/` with a `BLOCKED:` line at the top. Human decides.
4. Anything touching design direction, money, or exposure outside the tailnet: straight to the
   human, no retries.

## Starting lineup

Milestones 1-4 use only **orchestrator, coder, 2D artist, reviewer**. Audio joins at
milestone 5. This keeps VRAM contention and debugging surface small while the pipeline is proven.

