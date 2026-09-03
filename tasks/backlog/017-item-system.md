# 017 Item system: rarity, upgrades, the Reliquary
priority: 17
roles: coder, artist-2d, reviewer
depends_on: 007, 012

## Goal
Load the generated item data and make it real: rarity rolls, workbench upgrades, and the Reliquary.

## Acceptance
- `scripts/item_db.gd` autoload loads `weapons.json`, `armor.json`, `rarities.json`, `classes.json`; unit test asserts 25 weapons, 12 sets, 10 classes.
- Loot drops roll rarity from a per-tier table and roll affixes from the weapon's pool; item instances serialise into the character save.
- Workbench station UI: +1..+10 with the scrap cost formula; server validates.
- Reliquary station: socket a relic (consumes it and 3 Saint materials and 2000 scrap), applies +25% and the relic ability; permanent. Server validates.
- Icon sheet: 25 weapons + 12 armor sets (3 pieces each) at 16x16, rarity border colours from `rarities.json`. Approved.
