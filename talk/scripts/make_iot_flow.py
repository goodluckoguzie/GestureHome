#!/usr/bin/env python3
"""Catchy silent loop: camera sees → data → decide → connect → act."""
from math import cos, pi, sin
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 420
FPS = 30
SECONDS = 12
N = FPS * SECONDS
INK = (0, 64, 80)
MINT = (0, 237, 181)
WHITE = (255, 255, 255)
CREAM = (247, 251, 250)
CYAN = (0, 180, 216)
PURPLE = (123, 97, 255)
GOLD = (255, 183, 3)
CORAL = (255, 107, 107)
SKY = (56, 189, 248)
NIGHT = (27, 42, 74)
STAGE_COL = [CYAN, PURPLE, MINT, GOLD]
DATA_COL = [CYAN, GOLD, CORAL, MINT, PURPLE, SKY]
ICONS = Path("/home/goodluck/Desktop/MyProjects/Tutorial/GestureHome/talk/media/iot-icons")
OUT = Path("/home/goodluck/Desktop/MyProjects/Tutorial/GestureHome/talk/media/iot-flow-frames")
MP4 = Path("/home/goodluck/Desktop/MyProjects/Tutorial/GestureHome/talk/media/iot-flow.mp4")

STAGES = [
    (0.00, 0.22, 0, "A person walks by.", "The camera sees it."),
    (0.22, 0.38, 0, "The picture is split", "into data packets."),
    (0.38, 0.54, 1, "Software checks the data", "and decides: a person."),
    (0.54, 0.70, 2, "The decision is sent", "across Wi-Fi."),
    (0.70, 1.00, 3, "The home acts.", "The light turns on."),
]


def font(size, bold=False):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ):
        p = Path(path)
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def span(t, a, b):
    if b <= a:
        return 0.0
    return ease((t - a) / (b - a))


def cutout(name, size):
    im = Image.open(ICONS / name).convert("RGBA").resize((size, size), Image.LANCZOS)
    a = np.array(im)
    d = (
        np.abs(a[:, :, 0].astype(np.int16) - INK[0])
        + np.abs(a[:, :, 1].astype(np.int16) - INK[1])
        + np.abs(a[:, :, 2].astype(np.int16) - INK[2])
    )
    a[:, :, 3] = np.where(d < 70, 0, a[:, :, 3])
    return Image.fromarray(a)


def paste(base, sprite, cx, cy, scale=1.0):
    if scale != 1.0:
        nw = max(1, int(sprite.width * scale))
        nh = max(1, int(sprite.height * scale))
        sprite = sprite.resize((nw, nh), Image.LANCZOS)
    x = int(cx - sprite.width / 2)
    y = int(cy - sprite.height / 2)
    base.alpha_composite(sprite, (x, y))


def caption_for(t):
    stage = STAGES[0]
    for item in STAGES:
        if item[0] <= t < item[1]:
            stage = item
    return stage[2], stage[3], stage[4]


