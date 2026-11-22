#!/usr/bin/env python3
"""Steaming ramen bowl - a single-ingredient food illustration.

Draws a large bowl of ramen (the noodle is the hero ingredient) with
a glossy broth, lifted noodles held by chopsticks, a soft-boiled egg,
chashu, green onion and rising steam on a dark warm background.

Standard library only (math, os, struct, zlib). No network, no
randomness, fixed geometry: the same bytes come out of every run.
The picture is painted on a bytearray canvas with a small scanline
rasterizer (row-slice fills, scanline ellipses, polygon fills and
circle-stamp strokes). Soft glows and steam are painted as low
resolution alpha layers and blended in.

Run:  python3 main.py        -> writes /output/entry.png (1024x1024)
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
BG_TOP = (16, 9, 5)
BG_BOT = (38, 21, 10)
GLOW1 = (150, 84, 28)
GLOW2 = (214, 138, 52)
TABLE_TOP = (58, 36, 18)
TABLE_BOT = (30, 17, 8)
BOWL_TOP = (66, 60, 84)
BOWL_BOT = (20, 18, 30)
BROTH_OUT = (198, 118, 32)
BROTH_IN = (112, 60, 15)
NOODLE = (242, 211, 138)
NOODLE_DARK = (214, 168, 92)
LIFT = (240, 208, 134)
LIFT_DARK = (220, 176, 98)
CHASHU_OUT = (236, 172, 138)
CHASHU_IN = (168, 92, 64)
CHASHU_RING = (150, 78, 54)
EGG_WHITE = (255, 250, 238)
EGG_OUTLINE = (226, 208, 182)
YOLK_OUT = (246, 158, 44)
YOLK_IN = (214, 106, 20)
YOLK_HI = (255, 214, 130)
ONION = (74, 160, 80)
ONION_IN = (190, 226, 120)
NORI = (18, 32, 22)
CHOP = (139, 90, 43)
CHOP_HI = (198, 142, 74)
RIM = (172, 44, 30)
RIM_HI = (255, 226, 170)
GOLD = (198, 158, 92)
MENMA = (196, 142, 52)
MENMA_HI = (232, 184, 96)
SESAME = (250, 240, 214)
STEAM_COL = (255, 250, 240)
POOL_COL = (255, 186, 92)
BOWL_HI = (255, 205, 140)
FOOT = (16, 14, 22)
FOOT_RING = (64, 58, 80)


def lerp(a, b, t):
    return (int(round(a[0] + (b[0] - a[0]) * t)),
            int(round(a[1] + (b[1] - a[1]) * t)),
            int(round(a[2] + (b[2] - a[2]) * t)))


def blend(under, over, alpha):
    """Blend `over` onto `under` with alpha 0..255."""
    ia = 255 - alpha
    return ((over[0] * alpha + under[0] * ia) // 255,
            (over[1] * alpha + under[1] * ia) // 255,
            (over[2] * alpha + under[2] * ia) // 255)


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bytes(bg)) * (w * h)

    def row(self, y, x0, x1, c):
        """Fill one horizontal run [x0, x1) on row y with color c."""
        if y < 0 or y >= self.h:
            return
        x0 = max(0, x0)
        x1 = min(self.w, x1)
        if x1 <= x0:
            return
        n = x1 - x0
        i = (y * self.w + x0) * 3
        self.px[i:i + 3 * n] = bytes(c) * n

    def vgrad(self, y0, y1, top, bot):
        span = max(1, y1 - y0)
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            self.row(y, 0, self.w, lerp(top, bot, (y - y0) / span))

    def ellipse(self, cx, cy, rx, ry, c, y_lo=None, y_hi=None):
        """Scanline-filled ellipse (optionally clipped to a y range)."""
        if rx <= 0 or ry <= 0:
            return
        lo = max(0, cy - ry) if y_lo is None else max(0, y_lo)
        hi = min(self.h - 1, cy + ry) if y_hi is None else min(self.h - 1, y_hi)
        for y in range(lo, hi + 1):
            dy = (y - cy) / ry
            d = 1.0 - dy * dy
            if d <= 0:
                continue
            hw = int(rx * math.sqrt(d))
            self.row(y, cx - hw, cx + hw + 1, c)

    def ellipse_ring(self, cx, cy, rx, ry, t, c):
        """Filled ring of thickness t around an ellipse."""
        if rx <= 0 or ry <= 0 or t <= 0:
            return
        irx, iry = rx - t, ry - t
        for y in range(max(0, cy - ry), min(self.h - 1, cy + ry) + 1):
            dy = (y - cy) / ry
            d = 1.0 - dy * dy
            if d <= 0:
                continue
            hw = int(rx * math.sqrt(d))
            if irx > 0 and iry > 0:
                dy2 = (y - cy) / iry
                d2 = 1.0 - dy2 * dy2
                if d2 > 0:
                    hw2 = int(irx * math.sqrt(d2))
                    self.row(y, cx - hw, cx - hw2, c)
                    self.row(y, cx + hw2 + 1, cx + hw + 1, c)
                    continue
            self.row(y, cx - hw, cx + hw + 1, c)

    def rings(self, cx, cy, rx, ry, n, col_out, col_in):
        """Concentric filled ellipses, outer colour -> inner colour."""
        for i in range(n, 0, -1):
            t = i / n
            self.ellipse(cx, cy, max(1, int(rx * t)), max(1, int(ry * t)),
                         lerp(col_out, col_in, t))

    def polygon(self, pts, c):
        ys = [p[1] for p in pts]
        n = len(pts)
        for y in range(max(0, min(ys)), min(self.h - 1, max(ys)) + 1):
            nodes = []
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    nodes.append(x0 + (y - y0) * (x1 - x0) // (y1 - y0))
            nodes.sort()
            for i in range(0, len(nodes) - 1, 2):
                self.row(y, nodes[i], nodes[i + 1] + 1, c)

    def stamp(self, cx, cy, r, c):
        """Small filled circle, used as a brush tip."""
        for y in range(max(0, cy - r), min(self.h - 1, cy + r) + 1):
            dy = y - cy
            d = r * r - dy * dy
            if d < 0:
                continue
            hw = int(math.sqrt(d))
            self.row(y, cx - hw, cx + hw + 1, c)

    def thick_line(self, x0, y0, x1, y1, w, c):
        r = max(1, w // 2)
        length = math.hypot(x1 - x0, y1 - y0)
        steps = max(1, int(length / max(2, r // 2)) + 1)
        for i in range(steps + 1):
            t = i / steps
            self.stamp(int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t), r, c)

    def polyline(self, pts, w, c):
        for i in range(len(pts) - 1):
            self.thick_line(pts[i][0], pts[i][1], pts[i + 1][0],
                            pts[i + 1][1], w, c)

    def arc(self, cx, cy, rx, ry, a0, a1, w, c):
        """Ellipse arc, angles in degrees, clockwise (y grows down)."""
        if a1 < a0:
            a1 += 360.0
        span = a1 - a0
        r = max(1, w // 2)
        step = max(0.5, math.degrees(3.0 / max(rx, ry)))
        a = a0
        while a <= a1:
            rad = math.radians(a)
            self.stamp(int(cx + rx * math.cos(rad)),
                       int(cy + ry * math.sin(rad)), r, c)
            a += step

    def glow(self, cx, cy, rx, ry, color, peak, bg_fn, steps=26,
             clip=None):
        """Soft elliptical glow over a background whose colour is a
        known function of y only. Painted as nested ellipses, outer
        (faint) first so inner (stronger) rings overwrite. `clip` is
        an optional (ccx, ccy, crx, cry) ellipse the glow stays in."""
        for s in range(steps, 0, -1):
            t = s / steps
            alpha = int(peak * (1.0 - t) ** 1.6)
            if alpha <= 0:
                continue
            for y in range(max(0, cy - ry), min(self.h - 1, cy + ry) + 1):
                dy = (y - cy) / ry
                d = t * t - dy * dy
                if d <= 0:
                    continue
                hw = int(rx * math.sqrt(d))
                x0, x1 = cx - hw, cx + hw + 1
                if clip is not None:
                    ccx, ccy, crx, cry = clip
                    cdy = (y - ccy) / cry
                    cd = 1.0 - cdy * cdy
                    if cd <= 0:
                        continue
                    chw = int(crx * math.sqrt(cd))
                    x0 = max(x0, ccx - chw)
                    x1 = min(x1, ccx + chw + 1)
                    if x1 <= x0:
                        continue
                self.row(y, x0, x1, blend(bg_fn(y), color, alpha))


# ---------------------------------------------------------------- steam
def wavy_points(x0, y0, y1, amp, phase, step=14):
    pts = []
    y = y0
    while y <= y1:
        x = x0 + amp * math.sin((y - y0) / 130.0 + phase)
        pts.append((x, y))
        y += step
    return pts


def box_blur(grid, w, h, radius):
    """Separable box blur on a flat list of ints, radius in cells."""
    # horizontal pass (prefix sums, clamped edges)
    tmp = [0] * (w * h)
    for y in range(h):
        base = y * w
        row = grid[base:base + w]
        pref = [0] * (w + 1)
        for x in range(w):
            pref[x + 1] = pref[x] + row[x]
        for x in range(w):
            lo = max(0, x - radius)
            hi = min(w - 1, x + radius)
            tmp[base + x] = (pref[hi + 1] - pref[lo]) // (hi - lo + 1)
    # vertical pass
    out = [0] * (w * h)
    for x in range(w):
        col = [tmp[y * w + x] for y in range(h)]
        pref = [0] * (h + 1)
        for y in range(h):
            pref[y + 1] = pref[y] + col[y]
        for y in range(h):
            lo = max(0, y - radius)
            hi = min(h - 1, y + radius)
            out[y * w + x] = (pref[hi + 1] - pref[lo]) // (hi - lo + 1)
    return out


def steam_layer(cv):
    """Paint steam on a 256x256 alpha layer, blur it, then blend it
    onto the canvas over its bounding box (nearest-neighbour upscale
    of a smooth field is invisible at this softness)."""
    S = 4  # downscale factor
    LW, LH = W // S, H // S
    layer = [0] * (LW * LH)

    def lstamp(cx, cy, r, a):
        for y in range(max(0, cy - r), min(LH - 1, cy + r) + 1):
            dy = y - cy
            d = r * r - dy * dy
            if d < 0:
                continue
            hw = int(math.sqrt(d))
            base = y * LW
            for x in range(max(0, cx - hw), min(LW - 1, cx + hw) + 1):
                if layer[base + x] < a:
                    layer[base + x] = a

    def lline(x0, y0, x1, y1, w, a):
        r = max(1, w // 2)
        length = math.hypot(x1 - x0, y1 - y0)
        steps = max(1, int(length / 3) + 1)
        for i in range(steps + 1):
            t = i / steps
            lstamp(int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t), r, a)

    cols = [(380, 23, 0.0, 100), (450, 30, 1.2, 88), (520, 26, 2.4, 96),
            (590, 29, 3.6, 80), (665, 22, 4.8, 70), (345, 20, 5.6, 60)]
    for (x0, amp, ph, a) in cols:
        pts = [(int(x / S), int(y / S))
               for (x, y) in wavy_points(x0, 165, 520, amp, ph, step=18)]
        for i in range(len(pts) - 1):
            lline(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], 6, a)

    layer = box_blur(layer, LW, LH, 6)
    # fade the tops of the columns in so they do not start abruptly
    for ly in range(38, 56):
        f = (ly - 38) / 18.0
        base = ly * LW
        for lx in range(LW):
            layer[base + lx] = int(layer[base + lx] * f)

    x0, x1, y0, y1 = 300, 712, 140, 545
    px = cv.px
    for y in range(y0, y1 + 1):
        fy = y / S
        ly0 = int(fy)
        wy = fy - ly0
        ly1 = min(LH - 1, ly0 + 1)
        prow = y * W * 3
        for x in range(x0, x1 + 1):
            fx = x / S
            lx0 = int(fx)
            wx = fx - lx0
            lx1 = min(LW - 1, lx0 + 1)
            a00 = layer[ly0 * LW + lx0]
            a10 = layer[ly0 * LW + lx1]
            a01 = layer[ly1 * LW + lx0]
            a11 = layer[ly1 * LW + lx1]
            a = int(a00 * (1 - wx) * (1 - wy) + a10 * wx * (1 - wy)
                    + a01 * (1 - wx) * wy + a11 * wx * wy)
            if a == 0:
                continue
            ia = 255 - a
            i = prow + x * 3
            px[i] = (STEAM_COL[0] * a + px[i] * ia) // 255
            px[i + 1] = (STEAM_COL[1] * a + px[i + 1] * ia) // 255
            px[i + 2] = (STEAM_COL[2] * a + px[i + 2] * ia) // 255


# ---------------------------------------------------------------- png
def write_png(canvas, path):
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)
        raw += canvas.px[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    png = bytearray(b"\x89PNG\r\n\x1a\n")
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", canvas.w, canvas.h,
                                      8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    os.chmod(path, 0o644)


# ---------------------------------------------------------------- scene
def bg_color(y):
    if y < 750:
        return lerp(BG_TOP, BG_BOT, y / 1023)
    return lerp(TABLE_TOP, TABLE_BOT, (y - 750) / 273)


def bowl_color(y):
    return lerp(BOWL_TOP, BOWL_BOT, max(0.0, min(1.0, (y - 540) / 260)))


def broth_color(x, y):
    t = math.sqrt(((x - 512) / 310.0) ** 2 + ((y - 540) / 64.0) ** 2)
    return lerp(BROTH_OUT, BROTH_IN, min(1.0, t))


def build():
    cv = Canvas(W, H, BG_TOP)
    cv.vgrad(0, 1023, BG_TOP, BG_BOT)

    # warm glows behind the bowl
    cv.glow(512, 450, 575, 575, GLOW1, 150, bg_color)
    cv.glow(512, 500, 350, 350, GLOW2, 90, bg_color)

    # table
    cv.vgrad(750, 1023, TABLE_TOP, TABLE_BOT)
    # soft shadow under the bowl
    cv.glow(512, 825, 297, 45, (0, 0, 0), 150,
            lambda y: lerp(TABLE_TOP, TABLE_BOT, (y - 750) / 273), steps=20)

    # nori sheet rising behind the bowl
    cv.polygon([(280, 280), (410, 260), (440, 560), (310, 580)], NORI)
    cv.thick_line(300, 295, 325, 550, 5, (46, 78, 52))
    cv.thick_line(380, 280, 410, 540, 3, (34, 58, 40))

    # bowl body: lower half of a tall ellipse, vertical ceramic gradient
    for y in range(540, 801):
        dy = (y - 540) / 260.0
        d = 1.0 - dy * dy
        if d <= 0:
            continue
        hw = int(330 * math.sqrt(d))
        cv.row(y, 512 - hw, 512 + hw + 1, bowl_color(y))
    # glossy highlight on the left of the bowl (clipped to the bowl)
    cv.glow(282, 670, 67, 110, BOWL_HI, 40, bowl_color, steps=18,
            clip=(512, 540, 330, 260))
    # foot ring
    cv.ellipse_ring(512, 790, 72, 20, 5, FOOT_RING)
    cv.ellipse(512, 790, 67, 15, FOOT)
    # decorative gold emblem
    cv.ellipse_ring(512, 688, 28, 28, 4, blend(bowl_color(688), GOLD, 130))
    cv.arc(512, 688, 22, 22, 200, 60, 3, blend(bowl_color(688), GOLD, 130))

    # broth surface: concentric warm gradient
    cv.rings(512, 540, 310, 64, 28, BROTH_OUT, BROTH_IN)
    # warm light pool on the broth
    cv.glow(487, 540, 137, 40, POOL_COL, 70,
            lambda y: broth_color(487, y), steps=16)
    # chilli-oil arcs hugging the broth edge
    cv.arc(290, 532, 60, 38, 90, 200, 7, (178, 44, 18))
    cv.arc(755, 532, 45, 33, 250, 30, 6, (198, 62, 22))
    # oil droplets catching light
    for (x, y, r) in [(380, 525, 7), (665, 555, 6), (575, 585, 5),
                      (450, 570, 4), (725, 520, 4)]:
        cv.stamp(x, y, r, (255, 214, 130))
        cv.stamp(x - r // 2, y - r // 2, max(1, r // 3), (255, 240, 200))

    # noodles resting on the broth
    strands = [(380, 540, 150, 31, 200, 330), (450, 545, 130, 28, 150, 20),
               (575, 545, 140, 29, 200, 10), (640, 535, 120, 26, 160, 350),
               (512, 555, 160, 33, 10, 170), (420, 565, 110, 25, 210, 40),
               (690, 555, 100, 23, 180, 60), (540, 520, 130, 27, 300, 80),
               (480, 570, 120, 25, 40, 200), (620, 570, 110, 24, 120, 300)]
    for (cx, cy, rx, ry, a0, a1) in strands:
        cv.arc(cx, cy, rx, ry, a0, a1, 10, NOODLE_DARK)
        cv.arc(cx, cy, rx, ry - 3, a0, a1, 7, NOODLE)

    # menma (bamboo shoots)
    for (x, y) in [(750, 575), (780, 540)]:
        cv.polygon([(x - 33, y - 8), (x + 33, y - 8), (x + 33, y + 8),
                    (x - 33, y + 8)], MENMA)
        cv.stamp(x - 33, y, 8, MENMA)
        cv.stamp(x + 33, y, 8, MENMA)
        cv.thick_line(x - 28, y - 3, x + 28, y - 3, 3, MENMA_HI)

    # chashu slices
    for (cx, cy, r) in [(675, 550, 60), (760, 525, 48)]:
        ry = int(r * 0.62)
        cv.rings(cx, cy, r, ry, 12, CHASHU_OUT, CHASHU_IN)
        cv.ellipse_ring(cx, cy, int(r * 0.55), int(ry * 0.55), 4, CHASHU_RING)
        cv.arc(cx, cy, r, ry, 200, 340, 4, (255, 226, 196))

    # soft-boiled egg, yolk facing the viewer
    ex, ey = 350, 545
    cv.ellipse(ex, ey, 59, 46, EGG_WHITE)
    cv.ellipse_ring(ex, ey, 59, 46, 3, EGG_OUTLINE)
    cv.rings(ex, ey, 31, 31, 8, YOLK_OUT, YOLK_IN)
    cv.ellipse(345, 538, 9, 8, YOLK_HI)

    # green onion rings
    for (x, y, r) in [(310, 510, 10), (340, 585, 8), (490, 590, 9),
                      (600, 510, 8), (700, 590, 9), (430, 495, 7),
                      (780, 580, 7), (550, 480, 7), (480, 520, 6)]:
        cv.stamp(x, y, r, ONION)
        cv.stamp(x, y, max(1, r // 2), ONION_IN)
    # sesame seeds
    for (x, y) in [(440, 600), (580, 600), (650, 485), (515, 475),
                   (720, 555), (400, 560), (800, 520)]:
        cv.ellipse(x, y, 5, 3, SESAME)

    # lifted noodles + chopsticks (upper right)
    for k in range(11):
        x0 = 600 + k * 12
        pts = wavy_points(x0, 320, 530, 12 + (k % 3) * 4, phase=k * 0.7,
                          step=14)
        pts += [(x0 + 15 * math.sin(k), 550 + k * 2), (x0 - 20, 580)]
        cv.polyline(pts, 10, LIFT)
        cv.polyline(pts, 3, LIFT_DARK)
    # chopsticks gripping the bundle
    cv.polygon([(850, 110), (863, 115), (718, 320), (705, 315)], CHOP)
    cv.thick_line(850, 110, 705, 315, 3, CHOP_HI)
    cv.polygon([(880, 140), (892, 147), (742, 332), (730, 325)], CHOP)
    cv.thick_line(880, 140, 730, 325, 3, CHOP_HI)
    # pinched noodle knot where the sticks grip
    cv.ellipse(717, 315, 15, 9, LIFT)
    cv.thick_line(705, 316, 730, 311, 3, LIFT_DARK)

    # steam
    steam_layer(cv)

    # rim: thin red band + warm light, top arc only
    cv.arc(512, 540, 330, 64, 180, 360, 13, RIM)
    cv.arc(512, 540, 330, 64, 200, 340, 4, RIM_HI)

    return cv


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(outdir, exist_ok=True)
    try:
        os.umask(0o022)
    except OSError:
        pass
    write_png(build(), os.path.join(outdir, "entry.png"))


if __name__ == "__main__":
    main()
