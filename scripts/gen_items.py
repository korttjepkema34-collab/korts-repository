#!/usr/bin/env python3
"""Generate game/data/{weapons,armor,classes,rarities}.json from the stat budget in
docs/17-gameplay-systems.md section 8. Edit the tables here, never the JSON.
Run from the repo root: python scripts/gen_items.py"""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "game" / "data"

RARITIES = [
    {"id": "scrap", "name": "Scrap", "mult": 0.85, "affixes": 0, "colour": 5},
    {"id": "worn", "name": "Worn", "mult": 1.0, "affixes": 1, "colour": 7},
    {"id": "sound", "name": "Sound", "mult": 1.15, "affixes": 1, "colour": 15},
    {"id": "fine", "name": "Fine", "mult": 1.3, "affixes": 2, "colour": 11},
    {"id": "saint", "name": "Saint", "mult": 1.5, "affixes": 3, "colour": 16},
]

# class: attacks per second, reach (tiles), stamina cost per attack, noise (0-10), animation set
CLASSES = {
    "dagger":     {"aps": 2.4, "reach": 0.8, "stamina": 6,  "noise": 1, "verb": "fast, backstab bonus",              "affixes": ["bleed", "quick", "silent", "lifesteal"]},
    "sword":      {"aps": 1.5, "reach": 1.2, "stamina": 10, "noise": 3, "verb": "balanced",                           "affixes": ["bleed", "stagger", "quick", "cheap"]},
    "greatblade": {"aps": 0.8, "reach": 1.8, "stamina": 18, "noise": 4, "verb": "slow, wide arc",                     "affixes": ["stagger", "cleave", "lifesteal", "cheap"]},
    "hammer":     {"aps": 0.7, "reach": 1.3, "stamina": 20, "noise": 6, "verb": "slow, breaks doors and shields",     "affixes": ["stagger", "breaker", "cheap", "quake"]},
    "spear":      {"aps": 1.2, "reach": 2.2, "stamina": 11, "noise": 2, "verb": "reach, thrusts through a barred door", "affixes": ["pierce", "quick", "cheap", "bleed"]},
    "whip":       {"aps": 1.3, "reach": 2.5, "stamina": 9,  "noise": 3, "verb": "crowd control, pulls",              "affixes": ["pull", "stagger", "quick", "shock"]},
    "bow":        {"aps": 1.0, "reach": 8.0, "stamina": 8,  "noise": 1, "verb": "silent ranged, ammo",               "affixes": ["pierce", "silent", "quick", "light"]},
    "throwable":  {"aps": 0.6, "reach": 6.0, "stamina": 8,  "noise": 8, "verb": "area, noise",                       "affixes": ["burn", "shrapnel", "cheap", "quake"]},
    "gun":        {"aps": 0.9, "reach": 10.0, "stamina": 4, "noise": 10, "verb": "huge damage, every shot calls the horde", "affixes": ["pierce", "stagger", "breaker", "burn"]},
}

