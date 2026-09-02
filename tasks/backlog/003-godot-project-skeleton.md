# 003 Godot project skeleton
priority: 3
roles: coder, reviewer

## Goal
Extend the minimal project in `game/` so it loads headless, has the folder layout from
`docs/09-godot-conventions.md`, a dedicated-server/client split at startup, and one gdUnit4
test if the addon is present.

## Acceptance
- `game/project.godot` loads headless without errors.
- Folders exist: scenes/player, scenes/enemies, scenes/levels, scenes/ui, scripts, data, tests.
- `scenes/main/main.gd` starts an ENet server when run with `--server` (headless) and a client
  otherwise, using `MultiplayerAPI` / `ENetMultiplayerPeer`. Port from `data/config.json`.
- `data/config.json` exists with `server_port`.
- One test in `tests/` passes if gdUnit4 is installed.
