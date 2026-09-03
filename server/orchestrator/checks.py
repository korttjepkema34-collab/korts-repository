"""Deterministic asset checks that run before the vision reviewer. Cheap, strict, no opinions."""
from __future__ import annotations

import re
from pathlib import Path

PALETTE_HEX = None


def palette(repo: Path) -> list[tuple[int, int, int]]:
    global PALETTE_HEX
    if PALETTE_HEX is None:
        hexes = re.findall(r"`#([0-9a-f]{6})`", (repo / "style" / "style-bible.md").read_text())[:16]
        PALETTE_HEX = [tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) for h in hexes]
    return PALETTE_HEX


def check_image(repo: Path, path: Path, spec: dict) -> tuple[bool, str]:
    """Returns (ok, reason). Rejects wrong size, off-palette pixels, and missing transparency."""
    try:
        from PIL import Image
    except ImportError:
        return True, "pillow not installed; skipped deterministic checks"
    try:
        im = Image.open(path).convert("RGBA")
    except Exception as e:
        return False, f"unreadable image: {e}"
    w, h = im.size
    want_w, want_h = spec.get("final_width"), spec.get("final_height")
    if want_w and want_h and (w, h) != (want_w, want_h):
        return False, f"size {w}x{h}, expected {want_w}x{want_h}"
    pal = set(palette(repo))
    px = list(im.get_flattened_data()) if hasattr(im, "get_flattened_data") else list(im.getdata())
    opaque = [p for p in px if p[3] > 8]
    if not opaque:
        return False, "image is fully transparent"
    off = sum(1 for p in opaque if (p[0], p[1], p[2]) not in pal)
    frac = off / len(opaque)
    limit = float(spec.get("max_off_palette", 0.02))
    if frac > limit:
        return False, f"{frac:.1%} of opaque pixels are off-palette (limit {limit:.0%}); run the worker postprocess"
    if spec.get("transparent_bg") and len(opaque) > 0.97 * len(px):
        return False, "expected a transparent background but the image is almost fully opaque"
    return True, f"size ok, {frac:.2%} off-palette"