# name, class, tier (1-5 by where found), material tags, notes
WEAPONS = [
    ("Shiv", "dagger", 1, ["scrap"], "A sharpened spoon. Everyone starts with something like it."),
    ("Kitchen Knife", "dagger", 2, ["steel"], "Still says DISHWASHER SAFE on the handle."),
    ("Surgeon's Knife", "dagger", 4, ["relic"], "Medical relic. Cuts what it is pointed at."),
    ("Machete", "sword", 1, ["steel"], "Trade goods from before. Cheap, honest."),
    ("Guard's Sword", "sword", 2, ["steel"], "Issued to a lord's guard. Taken off one."),
    ("Rebar Blade", "sword", 3, ["rebar"], "Ground on a wheel for a month. Heavy for its length."),
    ("Ceremonial Sword", "sword", 4, ["steel", "gold"], "From a guild hall wall. Sharper than it should be."),
    ("Scythe", "greatblade", 2, ["steel"], "The Reaper's tool. A harvest blade on a long haft."),
    ("Signpost Blade", "greatblade", 3, ["steel"], "A street sign, folded and edged."),
    ("Turbine Blade", "greatblade", 5, ["relic"], "One fin of a wind turbine. Nobody knows how it was cut."),
    ("Sledge", "hammer", 1, ["steel", "wood"], "Breaks doors. Breaks Thralls."),
    ("Manhole Maul", "hammer", 3, ["iron"], "A manhole cover on a pipe."),
    ("Piston Hammer", "hammer", 5, ["relic"], "Fires on impact. Needs power."),
    ("Rebar Spear", "spear", 1, ["rebar"], "Reach is armour."),
    ("Antenna Pike", "spear", 3, ["relic"], "A broadcast mast section. Hums near the Wired."),
    ("Cable Whip", "whip", 2, ["cable"], "Braided power cable. Pulls what it catches."),
    ("Chain Flail", "whip", 3, ["chain"], "A padlock on a chain, mostly."),
    ("Fibreglass Bow", "bow", 2, ["fibreglass"], "Sporting goods, salvaged. Quiet."),
    ("Compound Bow", "bow", 3, ["fibreglass", "steel"], "Pulleys still work. Hits hard."),
    ("Crossbow", "bow", 4, ["steel", "wood"], "Slow to wind. Ends arguments."),
    ("Brick", "throwable", 1, ["brick"], "The first ranged weapon. Loud on cobbles."),
    ("Molotov", "throwable", 2, ["glass", "oil"], "Fire. The Wired do not stop for it, but they burn."),
    ("Shrapnel Jar", "throwable", 3, ["glass", "scrap"], "A jar of nails around a firecracker."),
    ("Pipe Pistol", "gun", 3, ["relic", "pipe"], "One shot, then everything knows where you are."),
    ("Scavenged Rifle", "gun", 5, ["relic"], "A real one. The Keep's most expensive sound."),
]

ARMOR_WEIGHTS = {
    "light":  {"armour": 10, "stamina_regen": 0.20, "dodge_cost": -0.20},
    "medium": {"armour": 20, "stamina_regen": 0.0,  "dodge_cost": 0.0},
    "heavy":  {"armour": 35, "stamina_regen": -0.20, "dodge_cost": 0.30},
}
# name, weight, tier, bonus2, bonus3, side effect
ARMOR_SETS = [
    ("Scavenger's Rags", "light", 1, "carry +10", "stamina regen +10%", "Nobody looks twice: merchants charge you less."),
    ("Reeve's Coat", "light", 2, "carry +30", "trade prices +15%", "Little armour to speak of. Relics stored on you are safe on death."),
    ("Wired-hide", "light", 3, "stealth +20%", "Thralls ignore you 2 s after each kill", "Wearing their skin. NPCs trust you slower."),
    ("Hunter's Leathers", "light", 2, "bow damage +10%", "see 3 tiles further at night", "Silent footsteps on grass."),
    ("Lamplighter", "medium", 2, "your lamps reach +30%", "lamp flicker no longer blinds you", "The horde's interest in you scales with your light."),
    ("Toll-Road Mail", "medium", 3, "armour +5", "block +15%", "Loud on cobbles: noise +1."),
    ("Physician's Wraps", "medium", 3, "heal +20%", "revive 2x faster", "Grabs release you 0.5 s sooner."),
    ("Tinker's Harness", "medium", 3, "repair +30%", "turrets reload faster", "Carries a toolkit: sealed doors open without a hammer."),
    ("Linker's Shroud", "medium", 4, "pack size +1", "linked Thralls +20% health", "The Wired treat you as one of them for 1 s after linking."),
    ("Guard's Plate", "heavy", 3, "armour +10", "stagger resistance", "A lord's colours: Keep guards are polite, lords' guards are not."),
    ("Reactor Suit", "heavy", 4, "Wright overheat -25%", "EMP radius +30%", "Glows faintly: light radius 2 tiles, always."),
    ("Castellan Plate", "heavy", 5, "armour +15", "the siren works for you: pulls Thralls to you", "Boss set. Slow. The Keep goes quiet when you walk in."),
]

