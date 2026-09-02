# 006 Server-authoritative Reaper controller
priority: 6
roles: coder, reviewer
depends_on: 003

## Goal
`scenes/player/reaper.tscn`: eight-direction movement, four-direction sprites, dodge roll with
stamina, server-authoritative: clients send input vectors and action bits via RPC, the server moves
the `CharacterBody2D` and syncs with `MultiplayerSynchronizer`. Solo runs a local server peer.

## Acceptance
- `MultiplayerSpawner` spawns a Reaper per peer in `keep.tscn`.
- Speed, stamina, dodge cost and i-frames in `data/player.json`.
- Water tiles halve speed (tile custom data). Y-sorted with feet origin.
- Placeholder 32x48 rectangle until `reaper-sheet.png` is approved, then `AnimatedSprite2D` with the walk cycle.
- `run_scene_capture_output` with `--server` prints "server: peer N spawned".
