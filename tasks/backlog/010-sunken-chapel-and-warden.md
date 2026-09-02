# 010 The Sunken Chapel and the Warden
priority: 10
roles: artist-2d, coder, reviewer
depends_on: 009

## Goal
First dungeon and boss. The bell-ring telegraph is the whole fight.

## Acceptance
- Tileset: chapel stone, knee-deep water, stained-glass light patches. Warden sprite 16x32, approved.
- `scenes/levels/chapel.tscn` with nave, three Wanderers, the bell above the altar.
- Warden: three patterns (sweep, charge, summon two Wanderers), each preceded by a 0.6 s bell ring and a visible wind-up frame. Server-side.
- On defeat the bell becomes interactable; picking it up sets `quest.bell = true` in the party's server state.
