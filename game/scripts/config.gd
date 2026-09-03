extends Node
## Autoload "Config". Loads res://data/config.json once. Everything tunable lives there.

var data: Dictionary = {}


func _ready() -> void:
	var text: String = FileAccess.get_file_as_string("res://data/config.json")
	var parsed: Variant = JSON.parse_string(text)
	if parsed is Dictionary:
		data = parsed
	else:
		push_error("config.json failed to parse")


func value(key: String, default_value: Variant = null) -> Variant:
	return data.get(key, default_value)


func load_json(path: String) -> Variant:
	## Helper for any data file: Config.load_json("res://data/waves.json")
	var text: String = FileAccess.get_file_as_string(path)
	var parsed: Variant = JSON.parse_string(text)
	if parsed == null:
		push_error("failed to parse " + path)
	return parsed
