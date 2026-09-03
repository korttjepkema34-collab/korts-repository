extends SceneTree
## Dev tool used by the coder's run_scene_capture_output. Loads a scene headless, lets it run for
## a number of real seconds (timers, network handshakes and RPCs get wall-clock time, unlike
## --quit-after which counts frames), then quits. Printed output and errors go to stdout/stderr.
##
## godot --headless --path game -s res://scripts/dev/run_scene.gd -- <scene_path> [seconds]


func _initialize() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	if args.size() < 1:
		push_error("usage: -- <scene_path> [seconds]")
		quit(2)
		return
	var packed: PackedScene = load(args[0])
	if packed == null:
		push_error("cannot load scene: " + args[0])
		quit(3)
		return
	root.add_child(packed.instantiate())
	var seconds: float = float(args[1]) if args.size() > 1 else 3.0
	_run_for(seconds)


func _run_for(seconds: float) -> void:
	await create_timer(seconds).timeout
	print("run_scene: %.1f s elapsed, quitting" % seconds)
	quit(0)
