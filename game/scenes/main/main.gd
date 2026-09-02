extends Node2D
## Entry scene. Decides whether this process is a dedicated server or a client.
## See docs/10-game-design.md: server-authoritative from the first commit.


func _ready() -> void:
	if "--server" in OS.get_cmdline_user_args() or DisplayServer.get_name() == "headless":
		print("main: starting as dedicated server")
	else:
		print("main: starting as client")
