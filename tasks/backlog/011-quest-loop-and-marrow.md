# 011 Quest loop: Bring Up the Bell
priority: 11
roles: coder, reviewer
depends_on: 005, 010

## Goal
Tie the prototype together: Marrow gives the quest, the party clears the Chapel, returns, hangs
the bell, rings it. Quest state lives on the server and is saved per character to JSON.

## Acceptance
- `data/quests.json` defines the quest with four steps; `data/dialogue.json` has Marrow's lines in the world-bible voice.
- Interacting with `BellTower` with the bell hangs it and plays a placeholder ring.
- Character save file per peer in `user://saves/<name>.json` on the server: position, oil, quest state.
- Two clients on one server can complete the quest together; a solo client can complete it alone.
