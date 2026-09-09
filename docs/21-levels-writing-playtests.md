> **Setup migration notice:** For the personal/business/game assistant, [assistant/SETUP.md](assistant/SETUP.md) and [assistant/DECISIONS.md](assistant/DECISIONS.md) supersede older model, hardware, autonomy and installation choices below. Game design remains preserved.

# 21 - Levels, writing, playtests (added 2026-09-04)

Three things a studio has that the first version lacked: someone who lays out levels, someone who
writes, and someone who plays the game.

## Levels are ASCII

`game/data/tiles.json` is the legend: one character per tile with layer, walkability, a
placeholder palette colour and optional marker. A `level` job asks the level-designer role for
`rows`, `server/orchestrator/levels.py` validates (size, known characters, required markers,
every marker reachable from the player spawn, no walkable edge without an Exit) and saves
`game/data/maps/<name>.json`. `game/scripts/map_builder.gd` renders any map: collision for solid
cells, doors as areas, lights on lamp and hearth cells, `Marker2D` nodes for spawns and exits, and
palette-coloured rectangles until real tiles exist. So levels are playable before art, proof runs
and playtests work from day one, and the coder never lays out tiles. When tiles are approved the
coder swaps the placeholder draw for `TileMapLayer.set_cell` (cookbook), same JSON.

`game/data/maps/keep.json` is the hub, hand-laid from the mock frames. `main.gd` builds
`Config.start_map` when no level scene is set.

## Writing is data

A `text` job asks the writer role for JSON in one of five shapes (dialogue, quests, items, names,
signs). `server/orchestrator/writer.py` validates line length, bans exclamation marks and the
world's forbidden words, checks the shape, merges with the existing file keeping ids, saves under
`game/data/` and commits. The coder loads the JSON; it never writes prose.

## Playtests are nightly

`server/orchestrator/playtest.py` starts a dedicated server, one screenshotting bot client (needs
the auto-login desktop) and one headless co-op bot, both following
`game/data/playtest/plan.json` (timed input actions; the plan is the test, the bot decides
nothing). Telemetry (`game/scripts/telemetry.gd`, one JSON line per event) and screenshots land in
`reports/playtests/<date>/`. The playtester role judges the frames; the report goes to
`reports/playtest-<date>.md`; every new runtime error class becomes a priority-1 bug task.

`server/orchestrator/export.py` then exports a Windows build to `builds/reapers-relics-<date>/`
if the export templates are installed (Godot editor: Editor > Manage Export Templates), keeping
the last seven. That is what you double-click when you come back.

Both are on by default (`PLAYTEST_DAILY`, `BUILD_DAILY` in `server/.env`).

## Input actions

`project.godot` defines `move_left/right/up/down` (WASD), `attack` (J), `dodge` (Space),
`interact` (E). Bots and proof runs use these names; the coder must not rename them.

