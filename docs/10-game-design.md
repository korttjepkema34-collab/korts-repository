# 10 - Game design and scope: Reaper's Relics

Approved 2026-09-02. The proposal page with the mock frames is archived at
`docs/pitch/reapers-relics-pitch.html`; the frames are in `style/references/`.

## Four pillars, one clock

| From | System | In the prototype |
|---|---|---|
| Survivor.io | **Night hordes.** Waves in the hundreds, simple steering, one screen of threat. Relics dropped by the horde grant night-long upgrades. | 5 waves per night, cap 150 Wired per instance, Thralls + Coursers + one Herald |
| Stardew Valley | **The look and the daylight loop.** Three-quarter pixel art, dense tiles, scavenging, crafting, tending your Hold, talking to the few people left. | Day scavenging in the Fallows, two NPCs, crafting at the Hold |
| Elden Ring | **Bosses, stamina, death that costs.** Telegraphed patterns, dodge roll, stamina on every swing. Die and unbanked relics drop where you fell. Hearths are where you rest and bank. | The Castellan with three siren-telegraphed patterns; dodge; relic drop on death |
| Minecraft | **Your Hold.** A tile plot inside the Keep you wall, roof, door and wire. Persistent, visible to every player. Walls and doors take horde damage; a broken door lets the Wired in. | Plot building with 6 piece types, persistence, damage and repair |

**The clock makes them one game.** Day (12 min): scavenge, build, trade, dungeons. Night (6 min):
five waves, the Wired move on light, the wall holds if the shared lamps are powered. Dawn banks
relics and respawns the dead at the tower. Lengths live in `game/data/config.json`.

## Scope ladder

| Rung | What it is | Players | Needs |
|---|---|---|---|
| **1. Co-op campaign** (build first) | Story campaign, drop-in co-op, dedicated server, the Keep as hub, plots, hordes | 1-8 | Godot 4 high-level multiplayer (ENet), server-authoritative everything, `MultiplayerSpawner`/`Synchronizer` |
| 2. Persistent world | Accounts, saved characters, everyone online shares the Keep, campaign in instances | 10s-100s | Nakama (accounts, chat, storage, matchmaking) + headless Godot world server + instanced campaign servers |
| 3. MMO | Many zones, thousands online, economy, guilds | 1000s | Everything above, sharded. Decided later with real players. |

Build rung 1 designed so rung 2 is an addition, not a rewrite.

## Architecture rules

1. **Server-authoritative from the first commit.** Clients send inputs; the server simulates and
   sends state. Never trust the client for position, damage, inventory, relics, or build actions.
2. **Dedicated server is the default.** The game runs headless on the home server. Solo play spins
   up a local server process.
3. **Campaign content is instanced.** Every campaign map is a scene the server instantiates per
   party. A party of one is a small instance. The Keep is shared.
4. **Platform backend is separate.** Accounts, characters, chat, matchmaking are Nakama's job at
   rung 2. Rung 1 stubs it with JSON saves on the server.
5. **Data-driven content.** Items, enemies, quests, dialogue, build pieces, wave tables in
   `game/data/*.json`. Code loads them; it never hardcodes them.

## Hordes (decision 2)

- Cap **150 Wired per instance** at rung 1. Thousands come once the netcode is proven.
- Server-side simulation with a **shared flow field** toward the nearest powered light or marked
  player, recomputed every 0.5 s on a 32 px grid. Thralls sample the field; Coursers path
  directly to their target; the Herald hovers and re-targets the field.
- Network: the server sends compressed positions (16-bit per axis, delta, 10 Hz) and lets clients
  interpolate. Damage and grabs resolve on the server only.
- Waves from `data/waves.json`: count, mix, spawn edges, per-party scaling (health only).

## Building: the Hold (decision 3)

- One fixed plot per player inside the Keep's wall (12x8 tiles) at rung 1. Free-build anywhere is
  rung 2.
- Tile-based: wall, door, window, roof, lamp, workbench. Pieces from `data/build.json` with cost,
  health, and what they block.
- Persisted as a tile diff per player on the server (`user://saves/<name>.hold.json`).
- Walls and doors take horde damage and need repair. A broken door lets Thralls inside.
- Roofs fade when any player is under them. Interiors are on the same map as the world (decision 7).

## Movement and interiors (decision 7)

- Three-quarter top-down. Eight-direction movement, four-direction sprites (right = flipped left).
- `Y-sort` on every level: characters, props and buildings sort by their feet.
- Buildings are part of the world map. Roof layer fades when the player is inside its footprint.
  Doors are tiles that open, close, lock, and break. Walls block movement and horde pathing.
- The camera zooms: 1x in the world (30x17 tiles), 1.5x indoors, 3x for dialogue.

## Death and relics

- Unbanked relics drop where you die. Walk back to reclaim; anyone in the party can.
- Resting at a Hearth banks relics and restores vigour and stamina. Dawn banks automatically.
- Dead players respawn at the tower at dawn, or when a party member touches a Hearth at night.

## Rendering: 2.5D in 2D (decision 9)

Two layers. The **pixel layer** uses only the 16-colour palette. The **lighting layer** is free:

- `CanvasModulate` day/night tint driven by the clock.
- `PointLight2D` on lamps (warm, flicker), hearths (cold), the Herald (searchlight cone via a
  light texture), the Castellan's shield. Sprites and tiles get normal maps so light has direction.
- `GPUParticles2D`: chimney smoke, dust motes, embers at night, fog sheets in the Fallows.
- One full-screen post-process shader: vignette, soft glow on bright pixels, 1-2 px blur on the
  top ~10% and bottom ~5% of the frame.
- **Readability rule**: every enemy identifiable at any distance at night; lamps light ground,
  not air. See `style/style-bible.md`.
- True HD-2D (3D geometry, Sprite3D) is a later option. Sprites and tiles carry over as textures.

## Where the AI team will struggle

- **Netcode** with hordes. Server-authoritative prediction plus 150 moving enemies is the hardest
  code in the project. It has its own tasks and the escalation model reviews the design first.
- **Consistency at 32 px.** More pixels per sprite means more ways to drift. Reference sheets and
  IP-Adapter are mandatory; the modular body + equipment layers keep art volume sane.
- **Animation.** 4-direction walk (6 frames), attack (4), dodge (3), idle (2) per character.
  Generate against a fixed reference sheet; the reviewer compares frames. Open sprite bases (LPC,
  check licence) remain a fallback.

## First prototype (milestone 4)

- The Keep (hub) with gatehouse, 4 buildings you can enter, tower, pond, one plot per player.
- The Fallows (one map) and the Undercroft (one dungeon) as instances.
- The Reaper with scythe, hook, dodge, one relic ability. Vigour, stamina, relic on screen.
- Thrall, Courser, Herald, the Castellan. Night waves from a table, capped at 150.
- Hold building with 6 pieces, persistence, damage, repair.
- Day/night clock, Hearths, relic banking, death drop.
- The quest "Keep the Lights On" completable solo or with two clients on a dedicated server.
- Lighting layer live: day/night tint, lamps, hearths, smoke, post-process.
