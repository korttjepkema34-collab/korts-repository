# 002 Choose the game and fill the style bible
priority: 2
roles: human

## Goal
Decide genre, perspective, and visual style so the style bible stops being a template.

## Acceptance
- `style/style-bible.md` has no TBD lines in Game, Visual style, and Prompt fragments.
- At least a palette swatch and one mood reference are in `style/references/`.
- Decision logged in `docs/decisions.md`.

## Notes
Recommendation from the scaffold: 2D pixel art. Cheapest to generate, easiest to keep consistent,
and sidesteps the weak 3D-animation tooling for the first prototype. The orchestrator should not
plan this task; it is for the human. Leave it in backlog until done.
