# 003 Verify the Godot project skeleton
priority: 3
roles: coder, reviewer

## Goal
The skeleton already exists (autoloads `Config`, `Net`, `Clock`, `main.gd` server/client/solo
split, two gdUnit4 tests). It was written without an engine run. Make it load and pass.

## Acceptance
- `project.godot` loads headless with no script errors; fix any API mismatch using `search_godot_api`.
- `run_scene_capture_output` with `-- --server` prints "server: listening on port 7777".
- `tests/test_config.gd` and `tests/test_items_data.gd` pass headless.
- Folders exist: scenes/player, scenes/enemies, scenes/levels, scenes/ui, scenes/fx.
- `scripts/clock.gd` advances day -> night when `day_seconds` is set to 2 in a test copy of the config (write `tests/test_clock.gd`).
