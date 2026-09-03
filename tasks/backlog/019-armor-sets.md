# 019 Armor sets
priority: 19
roles: artist-2d, coder, reviewer
depends_on: 017

## Goal
Twelve armor sets with weight classes, set bonuses and side effects from `armor.json`.

## Acceptance
- Outfit layer sprites: 3 silhouettes per weight class (light, medium, heavy), each set a recolour + trim of its silhouette; 4 directions, walk/attack/dodge frames. Approved.
- Weight class applies stamina regen and dodge cost; set bonuses at 2 and 3 pieces; every side effect implemented as a named effect in `scripts/effects.gd`.
- Equipment screen shows set progress.
