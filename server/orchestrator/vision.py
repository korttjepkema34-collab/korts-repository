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


def proof_run(repo: Path, scene: str, seconds: int = 4, actions: list[str] | None = None) -> tuple[bool, list[Path], str]:
    """Run the scene with simulated input and capture one screenshot per second."""
    b = os.environ.get("GODOT_BIN")
    if not b or not Path(b).exists():
        return False, [], "GODOT_BIN not set"
    out = repo / "reports" / "proofs" / f"{int(time.time())}-{Path(scene).stem}"
    out.mkdir(parents=True, exist_ok=True)
    seconds = max(2, min(int(seconds or 4), 12))
    cmd = [b, "--path", str(repo / "game"), "-s", "res://scripts/dev/proof.gd", "--", scene, str(out), str(seconds), ",".join(actions or [])]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=seconds + 90)
    except subprocess.TimeoutExpired:
        return False, [], "Godot hung during the proof run; killed"
    frames = sorted(out.glob("proof-*.png"))
    if p.returncode != 0 or not frames:
        return False, [], (p.stdout + p.stderr)[-3000:]
    return True, frames, str(out.relative_to(repo))


def proof_check(repo: Path, proof: dict) -> str:
    """Proof over claims: judge the running scene, not the compile. Returns 'PASS: ...' or 'FAIL: ...'."""
    ok, frames, msg = proof_run(repo, proof["scene"], proof.get("seconds", 4), proof.get("actions"))
    if not ok:
        return "FAIL: proof run did not produce frames: " + msg
    import base64 as _b64
    from PIL import Image
    import io
    content = [{"type": "text", "text": (
        "These are consecutive one-second screenshots of a Godot 2D scene while the player input "
        f"{', '.join(proof.get('actions') or ['nothing'])} was held. Expected behaviour: {proof.get('expect', '')}\n"
        "Answer JSON only: {\"scene_visible\": bool, \"something_moved_between_frames\": bool, "
        "\"expected_behaviour_seen\": bool, \"note\": \"one sentence\"}")}]
    for f in frames[:4]:
        im = Image.open(f).convert("RGB")
        im.thumbnail((640, 640), Image.NEAREST)
        buf = io.BytesIO(); im.save(buf, format="PNG")
        content.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + _b64.b64encode(buf.getvalue()).decode()}})
    try:
        import json as _json
        resp = llm.vision_route().chat.completions.create(
            model=llm.reviewer_model(), temperature=0.0, response_format={"type": "json_object"},
            messages=[{"role": "user", "content": content}])
        d = _json.loads(resp.choices[0].message.content or "{}")
    except Exception as e:
        return f"FAIL: vision model error during proof: {e} (frames at {msg})"
    good = bool(d.get("scene_visible")) and bool(d.get("expected_behaviour_seen"))
    return ("PASS" if good else "FAIL") + f": {d.get('note', '')} (frames at {msg}; moved={d.get('something_moved_between_frames')})"
