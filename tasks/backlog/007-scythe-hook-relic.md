# 007 Scythe, hook, relic slot, HUD
priority: 7
roles: coder, artist-2d, reviewer
depends_on: 006

## Goal
The Reaper's three actions from the world bible, validated on the server, plus the HUD.

## Acceptance
- Scythe: 4-frame attack request to the artist; wide arc hitbox active on frames 2-3; heavy stamina cost. Values in `data/player.json`.
- Hook: fast short hitbox, pulls enemies tagged `small` one tile toward the player.
- Relic slot: equips a relic from `data/relics.json`; one active ability (battery burst: AoE stun) with a charge meter.
- HUD scene: vigour (13), stamina (11), relic (16) bars, lowercase labels; night counter top-right. Checked via `visual_check`.
