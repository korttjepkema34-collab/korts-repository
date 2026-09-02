# 009 The Shallows map
priority: 9
roles: artist-2d, coder, reviewer
depends_on: 004, 008

## Goal
First campaign map: exposed street, tide pools, kelp, a collapsed bridge; instanced per party.

## Acceptance
- Tileset additions: cobble, kelp overlay, tide pool water, mud, broken bridge pieces. Approved.
- `scenes/levels/shallows.tscn` with 6 Brinecrabs, 3 Wanderers near the exit, one hidden salvage.
- Entered from Saltreach via a trigger at the pier end; the server instantiates one copy per party.
- Old Pell placeholder NPC with two lines of dialogue from `data/dialogue.json`.
