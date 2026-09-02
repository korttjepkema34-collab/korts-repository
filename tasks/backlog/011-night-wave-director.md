# 011 Night wave director and the Herald
priority: 11
roles: artist-2d, coder, reviewer
depends_on: 009, 010

## Goal
Five waves per night from a table, capped at 150 alive, plus the Herald drone.

## Acceptance
- `data/waves.json`: per-night wave list (count, mix, spawn edges, delay). Director on the server spawns from map edges, respects the cap, scales count by party size.
- Herald sprite 14x10 approved; hovers, marks the nearest player (a `PointLight2D` searchlight cone), re-targets the flow field to them until killed.
- Dawn: remaining Wired retreat off-map and despawn; unbanked relics bank; dead players respawn at the tower.
- Night counter HUD updates live.
