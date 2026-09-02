# 10 - Game design and scope

## Decision

**2D pixel-art online RPG.** A story campaign that plays solo or with friends, on top of a
persistent shared world. The owner's wording is "MMO RPG"; the plan below builds towards that
without betting the project on it.

## Why "MMO" needs a ladder

"MMO" means hundreds to thousands of concurrent players in one shared world: sharded zones,
server-authoritative simulation, persistent economy, anti-cheat, live ops. That is the most
common way indie projects die, and it is the hardest code an AI coder will face. The good news
is that the architecture for a small persistent-world co-op RPG and for an MMO is the **same
shape**; only the scale differs. So we build the shape correctly from day one and grow.

| Rung | What it is | Players | Needs |
|---|---|---|---|
| **1. Co-op campaign** | Story campaign, drop-in co-op, one player hosts or a dedicated server runs the session | 1-8 | Godot 4 high-level multiplayer (ENet), server-authoritative movement/combat, `MultiplayerSpawner`/`MultiplayerSynchronizer` |
| **2. Persistent world** | Accounts, saved characters, a hub town where everyone online sees each other, campaign runs in instances | 10s-100s | Nakama (accounts, chat, storage, matchmaking) + headless Godot world server + instanced campaign servers |
| **3. MMO** | Many zones, thousands online, economy, guilds | 1000s | Everything above, sharded, plus ops work that is out of scope until rung 2 is live and fun |

**We build rung 1 first, designed so rung 2 is an addition, not a rewrite.** Rung 3 is a
decision for later, made with real players.

## Architecture rules that make the ladder work

1. **Server-authoritative from the first commit.** Clients send inputs, the server simulates and
   sends state. Never trust the client for position, damage, or inventory. This is the one rule
   that cannot be retrofitted.
2. **Dedicated server is the default, host-mode is a convenience.** The game runs as a headless
   server (`--headless --server`) on the home server. Solo play spins up a local server process.
3. **Campaign content is instanced.** Every campaign map is a scene the server can instantiate
   per party. A party of one is just a small instance. This is what makes "single-player campaign
   that can be done multiplayer" one code path instead of two.
4. **Separate the platform backend from the game server.** Accounts, characters, chat, friends,
   and matchmaking are Nakama's job (open source, Docker, Godot SDK). The Godot server only
   simulates gameplay. Rung 1 can stub Nakama with a local JSON save; rung 2 swaps it in.
5. **Data-driven content.** Items, enemies, quests, dialogue live in JSON/CSV resources, not in
   code. This is also what lets the AI team generate content at volume.

## Where the AI team will struggle

- **Netcode.** Server-authoritative prediction and reconciliation is the hardest code in the
  project. Expect local models to need escalation to a frontier model here, and the human to
  review the design before it is built. Track it as its own task with `roles: coder, human`.
- **Pixel-art consistency across a large character roster.** MMO-style games need many sprites.
  Character reference sheets and IP-Adapter are mandatory, and a modular sprite system
  (body + equipment layers) is worth building early so equipment does not multiply art work.
- **Animation.** Walk cycles and attack animations per direction. Plan a 4-direction, 4-6 frame
  standard and generate against a fixed character reference sheet. Consider open sprite bases
  (e.g. the LPC / Universal LPC sprite sheets, CC-BY-SA / GPL, check licence) as a fallback for
  the modular character system.

## First prototype (milestone 4 in `01-vision.md`, restated for this design)

- One hub map, one campaign map, two players over Tailscale on a dedicated headless server.
- One player class, one enemy type, one boss, one quest, one music loop, six SFX.
- Server-authoritative movement and melee combat. Character saved to JSON on the server.
- 16x16 tiles, 640x360 base resolution scaled 3x, 4-direction sprites.
