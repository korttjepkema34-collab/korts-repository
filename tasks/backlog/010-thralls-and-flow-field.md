# 010 Thralls, Coursers, the flow field
priority: 10
roles: artist-2d, coder, reviewer
depends_on: 002, 006

## Goal
The horde units and their server-side steering.

## Notes
Walk cycles: prefer `flux2_klein_walkcycle` if that workflow exists; else `character_sheet` frame by frame.

## Acceptance
- Sprites: Thrall 32x48 (walk 6, grab 2), Courser (walk 6, sprint 4), approved and matching `thrall-sheet.png`.
- Flow field on a 32 px grid toward the nearest powered light or marked player, recomputed every 0.5 s on the server; Thralls sample it, Coursers path directly when a player is within 8 tiles.
- Grab: on contact holds the player 1 s; Courser sprint at 160% player speed.
- Stats in `data/enemies.json`; health scales by peer count. Positions sent compressed at 10 Hz; clients interpolate.
- 150 Thralls on the Keep map hold 60 fps headless on the server (print the tick time).
