"""Give text models eyes: render a scene to PNG with Godot, describe it with the vision model."""
from __future__ import annotations

import base64
import os
import subprocess
import time
from pathlib import Path

from . import llm


def screenshot(game: Path, scene: str, out: Path, frames: int = 10, timeout_s: int = 120) -> tuple[bool, str]:
    b = os.environ.get("GODOT_BIN")
    if not b or not Path(b).exists():
        return False, "GODOT_BIN not set"
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [b, "--path", str(game), "-s", "res://scripts/dev/screenshot.gd", "--", scene, str(out), str(frames)]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return False, "Godot hung while rendering; killed after timeout (GUI dialog? missing display?)"
    if p.returncode != 0 or not out.exists():
        return False, (p.stdout + p.stderr)[-3000:]
    return True, str(out)


def describe(image: Path, question: str) -> str:
    data = base64.b64encode(image.read_bytes()).decode()
    model = llm.reviewer_model()
    resp = llm.client(llm.slot_for(model)).chat.completions.create(
        model=model, temperature=0.1,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": question},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{data}"}}]}])
    return resp.choices[0].message.content or ""


def visual_check(repo: Path, scene: str, expectation: str) -> str:
    """Screenshot a scene and ask the vision model whether it matches the expectation."""
    out = repo / "reports" / "screenshots" / f"{int(time.time())}-{Path(scene).stem}.png"
    ok, msg = screenshot(repo / "game", scene, out)
    if not ok:
        return "SCREENSHOT FAILED: " + msg
    style = (repo / "style" / "style-bible.md").read_text()[:3000]
    q = ("You are looking at a screenshot of a Godot 2D scene under development.\n"
         f"Expected: {expectation}\n\nStyle bible excerpt:\n{style}\n\n"
         "Describe what is actually visible in 3-5 sentences, then list concrete problems "
         "(empty screen, wrong scale, missing sprite, wrong colours, overlapping UI). Be specific.")
    try:
        return f"screenshot: {out.relative_to(repo)}\n" + describe(out, q)
    except Exception as e:
        return f"screenshot saved at {out.relative_to(repo)} but the vision model failed: {e}"
