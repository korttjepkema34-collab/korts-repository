extends SceneTree
## Playtest proof: load a scene, simulate inputs, screenshot every second, quit.
## godot --path game -s res://scripts/dev/proof.gd -- <scene> <out_dir> <seconds> [action,action,...]
## Actions are input action names from project.godot (e.g. move_right); each is pressed for one
## second in turn, cycling. Unknown actions are ignored. Needs a display (not --headless).


func _initialize() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	if args.size() < 3:
		push_error("usage: -- <scene> <out_dir> <seconds> [actions]")
		quit(2)
		return
	var packed: PackedScene = load(args[0])
	if packed == null:
		push_error("cannot load scene: " + args[0])
		quit(3)
		return
	root.add_child(packed.instantiate())
	var seconds: int = int(args[2])
	var actions: PackedStringArray = args[3].split(",") if args.size() > 3 else PackedStringArray()
	DirAccess.make_dir_recursive_absolute(args[1])
	_run(args[1], seconds, actions)


func _run(out_dir: String, seconds: int, actions: PackedStringArray) -> void:
	for i: int in seconds:
		var action: String = actions[i % actions.size()] if actions.size() > 0 else ""
		if action != "" and InputMap.has_action(action):
			Input.action_press(action)
		var t0: float = Time.get_ticks_msec() / 1000.0
		while Time.get_ticks_msec() / 1000.0 - t0 < 1.0:
			await process_frame
		if action != "" and InputMap.has_action(action):
			Input.action_release(action)
		var img: Image = root.get_texture().get_image()
		img.save_png(out_dir.path_join("proof-%02d.png" % i))
	print("proof: %d frames saved to %s" % [seconds, out_dir])
	quit(0)
