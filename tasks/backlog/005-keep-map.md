# 005 The Keep map
priority: 5
roles: coder, reviewer
depends_on: 003, 004

## Goal
`data/maps/keep.json` already exists (hand-laid). Load it in `scenes/levels/keep.tscn` with `MapBuilder`, then replace the placeholder draw with `TileMapLayer` cells once task 004's tiles are approved. Gatehouse and wall, four enterable
buildings (guild house two-storey with sign), tower, cooling pond, garden plots, stall, well,
lamps with cables, eight 12x8 plots for Holds, spawn markers.

## Acceptance
- Loads headless; `visual_check` describes a walled town with a gatehouse, houses, a tower and a pond.
- `y_sort_enabled` on the root; `Roofs` layer separate; collision on walls, water, pond edge.
- Markers: `PlayerSpawn`, `HesperSpawn`, `CutterSpawn`, `Tower`, `Gate`, `Plot01..08`.
- Building footprints and door positions in `data/maps/keep.json`.
