# 003 Godot project skeleton
priority: 3
roles: coder, reviewer

## Goal
Extend `game/` so it loads headless, has the folder layout from `docs/09-godot-conventions.md`,
a dedicated-server/client split at startup, the clock, and one gdUnit4 test if the addon is present.

## Acceptance
- `project.godot` loads headless; base 960x540, viewport stretch, texture filter nearest.
- Folders: scenes/player, scenes/enemies, scenes/levels, scenes/ui, scenes/fx, scripts, data, tests.
- `main.gd` starts an ENet server with `--server` (headless) and a client otherwise; port and clock lengths from `data/config.json`.
- `scripts/clock.gd` autoload: day/night state machine from `data/config.json`, emits `phase_changed`.
- One test in `tests/` passes if gdUnit4 is installed.
