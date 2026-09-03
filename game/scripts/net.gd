extends Node
## Autoload "Net". Server-authoritative networking. The server simulates; clients send input.
## Start as server:  godot --headless --path game -- --server
## Start as client:  godot --path game -- --connect 127.0.0.1

signal peer_joined(peer_id: int)
signal peer_left(peer_id: int)
signal connected_to_server
signal connection_failed

var is_server: bool = false


func _ready() -> void:
	multiplayer.peer_connected.connect(_on_peer_connected)
	multiplayer.peer_disconnected.connect(_on_peer_disconnected)
	multiplayer.connected_to_server.connect(func() -> void: connected_to_server.emit())
	multiplayer.connection_failed.connect(func() -> void: connection_failed.emit())


func start_server(port: int, max_players: int) -> Error:
	var peer: ENetMultiplayerPeer = ENetMultiplayerPeer.new()
	var err: Error = peer.create_server(port, max_players)
	if err != OK:
		push_error("server failed to start on port %d: %s" % [port, error_string(err)])
		return err
	multiplayer.multiplayer_peer = peer
	is_server = true
	print("server: listening on port %d" % port)
	return OK


func start_client(address: String, port: int) -> Error:
	var peer: ENetMultiplayerPeer = ENetMultiplayerPeer.new()
	var err: Error = peer.create_client(address, port)
	if err != OK:
		push_error("client failed to connect to %s:%d: %s" % [address, port, error_string(err)])
		return err
	multiplayer.multiplayer_peer = peer
	is_server = false
	print("client: connecting to %s:%d" % [address, port])
	return OK


func start_local_server_and_client(port: int) -> void:
	## Solo play: this process is both the server and the only client (peer id 1).
	if start_server(port, 1) == OK:
		print("solo: local server up")


func _on_peer_connected(peer_id: int) -> void:
	if multiplayer.is_server():
		print("server: peer %d spawned" % peer_id)
	peer_joined.emit(peer_id)


func _on_peer_disconnected(peer_id: int) -> void:
	peer_left.emit(peer_id)


static func wants_server() -> bool:
	return "--server" in OS.get_cmdline_user_args() or DisplayServer.get_name() == "headless"


static func connect_address() -> String:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	var i: int = args.find("--connect")
	if i >= 0 and i + 1 < args.size():
		return args[i + 1]
	return ""
