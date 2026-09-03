# 021 Holdouts, wild Hearths, distance danger
priority: 21
roles: coder, artist-2d, reviewer
depends_on: 011, 013

## Goal
The prepared player's outs when caught outside, and the rule that distance from light is danger.

## Acceptance
- Night density and Thrall speed scale with distance from the nearest powered light (`data/config.json` curve).
- Any building with an intact door can be barred from inside; the horde attacks the door; repair from inside.
- Wild Hearth prop in the Fallows: interact with a relic to light it for one night (relic consumed), a safe radius the flow field avoids.
- The dusk bell and a home-direction marker on the HUD.
