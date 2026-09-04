extends Node2D
## Entry scene. Decides whether this process is a dedicated server, a client, or solo (both).
## See docs/10-game-design.md: server-authoritative from the first commit.

@export var first_level: PackedScene


func _ready() -> void:
	var port: int = int(Config.value("server_port", 7777))
	var address: String = Net.connect_address()
	if Net.wants_server():
		print("main: starting as dedicated server")
		Net.start_server(port, int(Config.value("max_players", 8)))
	elif address != "":
		print("main: starting as client -> %s" % address)
		Net.start_client(address, port)
	else:
		print("main: starting solo (local server + client)")
		Net.start_local_server_and_client(port)
	Clock.phase_changed.connect(func(p: String) -> void:
		print("clock: %s %d" % [p, Clock.day_number])
		Telemetry.log_event("phase", {"phase": p, "day": Clock.day_number}))
	Net.peer_joined.connect(func(id: int) -> void: Telemetry.log_event("peer_joined", {"peer": id}))
	if first_level != null:
		add_child(first_level.instantiate())
	else:
		var map: MapBuilder = MapBuilder.new()
		map.name = "Map"
		add_child(map)
		map.build(str(Config.value("start_map", "keep")))
		Telemetry.log_event("map_built", {"map": map.map_name, "w": map.width, "h": map.height, "markers": map.markers.keys()})
