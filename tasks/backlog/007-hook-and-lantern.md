# 007 Hook attack and lantern
priority: 7
roles: coder, artist-2d, reviewer
depends_on: 006

## Goal
Two player actions from the world bible: salvage hook (quick, short) and lantern (reveal + stun,
consumes oil). Server validates hits.

## Acceptance
- Hook: 4-frame attack animation request to the artist, hitbox active on frames 2-3, damage in `data/player.json`.
- Lantern: toggles a Light2D-free "lit" state (no dynamic lighting; swap a sprite ring), drains oil per second, reveals nodes in group `hidden_salvage`.
- HUD scene with three bars (health, stamina, oil), lowercase labels, palette colours 15/14/13.
- Reviewer checks HUD via `visual_check`.