PLAYER_CLASSES = [
    ("Reaper", "warrior", "Scythe sweep: a full-circle strike, stamina-heavy", "Scythe", "medium", ["harvest", "endurance", "wrath"]),
    ("Warden", "tank", "Siren shield: holds a doorway alone, staggers what touches it", "Guard's Sword", "heavy", ["bulwark", "vigil", "retort"]),
    ("Gunner", "gunslinger", "Relic firearms: huge damage, every shot draws the horde", "Pipe Pistol", "light", ["deadeye", "ammunition", "escape"]),
    ("Hunter", "ranger", "Silent bow, traps, sees further at night", "Fibreglass Bow", "light", ["stalk", "snare", "provision"]),
    ("Shade", "rogue", "Daggers and stealth: the Wired lose you after a kill", "Shiv", "light", ["knife", "shadow", "theft"]),
    ("Wright", "wizard", "Reactor pack: bursts and EMP, overheats", "Rebar Blade", "medium", ["surge", "pulse", "coolant"]),
    ("Linker", "necromancer", "Re-links Thralls into a pack that follows you", "Cable Whip", "medium", ["binding", "pack", "signal"]),
    ("Cantor", "bard", "Relic speaker: buffs allies, disorients the Wired, who listen", "Machete", "light", ["hymn", "dirge", "chorus"]),
    ("Physician", "cleric", "Medical relics: heal, revive, cure grabs", "Surgeon's Knife", "medium", ["triage", "stimulant", "quarantine"]),
    ("Tinker", "engineer", "Turrets, repairs, robot workers obey faster", "Sledge", "medium", ["fabricate", "fortify", "automate"]),
]


def slug(s: str) -> str:
    return s.lower().replace("'", "").replace(" ", "_")


def weapons() -> list[dict]:
    out = []
    for name, cls, tier, mats, notes in WEAPONS:
        p = CLASSES[cls]
        budget = 40 * tier
        base = {"id": slug(name), "name": name, "class": cls, "tier": tier, "materials": mats, "notes": notes,
                "aps": p["aps"], "reach": p["reach"], "stamina": p["stamina"], "noise": p["noise"],
                "affix_pool": p["affixes"], "damage_by_rarity": {}, "upgrade": {"max": 10, "damage_per_level": 0.06, "scrap_cost": "20*level^2"},
                "reliquary": {"stat_mult": 1.25, "cost": {"relic": 1, "saint_materials": 3, "scrap": 2000}, "permanent": True}}
        for r in RARITIES:
            base["damage_by_rarity"][r["id"]] = round(budget * r["mult"] / p["aps"], 1)
        out.append(base)
    return out


def armor() -> list[dict]:
    out = []
    for name, weight, tier, b2, b3, side in ARMOR_SETS:
        w = ARMOR_WEIGHTS[weight]
        out.append({"id": slug(name), "name": name, "weight": weight, "tier": tier, "pieces": ["head", "body", "legs"],
                    "armour_per_piece": round(w["armour"] / 3, 1), "stamina_regen": w["stamina_regen"], "dodge_cost": w["dodge_cost"],
                    "bonus_2": b2, "bonus_3": b3, "side_effect": side, "silhouette": f"{weight}_{(tier % 3) + 1}"})
    return out


def classes() -> list[dict]:
    return [{"id": slug(n), "name": n, "fantasy": f, "signature": sig, "starting_weapon": slug(w), "starting_armor_weight": aw,
             "talent_branches": br, "proficiency_bonus": 0.10, "species": "human"} for n, f, sig, w, aw, br in PLAYER_CLASSES]


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for fn, data in [("rarities.json", RARITIES), ("weapons.json", weapons()), ("armor.json", armor()), ("classes.json", classes())]:
        (OUT / fn).write_text(json.dumps(data, indent=2) + "\n")
        print("wrote", fn, len(data))
