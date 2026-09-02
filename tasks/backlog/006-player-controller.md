# 006 Server-authoritative player controller
priority: 6
roles: coder, reviewer
depends_on: 003

## Goal
`scenes/player/player.tscn` with 4-direction movement, run as server-authoritative: the client
sends input vectors via RPC, the server moves the CharacterBody2D and syncs position with a
MultiplayerSynchronizer. Solo play runs a local server peer.

## Acceptance
- `MultiplayerSpawner` spawns a player per peer in `saltreach.tscn`.
- Movement speed, stamina cost in `data/player.json`.
- Water tiles halve speed (read tile custom data).
- Placeholder rectangle sprite until the player sheet is approved, then swap to AnimatedSprite2D with the 4-direction walk.
- `run_scene_capture_output` shows "server: peer N spawned" when run with `--server`.