def mix(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def make_pixels():
    tiles = []
    for r in range(5):
        for c in range(7):
            col = DATA_COL[(r * 7 + c) % len(DATA_COL)]
            tile = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
            ImageDraw.Draw(tile).rounded_rectangle([0, 0, 11, 11], 2, fill=col)
            tiles.append((c, r, tile))
    return tiles


def draw_frame(i, icons, tiles):
    t = i / N
    base = Image.new("RGBA", (W, H), INK + (255,))
    d = ImageDraw.Draw(base)

    cam, person, chip, wifi, bulb, lock = icons
    f_title = font(22, True)
    f_tag = font(13, True)
    f_cap = font(18, False)
    f_lead = font(21, True)
    f_small = font(14, True)

    d.text((W // 2, 28), "How IoT works", fill=MINT + (255,), font=f_title, anchor="mt")

    # four stage cards
    cards = [
        (150, 210, "SENSE", "Camera"),
        (470, 210, "DECIDE", "Software"),
        (790, 210, "CONNECT", "Wi-Fi"),
        (1110, 210, "ACT", "Home"),
    ]
    active = 0
    if t >= 0.38:
        active = 1
    if t >= 0.54:
        active = 2
    if t >= 0.70:
        active = 3

    for n, (cx, cy, tag, name) in enumerate(cards):
        on = n == active or (t > 0.78 and n <= active)
        accent = STAGE_COL[n]
        fill = mix(INK, accent, 0.22 if on else 0.08) + (255,)
        d.rounded_rectangle(
            [cx - 118, cy - 118, cx + 118, cy + 118], 16, fill=fill, outline=accent, width=4
        )
        d.text((cx, cy - 104), tag, fill=accent + (255,), font=f_tag, anchor="mt")

    # arrows between cards
    for i, (a, b) in enumerate(zip(cards, cards[1:])):
        x1, x2 = a[0] + 126, b[0] - 126
        y = a[1]
        col = STAGE_COL[i + 1] + (255,)
        d.line([(x1, y), (x2 - 12, y)], fill=col, width=4)
        d.polygon([(x2, y), (x2 - 14, y - 8), (x2 - 14, y + 8)], fill=col)

    # --- SENSE: camera in the corner, person walks through the viewfinder ---
    vf = (62, 142, 238, 300)
    d.rounded_rectangle(vf, 10, fill=NIGHT + (255,), outline=CYAN, width=2)
    lamp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(lamp).ellipse([168, 148, 228, 208], fill=(255, 196, 90, 70))
    base.alpha_composite(lamp)
    paste(base, cam, 92, 168, 0.28)
    walk = span(t, 0.02, 0.18)
    px = vf[0] + 36 + walk * 96
    py = vf[3] - 58
    if t < 0.28:
        paste(base, person, px, py, 0.48)
    if 0.10 <= t <= 0.22:
        sy = vf[1] + 10 + span(t, 0.10, 0.22) * (vf[3] - vf[1] - 20)
        d.line([(vf[0] + 8, sy), (vf[2] - 8, sy)], fill=GOLD + (230,), width=3)
    if 0.18 <= t <= 0.26:
        flash = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        a = int(150 * (1 - span(t, 0.18, 0.26)))
        ImageDraw.Draw(flash).rounded_rectangle(vf, 10, fill=(255, 255, 255, a))
        base.alpha_composite(flash)

    # --- TRANSFORM: mint data cubes fly from the person to the chip ---
    if 0.20 <= t <= 0.50:
        fly = span(t, 0.20, 0.40)
        origin = (px if t < 0.28 else 170, py if t < 0.28 else 240)
        dest = (470, 200)
        for k, (c, r, tile) in enumerate(tiles):
            delay = (k / len(tiles)) * 0.35
            local = ease(max(0.0, min(1.0, (fly - delay) / 0.65)))
            ox = origin[0] + (c - 3) * 10
            oy = origin[1] + (r - 2) * 10
            x = ox + (dest[0] - ox) * local
            y = oy + (dest[1] - oy) * local - 55 * sin(local * pi)
            if 0.02 < local < 0.97:
                paste(base, tile, x, y, 1.0 + 0.4 * sin(local * pi))

    paste(base, chip, 470, 198, 0.62 + 0.05 * (0.38 <= t <= 0.54))

    # detected badge
    if t >= 0.40:
        alpha = int(255 * span(t, 0.40, 0.48))
        badge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bd = ImageDraw.Draw(badge)
        bd.text((470, 284), "DETECTED", fill=(255, 255, 255, alpha), font=f_small, anchor="mm")
        base.alpha_composite(badge)

    paste(base, wifi, 790, 188, 0.52)

    # wifi rings
    if t >= 0.54:
        rings = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        rd = ImageDraw.Draw(rings)
        phase = (t * 2.2) % 1.0
        for k in range(3):
            rr = 28 + ((phase + k / 3) % 1.0) * 46
            aa = int(140 * (1 - ((phase + k / 3) % 1.0)))
            rd.ellipse([790 - rr, 188 - rr, 790 + rr, 188 + rr], outline=SKY + (aa,), width=3)
        base.alpha_composite(rings)

    # packet traveling sense→decide already done; now chip → wifi → home
    if 0.50 <= t <= 0.78:
        u = span(t, 0.50, 0.72)
        path = [(470, 200), (790, 200), (1110, 168)]
        if u < 0.5:
            p = u / 0.5
            x = path[0][0] + (path[1][0] - path[0][0]) * p
            y = path[0][1] + (path[1][1] - path[0][1]) * p - 18 * sin(p * pi)
        else:
            p = (u - 0.5) / 0.5
            x = path[1][0] + (path[2][0] - path[1][0]) * p
            y = path[1][1] + (path[2][1] - path[1][1]) * p - 18 * sin(p * pi)
        pkt = Image.new("RGBA", (36, 22), (0, 0, 0, 0))
        ImageDraw.Draw(pkt).rounded_rectangle([0, 0, 35, 21], 6, fill=GOLD if u >= 0.5 else PURPLE)
        paste(base, pkt, x, y)

    # ACT: glow bulb + lock opens (rotate)
    glow_amt = span(t, 0.70, 0.82)
    if glow_amt > 0:
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(g)
        rr = int(36 + 40 * glow_amt)
        gd.ellipse(
            [1074 - rr, 150 - rr, 1074 + rr, 150 + rr],
            fill=GOLD + (int(90 * glow_amt),),
        )
        base.alpha_composite(g)
    paste(base, bulb, 1074, 158, 0.42 + 0.04 * glow_amt)

    lock_img = lock
    if t >= 0.76:
        ang = -28 * span(t, 0.76, 0.86)
        lock_img = lock.rotate(ang, resample=Image.BICUBIC, expand=True)
    paste(base, lock_img, 1146, 250, 0.36)

    if t >= 0.78:
        a = int(255 * span(t, 0.78, 0.86))
        badge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bd = ImageDraw.Draw(badge)
        bd.text((1110, 316), "LIGHT ON", fill=(255, 255, 255, a), font=f_small, anchor="mm")
        base.alpha_composite(badge)

    d = ImageDraw.Draw(base)
    idx, line1, line2 = caption_for(t)
    cx = cards[idx][0]
    shadow = (0, 32, 40, 180)

    def white_line(xy, text, fnt):
        x, y = xy
        for dx, dy in ((0, 2), (2, 0), (0, -1), (-1, 0), (1, 1)):
            d.text((x + dx, y + dy), text, fill=shadow, font=fnt, anchor="mt")
        d.text((x, y), text, fill=WHITE + (255,), font=fnt, anchor="mt")

    white_line((cx, 348), line1, f_cap)
    white_line((cx, 374), line2, f_lead)
    return base.convert("RGB")


def main():
    icons = (
        cutout("iot-icon-camera.png", 220),
        cutout("iot-icon-person.png", 180),
        cutout("iot-icon-chip.png", 200),
        cutout("iot-icon-wifi.png", 200),
        cutout("iot-icon-bulb.png", 180),
        cutout("iot-icon-lock.png", 160),
    )
    tiles = make_pixels()
    OUT.mkdir(parents=True, exist_ok=True)
    for i in range(N):
        draw_frame(i, icons, tiles).save(OUT / f"f{i:04d}.png")
        if i % 60 == 0:
            print(f"frame {i}/{N}")
    print(f"wrote {N} frames")


if __name__ == "__main__":
    main()
