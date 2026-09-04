"""Nightly playtest: a dedicated server, one screenshotting bot client (needs a display) and one
headless co-op bot, all following game/data/playtest/plan.json. Telemetry and screenshots go to
reports/playtests/<date>/; the vision model writes the verdict; errors become bug tasks."""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path

from . import llm

ERROR_RE = re.compile(r"(SCRIPT ERROR|ERROR:|Parse Error).*")


def run(repo: Path, ev) -> str | None:
    b = os.environ.get("GODOT_BIN")
    if not b or not Path(b).exists():
        return None
    game = repo / "game"
    plan = repo / "game" / "data" / "playtest" / "plan.json"
    if not plan.exists():
        return None
    day = time.strftime("%Y-%m-%d")
    out = repo / "reports" / "playtests" / day
    out.mkdir(parents=True, exist_ok=True)
    seconds = sum(float(s.get("seconds", 1)) for s in json.loads(plan.read_text()).get("steps", [])) + 8
    server = subprocess.Popen([b, "--headless", "--path", str(game), "--", "--server", "--telemetry", str(out / "server.jsonl")],
                              stdout=open(out / "server.log", "w"), stderr=subprocess.STDOUT, text=True)
    time.sleep(4)
    clients = []
    for i, headless in enumerate((False, True)):
        args = [b] + (["--headless"] if headless else []) + ["--path", str(game), "-s", "res://scripts/dev/bot.gd", "--",
                str(plan), str(out / f"bot{i}"), "--connect", "127.0.0.1", "--telemetry", str(out / f"bot{i}.jsonl")]
        clients.append(subprocess.Popen(args, stdout=open(out / f"bot{i}.log", "w"), stderr=subprocess.STDOUT, text=True))
        time.sleep(2)
    deadline = time.time() + seconds + 60
    for c in clients:
        try:
            c.wait(timeout=max(5, deadline - time.time()))
        except subprocess.TimeoutExpired:
            c.kill()
    server.terminate()
    try:
        server.wait(timeout=15)
    except subprocess.TimeoutExpired:
        server.kill()
    # gather
    errors: list[str] = []
    for lf in ("server.log", "bot0.log", "bot1.log"):
        for line in (out / lf).read_text(errors="ignore").splitlines():
            if ERROR_RE.search(line):
                errors.append(f"{lf}: {line.strip()[:200]}")
    events: dict[str, int] = {}
    for jf in out.glob("*.jsonl"):
        for line in jf.read_text(errors="ignore").splitlines():
            try:
                events[json.loads(line).get("event", "?")] = events.get(json.loads(line).get("event", "?"), 0) + 1
            except Exception:
                pass
    shots = sorted((out / "bot0").glob("bot-*.png")) if (out / "bot0").exists() else []
    verdict = _judge(repo, shots) if shots else {"note": "no screenshots (no display for the bot client?)"}
    peers = events.get("peer_joined", 0)
    report = f"""# Playtest {day}

| | |
|---|---|
| Server errors + bot errors | {len(errors)} |
| Peers that joined the server | {peers} (expected 2) |
| Telemetry events | {events} |
| Screenshots | {len(shots)} |
| Vision verdict | {json.dumps(verdict)} |

## Errors
{chr(10).join('- ' + e for e in errors[:40]) or '- none'}

## What the playtester saw
{verdict.get('note', '')}
"""
    (out / "report.md").write_text(report)
    (repo / "reports" / f"playtest-{day}.md").write_text(report)
    ev(f"playtest: {len(errors)} errors, {peers} peers, {len(shots)} shots, verdict {verdict.get('playable', '?')}")
    _file_bugs(repo, errors, ev)
    return str(out.relative_to(repo))


def _judge(repo: Path, shots: list[Path]) -> dict:
    import base64, io
    from PIL import Image
    content = [{"type": "text", "text": (
        "You are the playtester for a 2D pixel-art RPG. These screenshots are from a bot walking, attacking and "
        "dodging for a few seconds in the hub map. Judge what is actually visible. Answer JSON only: "
        "{\"playable\": bool, \"saw_player\": bool, \"saw_map\": bool, \"saw_hud\": bool, \"saw_enemies\": bool, "
        "\"something_changed_between_frames\": bool, \"problems\": [str], \"note\": \"two sentences\"}")}]
    for s in shots[:6]:
        im = Image.open(s).convert("RGB"); im.thumbnail((640, 640), Image.NEAREST)
        buf = io.BytesIO(); im.save(buf, format="PNG")
        content.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}})
    try:
        resp = llm.vision_route().chat.completions.create(
            model=llm.reviewer_model(), temperature=0.0, response_format={"type": "json_object"},
            messages=[{"role": "system", "content": llm.load_role(repo, "playtester")}, {"role": "user", "content": content}])
        return json.loads(resp.choices[0].message.content or "{}")
    except Exception as e:
        return {"note": f"vision model error: {e}"}


def _file_bugs(repo: Path, errors: list[str], ev) -> None:
    """One bug task per error class, deduplicated by a signature file."""
    if not errors:
        return
    seen_path = repo / "reports" / "playtests" / ".filed.json"
    seen = json.loads(seen_path.read_text()) if seen_path.exists() else {}
    from .planner import next_task_id
    for e in errors:
        sig = re.sub(r"\d+|res://\S+", "", e.split(":", 1)[-1]).strip()[:100]
        if sig in seen:
            continue
        tid = next_task_id(repo)
        (repo / "tasks" / "backlog" / f"{tid}-bug-playtest.md").write_text(
            f"# {tid} Bug from playtest: {sig[:60]}\npriority: 1\nroles: coder, reviewer\n\n## Goal\nFix this runtime error seen in the nightly playtest.\n\n"
            f"## Acceptance\n- The error below no longer appears in a playtest run (`reports/playtests/`).\n- A gdUnit4 test covers the fix where practical.\n\n## Notes\n```\n{e}\n```\n")
        seen[sig] = time.strftime("%Y-%m-%d")
        ev(f"filed bug task {tid}: {sig[:60]}")
    seen_path.write_text(json.dumps(seen, indent=2))
