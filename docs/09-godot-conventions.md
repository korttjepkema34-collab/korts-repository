# 09 - Godot conventions (for the coder and reviewer)

## Version

**Godot 4.x, GDScript 2.0.** Never Godot 3. Signs you are writing Godot 3 code (all wrong):
`export var`, `onready var`, `yield(`, `connect("signal", self, "method")`, `KinematicBody2D`,
`instance()`, `get_tree().change_scene(`, `.empty()`. The Godot 4 forms are: `@export var`,
`@onready var`, `await`, `signal.connect(callable)`, `CharacterBody2D`, `instantiate()`,
`get_tree().change_scene_to_file(`, `.is_empty()`.

## Project layout

```
game/
  project.godot
  scenes/        one folder per feature: player/, enemies/, levels/, ui/
  scripts/       shared scripts, autoloads
  assets/        symlink or import target for approved assets (sprites/, tiles/, audio/)
  tests/         gdUnit4 tests
  addons/        gdUnit4, Godot MCP plugin if editor-side
```

## Style

- `snake_case` for files, functions, variables. `PascalCase` for classes and nodes.
- Static typing everywhere: `var speed: float = 200.0`, `func take_damage(amount: int) -> void:`.
- One script per scene root. Name it after the scene.
- Signals up, calls down. Children never reach up into parents.
- Use `class_name` for anything instantiated from code.
- No magic numbers in `_process`. Export them.

## Tests

- gdUnit4. Every job that adds logic adds a test. Tests run headless on the server:
  `godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd --add tests/`.
- A branch does not merge with a failing or missing test.

## Rendering

- Base resolution 960x540, `window/stretch/mode="viewport"`, integer scale. Camera2D zoom 1x world, 1.5x indoors, 3x dialogue.
- Every level root has `y_sort_enabled = true`. Buildings, props and characters sort by their feet (offset the sprite so the origin is at the feet).
- Roof tiles live on their own `TileMapLayer` named `Roofs`; fade it when a player is inside the building footprint.
- Lighting layer: `CanvasModulate` for the clock, `PointLight2D` with normal maps, `GPUParticles2D`, one post-process `ColorRect` shader. Pixel assets never bake lighting in.
- Palette: pixel assets use only the 16 colours in `style/style-bible.md`.

## Assets

- Import only from `assets/approved/`. Never from `incoming/`.
- Sprites: PNG, 32x48 characters, 32x32 tiles, power-of-two sheets when animated, filter off for pixel art, a normal map per sheet for lighting.
- Audio: OGG Vorbis for music, WAV for short SFX.

## Commits

- Branch: `coder/<task-id>-<slug>`.
- Message: `<task-id>: <what changed>` then a blank line then why. No model names in messages.
