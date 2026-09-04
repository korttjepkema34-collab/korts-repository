extends Node
## Autoload "Telemetry". Appends one JSON line per event so playtests and balance passes have data.
## Path: --telemetry <file> (user arg) or user://telemetry/session-<unix>.jsonl

var _file: FileAccess
var _path: String = ""


func _ready() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	var i: int = args.find("--telemetry")
	if i >= 0 and i + 1 < args.size():
		_path = args[i + 1]
	else:
		DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("user://telemetry"))
		_path = "user://telemetry/session-%d.jsonl" % int(Time.get_unix_time_from_system())
	_file = FileAccess.open(_path, FileAccess.WRITE)
	log_event("boot", {"headless": DisplayServer.get_name() == "headless", "args": args})


func log_event(name: String, data: Dictionary = {}) -> void:
	if _file == null:
		return
	var rec: Dictionary = {"t": Time.get_ticks_msec() / 1000.0, "event": name}
	rec.merge(data)
	_file.store_line(JSON.stringify(rec))
	_file.flush()
