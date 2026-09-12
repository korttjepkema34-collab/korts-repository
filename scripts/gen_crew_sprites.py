"""Generate the dashboard crew sprites.

Each specialist is drawn on a 48x64 pixel grid, four times the pixel count of the
first pass, which is what buys the detail: form shading down the shaded side,
eyes built from sclera, iris, pupil and two highlights, cloth with collars,
seams, cuffs and belts, and props drawn as real objects rather than a few
suggestive pixels.

The art is authored here rather than by hand in CSS because the sprite it
replaces was a single 16x17 block copied by fourteen box-shadow offsets - no room
for a hat, a prop, or even an outline, so every agent read as the same smudge.

Shared routines place the skull, body and face so the crew looks like one cast;
per-character routines then spend their pixels on hair, outfit and prop, which is
what has to differ. Outlines and shading are applied automatically at the end, so
a drawing routine only places colour and still comes out with a clean edge.
"""

import json
import math
import os

W, H = 48, 64
T = '.'          # transparent
O = 'o'          # outline, filled in automatically

BASE = {
    'o': '#120f20',                                     # outline
    'k': '#f0bd94', 'K': '#d0956c', 'j': '#b0744f',     # skin, shade, deep shade
    'b': '#ef8394',                                     # blush
    'e': '#241a33', 'w': '#ffffff', 'i': '#5fa8d8',     # eye dark, highlight, iris
    'h': '#6b4430', 'H': '#8f5d40', 'd': '#4a2c1e',     # hair, highlight, shade
    'c': '#d8e8ef', 'C': '#aabfcd', 'D': '#8399a8',     # cloth, shade, deep shade
    't': '#3c4a6b', 'T': '#55698f',                     # trim
    'a': '#f3bd4f', 'A': '#ffe9a8',                     # accent
    'm': '#9fb3c8', 'M': '#dce7f2',                     # metal
    'g': '#7ef0c8', 'f': '#2b2439', 'n': '#ffffff',     # glow, dark, white
}

HEAD_TOP, HEAD_BOT = 5, 32
HW = [7, 9, 10, 11, 12, 12, 13, 13, 13, 13, 13, 13, 13, 13,
      13, 13, 13, 13, 12, 12, 12, 11, 11, 10, 9, 8, 6, 4]
assert len(HW) == HEAD_BOT - HEAD_TOP + 1


def span(y, grow=0):
    """Left and right edge of the skull on row y, optionally grown outwards."""
    if HEAD_TOP <= y <= HEAD_BOT:
        hw = HW[y - HEAD_TOP] + grow
    elif y == HEAD_TOP - 1:
        hw = 7 + grow
    elif y == HEAD_TOP - 2:
        hw = 5 + grow
    elif y == HEAD_TOP - 3:
        hw = 3 + grow
    else:
        return None
    return 24 - hw, 23 + hw


class Canvas:
    def __init__(self):
        self.g = [[T] * W for _ in range(H)]

    def set(self, x, y, ch):
        if 0 <= x < W and 0 <= y < H:
            self.g[y][x] = ch

    def get(self, x, y):
        return self.g[y][x] if 0 <= x < W and 0 <= y < H else T

    def row(self, y, x0, x1, ch):
        for x in range(x0, x1 + 1):
            self.set(x, y, ch)

    def col(self, x, y0, y1, ch):
        for y in range(y0, y1 + 1):
            self.set(x, y, ch)

    def box(self, x0, y0, x1, y1, ch):
        for y in range(y0, y1 + 1):
            self.row(y, x0, x1, ch)

    def px(self, ch, *pts):
        for x, y in pts:
            self.set(x, y, ch)

    def oval(self, cx, cy, rx, ry, ch):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.02:
                    self.set(x, y, ch)

    def hollow(self, cx, cy, rx, ry, ch, fill):
        """Ring of `ch` with the middle set to `fill`."""
        self.oval(cx, cy, rx, ry, ch)
        self.oval(cx, cy, rx - 1, ry - 1, fill)

    def mirror(self, y, x0, x1, ch):
        self.row(y, x0, x1, ch)
        self.row(y, W - 1 - x1, W - 1 - x0, ch)

    def shade_right(self, src, dst, depth=2):
        """Form shading: darken the last few pixels of each row of a material."""
        for y in range(H):
            xs = [x for x in range(W) if self.g[y][x] == src]
            if not xs:
                continue
            hi = max(xs)
            for x in range(hi - depth + 1, hi + 1):
                if self.g[y][x] == src:
                    self.set(x, y, dst)

    def shade_bottom(self, src, dst, depth=1):
        for x in range(W):
            ys = [y for y in range(H) if self.g[y][x] == src]
            if not ys:
                continue
            lo = max(ys)
            for y in range(lo - depth + 1, lo + 1):
                if self.g[y][x] == src:
                    self.set(x, y, dst)

    def outline(self):
        g = self.g
        out = [r[:] for r in g]
        for y in range(H):
            for x in range(W):
                if g[y][x] != T:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < H and g[ny][nx] not in (T, O):
                        out[y][x] = O
                        break
        self.g = out

    def rows(self):
        return [''.join(r) for r in self.g]


# ----------------------------------------------------------------- shared parts

def head(c, skin='k'):
    for y in range(HEAD_TOP, HEAD_BOT + 1):
        l, r = span(y)
        c.row(y, l, r, skin)
    c.box(9, 19, 10, 24, skin)                          # ears
    c.box(37, 19, 38, 24, skin)
    c.px('K', (10, 21), (10, 22), (37, 21), (37, 22))


