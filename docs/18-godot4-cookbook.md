# 18 - Godot 4 cookbook (known-good snippets for the coder)

Read this before writing any GDScript. Every snippet targets Godot 4.3+. When in doubt, call
`search_godot_api` (the coder tool backed by the engine's own class reference dump) instead of
guessing a signature. Anything not here and not in the dump does not exist.

## Rules that save the most time

1. **Never hand-write `tile_map_data` or a TileSet in `.tscn` text.** They are packed bytes. Build
   tile sets and maps from code and JSON (snippets below).
2. **Prefer building complex scenes in `_ready()` from code** over long `.tscn` files. A `.tscn`
   you write by hand should be a root node, a script, and a handful of children.
3. **Autoloads** are registered in `project.godot` under `[autoload]` and accessed by name:
   `Config`, `Net`, `Clock` exist already.
4. **Static typing everywhere.** `var x: int = 0`, `func f(a: float) -> void:`.
5. **Server only simulates.** Guard with `if not multiplayer.is_server(): return`.

## Files, JSON, config

```gdscript
var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string("res://data/waves.json"))
var waves: Array = parsed as Array
var port: int = int(Config.value("server_port", 7777))
var enemies: Array = Config.load_json("res://data/enemies.json")
```

Saves go to `user://`: `FileAccess.open("user://saves/%s.json" % name, FileAccess.WRITE).store_string(JSON.stringify(d, "\t"))`.

## Networking (high-level multiplayer, ENet)

Already wrapped in `scripts/net.gd`. The primitives:

```gdscript
var peer: ENetMultiplayerPeer = ENetMultiplayerPeer.new()
peer.create_server(7777, 8)            # or peer.create_client("127.0.0.1", 7777)
multiplayer.multiplayer_peer = peer
multiplayer.peer_connected.connect(_on_peer_connected)   # (id: int)
multiplayer.is_server()
multiplayer.get_unique_id()            # 1 is always the server
multiplayer.get_remote_sender_id()     # inside an RPC: who called
```

RPC annotations. Clients send input to the server; the server owns state.

```gdscript
@rpc("any_peer", "call_remote", "unreliable_ordered")
func send_input(move: Vector2, actions: int) -> void:
	if not multiplayer.is_server():
		return
	var who: int = multiplayer.get_remote_sender_id()
	_inputs[who] = move

@rpc("authority", "call_remote", "reliable")
func announce(text: String) -> void:
	print(text)
# call: send_input.rpc(move, 0)   or   announce.rpc_id(peer_id, "hi")
```

Spawning a node per peer, replicated to everyone:

```gdscript
var spawner: MultiplayerSpawner = MultiplayerSpawner.new()
spawner.spawn_path = get_path()                      # children of this node are spawned
spawner.add_spawnable_scene("res://scenes/player/reaper.tscn")
add_child(spawner)
# on the server, when a peer joins:
var p: Node2D = preload("res://scenes/player/reaper.tscn").instantiate()
p.name = str(peer_id)
p.set_multiplayer_authority(1)                       # server owns it
add_child(p)                                         # spawner replicates it
```

Syncing properties from code:

```gdscript
var sync: MultiplayerSynchronizer = MultiplayerSynchronizer.new()
var cfg: SceneReplicationConfig = SceneReplicationConfig.new()
cfg.add_property(NodePath(".:position"))
cfg.add_property(NodePath(".:facing"))
sync.replication_config = cfg
sync.root_path = NodePath("..")
add_child(sync)
```

## Tile sets and maps from code (never from .tscn text)

```gdscript
func make_tileset(texture: Texture2D, tile: int = 32) -> TileSet:
	var ts: TileSet = TileSet.new()
	ts.tile_size = Vector2i(tile, tile)
	var src: TileSetAtlasSource = TileSetAtlasSource.new()
	src.texture = texture
	src.texture_region_size = Vector2i(tile, tile)
	var cols: int = int(texture.get_width() / tile)
	var rows: int = int(texture.get_height() / tile)
	for y: int in rows:
		for x: int in cols:
			src.create_tile(Vector2i(x, y))
	ts.add_source(src, 0)                              # source id 0
	ts.add_physics_layer()                             # layer 0
	ts.add_custom_data_layer()
	ts.set_custom_data_layer_name(0, "water")
	return ts

func mark_solid(ts: TileSet, coords: Vector2i, tile: int = 32) -> void:
	var src: TileSetAtlasSource = ts.get_source(0) as TileSetAtlasSource
	var td: TileData = src.get_tile_data(coords, 0)
	td.add_collision_polygon(0)
	var h: float = tile / 2.0
	td.set_collision_polygon_points(0, 0, PackedVector2Array([Vector2(-h, -h), Vector2(h, -h), Vector2(h, h), Vector2(-h, h)]))

func mark_water(ts: TileSet, coords: Vector2i) -> void:
	var src: TileSetAtlasSource = ts.get_source(0) as TileSetAtlasSource
	src.get_tile_data(coords, 0).set_custom_data("water", true)

# a layer:
var ground: TileMapLayer = TileMapLayer.new()
ground.tile_set = ts
ground.set_cell(Vector2i(3, 4), 0, Vector2i(1, 0))    # (cell, source id, atlas coords)
add_child(ground)
# read custom data at a world position:
var cell: Vector2i = ground.local_to_map(ground.to_local(world_pos))
var td: TileData = ground.get_cell_tile_data(cell)
var in_water: bool = td != null and bool(td.get_custom_data("water"))
```

Map layouts live in JSON (`data/keep.json`): a 2D array of atlas coords per layer plus named
markers. A `MapBuilder` reads it and calls `set_cell`. Roofs go on a separate layer named `Roofs`.

## Y-sort, movement, camera

```gdscript
y_sort_enabled = true                                  # on the level root and any container
# sprites: put the origin at the feet: sprite.offset = Vector2(0, -24) for a 32x48 sprite
# movement (server):
velocity = input_dir.normalized() * speed
move_and_slide()
# facing from an 8-direction vector to 4 sprites: if abs(v.x) > abs(v.y): right/left else down/up
# camera zoom:
camera.zoom = Vector2(1.5, 1.5)
create_tween().tween_property(camera, "zoom", Vector2(1.0, 1.0), 0.3)
```

## Lighting layer

```gdscript
var tint: CanvasModulate = CanvasModulate.new()
tint.color = Color("#f0e4cd")                          # night: Color("#465878")
add_child(tint)

var lamp: PointLight2D = PointLight2D.new()
lamp.texture = preload("res://assets/fx/light_disc.png") # a soft white radial disc
lamp.color = Color("#ffb464")
lamp.energy = 1.2
lamp.texture_scale = 2.0
lamp.position = Vector2(x, y)
add_child(lamp)

var smoke: GPUParticles2D = GPUParticles2D.new()
var mat: ParticleProcessMaterial = ParticleProcessMaterial.new()
mat.direction = Vector3(0, -1, 0)
mat.initial_velocity_min = 10.0
mat.initial_velocity_max = 20.0
mat.gravity = Vector3(0, -5, 0)
smoke.process_material = mat
smoke.amount = 12
smoke.lifetime = 3.0
add_child(smoke)
```

Post-process: a `CanvasLayer` with a full-screen `ColorRect` and a `ShaderMaterial` that reads
`screen_texture` (`uniform sampler2D screen_texture : hint_screen_texture;`).

## Timers, tweens, signals

```gdscript
await get_tree().create_timer(0.8).timeout
var t: Tween = create_tween()
t.tween_property(self, "modulate:a", 0.15, 0.2)
signal died(peer_id: int)
died.emit(1)
died.connect(_on_died)
```

## Headless and command line

```gdscript
var headless: bool = DisplayServer.get_name() == "headless"
var user_args: PackedStringArray = OS.get_cmdline_user_args()   # everything after "--"
```

Run: `godot --headless --path game -- --server`. Quit after N frames: `--quit-after N`.

## gdUnit4 test template

```gdscript
class_name TestSomething
extends GdUnitTestSuite

func test_it() -> void:
	var node: Node = auto_free(Node.new())
	assert_int(2 + 2).is_equal(4)
	assert_bool(true).is_true()
	assert_that(node).is_not_null()
	assert_str("a").is_equal("a")
```

## Godot 3 traps (the gate rejects these)

`export var` -> `@export var`; `onready var` -> `@onready var`; `yield(` -> `await`;
`connect("sig", self, "m")` -> `sig.connect(m)`; `instance()` -> `instantiate()`;
`KinematicBody2D` -> `CharacterBody2D`; `change_scene(` -> `change_scene_to_file(`;
`.empty()` -> `.is_empty()`; `PoolStringArray` -> `PackedStringArray`; `TileMap` -> `TileMapLayer`.

## Maps from data (never lay out tiles by hand)

```gdscript
var map: MapBuilder = MapBuilder.new()
add_child(map)
map.build("fallows")                         # data/maps/fallows.json, validated by the level designer job
var spawn: Vector2 = map.get_node("PlayerSpawn").position
var exits: Array[Node] = map.find_children("Exit*", "Marker2D")
var in_water: bool = bool(map.entry_at(player.global_position).get("slow", false))
```

Swap the placeholder draw for real tiles by iterating `map.rows` and calling `TileMapLayer.set_cell`
with the atlas coords from `data/tileset_map.json` (task 005). Input actions are fixed:
`move_left/right/up/down`, `attack`, `dodge`, `interact`.

## Normal maps for 2D lights

Approved sprites and tiles come with a `<name>.n.png` normal map when the job asked for
`postprocess.normal_map: true`. Use it so lamps light faces, not just colours:

```gdscript
var tex: CanvasTexture = CanvasTexture.new()
tex.diffuse_texture = preload("res://assets/approved/tiles/keep/wall.px.png")
tex.normal_texture = preload("res://assets/approved/tiles/keep/wall.px.n.png")
sprite.texture = tex          # Sprite2D / AnimatedSprite2D frames / TileSetAtlasSource.texture
```
