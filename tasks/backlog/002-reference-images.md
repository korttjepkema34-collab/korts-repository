# 002 Reference images
priority: 2
roles: artist-2d, reviewer

## Goal
Produce the three reference images every later art job cites, matching the style bible palette.

## Acceptance
- `saltreach-mood.png`: the pier at golden hour, stilt houses, lantern posts, bell tower without a bell. 1024x576 then nearest-neighbour to 640x360.
- `player-sheet.png`: Salvager front/side/back on one row, transparent, 16x24 scale (generate at 8x and downscale).
- `drowned-sheet.png`: Drowned Wanderer front/side/back, same layout.
- All three approved by the reviewer and copied into `style/references/`.

## Notes
Prompt subject first, then the verbatim positive suffix from the style bible. Cite
`style/references/palette.png` as a reference. Generate 4 candidates each. The reviewer should
be strict on palette and proportions and lenient on detail.
