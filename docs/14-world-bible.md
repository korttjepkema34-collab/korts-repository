# 14 - World bible: Reaper's Relics

The creative constraints for everything the studio makes. Every role reads this. The
orchestrator does not invent settings, factions, or names outside it; it fills it in. Approved
by the owner on 2026-09-02 (docs/pitch/reapers-relics-pitch.html is the approved proposal).

## The pitch

**Reaper's Relics.** The near future, forty years after the grid died. Nobody fixed it. What grew
back was feudal: whoever holds a working reactor is a lord, whoever holds a printer is a priest,
and everyone else farms, fights or scavenges. The old tech is not understood any more. It is
venerated. A drone battery is a relic. A server rack is a shrine.

By day you scavenge and build. By night the Wired come in their hundreds. Somewhere out there a
knight in dead armour is holding the one relic that would keep the lights on.

**Tone: bleak but not hopeless.** The Keep is home. People joke. The wall holds more nights than
it falls. Elden Ring's weight with Stardew's warmth underneath. Not grimdark, never cosy.

## The world in five facts

1. **The Wired** are the grid's last users. When it fell, the implant network kept running on
   people instead of servers. They are still linked, still walking, still looking for signal.
   They are drawn to light and power. Nobody knows if anyone is still in there.
2. **Reapers** are the outcasts who go into the dead fields to harvest relics from the Wired and
   the ruins. Lords pay in food and shelter for what a Reaper brings back, but do not let Reapers
   inside their walls. So Reapers built their own, and called it the Keep.
3. **Relics** are working old tech. They power lamps and walls, they slot into a Reaper's harness
   for an active ability, and they are the currency the Keep runs on. Unbanked relics drop where
   you die.
4. **Hearths** are working power nodes. Resting at one banks your relics and restores you. They
   are the only safe light at night.
5. **Nights belong to the Wired.** They move on any light. The wall you built by day, and the
   door you did or did not fix, decide whether you survive. Caught outside, you bar a door
   (a **Holdout**) or burn a relic in a dead power node (a **wild Hearth**). Every seventh night
   is **the Long Night**.
6. **Holdfasts.** Beyond the Keep, a party can claim a ruin and make it theirs: walls, turrets,
   a Reliquary, rescued survivors and repaired robots working the place. The Wired notice.

## Places

| Place | Role | Look |
|---|---|---|
| **The Keep** | Shared hub. Every player's Hold sits inside its wall. | A settlement in a dead power substation. Car doors and highway barriers for walls, a brick gatehouse with a portcullis and guild banners. The transformer tower is the tower. A cooling pond, cables strung between lamp posts, a guild house with a sign, a market stall, garden plots, scrap piles from last night's repairs. Houses you can walk into. |
| **The Fallows** | First open zone. Day scavenging; night waves spill from here. | Suburbs gone to meadow. Roofs under ivy, a rusted overpass, one cul-de-sac of intact houses the Wired still walk through in circles. Every house can be entered. |
| **The Undercroft** | First dungeon and boss. | A bank basement lit by a single working reactor. Marble, deposit boxes, gold-leafed cables. Someone made it a chapel. |

Later regions (do not build yet): the Millrace, the Glass Market, the Deep Stair.

## Classes (everyone is human)

A class is a starting kit, a signature relic, and a talent tree. Reaper, Warden, Gunner, Hunter,
Shade, Wright, Linker, Cantor, Physician, Tinker. Nothing is magic: the Wright channels a reactor
pack, the Linker re-links Thralls to their own signal, the Cantor broadcasts through a relic
speaker. Full table in `docs/15-gameplay-systems.md` §6.

## People

| Name | Role | Voice |
|---|---|---|
| **The Reaper** | Player. Scythe (slow, wide), hook (fast, short), one relic slot for an active ability. | Silent. |
| **Hesper the Reeve** | Keeps the Keep's ledger, gives contracts and the first quest | Tired, exact, secretly kind. Short sentences. Never says please. |
| **Old Cutter** | Retired Reaper by the garden fence, tutorial hints. Named for the hook they never put down. | Rambling, cheerful, wrong about half of it. |
| **Rescued survivors** | Farmer, Smith, Guard, Scout. Join a Holdfast if fed and trusted; leave if it falls twice. | Each has one line of history and never repeats it. |
| **Repaired robots** | Mule, Maintenance drone, Sentry. Relics with jobs. | Beep in a way that sounds like an old modem. |
| **The Castellan** | First boss. A lord's champion in augmented plate, sent to take the Undercroft reactor, never came back. Now they keep it. | Does not speak. The shield's siren sounds before each pattern. |

## Enemies (prototype set)

| Enemy | Behaviour | Threat |
|---|---|---|
| **Thrall** | Horde unit. Walks toward the nearest light. Grabs on contact. | Low alone, lethal in fifty. |
| **Courser** | Sprints at the player when the horde is engaged, flanks. | Medium. Forces movement. |
| **Herald** | A drone. Hovers, marks a player with a searchlight, calls the horde to them. | Medium. Kill it first. |
| **The Castellan** (boss) | Three patterns after a siren: shield sweep, charge, a call that pulls six Thralls into the arena. | Boss. The siren is the whole fight. |

## Player: the Reaper

- Scythe: slow, wide arc, stamina-heavy. Hook: fast, short, pulls small enemies.
- Relic slot: one active ability from the equipped relic (a battery burst, a siren jammer).
- Stats on screen: vigour, stamina, relic charge. Nothing else in the prototype.
- Dodge roll costs stamina. Death drops unbanked relics where you fell; return to reclaim.
- Progression in the prototype: gear found and relics equipped. Levels come at rung 2.

## The first quest: "Keep the Lights On"

1. Hesper: the Keep's lamps are failing. There is a reactor in the Undercroft. Someone is
   standing on it. Go.
2. The Fallows: learn to move, dodge, scythe, hook. Fight Thralls and a Courser. Meet Old Cutter.
3. The Undercroft: Thralls in the nave, a Herald above. The Castellan at the reactor.
4. Bring the reactor home and wire it to the wall. The night after it goes in, the Wired come
   anyway, and they come toward the light. End of prototype.

Solo or with a party: same maps, same quest, enemy count and health scale by party size.

## Naming and text rules

The rule: **medieval words that happen to describe the tech.**

- Places are what they were for: the Keep, the Fallows, the Undercroft, Substation Row.
- Enemies are what the network made of people: Thrall, Courser, Herald, Castellan.
- Roles are old offices: Reeve, Reaper.
- Relics are old tech named as if holy: the Reactor, a Saint (a battery), the Rack. Rarity
  tiers: Scrap, Worn, Sound, Fine, Saint.
- Weapons are what they were before, named plainly: Rebar Blade, Manhole Maul, Cable Whip,
  Pipe Pistol. Armor sets are named for who wore them: Reeve's Coat, Guard's Plate, Wired-hide.
- Stations: Workbench (upgrade), Forge (craft), **Reliquary** (socket a relic, permanent).
- People get one short name and maybe a nickname: Hesper, Old Cutter.
- Dialogue: short, no exclamation marks, nobody explains the lore, they mention it sideways.
- UI text: lowercase labels, terse ("vigour", "hook", "leave").

## Things this world is not

- No elves, dwarves, orcs, magic, or a chosen one.
- No purple glow, no neon streets. Tech glows only when it works, and almost nothing works.
- No skeletons. The Wired are people.
- No shops in the prototype. Relics are tallied by the Reeve, not sold.
