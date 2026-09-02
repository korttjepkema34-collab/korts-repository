# 005 Saltreach map scene
priority: 5
roles: coder, reviewer
depends_on: 003, 004

## Goal
Build `scenes/levels/saltreach.tscn`: a TileMapLayer hub with a pier, three stilt houses, the
guild hall, the empty bell tower, and spawn points. Use approved tiles; placeholders only where
an approved tile is missing.

## Acceptance
- Scene loads headless and `visual_check` describes a coastal town with a pier and water.
- Spawn point marker nodes: `PlayerSpawn`, `MarrowSpawn`, `PellSpawn`, `BellTower`.
- Collision on water and building walls via TileSet physics layers.
- Map data-driven where sensible: house positions in `data/saltreach.json`.
