# 014 The Undercroft and the Castellan
priority: 14
roles: artist-2d, coder, reviewer
depends_on: 013

## Goal
First dungeon and boss. The siren telegraph is the whole fight.

## Acceptance
- Tileset: marble floor and walls, gold-leafed cables, reactor with glow, knee-deep water. Castellan sprite 36x60 (idle, sweep, charge, call) approved.
- `scenes/levels/undercroft.tscn`: nave with three Thralls and a Herald, the reactor room.
- Castellan: three patterns (shield sweep, charge, call that pulls six Thralls in), each preceded by a 0.8 s siren SFX cue and a visible wind-up frame. Server-side. Health scales by party.
- On defeat the reactor becomes interactable; picking it up sets `quest.reactor = true` in the party's server state.
