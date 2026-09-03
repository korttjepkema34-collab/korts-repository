# 024 The Long Night and wave pressure
priority: 24
roles: coder, audio, reviewer
depends_on: 011, 022

## Goal
Every seventh night doubles the waves and adds a mini-boss; pressure scales with the base.

## Acceptance
- Night 7, 14, ... use the Long Night table: double count, a Castellan-class champion at wave 3.
- Pressure formula in `data/waves.json` from light radius, noise, stored relics; visible on the HUD as a threat meter the day before.
- Long Night music variant and a bell cue at dusk.
