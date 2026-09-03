# 018 Weapon classes and attack animations
priority: 18
roles: artist-2d, coder, reviewer
depends_on: 017

## Goal
The nine weapon classes as distinct verbs with their own attack animations on the modular rig.

## Acceptance
- Held-item layer sprites for all 25 weapons (4 directions, idle + 4 attack frames) matching `docs/15-gameplay-systems.md` §4. Approved.
- Per-class attack behaviour from `weapons.json`: aps, reach, stamina, noise; spear thrusts through barred doors; hammer breaks doors; whip pulls; bow and guns spawn projectiles; throwables arc.
- Noise feeds the flow field (task 010): a gunshot re-targets Thralls within 20 tiles.
- gdUnit4 tests for damage-by-rarity and stamina drain.
