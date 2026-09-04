# 013 The Fallows
priority: 13
roles: artist-2d, coder, reviewer
depends_on: 004, 010

## Goal
Plan as: a `level` job (name fallows, 40x24, markers PlayerSpawn, Exit, EnemySpawn x6, NpcSpawn) -> a `code` job that loads it with MapBuilder and adds the entry/exit triggers -> a `text` job for Old Cutter's lines. First open zone: suburbs gone to meadow, day scavenging, the night waves' source. Instanced per party.

## Acceptance
- Tileset additions: tall grass, ivy, overpass pieces, wrecked cars, intact-house set with enterable interiors. Approved.
- `scenes/levels/fallows.tscn` with scrap nodes, relic fragments, 10 Thralls and 2 Coursers, one hidden relic.
- Entered from the Keep's gate; the server instantiates one copy per party; return trigger at the overpass.
- Old Cutter placeholder NPC with three lines from `data/dialogue.json` in the world-bible voice.
