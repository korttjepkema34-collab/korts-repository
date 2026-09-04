# 015 Quest loop: Keep the Lights On
priority: 15
roles: coder, reviewer
depends_on: 005, 011, 014

## Goal
Tie the prototype together: Hesper gives the quest, the party clears the Undercroft, brings the
reactor home, wires it to the wall, and survives the night that follows.

## Acceptance
- `data/quests.json` (from a `text` job, content quests) with four steps; `data/dialogue.json` (a `text` job, content dialogue) with Hesper's lines. The coder loads them; it does not write them.
- Interacting with the tower with the reactor powers the gate lamps (lighting layer) and unlocks night 4's wave table.
- Character save per peer in `user://saves/<name>.json`: position, relics, quest state, hold reference.
- Two clients on one dedicated server complete the quest together; a solo client completes it alone.
