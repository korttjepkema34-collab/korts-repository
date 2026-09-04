# Claude Code entry point

This repository's instructions for AI models live in **AGENTS.md**. Read it first.
If the human asks how to set up or what is missing: `START-HERE.md` and `scripts/doctor.py`.

Then, depending on what you are doing:

- Planning or architecture work: `docs/03-architecture.md`, `docs/decisions.md`
- Choosing or configuring models: `docs/04-models.md` and `docs/20-research-notes.md`
- Writing Godot code: `docs/09-godot-conventions.md` and `agents/coder.md`
- The approved look: `style/references/mock-day.png`, `mock-night.png`, and `docs/pitch/`
- Generating art or audio: `style/style-bible.md`, `docs/14-world-bible.md` and the matching `agents/*.md`
- Anything about the game's world, characters, places, quests: `docs/14-world-bible.md`
- Gameplay systems, items, classes, building, workers: `docs/17-gameplay-systems.md`; item JSON comes from `scripts/gen_items.py`
- Touching the queue or job format: `shared/jobs.py` and `docs/08-job-schema.md`

Skills for this repo live in `.claude/skills/`: `studio-status`, `godot-check`, `asset-review`,
`new-task`, `act-as`. Known-good Godot snippets: `docs/18-godot4-cookbook.md`.

When acting as one of the team roles, load the matching file in `agents/` as your system prompt.
When unsure which role applies, act as the orchestrator (`agents/orchestrator.md`).
