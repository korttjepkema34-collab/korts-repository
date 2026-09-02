# 003 Godot project skeleton
priority: 3
roles: coder, reviewer
depends_on: 002

## Goal
Create the Godot 4 project in `game/` following `docs/09-godot-conventions.md`, with gdUnit4
installed and one passing test, so the headless test container has something to run.

## Acceptance
- `game/project.godot` exists, Godot 4.x, project name from the style bible.
- Folder layout matches the conventions doc.
- `game/addons/gdUnit4` present; `game/tests/test_smoke.gd` passes headless.
- A main scene that opens to a blank level with a camera.
- Branch `coder/003-godot-skeleton` pushed; headless test output attached to this file.
