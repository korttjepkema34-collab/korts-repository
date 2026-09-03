"""Post-process generated images so they obey the style bible mechanically:
downscale (nearest after a box filter), quantize to the 16-colour palette, cut a flat background
to transparency. Driven by job.spec.postprocess, e.g.
  {"downscale": 4, "palette": true, "transparent_bg": true, "final_width": 96, "final_height": 48}
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image


def load_palette(repo_root: Path) -> list[tuple[int, int, int]]:
    hexes = re.findall(r"`#([0-9a-f]{6})`", (repo_root / "style" / "style-bible.md").read_text())[:16]
    return [tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) for h in hexes]


def _nearest(c: tuple, pal: list[tuple[int, int, int]]) -> tuple[int, int, int]:
    r, g, b = c[:3]
    return min(pal, key=lambda p: (p[0] - r) ** 2 + (p[1] - g) ** 2 + (p[2] - b) ** 2)


def cut_background(im: Image.Image, tolerance: int = 28) -> Image.Image:
    """Flood-fill from the four corners: pixels close to the corner colour become transparent."""
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    seen = bytearray(w * h)
    for sx, sy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        ref = px[sx, sy][:3]
        stack = [(sx, sy)]
        while stack:
            x, y = stack.pop()
            if x < 0 or y < 0 or x >= w or y >= h or seen[y * w + x]:
                continue
            c = px[x, y]
            if sum(abs(c[i] - ref[i]) for i in range(3)) > tolerance * 3:
                continue
            seen[y * w + x] = 1
            px[x, y] = (c[0], c[1], c[2], 0)
            stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return im


def process(path: Path, repo_root: Path, opts: dict) -> Path:
    im = Image.open(path).convert("RGBA")
    if opts.get("transparent_bg"):
        im = cut_background(im)
    ds = int(opts.get("downscale", 1) or 1)
    if opts.get("final_width") and opts.get("final_height"):
        im = im.resize((int(opts["final_width"]), int(opts["final_height"])), Image.BOX)
    elif ds > 1:
        im = im.resize((im.width // ds, im.height // ds), Image.BOX)
    if opts.get("palette", True):
        pal = load_palette(repo_root)
        cache: dict = {}
        px = im.load()
        for y in range(im.height):
            for x in range(im.width):
                c = px[x, y]
                if c[3] < 128:
                    px[x, y] = (0, 0, 0, 0)
                    continue
                key = c[:3]
                if key not in cache:
                    cache[key] = _nearest(key, pal)
                n = cache[key]
                px[x, y] = (n[0], n[1], n[2], 255)
    out = path.with_name(path.stem + ".px.png")
    im.save(out)
    if opts.get("normal_map"):
        from normalmap import normal_map
        normal_map(out, float(opts.get("normal_strength", 2.0)))
    return out
