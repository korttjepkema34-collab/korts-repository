extends SceneTree
## Playtest bot. Runs the game as a client (or solo) and follows a plan of timed input actions,
## saving a screenshot every N seconds when a display is available.
## godot --path game -s res://scripts/dev/bot.gd -- <plan.json> <out_dir> [--connect 127.0.0.1] [--telemetry file]
## plan.json: {"steps": [{"action": "move_right", "seconds": 3}, {"action": "attack", "seconds": 1, "taps": 4}, ...],
##             "screenshot_every": 5}
## Unknown actions are skipped. The bot never decides anything; the plan is the test.


func _initialize() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	if args.size() < 2:
		push_error("usage: -- <plan.json> <out_dir> [--connect host]")
		quit(2)
		return
	var plan: Variant = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	if not plan is Dictionary:
		push_error("bad plan: " + args[0])
		quit(3)
		return
	var main: PackedScene = load("res://scenes/main/main.tscn")
	root.add_child(main.instantiate())  # main.gd reads --connect from the same user args
	DirAccess.make_dir_recursive_absolute(args[1])
	_run(plan, args[1])


func _run(plan: Dictionary, out_dir: String) -> void:
	var every: float = float(plan.get("screenshot_every", 5))
	var headless: bool = DisplayServer.get_name() == "headless"
	var t_last_shot: float = 0.0
	var shot: int = 0
	var t_total: float = 0.0
	await create_timer(2.0).timeout  # let the network settle
	for step: Dictionary in plan.get("steps", []):
		var action: String = str(step.get("action", ""))
		var seconds: float = float(step.get("seconds", 1))
		var taps: int = int(step.get("taps", 0))
		var known: bool = action != "" and InputMap.has_action(action)
		if known and taps == 0:
			Input.action_press(action)
		var t0: float = Time.get_ticks_msec() / 1000.0
		var next_tap: float = t0
		while Time.get_ticks_msec() / 1000.0 - t0 < seconds:
			await process_frame
			var now: float = Time.get_ticks_msec() / 1000.0
			if known and taps > 0 and now >= next_tap:
				Input.action_press(action)
				await process_frame
				Input.action_release(action)
				next_tap = now + seconds / float(taps)
			t_total = now
			if not headless and now - t_last_shot >= every:
				t_last_shot = now
				var img: Image = root.get_texture().get_image()
				img.save_png(out_dir.path_join("bot-%03d.png" % shot))
				shot += 1
		if known and taps == 0:
			Input.action_release(action)
		if has_node("/root/Telemetry"):
			get_root().get_node("/root/Telemetry").log_event("bot_step", {"action": action, "seconds": seconds})
	print("bot: plan finished, %d screenshots" % shot)
	quit(0)
