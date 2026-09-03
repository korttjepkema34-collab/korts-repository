extends Node
## Autoload "Clock". The day/night state machine. Runs on the server; clients receive syncs.

signal phase_changed(phase: String)
signal dusk_bell
signal tick(phase: String, seconds_left: float)

const DAY: String = "day"
const NIGHT: String = "night"

var phase: String = DAY
var seconds_left: float = 0.0
var day_number: int = 1
var _bell_rung: bool = false


func _ready() -> void:
	seconds_left = float(Config.value("day_seconds", 720))


func _process(delta: float) -> void:
	if not multiplayer.is_server() and multiplayer.multiplayer_peer != null and multiplayer.get_unique_id() != 1:
		return
	seconds_left -= delta
	if phase == DAY and not _bell_rung and seconds_left <= float(Config.value("dusk_bell_seconds", 120)):
		_bell_rung = true
		dusk_bell.emit()
		_rpc_bell.rpc()
	if seconds_left <= 0.0:
		_advance()
	tick.emit(phase, seconds_left)


func _advance() -> void:
	if phase == DAY:
		phase = NIGHT
		seconds_left = float(Config.value("night_seconds", 360))
	else:
		phase = DAY
		day_number += 1
		_bell_rung = false
		seconds_left = float(Config.value("day_seconds", 720))
	phase_changed.emit(phase)
	_rpc_phase.rpc(phase, seconds_left, day_number)


func is_long_night() -> bool:
	return phase == NIGHT and day_number % int(Config.value("long_night_every", 7)) == 0


@rpc("authority", "call_remote", "reliable")
func _rpc_phase(new_phase: String, new_seconds_left: float, new_day: int) -> void:
	phase = new_phase
	seconds_left = new_seconds_left
	day_number = new_day
	phase_changed.emit(phase)


@rpc("authority", "call_remote", "reliable")
func _rpc_bell() -> void:
	dusk_bell.emit()
