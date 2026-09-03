# 15 - Gameplay systems

Approved 2026-09-03. Extends `docs/10-game-design.md`. Everything here is post-prototype unless
marked **P** (needed in the prototype) or **S** (schema needed now so prototype content is built
the right way). The prototype scope in `10-game-design.md` does not grow.

## 1. The loop: day out, night home

**Design law: survival is a decision, never a dice roll.** Every death must trace to a choice.

- **Distance is danger.** Night density and speed of the Wired scale with distance from the
  nearest powered light. Near the Keep: waves. Deep in the Fallows: a tide.
- **The dusk bell** rings two minutes before night. The map shows the way home. **P**
- **Holdouts.** Any abandoned building with an intact door can be barred for the night. The
  horde tests the door all night; door health from `data/build.json`. Sit in the dark, listen,
  repair from inside. Uses the same-map interiors (decision 7).
- **Wild Hearths.** Dead power nodes in the world. Light one with a relic: a safe circle for one
  night, and the relic burns. Trade a relic for your life.
- **The base is safe because you built it.** Target survival for a maintained Keep or Holdfast:
  7-10 nights in 10. An unattended one falls. A breach costs walls, stored scrap and workers,
  not necessarily lives.
- **Outside at night** is meant to kill unprepared players most of the time. Prepared players
  (Holdout, wild Hearth, Shade stealth, a Cantor's hymn) survive on purpose.
- **The Long Night**, every seventh night: doubled waves and a mini-boss (a Castellan-class
  champion). The week has a rhythm and a reason to prepare.
- **Wave pressure scales with the base**, not only the calendar: light radius, noise made in the
  last day, relics stored. Dark, quiet, poor bases get quiet nights.

## 2. Scavenging

- Abandoned houses, streets and later whole cities. The Fallows first (**P**), the Glass Market
  and the Deep Stair later.
- **Ruins are assembled from hand-authored room prefabs** (the art pipeline is good at making
  many of these): shells, interiors, cellars, rooftops, with door and loot sockets.
- Loot tiers by distance from the Keep. Sealed buildings need tools (hammer, Tinker's kit).
- **Dark interiors hold Wired by day.** A building is never free.
- Scavenge yields: scrap (build/upgrade currency), materials by tier, relic fragments, relics,
  food, survivors to rescue.

## 3. Building

Two kinds of home:

| | The Keep plot **P** | The Holdfast |
|---|---|---|
| What | 12x8 tiles inside the Keep's wall, one per player | An abandoned site out in the world a party claims and fortifies |
| Shared? | Keep is shared by everyone online; plot is yours | One per party, instanced at rung 2 |
| Nights | The Keep's wall and lamps defend everyone | Your walls, your workers, your wave |
| Purpose | Trade, quests, a bed, a workbench | The Palworld base: workers, turrets, farms, the Reliquary |

Building rules (both):

- **Tile grid.** Pieces snap to the 32 px grid. No free placement.
- **Pieces** (`data/build.json`): wall, door, window, floor, roof, stairs, lamp, turret,
  workbench, forge, Reliquary, bed, farm plot, cable, generator socket. Each has cost, health,
  and what it blocks (movement, sight, pathing).
- **Structure.** Roofs need wall support on two sides. Doors need a wall either side.
- **Power.** Lamps, turrets, the Reliquary and robot workers need power. Power runs by cable from
  a generator socket holding a relic reactor. The reactor is the heart of every base and the
  thing the Wired are drawn to.
- **Light is a double edge.** Lamps let you see and let turrets aim; the horde walks toward
  light. Bigger, brighter base, bigger wave.
- **Damage and repair.** Walls and doors take horde damage. Repair costs scrap. A broken door lets
  Thralls inside. Workers can be assigned to repair.
- **Persistence.** Tile diff per plot/Holdfast on the server. Holdfasts persist across sessions
  and are visible to the party.

## 4. Weapons **S**

Nine classes with distinct verbs; twenty-five base weapons inside them. Every class needs its own
attack animations (4 directions); weapons within a class are stat and palette variants.

| Class | Verb | Base weapons |
|---|---|---|
| Dagger | fast, backstab bonus | Shiv, Kitchen Knife, Surgeon's Knife |
| Sword | balanced | Machete, Guard's Sword, Rebar Blade, Ceremonial Sword |
| Greatblade | slow, wide arc | Scythe, Signpost Blade, Turbine Blade |
| Hammer | slow, breaks doors and shields | Sledge, Manhole Maul, Piston Hammer |
| Spear | reach, thrusts through a barred door | Rebar Spear, Antenna Pike |
| Whip | crowd control, pulls | Cable Whip, Chain Flail |
| Bow | silent ranged, ammo | Fibreglass Bow, Compound Bow, Crossbow |
| Throwables | area, noise | Brick, Molotov, Shrapnel Jar |
| Guns | huge damage, every shot calls the horde | Pipe Pistol, Scavenged Rifle |

- **Noise** is a stat. Guns and throwables are loud; bows and daggers are silent. Noise pulls the
  flow field. Guns are relics: rare, gated by relic drops, loud.
- **Rarity** (`data/rarities.json`): Scrap, Worn, Sound, Fine, Saint. Sets the stat multiplier and
  how many bonus affixes roll.
- **Upgrades.** Workbench, scrap, +1 to +10: damage +6% per level, cost 20 x level^2 scrap.
- **The Reliquary.** A base station. Socket a relic into a weapon: +25% to all stats and the
  relic's ability (a burst, a stun, an element). Costs the relic, three Saint-grade materials and
  2000 scrap. **Deterministic and permanent.** No failure roll, no unsocketing. Expensive and
  irreversible is the drama.
- The scythe stays the Reaper class's signature; anyone can use one.

## 5. Armor **S**

- Slots: head, body, legs. Weight class decides stamina regen and dodge cost:

| Weight | Armour | Stamina regen | Dodge cost |
|---|---|---|---|
| Light | 10 | +20% | -20% |
| Medium | 20 | 0 | 0 |
| Heavy | 35 | -20% | +30% |

- **Sets** give a bonus at two pieces and a second at three. Every set has a side effect that
  changes play, not only numbers. Twelve at launch (`data/armor.json`); the AI team generates
  them from three silhouettes per weight class with recolours and trim.
- Examples: Lamplighter (lamps reach further, so does the horde's interest); Wired-hide (Thralls
  ignore you 2 s after a kill); Reeve's Coat (carry more, trade better, little armour);
  Castellan Plate (boss set, heavy, the siren works for you).

## 6. Classes **S**

**Everyone is human.** A class is a starting kit, a signature ability, and a talent tree with
three branches. **All weapons and armor are usable by every class**; proficiency bonuses nudge
you toward your class's tools. Elden Ring's model: identity plus freedom.

| Class | Fantasy | Signature | Kit |
|---|---|---|---|
| Reaper | warrior | Scythe sweep, stamina-heavy | Scythe, medium |
| Warden | tank | Siren shield: holds a doorway alone | Guard's Sword, heavy |
| Gunner | gunslinger | Relic firearms; every shot draws the horde | Pipe Pistol, light |
| Hunter | ranger | Silent bow, traps, sees further at night | Fibreglass Bow, light |
| Shade | rogue | Daggers, stealth; the Wired lose you after a kill | Shiv, light |
| Wright | wizard | Reactor pack: bursts, EMP, overheats | Rebar Blade, medium |
| Linker | necromancer | Re-links Thralls into a pack that follows you | Cable Whip, medium |
| Cantor | bard | Relic speaker: buffs allies, disorients the Wired, who listen | Machete, light |
| Physician | cleric | Medical relics: heal, revive, cure grabs | Surgeon's Knife, medium |
| Tinker | engineer | Turrets, repairs, robot workers obey faster | Sledge, medium |

Nothing is magic. Every signature is a relic. The Linker is the setting's best class: the enemy
faction becomes your power source.

Cosmetics from the modular sprite layers: hair, scars, cloak colour, three skin tones inside the
palette (colours 6, 5, 9 with 1 for outline).

## 7. Workers and companions

- **Robot workers are relics you repair**: Mule (carry, fetch your dropped relics), Maintenance
  drone (repair walls and doors), Sentry (defend a spot, needs power and ammo).
- **Human companions are survivors you rescue** in ruins. Traits: Farmer, Smith, Guard, Scout.
  A trust meter rises with food and quests; they leave if the base falls twice.
- **Jobs are stations.** Assign a worker to a workbench, forge, farm plot, wall segment, or the
  gate. The job board UI lives at the Holdfast.
- **Stakes.** Workers can be lost in a breach.
- **Scope.** Three workers and a job board first. Full Palworld-style automation is rung 2.

## 8. Stat budget (how items are generated) **S**

Items come from rules, not hand-tuned numbers, because an unattended AI team cannot balance
25 weapons x 10 classes x 12 sets by hand. `scripts/gen_items.py` is the source of truth; it
writes `game/data/weapons.json`, `armor.json`, `classes.json`, `rarities.json`.

- Weapon DPS budget: `P = 40 * tier` (tier 1-5 by where the base weapon is found).
- Class profile fixes attacks per second, reach, stamina cost, noise. `damage = P / aps`.
- Rarity multiplier on damage and affix count: Scrap 0.85/0, Worn 1.0/1, Sound 1.15/1,
  Fine 1.3/2, Saint 1.5/3.
- Affix pool per class (bleed, stagger, lifesteal, silent, light, quick, cheap stamina, ...).
- Armour budget by weight class as in section 5, plus set bonuses as named effects.
- Balance changes edit the generator and regenerate. Never hand-edit the JSON.
