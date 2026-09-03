---
name: godot-check
description: Run the same gate the coder agent uses on game/: Godot 3 pattern scan, headless load, gdUnit4 tests, gdlint. Use before committing any GDScript or scene, or when asked to verify the project loads.
---
From the repo root, with `GODOT_BIN` set (server/.env):

```
python -c "import sys; sys.path[:0]=['.','server']; from pathlib import Path; from orchestrator import godot; print(godot.godot3_hits(Path('game'))); print(godot.lint(Path('game'))); print(godot.run_tests(Path('game')))"
```

Or by hand:
- `"%GODOT_BIN%" --headless --path game --import` then `--quit`: no `SCRIPT ERROR` / `Parse Error` lines.
- `"%GODOT_BIN%" --headless --path game -s res://addons/gdUnit4/bin/GdUnitCmdTool.gd --add res://tests --ignoreHeadlessMode`
- `gdlint game/**/*.gd`
Fix anything red before committing. Never skip a failing test. Unsure about an API: `python -c "import sys; sys.path[:0]=['.','server']; from orchestrator import docsearch; print(docsearch.search('TileMapLayer set_cell'))"`.
