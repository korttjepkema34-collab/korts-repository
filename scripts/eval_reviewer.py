#!/usr/bin/env python3
"""Measure the reviewer instead of feeling it.

eval/reviewer/manifest.json lists cases: {"file", "expect": "approved|rejected", "why", "spec"}.
This runs the same path the orchestrator runs (deterministic checks, then the vision model unless
--checks-only) and reports accuracy, precision/recall on "rejected", and every miss with reasons.

  python scripts/eval_reviewer.py                 # full (needs Ollama + REVIEWER_MODEL)
  python scripts/eval_reviewer.py --checks-only   # no model needed
  python scripts/eval_reviewer.py --make-seeds    # regenerate the synthetic seed cases

Replace the synthetic seeds with real approved/rejected assets as the pipeline produces them:
copy the file into eval/reviewer/cases/ and add a manifest entry with the human's reason.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "server"), str(ROOT / "worker")]
EVAL = ROOT / "eval" / "reviewer"
CASES = EVAL / "cases"
MANIFEST = EVAL / "manifest.json"


def make_seeds() -> None:
    """Synthetic seeds built from the approved mock frames. Clearly labelled as seeds."""
    from PIL import Image, ImageDraw, ImageFilter
    import postprocess
    CASES.mkdir(parents=True, exist_ok=True)
    day = Image.open(ROOT / "style" / "references" / "mock-day.png").convert("RGBA")
    night = Image.open(ROOT / "style" / "references" / "mock-night.png").convert("RGBA")
    pal = postprocess.load_palette(ROOT)

    def quant(im: Image.Image) -> Image.Image:
        px = im.load(); cache = {}
        for y in range(im.height):
            for x in range(im.width):
                c = px[x, y]
                if c[3] < 128: px[x, y] = (0, 0, 0, 0); continue
                k = c[:3]
                if k not in cache: cache[k] = postprocess._nearest(k, pal)
                n = cache[k]; px[x, y] = (n[0], n[1], n[2], 255)
        return im

    crops = {  # name: (frame, box) in the 960x540 frames
        "house-front": (day, (40, 30, 260, 200)), "reaper-inside": (day, (70, 40, 140, 140)), "guild-house": (day, (290, 0, 450, 190)),
        "stall-and-well": (day, (500, 220, 700, 300)), "gate-house": (night, (400, 20, 560, 200)), "horde-edge": (night, (560, 200, 760, 400)),
        "castellan": (night, (740, 280, 820, 380)), "tree-and-fence": (day, (10, 380, 260, 530)), "pond-tower": (night, (0, 400, 240, 540)), "lamp-post": (night, (100, 140, 160, 220)),
    }
    cases = []
    for name, (frame, box) in crops.items():
        im = quant(frame.crop(box).copy())
        f = f"seed-ok-{name}.png"; im.save(CASES / f)
        cases.append({"file": f, "expect": "approved", "why": "palette-pure crop of the approved mock frame", "spec": {"max_off_palette": 0.02}, "seed": True})
    # rejected seeds: each a different failure class
    base = quant(day.crop((40, 30, 260, 200)).copy())
    rej = []
    raw = day.crop((40, 30, 260, 200)).copy(); raw.save(CASES / "seed-bad-offpalette.png"); rej.append(("seed-bad-offpalette.png", "lighting baked in: pixels off the 16-colour palette", {"max_off_palette": 0.02}))
    b = base.copy().filter(ImageFilter.GaussianBlur(2)); b.save(CASES / "seed-bad-blurry.png"); rej.append(("seed-bad-blurry.png", "blurred, smooth shading, no crisp pixels", {"max_off_palette": 0.02}))
    t = base.copy(); ImageDraw.Draw(t).text((10, 10), "KEEP", fill=(217, 207, 191, 255)); t.save(CASES / "seed-bad-text.png"); rej.append(("seed-bad-text.png", "text rendered inside the image", {"max_off_palette": 0.5}))
    p = base.copy(); px = p.load()
    for y in range(p.height):
        for x in range(p.width):
            c = px[x, y]; px[x, y] = (min(255, c[0] + 60), c[1], min(255, c[2] + 90), c[3])
    p.save(CASES / "seed-bad-purple.png"); rej.append(("seed-bad-purple.png", "purple/neon tint, forbidden by the style bible", {"max_off_palette": 0.02}))
    s = base.copy().resize((base.width * 2, base.height * 2), Image.BILINEAR); s.save(CASES / "seed-bad-upscaled.png"); rej.append(("seed-bad-upscaled.png", "upscaled with smoothing", {"max_off_palette": 0.02}))
    o = base.copy(); o.save(CASES / "seed-bad-opaque-sprite.png"); rej.append(("seed-bad-opaque-sprite.png", "sprite job with no transparent background", {"transparent_bg": True, "max_off_palette": 0.02}))
    w = base.copy().resize((100, 100), Image.NEAREST); w.save(CASES / "seed-bad-wrongsize.png"); rej.append(("seed-bad-wrongsize.png", "wrong final size", {"final_width": 96, "final_height": 48}))
    g = base.copy(); ImageDraw.Draw(g).rectangle((0, 0, g.width, g.height), outline=(255, 255, 255, 255), width=3); g.save(CASES / "seed-bad-white-border.png"); rej.append(("seed-bad-white-border.png", "white frame around the image, off-palette", {"max_off_palette": 0.02}))
    e = Image.new("RGBA", (96, 48), (0, 0, 0, 0)); e.save(CASES / "seed-bad-empty.png"); rej.append(("seed-bad-empty.png", "fully transparent output", {}))
    h = base.copy(); ImageDraw.Draw(h).ellipse((60, 40, 160, 140), fill=(255, 220, 120, 120)); h.save(CASES / "seed-bad-glow.png"); rej.append(("seed-bad-glow.png", "baked lamp glow; lighting belongs on the lighting layer", {"max_off_palette": 0.02}))
    for f, why, spec in rej:
        cases.append({"file": f, "expect": "rejected", "why": why, "spec": spec, "seed": True})
    MANIFEST.write_text(json.dumps(cases, indent=2) + "\n")
    print(f"wrote {len(cases)} seed cases")


def run(checks_only: bool) -> int:
    from orchestrator import checks
    cases = json.loads(MANIFEST.read_text())
    tp = fp = fn = tn = 0; misses = []
    for c in cases:
        path = CASES / c["file"]
        ok, why = checks.check_image(ROOT, path, c.get("spec", {}))
        verdict, reason = ("approved", why) if ok else ("rejected", "auto-check: " + why)
        if ok and not checks_only:
            from orchestrator import reviewer
            from shared.jobs import Result, ResultStatus
            res = Result(job_id="eval", status=ResultStatus.OK, worker="eval", started_at="", outputs=[str(path.relative_to(ROOT))])
            verdict, reason = reviewer.review_result(ROOT, res, c.get("spec", {}))
        exp = c["expect"]
        if exp == "rejected" and verdict == "rejected": tp += 1
        elif exp == "rejected": fn += 1; misses.append((c["file"], exp, verdict, reason, c["why"]))
        elif verdict == "rejected": fp += 1; misses.append((c["file"], exp, verdict, reason, c["why"]))
        else: tn += 1
    n = len(cases); acc = (tp + tn) / n if n else 0
    prec = tp / (tp + fp) if tp + fp else 0; rec = tp / (tp + fn) if tp + fn else 0
    print(f"cases {n}  accuracy {acc:.0%}  reject-precision {prec:.0%}  reject-recall {rec:.0%}  (mode: {'checks only' if checks_only else 'checks + vision'})")
    for f, exp, got, reason, why in misses:
        print(f"  MISS {f}: expected {exp}, got {got}. reviewer said: {reason[:120]} | truth: {why}")
    return 0 if not misses else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--checks-only", action="store_true"); ap.add_argument("--make-seeds", action="store_true")
    a = ap.parse_args()
    if a.make_seeds: make_seeds()
    else: sys.exit(run(a.checks_only))
