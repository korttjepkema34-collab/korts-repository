# 008 Brinecrab and Drowned Wanderer
priority: 8
roles: artist-2d, coder, reviewer
depends_on: 002, 006

## Goal
The two prototype enemies with the behaviours from the world bible, server-side AI.

## Acceptance
- Sprites: Brinecrab 16x16 (idle 2, lunge 3), Drowned Wanderer 16x24 (walk 6, grab 2), approved.
- Brinecrab sidles perpendicular to the player, lunges when aligned within 6 tiles.
- Wanderer walks at 60% player speed, grabs on contact for 1 s (player cannot move), cannot be outrun in water tiles.
- Enemy stats in `data/enemies.json`. Health scales by party size (count of peers).
- Enemies are spawned and simulated only on the server.
