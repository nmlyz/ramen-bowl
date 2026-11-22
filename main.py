#!/usr/bin/env python3
"""Steaming ramen bowl - a single-ingredient food illustration.

Draws a large bowl of ramen (the noodle is the hero ingredient) with
Pillow only: glossy broth, lifted noodles held by chopsticks, a soft
boiled egg, chashu, green onion and rising steam on a dark warm
background. Fully deterministic: no randomness, fixed geometry.

Run:  python3 main.py        -> writes /output/entry.png (1024x1024)
"""

import math
import os

from PIL import Image, ImageDraw, ImageFilter

OUT = "/output/entry.png"
W = 1024          # final size
SS = 2            # supersample factor (draw at 2048, downscale for AA)
CW = W * SS       # canvas size


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def vgrad(img, top, bottom):
    """Vertical gradient over the whole canvas."""
    d = ImageDraw.Draw(img)
    for y in range(CW):
        t = y / (CW - 1)
        d.line([(0, y), (CW, y)], fill=lerp(top, bottom, t))


def radial_glow(base, cx, cy, radius, color, peak_alpha):
    """Soft radial glow composited onto base (RGBA)."""
    layer = Image.new("RGBA", (CW, CW), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    steps = 48
    for i in range(steps, 0, -1):
        t = i / steps
        r = radius * t
        a = int(peak_alpha * (1.0 - t) ** 1.6)
        d.ellipse([cx - r, cy - r, cx + r, cy + r],
                  fill=color + (a,))
    layer = layer.filter(ImageFilter.GaussianBlur(radius * 0.06))
    base.alpha_composite(layer)


def wavy_points(x0, y0, y1, amp, phase, step=14):
    pts = []
    y = y0
    while y <= y1:
        x = x0 + amp * math.sin((y - y0) / 130.0 + phase)
        pts.append((x, y))
        y += step
    return pts


def main():
    img = Image.new("RGBA", (CW, CW), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)

    # ---------- background: dark warm gradient + glow ----------
    vgrad(img, (16, 9, 5), (38, 21, 10))
    radial_glow(img, 1024, 900, 1150, (150, 84, 28), 150)
    radial_glow(img, 1024, 1000, 700, (214, 138, 52), 90)

    # ---------- table ----------
    d.rectangle([0, 1500, CW, CW], fill=(46, 28, 14))
    for y in range(1500, CW):
        t = (y - 1500) / (CW - 1500)
        d.line([(0, y), (CW, y)], fill=lerp((58, 36, 18), (30, 17, 8), t))
    # soft shadow under the bowl
    sh = Image.new("RGBA", (CW, CW), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sh)
    ds.ellipse([430, 1560, 1620, 1740], fill=(0, 0, 0, 150))
    sh = sh.filter(ImageFilter.GaussianBlur(34))
    img.alpha_composite(sh)
    d = ImageDraw.Draw(img)

    # ---------- nori sheet rising behind the bowl ----------
    nori = [(560, 560), (820, 520), (880, 1120), (620, 1160)]
    d.polygon(nori, fill=(18, 32, 22))
    d.line([(600, 590), (650, 1100)], fill=(46, 78, 52), width=10)
    d.line([(760, 560), (820, 1080)], fill=(34, 58, 40), width=6)

    # ---------- bowl body: deep rounded bowl ----------
    # rim centre (1024, 1080); body is the lower half of a tall ellipse
    body_box = [364, 560, 1684, 1600]
    # ceramic gradient (lighter warm indigo near the rim, darker below)
    grad = Image.new("RGB", (CW, CW), (0, 0, 0))
    dg = ImageDraw.Draw(grad)
    for y in range(1080, 1601):
        t = (y - 1080) / 520
        dg.line([(0, y), (CW, y)], fill=lerp((66, 60, 84), (20, 18, 30), t))
    mask = Image.new("L", (CW, CW), 0)
    dm = ImageDraw.Draw(mask)
    dm.pieslice(body_box, 0, 180, fill=255)
    img.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(img)
    # glossy highlight streak on the left of the bowl
    hl = Image.new("RGBA", (CW, CW), (0, 0, 0, 0))
    dh = ImageDraw.Draw(hl)
    dh.ellipse([430, 1120, 700, 1560], fill=(255, 205, 140, 40))
    hl = hl.filter(ImageFilter.GaussianBlur(46))
    img.alpha_composite(hl)
    d = ImageDraw.Draw(img)
    # foot ring: small lip flush with the bowl bottom
    d.ellipse([880, 1540, 1168, 1620], fill=(16, 14, 22))
    d.ellipse([880, 1540, 1168, 1620], outline=(64, 58, 80), width=10)
    # decorative emblem on the bowl body
    deco = Image.new("RGBA", (CW, CW), (0, 0, 0, 0))
    dd = ImageDraw.Draw(deco)
    dd.ellipse([968, 1320, 1080, 1432], outline=(198, 158, 92, 130),
               width=7)
    dd.arc([980, 1332, 1068, 1420], 200, 60, fill=(198, 158, 92, 130),
           width=6)
    deco = deco.filter(ImageFilter.GaussianBlur(1.5))
    img.alpha_composite(deco)
    d = ImageDraw.Draw(img)

    # ---------- broth surface ----------
    bcx, bcy, brx, bry = 1024, 1080, 620, 128
    for i in range(28, 0, -1):
        t = i / 28
        col = lerp((198, 118, 32), (112, 60, 15), t)
        d.ellipse([bcx - brx * t, bcy - bry * t,
                   bcx + brx * t, bcy + bry * t], fill=col)
    # warm light pool on the broth
    pool = Image.new("RGBA", (CW, CW), (0, 0, 0, 0))
    dp = ImageDraw.Draw(pool)
    dp.ellipse([700, 1000, 1250, 1160], fill=(255, 186, 92, 70))
    pool = pool.filter(ImageFilter.GaussianBlur(30))
    img.alpha_composite(pool)
    d = ImageDraw.Draw(img)
    # chilli-oil: small pools hugging the broth edge (under the toppings)
    d.arc([460, 990, 700, 1140], 90, 200, fill=(178, 44, 18), width=14)
    d.arc([1420, 1000, 1600, 1130], 250, 30, fill=(198, 62, 22), width=12)
    # oil droplets catching light
    for (x, y, r) in [(760, 1050, 15), (1330, 1110, 12), (1150, 1170, 10),
                      (900, 1140, 9), (1450, 1040, 9)]:
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 214, 130))
        d.ellipse([x - r // 2, y - r // 2, x + r // 3, y + r // 3],
                  fill=(255, 240, 200))

    # ---------- noodles resting on the broth ----------
    noodle_col = (242, 211, 138)
    noodle_dark = (214, 168, 92)
    strands = [
        (760, 1080, 300, 62, 200, 330),
        (900, 1090, 260, 56, 150, 20),
        (1150, 1090, 280, 58, 200, 10),
        (1280, 1070, 240, 52, 160, 350),
        (1024, 1110, 320, 66, 10, 170),
        (840, 1130, 220, 50, 210, 40),
        (1380, 1110, 200, 46, 180, 60),
        (1080, 1040, 260, 54, 300, 80),
        (960, 1140, 240, 50, 40, 200),
        (1240, 1140, 220, 48, 120, 300),
    ]
    for (cx, cy, rx, ry, a0, a1) in strands:
        d.arc([cx - rx, cy - ry, cx + rx, cy + ry], a0, a1,
              fill=noodle_dark, width=20)
        d.arc([cx - rx, cy - ry - 6, cx + rx, cy + ry - 6], a0, a1,
              fill=noodle_col, width=15)

    # ---------- menma (bamboo shoots) ----------
    for (x, y) in [(1500, 1150), (1560, 1080)]:
        d.rounded_rectangle([x - 66, y - 17, x + 66, y + 17],
                            radius=15, fill=(196, 142, 52))
        d.line([(x - 56, y - 6), (x + 56, y - 6)], fill=(232, 184, 96),
               width=6)

    # ---------- chashu slices: flat rolled rounds, inside the broth ----------
    for (cx, cy, r) in [(1350, 1100, 120), (1520, 1050, 96)]:
        ry = r * 0.62
        for i in range(12, 0, -1):
            t = i / 12
            col = lerp((236, 172, 138), (168, 92, 64), t)
            rr = r * t
            d.ellipse([cx - rr, cy - ry * t, cx + rr, cy + ry * t],
                      fill=col)
        # rolled-meat ring
        d.ellipse([cx - r * 0.55, cy - ry * 0.55,
                   cx + r * 0.55, cy + ry * 0.55],
                  outline=(150, 78, 54), width=7)
        d.arc([cx - r, cy - ry, cx + r, cy + ry], 200, 340,
              fill=(255, 226, 196), width=7)

    # ---------- soft-boiled egg (halved, yolk facing viewer) ----------
    ex, ey = 700, 1090
    d.ellipse([ex - 118, ey - 92, ex + 118, ey + 92], fill=(255, 250, 238))
    d.ellipse([ex - 118, ey - 92, ex + 118, ey + 92],
              outline=(226, 208, 182), width=6)
    for i in range(8, 0, -1):
        t = i / 8
        col = lerp((246, 158, 44), (214, 106, 20), t)
        rr = 62 * t
        d.ellipse([ex - rr, ey - rr, ex + rr, ey + rr], fill=col)
    d.ellipse([ex - 26, ey - 30, ex + 8, ey + 2], fill=(255, 214, 130))

    # ---------- green onion rings ----------
    for (x, y, r) in [(620, 1020, 20), (680, 1170, 17), (980, 1180, 19),
                      (1200, 1020, 16), (1400, 1180, 18), (860, 990, 15),
                      (1560, 1160, 15), (1100, 960, 14), (960, 1040, 13)]:
        d.ellipse([x - r, y - r, x + r, y + r], fill=(74, 160, 80))
        d.ellipse([x - r // 2, y - r // 2, x + r // 2, y + r // 2],
                  fill=(190, 226, 120))
    # sesame seeds
    for (x, y) in [(880, 1200), (1160, 1200), (1300, 970), (1030, 950),
                   (1440, 1110), (800, 1120), (1600, 1040)]:
        d.ellipse([x - 9, y - 5, x + 9, y + 5], fill=(250, 240, 214))

    # ---------- lifted noodles + chopsticks (upper right) ----------
    lift = Image.new("RGBA", (CW, CW), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lift)
    for k in range(11):
        x0 = 1200 + k * 24
        pts = wavy_points(x0, 640, 1060, 24 + (k % 3) * 9, phase=k * 0.7)
        pts += [(x0 + 30 * math.sin(k), 1100 + k * 5),
                (x0 - 40, 1160)]
        dl.line(pts, fill=(240, 208, 134, 255), width=20, joint="curve")
        dl.line(pts, fill=(220, 176, 98, 255), width=6, joint="curve")
    lift = lift.filter(ImageFilter.GaussianBlur(1.2))
    img.alpha_composite(lift)
    d = ImageDraw.Draw(img)
    # chopsticks gripping the bundle at its top pinch point
    def chopstick(x1, y1, x2, y2, dx, dy):
        d.polygon([(x1, y1), (x1 + dx, y1 + dy), (x2 + dx, y2 + dy),
                   (x2, y2)], fill=(139, 90, 43))
        d.line([(x1, y1), (x2, y2)], fill=(198, 142, 74), width=7)
    chopstick(1700, 220, 1410, 630, 26, 10)
    chopstick(1760, 280, 1460, 650, 24, 14)
    # pinched noodle knot where the sticks grip
    d.ellipse([1405, 612, 1465, 648], fill=(240, 208, 134))
    d.line([(1410, 632), (1460, 622)], fill=(220, 176, 98), width=5)

    # ---------- steam ----------
    steam = Image.new("RGBA", (CW, CW), (0, 0, 0, 0))
    dst = ImageDraw.Draw(steam)
    for (x0, amp, ph, a) in [(760, 46, 0.0, 100), (900, 60, 1.2, 88),
                             (1040, 52, 2.4, 96), (1180, 58, 3.6, 80),
                             (1330, 44, 4.8, 70), (690, 40, 5.6, 60)]:
        pts = wavy_points(x0, 330, 1040, amp, ph, step=18)
        dst.line(pts, fill=(255, 250, 240, a), width=46, joint="curve")
    steam = steam.filter(ImageFilter.GaussianBlur(30))
    img.alpha_composite(steam)

    # ---------- rim: thin red band + warm light, top arc only ----------
    d.arc([364, 952, 1684, 1208], 180, 360, fill=(172, 44, 30), width=26)
    d.arc([364, 952, 1684, 1208], 200, 340, fill=(255, 226, 170), width=7)

    # ---------- downscale, save ----------
    out = img.convert("RGB").resize((W, W), Image.LANCZOS)
    os.makedirs("/output", exist_ok=True)
    out.save(OUT, format="PNG", optimize=True)
    os.chmod(OUT, 0o644)


if __name__ == "__main__":
    main()
