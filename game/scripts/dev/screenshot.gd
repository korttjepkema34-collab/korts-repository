extends SceneTree
## Dev tool used by the coder's visual check. Loads a scene, renders a few frames in a real
## window, saves a PNG, quits. Needs a display (not --headless).
##
## godot --path game -s res://scripts/dev/screenshot.gd -- <scene_path> <out.png> [frames]


func _initialize() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	if args.size() < 2:
		push_error("usage: -- <scene_path> <out.png> [frames]")
		quit(2)
		return
	var packed: PackedScene = load(args[0])
	if packed == null:
		push_error("cannot load scene: " + args[0])
		quit(3)
		return
	root.add_child(packed.instantiate())
	var frames: int = int(args[2]) if args.size() > 2 else 10
	_capture(args[1], frames)


func _capture(path: String, frames: int) -> void:
	for _i: int in frames:
		await process_frame
	var img: Image = root.get_texture().get_image()
	var err: Error = img.save_png(path)
	if err != OK:
		push_error("save failed: " + str(err))
		quit(4)
		return
	print("screenshot saved: " + path)
	quit(0)
