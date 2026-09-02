# 002 Style bible and references
priority: 2
roles: orchestrator, artist-2d, reviewer

## Goal
Fill the remaining TBDs in `style/style-bible.md` with conventional defaults for a 2D pixel-art
online RPG, then produce the first reference images so later art jobs have something to match.

## Acceptance
- Style bible has no TBD in Visual style, Prompt fragments, Characters (proportions), Audio.
- One palette swatch image and one environment mood image approved into `assets/approved/`.
- One player character reference sheet (front, side, back) approved.
- Choices logged "(auto)" in `docs/decisions.md`.

## Notes
Orchestrator: return the full rewritten bible in the plan's `style_bible` key and the choices in
`decisions`. Suggested defaults: 16-colour warm fantasy palette, 2.5-head proportions, 1 px dark
outline, flat 3-tone shading, chiptune-with-strings music, dry retro SFX. Then plan three image
jobs (palette swatch, environment mood, character sheet front/side/back on transparent
background). The approved character sheet becomes `spec.references` for every character job
after this.
