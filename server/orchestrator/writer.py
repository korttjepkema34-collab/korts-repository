"""Writer job: dialogue, quests, item flavour and names in the world-bible voice, as JSON data
files under game/data/. Validated by rules (shape, line length, voice) before saving.
Cheap: one CPU model call, no GPU."""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import llm

SCHEMAS = {
    "dialogue": {"target": "game/data/dialogue.json", "shape": "object: {npc_id: [{\"id\": str, \"text\": str, \"when\": str}]}", "max_line": 90},
    "quests": {"target": "game/data/quests.json", "shape": "array: [{\"id\": str, \"title\": str, \"giver\": str, \"steps\": [{\"id\": str, \"text\": str, \"objective\": str}]}]", "max_line": 120},
    "items": {"target": "game/data/item_flavour.json", "shape": "object: {item_id: str}  (one line of flavour text per item id from weapons.json / armor.json)", "max_line": 110},
    "names": {"target": "game/data/names.json", "shape": "object: {\"survivors\": [str], \"places\": [str], \"relics\": [str]}", "max_line": 40},
    "signs": {"target": "game/data/signs.json", "shape": "object: {sign_id: str}  (in-world signs and notes, 1-2 short lines)", "max_line": 60},
}
FORBIDDEN = ["!", "elf", "elves", "dwarf", "orc", "magic", "wizard", "spell", "mana", "neon"]


def _texts(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from _texts(x)
    elif isinstance(v, list):
        for x in v:
            yield from _texts(x)


def validate(content: str, data, max_line: int) -> list[str]:
    errs: list[str] = []
    if data is None or (isinstance(data, (dict, list)) and not data):
        return ["empty output"]
    lines = list(_texts(data))
    for s in lines:
        for line in s.splitlines():
            if len(line) > max_line:
                errs.append(f"line too long ({len(line)} > {max_line}): {line[:50]}...")
            low = line.lower()
            for f in FORBIDDEN:
                if f == "!" and "!" in line:
                    errs.append(f"exclamation mark: {line[:50]}")
                elif f != "!" and re.search(rf"\b{re.escape(f)}\b", low):
                    errs.append(f"forbidden word {f!r}: {line[:50]}")
    if content == "dialogue" and isinstance(data, dict):
        for npc, arr in data.items():
            if not isinstance(arr, list) or not all(isinstance(x, dict) and "text" in x for x in arr):
                errs.append(f"dialogue for {npc} must be a list of objects with text")
    if content == "quests" and not isinstance(data, list):
        errs.append("quests must be an array")
    return errs[:15]


def run_text_job(repo: Path, spec: dict, notes: str | None, escalate: bool = False) -> tuple[bool, str]:
    content = str(spec.get("content", "dialogue"))
    schema = SCHEMAS.get(content)
    if not schema:
        return False, f"unknown content type {content}; use one of {list(SCHEMAS)}"
    target = repo / str(spec.get("target", schema["target"]))
    existing = json.loads(target.read_text()) if target.exists() else None
    system = llm.load_role(repo, "writer")
    items_hint = ""
    if content == "items":
        ids = [w["id"] for w in json.loads((repo / "game" / "data" / "weapons.json").read_text())] + [a["id"] for a in json.loads((repo / "game" / "data" / "armor.json").read_text())]
        items_hint = "\nItem ids: " + ", ".join(ids)
    user = (f"Write {content}. Brief:\n{spec.get('brief', '')}\n\nShape: {schema['shape']}{items_hint}\n"
            f"Max {schema['max_line']} characters per line. Count: {spec.get('count', 'as the brief needs')}.\n\n"
            "World bible:\n" + (repo / "docs" / "14-world-bible.md").read_text()[:6000]
            + (f"\n\nExisting file (merge with it; keep ids stable):\n{json.dumps(existing)[:3000]}" if existing else "")
            + (f"\n\nPrevious attempt was rejected:\n{notes}" if notes else "")
            + "\n\nRespond with the JSON only.")
    model = llm.escalation_model() if escalate else None
    last = ""
    for attempt in range(3):
        data = llm.chat_json(system, user + (f"\n\nFix these problems:\n{last}" if last else ""), model=model)
        errs = validate(content, data, schema["max_line"])
        if not errs:
            if isinstance(existing, dict) and isinstance(data, dict):
                merged = dict(existing); merged.update(data); data = merged
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            n = len(list(_texts(data)))
            return True, f"saved {target.relative_to(repo)} ({n} lines of text)"
        last = "\n".join(errs)
    return False, "writer failed validation 3 times:\n" + last