def neck(c, skin='k', shade='K'):
    c.box(20, 32, 27, 37, skin)
    c.box(20, 32, 27, 34, shade)                        # shadow cast by the jaw


def eyes(c, iris='i', style='round', lash='e'):
    """Sclera, iris, pupil and two highlights - the detail that reads first."""
    for cx in (18.0, 29.0):
        if style == 'closed':
            for d in range(-3, 4):
                c.set(int(cx) + d, 22 - abs(d) // 2, lash)
                c.set(int(cx) + d, 23 - abs(d) // 2, lash)
            continue
        if style == 'happy':                            # upward arcs
            for d in range(-4, 5):
                y = 23 - int(round(2.2 * math.cos(d / 4.0 * 1.6)))
                c.set(int(cx) + d, y, lash)
                c.set(int(cx) + d, y + 1, lash)
            continue
        # No white sclera: a full eye-white at this size reads as a goggle rather
        # than an eye. Dark opening, iris, pupil, one strong highlight.
        ry = 3.0 if style == 'round' else 2.4
        c.oval(cx, 22.0, 2.6, ry, lash)                 # eye opening
        c.oval(cx, 22.3, 1.8, ry - 0.8, iris)           # iris
        c.oval(cx, 22.6, 0.9, ry - 1.6, 'e')            # pupil
        c.px('w', (int(cx) - 2, 20), (int(cx) - 1, 20), (int(cx) - 2, 21))
        c.px('w', (int(cx) + 1, 24))
        c.row(int(22 - ry) - 1, int(cx) - 2, int(cx) + 2, lash)    # lash line


def brows(c, ch='d', lift=0, angry=False):
    for sx, sgn in ((14, 1), (27, -1)):
        for d in range(7):
            y = 14 - lift + (d * sgn if angry else 0) // 3
            c.set(sx + d, y, ch)
            c.set(sx + d, y + 1, ch)


def face(c, mouth='smile', blush=True, nose=True):
    if nose:
        c.px('K', (23, 26), (24, 26), (24, 27))
    if blush:
        c.oval(15.0, 26.5, 2.6, 1.6, 'b')
        c.oval(32.0, 26.5, 2.6, 1.6, 'b')
    if mouth == 'smile':
        c.px('e', (21, 29), (22, 30), (23, 30), (24, 30), (25, 30), (26, 29))
    elif mouth == 'grin':
        c.row(29, 21, 26, 'e')
        c.box(22, 30, 25, 31, 'e')
        c.px('n', (22, 30), (23, 30), (24, 30), (25, 30))
    elif mouth == 'flat':
        c.row(30, 21, 26, 'e')
    elif mouth == 'small':
        c.px('e', (23, 30), (24, 30))
    elif mouth == 'open':
        c.oval(23.5, 30.0, 1.6, 1.4, 'e')


def fringe(kind):
    """Bottom row of the hair for each column - the main silhouette control."""
    f = {}
    for x in range(6, 42):
        t = (x - 10) / 27.0
        if kind == 'straight':
            b = 18
        elif kind == 'short':
            b = 14
        elif kind == 'spiky':
            b = 15 + (4 if (x // 3) % 2 else 0)
        elif kind == 'wave':
            b = 17 + int(round(2.5 * math.sin(t * math.pi * 3)))
        elif kind == 'side':
            b = 12 + int(round(9 * t))
        elif kind == 'bowl':
            b = 16 + int(round(5 * abs(t - 0.5) * 2))
        elif kind == 'messy':
            b = 15 + [0, 3, 1, 4, 0, 2, 3, 1][(x // 2) % 8]
        elif kind == 'curl':
            b = 16 + int(round(3 * abs(math.sin(t * math.pi * 2))))
        else:
            b = 16
        f[x] = b
    return f


def hair(c, kind='straight', ch='h', hi='H', sh='d', top=1, grow=1, sides=26,
         thick=3):
    """Cap over the skull down to a shaped fringe, plus hair down both temples.

    The temple hair is what stops the cap reading as a helmet: without it the
    fringe is a straight bar across a bare head.
    """
    f = fringe(kind)
    for y in range(top, max(f.values()) + 1):
        s = span(y, grow)
        if not s:
            continue
        for x in range(s[0], s[1] + 1):
            if f.get(x, 0) >= y:
                c.set(x, y, ch)
    if sides:
        for y in range(8, sides + 1):
            s = span(min(y, HEAD_BOT), grow)
            if not s:
                continue
            c.row(y, s[0], s[0] + thick - 1, ch)
            c.row(y, s[1] - thick + 1, s[1], ch)
    for x in range(15, 25, 3):                          # sheen across the crown
        b = f.get(x, 0)
        if b >= 8:
            c.set(x, max(top + 2, b - 6), hi)
            c.set(x, max(top + 3, b - 5), hi)
            c.set(x + 1, max(top + 3, b - 5), hi)
    for x in range(12, 36, 5):                          # strand separations
        b = f.get(x, 0)
        if b >= 10:
            c.set(x, b, sh)
            c.set(x, b - 1, sh)
    c.shade_right(ch, sh, 2)


TORSO = {37: 6, 38: 8, 39: 9, 40: 10, 41: 10, 42: 10, 43: 10, 44: 10, 45: 10,
         46: 10, 47: 10, 48: 10, 49: 10, 50: 9, 51: 9, 52: 9, 53: 8}


def torso(c, cloth='c', trim='t', collar='round'):
    for y, hw in TORSO.items():                         # shoulders taper in
        c.row(y, 24 - hw, 23 + hw, cloth)
    if collar == 'round':
        c.oval(23.5, 37.0, 5.0, 2.2, trim)
    elif collar == 'v':
        for d in range(6):
            c.px(trim, (18 + d, 37 + d), (19 + d, 37 + d), (29 - d, 37 + d), (28 - d, 37 + d))
    elif collar == 'high':
        c.box(17, 36, 30, 40, trim)
    c.row(52, 14, 33, trim)                             # hem band


def arms(c, cloth='c', skin='k', cuff=None):
    # Arms sit one pixel clear of the torso so the automatic outline draws the
    # limb separately; without that gap the whole upper body reads as one slab.
    for x0, sx in ((7, 11.0), (35, 36.0)):
        c.oval(sx, 41.0, 3.6, 3.6, cloth)               # shoulder, overlapping
        c.box(x0, 41, x0 + 5, 50, cloth)
        c.box(x0 + 1, 50, x0 + 5, 52, cloth)            # taper to the wrist
        if cuff:
            c.box(x0 + 1, 50, x0 + 5, 52, cuff)
        c.oval(x0 + 2.5, 54.5, 2.6, 2.6, skin)          # hand


def legs(c, pants='t', shoe='f', sock=None):
    c.box(16, 54, 22, 59, pants)
    c.box(25, 54, 31, 59, pants)
    if sock:
        c.box(16, 57, 22, 59, sock)
        c.box(25, 57, 31, 59, sock)
    c.box(15, 60, 22, 62, shoe)                         # shoes, toe rounded forward
    c.box(25, 60, 32, 62, shoe)
    c.box(15, 62, 21, 63, shoe)
    c.box(26, 62, 32, 63, shoe)


def body(c, cloth='c', trim='t', skin='k', shoe='f', collar='round',
         cuff=None, sock=None, pants=None):
    neck(c, skin)
    torso(c, cloth, trim, collar)
    arms(c, cloth, skin, cuff)
    legs(c, pants or trim, shoe, sock)


BOB_BELOW = 36          # rows above this are head and neck, and bob together


def bobbed(grid):
    """Second animation frame: the head and neck drop one pixel.

    Done on the un-outlined grid so the frame can be outlined afterwards; moving
    an already-outlined sprite would drag its old edge along with it.
    """
    out = [row[:] for row in grid]
    for y in range(BOB_BELOW - 1, 0, -1):
        out[y] = grid[y - 1][:]
    out[0] = [T] * W
    return out


SPRITES = {}


def sprite(worker, callsign, pal):
    def deco(fn):
        c = Canvas()
        fn(c)
        # One light source, top left, applied to every sprite the same way so the
        # crew reads as one cast rather than seventeen separate drawings.
        c.shade_right('c', 'C', 3)
        c.shade_right('C', 'D', 1)
        c.shade_right('k', 'K', 2)
        raw = [row[:] for row in c.g]

        frames = []
        for grid in (raw, bobbed(raw)):
            f = Canvas()
            f.g = [row[:] for row in grid]
            f.outline()
            frames.append(f.rows())

        colours = dict(BASE)
        colours.update(pal)
        SPRITES[worker] = {'callsign': callsign, 'rows': frames[0],
                           'frames': frames, 'pal': colours}
        return fn
    return deco


# ------------------------------------------------------------------ characters

@sprite('orchestrator', 'Atlas', {'h': '#a8542b', 'H': '#cd7440', 'd': '#763819',
                                  'c': '#2a4163', 'C': '#1f3050', 'D': '#16223b',
                                  't': '#f3bd4f', 'i': '#6fd8ff', 'g': '#7ce4ff'})
def _atlas(c):
    """Cloud lead: gold circlet, command cape, a small orbiting holo-globe."""
    c.box(5, 38, 10, 58, 'C')                           # cape behind the shoulders
    c.box(37, 38, 42, 58, 'C')
    c.px(T, (5, 38), (42, 38), (5, 58), (42, 58))
    body(c, cloth='c', trim='t', collar='v', cuff='t')
    head(c)
    hair(c, 'short')
    eyes(c)
    brows(c, 'd', lift=1)
    face(c, 'smile')
    c.row(12, 10, 37, 't')                              # circlet
    c.row(13, 10, 37, 'a')
    c.px('A', (14, 10), (23, 9), (24, 9), (33, 10))
    c.px('t', (23, 8), (24, 8))
    c.row(39, 15, 32, 't')                              # rank braid
    c.oval(23.5, 45.0, 3.2, 3.2, 't')
    c.oval(23.5, 45.0, 1.6, 1.6, 'A')
    c.hollow(43.0, 44.0, 4.4, 4.4, 'g', 'C')            # holo-globe above the hand
    c.row(44, 39, 47, 'g')
    c.px('g', (43, 40), (43, 48))
    c.px('w', (41, 42))


@sprite('reviewer', 'Judge', {'h': '#eef0f6', 'H': '#ffffff', 'd': '#bfc6d6',
                              'c': '#1d2437', 'C': '#151a29', 'D': '#0e1220',
                              't': '#a86d3d', 'i': '#7a6a55', 'm': '#d9b877'})
def _judge(c):
    """Reviewer: the barrister wig is the widest silhouette on the floor."""
    body(c, cloth='c', trim='C', collar='high', cuff='C')
    c.box(20, 37, 27, 45, 'M')                          # white collar tabs
    c.px('D', (23, 39), (24, 39), (23, 43), (24, 43))
    head(c)
    hair(c, 'curl', top=2, sides=44)                    # wig, falling past the jaw
    for y in range(16, 44, 4):                          # curl rolls down each side
        c.px('d', (9, y), (10, y), (37, y), (38, y))
    eyes(c, iris='i', style='stern')
    brows(c, 'd', angry=True)
    face(c, 'flat', blush=False)
    for x0 in (13, 26):                                 # wire spectacles
        c.row(16, x0 + 1, x0 + 8, 'm')
        c.row(28, x0 + 1, x0 + 8, 'm')
        c.col(x0, 17, 27, 'm')
        c.col(x0 + 9, 17, 27, 'm')
    c.row(22, 23, 24, 'm')                              # bridge
    c.col(12, 20, 22, 'm')
    c.col(35, 20, 22, 'm')
    c.box(38, 40, 44, 45, 't')                          # gavel
    c.box(40, 45, 42, 54, 't')
    c.row(41, 38, 44, 'a')


@sprite('visual-qa', 'Iris', {'h': '#b98ad6', 'H': '#d7b4ec', 'd': '#8c60a8',
                              'c': '#e4e8f4', 'C': '#c2c9dd', 'D': '#a3abc2',
                              't': '#5b4a7a', 'i': '#8f6fd0', 'm': '#c9932f',
                              'M': '#f6f9ff'})
def _iris(c):
    """Visual QA: a lab coat and a brass magnifier inspecting one enlarged pixel."""
    body(c, cloth='c', trim='t', collar='v', cuff='C')
    c.col(23, 38, 52, 'C')                              # coat opening
    c.col(24, 38, 52, 'D')
    c.box(15, 44, 19, 48, 'C')                          # pockets
    c.box(28, 44, 32, 48, 'C')
    head(c)
    hair(c, 'wave', sides=34)                           # bob
    eyes(c, iris='i')
    brows(c, 'd')
    face(c, 'smile')
    c.hollow(39.0, 44.0, 7.0, 7.0, 'm', 'M')            # magnifier held out
    c.oval(39.0, 44.0, 4.6, 4.6, 'M')
    c.box(37, 42, 41, 46, 'e')                          # the pixel under the glass
    c.px('n', (35, 41), (36, 41))                       # glare
    c.box(42, 50, 44, 56, 'm')
    c.box(41, 55, 44, 60, 't')                          # grip


@sprite('optimizer', 'Tempo', {'h': '#2f2a3d', 'H': '#4d4560', 'd': '#1b1826',
                               'c': '#e8534f', 'C': '#c03c39', 'D': '#95292a',
                               't': '#1f2740', 'i': '#ffd447', 'a': '#ffd447'})
def _tempo(c):
    """Performance: sweatband, spiked hair, stopwatch and trailing speed lines."""
    body(c, cloth='c', trim='t', collar='round', cuff='n', sock='n')
    c.row(43, 13, 34, 'n')                              # track stripes
    c.row(44, 13, 34, 'n')
    head(c)
    hair(c, 'spiky', top=0)
    c.row(14, 10, 37, 'a')                              # sweatband
    c.row(15, 10, 37, 'a')
    c.row(16, 10, 37, 'A')
    eyes(c, iris='i', style='happy')
    face(c, 'grin', blush=True)
    c.hollow(42.0, 44.0, 5.0, 5.4, 'm', 'M')            # stopwatch
    c.px('e', (42, 41), (42, 42), (42, 43), (42, 44), (44, 45))
    c.box(41, 37, 43, 39, 'm')
    for y, x1 in ((44, 5), (49, 6), (54, 4)):           # speed lines
        c.row(y, 1, x1, 'M')
        c.row(y + 1, 1, x1 - 2, 'M')


@sprite('backend', 'Forge', {'h': '#28364a', 'H': '#44556f', 'd': '#1a2432',
                             'c': '#334e83', 'C': '#263c66', 'D': '#1a2b4a',
                             't': '#8a5a34', 'i': '#7fb8d8', 'a': '#ff9a3c'})
def _forge(c):
    """Backend: welding visor flipped up, leather apron, hammer mid-swing."""
    body(c, cloth='c', trim='t', collar='round', cuff='C')
    c.box(16, 41, 31, 56, 't')                          # apron
    c.px(T, (16, 41), (31, 41))
    c.row(40, 19, 28, 't')
    c.box(20, 46, 27, 50, 'C')                          # apron pocket
    c.px('a', (22, 48), (25, 48))
    head(c)
    hair(c, 'short')
    for y in range(2, 14):                              # visor raised on the crown
        s = span(y, 2)
        if s:
            c.row(y, s[0], s[1], 'm')
    c.box(13, 5, 34, 11, 'e')                           # dark glass
    c.row(5, 15, 23, 'M')                               # reflection
    c.row(12, 10, 37, 'm')
    c.row(13, 10, 37, 'M')
    eyes(c, iris='i', style='stern')
    brows(c, 'd', angry=True)
    face(c, 'flat')
    c.box(38, 26, 46, 33, 'm')                          # hammer head
    c.box(40, 28, 44, 31, 'M')
    c.box(41, 33, 43, 50, 't')                          # shaft
    c.px('a', (36, 22), (45, 22), (47, 27), (35, 30), (46, 37))


@sprite('game-coder', 'Rune', {'h': '#cf4f43', 'H': '#e8756a', 'd': '#9b3630',
                               'c': '#3a4f8c', 'C': '#2a3c6e', 'D': '#1d2a50',
                               't': '#253560', 'i': '#7cf0ff', 'g': '#7cf0ff'})
def _rune(c):
    """Game engineer: hooded, a lit sigil on the brow, crystal-tipped staff."""
    c.box(6, 37, 11, 60, 'C')                           # cloak
    c.box(36, 37, 41, 60, 'C')
    body(c, cloth='c', trim='t', collar='high', cuff='t')
    head(c)
    hair(c, 'straight')
    for y in range(1, 20):                              # hood shell
        s = span(y, 3)
        if s:
            c.row(y, s[0], s[1], 'C')
    c.px('C', (22, 0), (23, 0), (24, 0), (25, 0))
    for y in range(10, 40):                             # hood falling past the jaw
        s = span(min(y, HEAD_BOT), 3)
        if s:
            c.col(s[0], 10, 39, 'C')
            c.col(s[0] + 1, 10, 39, 'C')
            c.col(s[1], 10, 39, 'C')
            c.col(s[1] - 1, 10, 39, 'C')
    for y in range(13, HEAD_BOT + 1):                   # face opening
        s = span(y)
        if s:
            c.row(y, s[0] + 1, s[1] - 1, 'k')
    c.row(13, 12, 35, 'D')                              # shadow under the rim
    c.row(14, 13, 34, 'D')
    c.px('h', (13, 15), (14, 15), (33, 15), (34, 15))
    eyes(c, iris='i')
    face(c, 'small')
    c.oval(23.5, 16.5, 2.2, 1.8, 'g')                   # sigil
    c.px('n', (23, 16))
    c.box(43, 20, 45, 58, 'h')                          # staff
    c.hollow(44.0, 16.0, 4.0, 5.0, 'g', 'n')
    c.px('g', (44, 16))


@sprite('cloud-engineer', 'Nimbus', {'h': '#eef4fb', 'H': '#ffffff', 'd': '#c4d2e2',
                                     'c': '#4fa8e0', 'C': '#3a83b6', 'D': '#2a6289',
                                     't': '#2a4163', 'i': '#49c7f0', 'a': '#ffd447'})
def _nimbus(c):
    """Cloud engineer: hair shaped like a cumulus, goggles up, a bolt on the chest."""
    body(c, cloth='c', trim='t', collar='round', cuff='C')
    for d in range(7):                                  # lightning bolt
        c.row(42 + d, 26 - d, 29 - d, 'a')
    c.box(19, 45, 24, 48, 'a')
    for d in range(6):
        c.row(47 + d, 20 + d // 2, 23 + d // 2, 'a')
    head(c)
    c.oval(15.0, 9.0, 7.0, 5.5, 'h')                    # cumulus lobes
    c.oval(24.0, 5.5, 9.0, 5.5, 'h')
    c.oval(33.0, 9.0, 7.0, 5.5, 'h')
    c.oval(23.5, 12.0, 13.0, 4.5, 'h')
    c.oval(20.0, 6.0, 4.0, 2.4, 'H')
    c.oval(31.0, 8.0, 3.0, 1.8, 'H')
    c.shade_right('h', 'd', 2)
    c.row(14, 10, 37, 'm')                              # goggles pushed up
    c.row(15, 10, 37, 'm')
    c.hollow(16.0, 13.0, 5.0, 4.2, 'm', 'g')
    c.hollow(31.0, 13.0, 5.0, 4.2, 'm', 'g')
    c.px('n', (14, 11), (29, 11))
    eyes(c, iris='i', style='happy')
    face(c, 'open')


@sprite('operations', 'Ops', {'h': '#4a3a2e', 'H': '#6d5540', 'd': '#31261e',
                              'c': '#f6d33f', 'C': '#cfa91f', 'D': '#a07f12',
                              't': '#2f3b52', 'i': '#6a8f5a', 'm': '#e8edf5'})
def _ops(c):
    """Operations: hard hat, headset, hi-vis bands and a clipboard. On-call."""
    body(c, cloth='c', trim='t', collar='round', cuff='t')
    c.row(43, 13, 34, 'M')                              # reflective bands
    c.row(44, 13, 34, 'm')
    c.row(48, 13, 34, 'M')
    c.row(49, 13, 34, 'm')
    head(c)
    hair(c, 'short')
    for y in range(2, 13):                              # hard hat shell
        s = span(y, 2)
        if s:
            c.row(y, s[0], s[1], 'c')
    c.row(13, 7, 40, 'c')                               # brim
    c.row(14, 7, 40, 'C')
    c.box(22, 1, 25, 12, 'C')                           # crown ridge
    eyes(c, iris='i')
    brows(c, 'd')
    face(c, 'smile')
    c.hollow(9.0, 22.0, 4.0, 5.0, 'f', 'D')             # headset cups
    c.hollow(38.0, 22.0, 4.0, 5.0, 'f', 'D')
    c.px('f', (11, 27), (12, 28), (13, 29), (14, 30))   # boom mic
    c.oval(16.0, 30.0, 2.0, 1.6, 'f')
    c.box(39, 42, 47, 56, 'M')                          # clipboard
    c.box(41, 40, 45, 43, 'm')
    for y in (46, 49, 52):
        c.row(y, 41, 45, 'D')


@sprite('debugger', 'Scout', {'h': '#d2c4ae', 'H': '#efe4cf', 'd': '#a4977f',
                              'c': '#78a6d9', 'C': '#5b82ad', 'D': '#436383',
                              't': '#445273', 'i': '#4f8f5c', 'a': '#8ce06a'})
def _scout(c):
    """Debugger: explorer cap, goggles on the crown, and a bug in a jar."""
    body(c, cloth='c', trim='t', collar='round', cuff='t')
    c.box(15, 42, 21, 48, 'C')                          # chest pocket
    c.row(42, 15, 21, 't')
    head(c)
    hair(c, 'short')
    for y in range(3, 14):                              # cap crown
        s = span(y, 2)
        if s:
            c.row(y, s[0], s[1], 't')
    c.row(14, 2, 26, 't')                               # brim, swept left
    c.row(15, 3, 24, 'T')
    c.box(26, 5, 38, 12, 'm')                           # goggles on the crown
    c.hollow(30.0, 8.5, 3.6, 3.2, 'f', 'a')
    c.hollow(36.0, 8.5, 3.6, 3.2, 'f', 'a')
    eyes(c, iris='i')
    brows(c, 'd')
    face(c, 'smile')
    c.box(38, 42, 47, 57, 'M')                          # specimen jar
    c.box(39, 43, 46, 56, 'D')
    c.box(38, 40, 47, 42, 'm')
    c.oval(42.5, 50.0, 2.6, 2.0, 'a')                   # the bug
    c.px('e', (41, 49), (44, 49), (40, 48), (45, 48))
    c.px('n', (40, 44), (41, 45))


@sprite('narrative', 'Scribe', {'h': '#9e593a', 'H': '#c1784f', 'd': '#71391f',
                                'c': '#77b98d', 'C': '#589670', 'D': '#3f7354',
                                't': '#5b3843', 'i': '#4f7f6a', 'a': '#f4efd8'})
def _scribe(c):
    """Narrative: long hair, a heavy scarf, an open book and a raised quill."""
    body(c, cloth='c', trim='t', collar='round', cuff='C')
    head(c)
    hair(c, 'wave', sides=52)
    eyes(c, iris='i')
    brows(c, 'd')
    face(c, 'smile')
    c.box(14, 36, 33, 41, 't')                          # scarf
    c.px(T, (14, 36), (33, 36))
    c.box(21, 41, 28, 52, 't')                          # scarf tail
    c.row(38, 15, 32, 'T')
    c.box(33, 44, 47, 56, 'a')                          # open book
    c.box(39, 44, 41, 56, 'D')
    for y in (47, 50, 53):
        c.row(y, 34, 38, 'D')
        c.row(y, 42, 46, 'D')
    c.box(2, 26, 5, 44, 'a')                            # quill
    c.px('M', (1, 24), (2, 24), (1, 28), (0, 32), (1, 36))
    c.px('f', (3, 45), (4, 45), (3, 46), (4, 46))


@sprite('level-designer', 'Mapper', {'h': '#3f3a33', 'H': '#5d564c', 'd': '#2a2620',
                                     'c': '#6f8f9e', 'C': '#53707e', 'D': '#3c545f',
                                     't': '#2f3a44', 'i': '#7a8f5a', 'a': '#cfe3f5'})
def _mapper(c):
    """Level design: flat cap, a grid marked onto the vest, rolled blueprint."""
    body(c, cloth='c', trim='t', collar='v', cuff='t')
    for x in (18, 24, 30):                              # grid on the vest
        c.col(x, 40, 51, 'a')
    for y in (42, 47, 51):
        c.row(y, 14, 33, 'a')
    head(c)
    hair(c, 'short')
    for y in range(6, 14):                              # flat cap
        s = span(y, 2)
        if s:
            c.row(y, s[0], s[1], 't')
    c.row(5, 14, 33, 't')
    c.row(14, 22, 44, 't')                              # brim to the right
    c.row(15, 24, 42, 'T')
    c.px('T', (16, 7), (17, 7), (18, 6))
    eyes(c, iris='i')
    brows(c, 'd')
    face(c, 'flat')
    c.box(1, 44, 13, 50, 'a')                           # rolled blueprint
    c.oval(2.5, 47.0, 2.0, 3.4, 'C')
    c.oval(12.0, 47.0, 2.0, 3.4, 'C')
    c.row(46, 4, 11, 'D')
    c.row(48, 4, 11, 'D')


@sprite('cloud-analyst', 'Oracle', {'h': '#2b2447', 'H': '#453a6e', 'd': '#1c1732',
                                    'c': '#3b2f66', 'C': '#2c2350', 'D': '#1e1839',
                                    't': '#1d1735', 'i': '#9df0ff', 'a': '#9df0ff'})
def _oracle(c):
    """Cloud analyst: a hooded mystic reading a crystal ball, stars on the robe."""
    c.box(4, 36, 10, 62, 'C')                           # robe sweep
    c.box(37, 36, 43, 62, 'C')
    body(c, cloth='c', trim='t', collar='high', cuff='t')
    for x, y in ((16, 43), (30, 40), (19, 51), (32, 49), (24, 45)):
        c.px('a', (x, y), (x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
    head(c)
    for y in range(0, 20):                              # deep hood
        s = span(y, 4)
        if s:
            c.row(y, s[0], s[1], 'c')
    for y in range(10, 42):
        s = span(min(y, HEAD_BOT), 4)
        if s:
            c.box(s[0], 10, s[0] + 2, 41, 'c')
            c.box(s[1] - 2, 10, s[1], 41, 'c')
    for y in range(14, HEAD_BOT + 1):                   # shadowed face
        s = span(y)
        if s:
            c.row(y, s[0] + 2, s[1] - 2, 'k')
    c.row(14, 12, 35, 'D')
    c.row(15, 13, 34, 'D')
    c.row(16, 14, 33, 'D')
    c.oval(23.5, 8.0, 2.6, 2.2, 'a')                    # brow gem
    c.px('n', (23, 7))
    for cx in (18.0, 29.0):                             # glowing eyes
        c.oval(cx, 22.0, 3.4, 3.0, 'a')
        c.oval(cx, 22.0, 1.8, 1.6, 'n')
    c.hollow(23.5, 52.0, 8.0, 8.0, 'a', 'n')            # crystal ball
    c.oval(23.5, 52.0, 6.2, 6.2, 'a')
    c.oval(21.0, 49.5, 2.4, 2.0, 'n')
    c.box(16, 59, 31, 62, 't')                          # stand


@sprite('personal-helper', 'Sage', {'h': '#b9b3ac', 'H': '#dcd7d1', 'd': '#8f8981',
                                    'c': '#c58f6a', 'C': '#a06e4d', 'D': '#7c5236',
                                    't': '#5a4a3f', 'i': '#6f8a6a', 'a': '#f6efe2'})
def _sage(c):
    """Personal helper: grey bun, round glasses, a cardigan and a cup of tea."""
    body(c, cloth='c', trim='t', collar='v', cuff='C')
    c.col(23, 38, 52, 'C')                              # cardigan opening
    c.col(24, 38, 52, 'D')
    for y in (41, 45, 49):                              # buttons
        c.px('a', (21, y), (22, y), (21, y + 1), (22, y + 1))
    head(c)
    hair(c, 'bowl', sides=26)
    c.oval(23.5, 1.5, 6.0, 4.0, 'h')                    # bun
    c.oval(21.0, 1.0, 2.6, 1.6, 'H')
    eyes(c, iris='i', style='closed')
    face(c, 'smile')
    c.hollow(18.0, 22.0, 4.6, 4.6, 'M', 'n')            # round glasses
    c.hollow(29.0, 22.0, 4.6, 4.6, 'M', 'n')
    c.px('M', (23, 22), (24, 22), (12, 21), (13, 21), (34, 21), (35, 21))
    for cx in (18.0, 29.0):                             # eyes behind the lenses
        c.px('e', (int(cx) - 2, 22), (int(cx) - 1, 22), (int(cx), 22))
        c.px('e', (int(cx) - 2, 23), (int(cx) - 1, 23), (int(cx), 23))
    c.hollow(41.0, 48.0, 5.0, 5.0, 'a', 'M')            # teacup
    c.box(36, 53, 46, 55, 'a')
    c.px('a', (46, 46), (47, 47), (47, 48), (46, 49))   # handle
    c.px('M', (40, 40), (41, 38), (40, 36), (42, 42))   # steam


@sprite('ui', 'Pixel', {'h': '#ff5fa2', 'H': '#ff9ac8', 'd': '#c93b76',
                        'c': '#3fc7d6', 'C': '#2d9aa8', 'D': '#1f7280',
                        't': '#653a7e', 'i': '#ff8ec0', 'a': '#ffd447'})
def _pixel(c):
    """UI: asymmetric hot-pink hair, a raised stylus, floating colour swatches."""
    body(c, cloth='c', trim='t', collar='round', cuff='t')
    c.box(14, 40, 20, 44, 'C')                          # hoodie pocket
    c.box(27, 40, 33, 44, 'C')
    head(c)
    hair(c, 'side')
    c.box(35, 12, 40, 46, 'h')                          # one long side-tail
    c.px('H', (36, 18), (36, 26), (36, 34), (36, 42))
    c.box(8, 12, 11, 26, 'h')
    eyes(c, iris='i', style='happy')
    face(c, 'grin')
    c.box(2, 34, 5, 52, 'a')                            # stylus
    c.px('f', (2, 53), (3, 53), (4, 53), (3, 54))
    c.px('M', (2, 32), (3, 32))
    for y, ch in ((40, 'a'), (46, 'h'), (52, 'g')):     # colour swatches
        c.box(43, y, 47, y + 4, ch)


@sprite('environment', 'Moss', {'h': '#4f7a3e', 'H': '#79a85c', 'd': '#37592a',
                                'c': '#8db876', 'C': '#6a9257', 'D': '#4d6f3e',
                                't': '#5a4632', 'i': '#7aa84f', 'a': '#c8e6a0'})
def _moss(c):
    """Environment: leafy hair with a sprout, an apron, and a potted seedling."""
    body(c, cloth='c', trim='t', collar='round', cuff='C')
    c.box(16, 41, 31, 56, 'a')                          # apron
    c.px(T, (16, 41), (31, 41))
    c.row(40, 19, 28, 'a')
    c.box(20, 47, 27, 51, 'C')
    head(c)
    hair(c, 'messy', sides=30)
    c.px('H', (12, 18), (16, 14), (31, 15), (35, 19))
    c.box(22, 0, 25, 12, 'H')                           # sprout stem
    c.oval(18.0, 3.0, 4.6, 2.6, 'a')                    # leaves
    c.oval(29.0, 2.0, 4.6, 2.6, 'a')
    c.px('H', (18, 3), (29, 2))
    eyes(c, iris='i', style='happy')
    face(c, 'smile')
    c.px('K', (17, 25), (19, 26), (28, 26), (30, 25))   # freckles
    c.box(37, 50, 47, 58, 't')                          # pot
    c.box(36, 47, 48, 51, 'T')
    c.box(41, 40, 43, 48, 'H')                          # seedling
    c.oval(38.0, 40.0, 3.4, 2.2, 'a')
    c.oval(46.0, 38.0, 3.4, 2.2, 'a')


@sprite('sprites', 'Flip', {'h': '#653d7f', 'H': '#8b5aa8', 'd': '#48285c',
                            'c': '#dc76af', 'C': '#b6558c', 'D': '#8d3c6b',
                            't': '#394b72', 'i': '#c77fd8', 'a': '#ffd447'})
def _flip(c):
    """Sprite animator: twin buns, a film-strip sash, a flipbook mid-flip."""
    body(c, cloth='c', trim='t', collar='round', cuff='C')
    for d in range(9):                                  # film-strip sash
        c.box(14 + d * 2, 38 + d * 2, 17 + d * 2, 41 + d * 2, 'M')
        c.px('f', (15 + d * 2, 39 + d * 2), (15 + d * 2, 40 + d * 2))
    head(c)
    hair(c, 'bowl', sides=28)
    c.oval(6.0, 10.0, 5.4, 5.0, 'h')                    # twin buns
    c.oval(41.0, 10.0, 5.4, 5.0, 'h')
    c.oval(4.5, 8.5, 2.2, 1.8, 'H')
    c.oval(39.5, 8.5, 2.2, 1.8, 'H')
    eyes(c, iris='i')
    face(c, 'grin')
    c.box(37, 42, 47, 54, 'M')                          # flipbook
    c.box(37, 42, 39, 54, 'C')
    c.px('e', (42, 46), (43, 47), (44, 48), (43, 49), (42, 50))
    c.px('a', (40, 38), (45, 39), (47, 44), (44, 57))   # motion arcs


@sprite('audio', 'Echo', {'h': '#8f4fd6', 'H': '#b57ceb', 'd': '#66339f',
                          'c': '#5a4a86', 'C': '#41346a', 'D': '#2c234d',
                          't': '#2b2447', 'i': '#4de0d0', 'a': '#4de0d0'})
def _echo(c):
    """Audio: oversized headphones with waves off the cans, and a boom mic."""
    body(c, cloth='c', trim='t', collar='v', cuff='t')
    for d in range(5):                                  # waveform across the chest
        c.box(15 + d * 4, 46 - d % 3 * 3, 17 + d * 4, 50 + d % 2 * 3, 'a')
    head(c)
    hair(c, 'straight')
    for y in range(1, 6):                               # headband
        s = span(y, 3)
        if s:
            c.row(y, s[0], s[1], 'f')
    c.box(4, 5, 10, 10, 'f')
    c.box(37, 5, 43, 10, 'f')
    c.hollow(7.0, 20.0, 6.0, 9.0, 'f', 'a')             # ear cups
    c.hollow(40.0, 20.0, 6.0, 9.0, 'f', 'a')
    c.oval(7.0, 20.0, 3.0, 5.6, 'f')
    c.oval(40.0, 20.0, 3.0, 5.6, 'f')
    eyes(c, iris='i', style='happy')
    face(c, 'open')
    c.px('f', (33, 30), (34, 31), (35, 32))             # boom mic
    c.oval(29.0, 31.0, 2.4, 2.0, 'f')
    for d, y0 in ((0, 14), (3, 17)):                    # sound waves off the cans
        for dy in range(-4, 5):
            x = int(round(2.2 * math.cos(dy / 4.0 * 1.5)))
            c.set(1 - d + x, y0 + dy + 4, 'a')
            c.set(46 + d - x, y0 + dy + 4, 'a')


# ---------------------------------------------------------------------- export

def to_svg(rows, pal):
    """One rect per horizontal run, so the markup stays small."""
    parts = []
    for y, row in enumerate(rows):
        x = 0
        while x < W:
            ch = row[x]
            if ch == T:
                x += 1
                continue
            run = 1
            while x + run < W and row[x + run] == ch:
                run += 1
            parts.append('<rect x="%d" y="%d" width="%d" height="1" fill="%s"/>'
                         % (x, y, run, pal.get(ch, '#ff00ff')))
            x += run
    return ''.join(parts)


def write_js(path):
    """Emit the grids, not the SVG.

    The rows are about a tenth of the size of the expanded markup and they diff
    as pictures in review, so the dashboard expands them once at load instead.
    """
    out = ['// Generated by scripts/gen_crew_sprites.py - do not edit by hand.',
           '// Each sprite is a %d x %d grid; one character per palette entry,'
           % (W, H),
           '// "." is transparent. Two frames: rest, and the head dropped one pixel.',
           'window.CREW_SPRITES = {', '  size: [%d, %d],' % (W, H), '  crew: {']
    for name in sorted(SPRITES):
        s = SPRITES[name]
        used = {ch for f in s['frames'] for r in f for ch in r} - {T}
        pal = {k: v for k, v in s['pal'].items() if k in used}
        out.append('    %s: {' % json.dumps(name))
        out.append('      callsign: %s,' % json.dumps(s['callsign']))
        out.append('      pal: %s,' % json.dumps(pal, sort_keys=True))
        for n, f in enumerate(s['frames']):
            out.append('      f%d: [%s],'
                       % (n, ','.join('"%s"' % r for r in f)))
        out.append('    },')
    out += ['  },', '};', '']
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out))
    return os.path.getsize(path)


if __name__ == '__main__':
    import sys

    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    for name, s in SPRITES.items():
        for f in s['frames']:
            assert len(f) == H, (name, len(f))
            for r in f:
                assert len(r) == W, (name, len(r))
        unknown = {ch for f in s['frames'] for r in f for ch in r} - set(s['pal']) - {T}
        assert not unknown, (name, unknown)

    size = write_js(os.path.join(out, 'sprites.js'))
    print('%d sprites, %dx%d, 2 frames -> sprites.js (%.1f kB)'
          % (len(SPRITES), W, H, size / 1024.0))
