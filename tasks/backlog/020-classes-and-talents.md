# 020 Classes and talent trees
priority: 20
roles: coder, artist-2d, reviewer
depends_on: 018, 019

## Goal
Ten classes from `classes.json`: starting kit, signature relic ability, three-branch talent tree, proficiency.

## Acceptance
- Character creation: pick a class, hair, scar, cloak colour, one of three skin tones from the palette.
- Ten signatures implemented server-side; the Linker's pack uses the Thrall AI from task 010 with a friendly flag; the Cantor's hymn disorients the flow field.
- Talent trees in `data/talents.json` (30 talents, 3 per branch per class to start); XP from kills, relics banked, quests.
- Proficiency: +10% with the class's weapon class.
