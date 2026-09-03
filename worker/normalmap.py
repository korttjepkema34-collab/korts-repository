"""Generate a normal map for a sprite or tile sheet so Godot 2D lights have direction.
Height comes from luminance plus alpha edges; Sobel gives the gradient. Output <name>.n.png.
Good enough for pixel art: flat faces stay flat, outlines and highlights catch the light."""
from __future__ import annotations

from pathlib import Path

from PIL import Image


def normal_map(path: Path, strength: float = 2.0) -> Path:
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    px = im.load()

    def height(x: int, y: int) -> float:
        x = min(max(x, 0), w - 1); y = min(max(y, 0), h - 1)
        r, g, b, a = px[x, y]
        if a < 128:
            return 0.0
        return 0.3 + 0.7 * (0.299 * r + 0.587 * g + 0.114 * b) / 255.0

    out = Image.new("RGBA", (w, h))
    o = out.load()
    for y in range(h):
        for x in range(w):
            if px[x, y][3] < 128:
                o[x, y] = (128, 128, 255, 0)
                continue
            dx = (height(x + 1, y - 1) + 2 * height(x + 1, y) + height(x + 1, y + 1)) - (height(x - 1, y - 1) + 2 * height(x - 1, y) + height(x - 1, y + 1))
            dy = (height(x - 1, y + 1) + 2 * height(x, y + 1) + height(x + 1, y + 1)) - (height(x - 1, y - 1) + 2 * height(x, y - 1) + height(x + 1, y - 1))
            nx, ny, nz = -dx * strength, -dy * strength, 1.0
            l = (nx * nx + ny * ny + nz * nz) ** 0.5
            nx, ny, nz = nx / l, ny / l, nz / l
            o[x, y] = (int((nx * 0.5 + 0.5) * 255), int((ny * 0.5 + 0.5) * 255), int((nz * 0.5 + 0.5) * 255), 255)
    dst = path.with_name(path.stem + ".n.png")
    out.save(dst)
    return dst
