# 005 The Keep map
priority: 5
roles: coder, reviewer
depends_on: 003, 004

## Goal
`scenes/levels/keep.tscn`: the hub from `mock-day.png`. Gatehouse and wall, four enterable
buildings (guild house two-storey with sign), tower, cooling pond, garden plots, stall, well,
lamps with cables, eight 12x8 plots for Holds, spawn markers.

## Acceptance
- Loads headless; `visual_check` describes a walled town with a gatehouse, houses, a tower and a pond.
- `y_sort_enabled` on the root; `Roofs` layer separate; collision on walls, water, pond edge.
- Markers: `PlayerSpawn`, `HesperSpawn`, `CutterSpawn`, `Tower`, `Gate`, `Plot01..08`.
- Building footprints and door positions in `data/keep.json`.
