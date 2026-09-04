"""Level designer job: the model writes an ASCII map with the legend in game/data/tiles.json;
this validates it deterministically (size, known chars, markers, reachability) and saves
game/data/maps/<name>.json. The coder never lays out tiles; MapBuilder renders the JSON."""
from __future__ import annotations

import json
import re
from collections import deque
from pathlib import Path

from . import llm


def legend(repo: Path) -> dict:
    return json.loads((repo / "game" / "data" / "tiles.json").read_text())["legend"]


def validate(repo: Path, name: str, rows: list[str], width: int, height: int, required: list[str]) -> list[str]:
    lg = legend(repo)
    errs: list[str] = []
    if not re.fullmatch(r"[a-z0-9_]{2,40}", name or ""):
        errs.append("name must be lowercase letters, digits, underscores")
    if len(rows) != height:
        errs.append(f"expected {height} rows, got {len(rows)}")
    for i, r in enumerate(rows):
        if len(r) != width:
            errs.append(f"row {i} has {len(r)} chars, expected {width}")
        for ch in set(r):
            if ch not in lg:
                errs.append(f"row {i}: unknown legend char {ch!r}")
    if errs:
        return errs
    markers: dict[str, list[tuple[int, int]]] = {}
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            m = lg[ch].get("marker")
            if m:
                markers.setdefault(m, []).append((x, y))
    for m in required:
        if m not in markers:
            errs.append(f"missing marker {m}")
    if "PlayerSpawn" not in markers:
        return errs or ["missing PlayerSpawn"]
    # reachability from spawn over walkable cells (doors count as walkable)
    walk = lambda x, y: bool(lg[rows[y][x]].get("walk", False))
    seen = {markers["PlayerSpawn"][0]}
    dq = deque(seen)
    while dq:
        x, y = dq.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in seen and walk(nx, ny):
                seen.add((nx, ny)); dq.append((nx, ny))
    for m, cells in markers.items():
        for c in cells:
            if c not in seen:
                errs.append(f"marker {m} at {c} is not reachable from PlayerSpawn")
    walkable_total = sum(1 for y in range(height) for x in range(width) if walk(x, y))
    if walkable_total and len(seen) / walkable_total < 0.6:
        errs.append(f"only {len(seen)}/{walkable_total} walkable cells reachable from spawn; the map is split")
    edge_open = any(walk(x, 0) or walk(x, height - 1) for x in range(width)) or any(walk(0, y) or walk(width - 1, y) for y in range(height))
    if edge_open and not any(lg[ch].get("marker") == "Exit" for r in rows for ch in r):
        errs.append("map edge is walkable but there is no Exit marker; close the edge with walls or mark exits")
    return errs


def run_level_job(repo: Path, spec: dict, notes: str | None, escalate: bool = False) -> tuple[bool, str]:
    lg = legend(repo)
    legend_text = "\n".join(f"  {ch!r}: {e['tile']} ({e['layer']}, {'walkable' if e.get('walk') else 'solid'}{', marker ' + e['marker'] if e.get('marker') else ''})" for ch, e in lg.items())
    name = re.sub(r"[^a-z0-9_]", "_", str(spec.get("name", "map")).lower())
    width, height = int(spec.get("width", 30)), int(spec.get("height", 17))
    required = list(spec.get("markers_required", ["PlayerSpawn"]))
    system = llm.load_role(repo, "level-designer")
    user = (f"Design the map '{name}', exactly {width} columns by {height} rows.\n\nBrief:\n{spec.get('goal', '')}\n\n"
            f"Required markers: {', '.join(required)}\n\nLegend (use only these characters):\n{legend_text}\n\n"
            "World bible excerpt:\n" + (repo / "docs" / "14-world-bible.md").read_text()[:2500]
            + (f"\n\nYour previous attempt failed validation:\n{notes}" if notes else "")
            + "\n\nRespond with JSON only: {\"rows\": [\"...\", ...], \"notes\": \"one line on the layout\"}. "
            f"Every row must be exactly {width} characters; there must be exactly {height} rows.")
    model = llm.escalation_model() if escalate else None
    last_err = ""
    for attempt in range(3):
        data = llm.chat_json(system, user + (f"\n\nValidation errors to fix:\n{last_err}" if last_err else ""), model=model)
        rows = [str(r) for r in data.get("rows", [])] if isinstance(data, dict) else []
        errs = validate(repo, name, rows, width, height, required)
        if not errs:
            out = repo / "game" / "data" / "maps" / f"{name}.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps({"name": name, "width": width, "height": height, "rows": rows, "notes": str(data.get("notes", ""))[:300]}, indent=2) + "\n")
            return True, f"saved {out.relative_to(repo)}; {data.get('notes', '')}"[:300]
        last_err = "\n".join(errs[:12])
    return False, "level failed validation 3 times:\n" + last_err
