class_name MapBuilder
extends Node2D
## Builds a playable level from an ASCII map in data/maps/<name>.json (see docs/21-levels.md).
## Until real tiles exist it draws palette-coloured rectangles and still gives collision, markers,
## doors and lights, so the game is playable and proof runs work before any art is approved.
## When a TileSet exists for a layer, swap `_draw_placeholder` for TileMapLayer.set_cell per cell
## (docs/18-godot4-cookbook.md); the JSON stays the same.

const TILE: int = 32
const PALETTE: Array[Color] = [
	Color("#0d0c10"), Color("#1c1a22"), Color("#2e2b33"), Color("#4a4650"), Color("#706a72"), Color("#a39b93"), Color("#d9cfbf"), Color("#3a2a22"),
	Color("#6b4a34"), Color("#9c6a3c"), Color("#c9a24a"), Color("#5a1f22"), Color("#8c2f2a"), Color("#1f3a3a"), Color("#3e7f76"), Color("#7fd6d1"),
]

var map_name: String = ""
var width: int = 0
var height: int = 0
var rows: PackedStringArray = []
var legend: Dictionary = {}
var markers: Dictionary = {}  # name -> Array[Vector2i]
var _cells: Array = []  # of {pos, entry}


static func load_map(name: String) -> Dictionary:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string("res://data/maps/%s.json" % name))
	return parsed if parsed is Dictionary else {}


func build(name: String) -> void:
	var data: Dictionary = load_map(name)
	if data.is_empty():
		push_error("map not found: " + name)
		return
	var tiles: Variant = JSON.parse_string(FileAccess.get_file_as_string("res://data/tiles.json"))
	legend = (tiles as Dictionary).get("legend", {})
	map_name = name
	rows = PackedStringArray(data.get("rows", []))
	height = rows.size()
	width = rows[0].length() if height > 0 else 0
	y_sort_enabled = true
	for y: int in height:
		for x: int in width:
			var ch: String = rows[y][x]
			var entry: Dictionary = legend.get(ch, legend.get(".", {}))
			_cells.append({"pos": Vector2i(x, y), "entry": entry, "ch": ch})
			if entry.has("marker"):
				var arr: Array = markers.get(entry["marker"], [])
				arr.append(Vector2i(x, y))
				markers[entry["marker"]] = arr
			if not bool(entry.get("walk", true)) and not bool(entry.get("door", false)):
				_add_collision(Vector2i(x, y))
			if bool(entry.get("door", false)):
				_add_door(Vector2i(x, y))
			if bool(entry.get("light", false)):
				_add_light(Vector2i(x, y), bool(entry.get("hearth", false)))
	for mname: String in markers.keys():
		var i: int = 0
		for cell: Vector2i in markers[mname]:
			var m: Marker2D = Marker2D.new()
			m.name = mname if i == 0 else "%s%d" % [mname, i]
			m.position = cell_center(cell)
			add_child(m)
			i += 1
	queue_redraw()


func cell_center(cell: Vector2i) -> Vector2:
	return Vector2(cell.x * TILE + TILE / 2.0, cell.y * TILE + TILE / 2.0)


func cell_at(world_pos: Vector2) -> Vector2i:
	return Vector2i(int(floor(world_pos.x / TILE)), int(floor(world_pos.y / TILE)))


func entry_at(world_pos: Vector2) -> Dictionary:
	var c: Vector2i = cell_at(world_pos)
	if c.x < 0 or c.y < 0 or c.x >= width or c.y >= height:
		return {}
	return legend.get(rows[c.y][c.x], {})


func is_walkable(cell: Vector2i) -> bool:
	if cell.x < 0 or cell.y < 0 or cell.x >= width or cell.y >= height:
		return false
	return bool(legend.get(rows[cell.y][cell.x], {}).get("walk", false))


func _add_collision(cell: Vector2i) -> void:
	var body: StaticBody2D = StaticBody2D.new()
	body.position = cell_center(cell)
	var shape: CollisionShape2D = CollisionShape2D.new()
	var rect: RectangleShape2D = RectangleShape2D.new()
	rect.size = Vector2(TILE, TILE)
	shape.shape = rect
	body.add_child(shape)
	add_child(body)


func _add_door(cell: Vector2i) -> void:
	var door: Area2D = Area2D.new()
	door.name = "Door_%d_%d" % [cell.x, cell.y]
	door.position = cell_center(cell)
	door.set_meta("cell", cell)
	door.set_meta("state", "closed")
	add_child(door)


func _add_light(cell: Vector2i, hearth: bool) -> void:
	var light: PointLight2D = PointLight2D.new()
	light.position = cell_center(cell)
	light.color = Color("#78e6dc") if hearth else Color("#ffb464")
	light.energy = 0.9
	light.texture = _disc_texture()
	light.texture_scale = 4.0
	add_child(light)


static var _disc: Texture2D


static func _disc_texture() -> Texture2D:
	if _disc != null:
		return _disc
	var img: Image = Image.create(64, 64, false, Image.FORMAT_RGBA8)
	for y: int in 64:
		for x: int in 64:
			var d: float = Vector2(x - 32, y - 32).length() / 32.0
			var a: float = clampf(1.0 - d, 0.0, 1.0)
			img.set_pixel(x, y, Color(1, 1, 1, a * a))
	_disc = ImageTexture.create_from_image(img)
	return _disc


func _draw() -> void:
	for c: Dictionary in _cells:
		var entry: Dictionary = c["entry"]
		var pos: Vector2i = c["pos"]
		var col: Color = PALETTE[int(entry.get("colour", 2))]
		draw_rect(Rect2(pos.x * TILE, pos.y * TILE, TILE, TILE), col)
		if entry.get("layer", "") == "walls" or entry.get("layer", "") == "props":
			draw_rect(Rect2(pos.x * TILE, pos.y * TILE, TILE, TILE), PALETTE[0], false, 1.0)
