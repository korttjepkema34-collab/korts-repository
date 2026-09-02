# 008 Interiors on the same map: roofs and doors
priority: 8
roles: coder, reviewer
depends_on: 005, 006

## Goal
Buildings are part of the world. Roofs fade when a player is inside the footprint; doors open,
close, lock, and break; walls block movement and pathing.

## Acceptance
- `Roofs` TileMapLayer fades to 15% alpha over 0.2 s when the local player enters a footprint from `data/keep.json`, restores on exit.
- Door scene: states closed/open/locked/broken, health from `data/build.json`, server-authoritative interaction, blocks movement when closed.
- Camera2D zooms to 1.5x inside a building, 1x outside, tweened.
- `visual_check` of a Reaper inside the guild house shows the interior with the roof faded.
