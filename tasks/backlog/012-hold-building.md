# 012 The Hold: plot building
priority: 12
roles: artist-2d, coder, reviewer
depends_on: 005, 008

## Goal
Minecraft-style building on a fixed 12x8 plot per player inside the Keep.

## Acceptance
- Build pieces from `data/build.json`: wall, door, window, roof, lamp, workbench; each with cost in scrap, health, and blocking flags. Sprites approved.
- Build mode UI: ghost piece on the grid, place/remove, server validates ownership, cost and adjacency.
- Persistence: tile diff per player in `user://saves/<name>.hold.json` on the server, reloaded on join.
- Walls and doors take horde damage; repair costs scrap; a broken door lets Thralls in (uses task 008 doors).
- Placed lamps join the lighting layer and the flow field's light targets.
