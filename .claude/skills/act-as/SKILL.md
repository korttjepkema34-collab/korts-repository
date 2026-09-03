---
name: act-as
description: Take one of the studio's roles (orchestrator, coder, artist-2d, audio, reviewer) inside an interactive Claude Code session, with the same rules the local models follow. Use when asked to "act as the coder", "plan this task", "be the reviewer", etc.
---
1. Load `agents/<role>.md` as your operating instructions, plus `AGENTS.md` rules 1-10.
2. Coder: also load `docs/09-godot-conventions.md` and `docs/16-godot4-cookbook.md`; work on a branch `coder/<task-id>-<slug>`; run the `godot-check` skill before finishing; never touch files outside `game/`.
3. Orchestrator: read the task, produce the jobs JSON per `docs/08-job-schema.md`, then either enqueue with `scripts/enqueue_stub.py`-style code or hand the jobs to the human. Log decisions in `docs/decisions.md`.
4. Artist/audio: write the exact ComfyUI / audio job spec (prompt with the verbatim style-bible suffix, references, postprocess block) rather than describing it.
5. Reviewer: use the `asset-review` skill.
