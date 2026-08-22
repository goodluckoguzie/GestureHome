#!/usr/bin/env python3
"""From-scratch looping house: light, fan, door, and PIR actually work."""
from math import cos, pi, sin
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path("/home/goodluck/Desktop/MyProjects/Tutorial/GestureHome/talk/media/gesturehome-house-frames")
W, H = 1280, 430
FPS = 24
SECONDS = 12
N = FPS * SECONDS

INK = (0, 64, 80)
NIGHT = (8, 28, 36)
SKY_TOP = (6, 22, 32)
SKY_BOT = (0, 52, 64)
HOUSE = (18, 78, 90)
HOUSE_DARK = (10, 52, 64)
TRIM = (0, 237, 181)
WOOD = (92, 62, 42)
WOOD_LT = (138, 96, 62)
FLOOR = (36, 28, 22)
GOLD = (255, 214, 90)
WHITE = (255, 255, 255)
PIR = (230, 236, 240)


def font(size, bold=True):
    paths = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    )
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def span(t, a, b):
    if b <= a:
        return 0.0
    return ease((t - a) / (b - a))


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def sky(draw):
    for y in range(H):
        c = mix(SKY_TOP, SKY_BOT, y / H)
        draw.line([(0, y), (W, y)], fill=c)
    # moon
    draw.ellipse([1120, 28, 1174, 82], fill=(210, 228, 232))
    draw.ellipse([1134, 24, 1184, 74], fill=SKY_TOP)


def house_shell(draw, light):
    wall = mix(HOUSE_DARK, HOUSE, 0.35 + 0.45 * light)
    # lawn
    draw.rectangle([0, 368, W, H], fill=(12, 48, 38))
    draw.rectangle([0, 368, W, 376], fill=(0, 90, 70))
    # body
    draw.rounded_rectangle([90, 78, 1190, 372], 8, fill=wall, outline=TRIM, width=3)
    # roof
    draw.polygon([(60, 88), (640, 18), (1220, 88), (1190, 108), (90, 108)], fill=(8, 40, 50), outline=TRIM)
    # floor
    floor = mix((22, 18, 14), (70, 52, 36), 0.2 + 0.5 * light)
    draw.rectangle([110, 300, 1170, 362], fill=floor)
    # interior divider
    draw.line([(110, 300), (1170, 300)], fill=TRIM, width=2)


def window_glow(base, light):
    if light <= 0.02:
        return
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    a = int(70 * light)
    d.ellipse([430, 80, 850, 280], fill=GOLD + (a,))
    d.ellipse([540, 110, 740, 250], fill=WHITE + (int(40 * light),))
    base.alpha_composite(g.filter(ImageFilter.GaussianBlur(18)))


def draw_light(d, cx, cy, on):
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    if on > 0:
        r = int(28 + 90 * on)
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GOLD + (int(55 * on),))
        gd.ellipse([cx - r // 2, cy - r // 2, cx + r // 2, cy + r // 2], fill=WHITE + (int(70 * on),))
    # fixture
    d.line([(cx, 88), (cx, cy - 18)], fill=WHITE, width=3)
    shade = mix((40, 40, 40), GOLD, on)
    d.polygon([(cx - 22, cy - 6), (cx + 22, cy - 6), (cx + 14, cy + 18), (cx - 14, cy + 18)], fill=shade)
    d.ellipse([cx - 8, cy + 14, cx + 8, cy + 30], fill=mix((80, 80, 70), WHITE, on))
    return glow


def draw_fan(d, cx, cy, ang, spinning):
    d.ellipse([cx - 10, 86, cx + 10, 102], fill=(20, 20, 20))
    d.line([(cx, 100), (cx, cy)], fill=(30, 30, 30), width=4)
    blades = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blades)
    for k in range(3):
        a = ang + k * 2 * pi / 3
        pts = []
        for u, v in ((0, 0), (18, -8), (78, -6), (86, 0), (78, 6), (18, 8)):
            x = cx + u * cos(a) - v * sin(a)
            y = cy + u * sin(a) + v * cos(a)
            pts.append((x, y))
        col = mix((50, 70, 78), (180, 200, 206), 0.35 if spinning else 0.15)
        bd.polygon(pts, fill=col + (230,))
    bd.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=(24, 28, 32, 255), outline=TRIM + (255,), width=2)
    return blades


def draw_pir(d, x, y, detect):
    d.rounded_rectangle([x, y, x + 28, y + 36], 6, fill=(40, 48, 52), outline=WHITE, width=2)
    d.ellipse([x + 4, y + 6, x + 24, y + 26], fill=PIR)
    led = (255, 40, 40) if detect > 0.4 else (40, 80, 70)
    d.ellipse([x + 10, y + 28, x + 18, y + 34], fill=led)
    if detect > 0:
        cone = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cd = ImageDraw.Draw(cone)
        a = int(70 * detect)
        cd.polygon([(x + 28, y + 16), (x + 210, y - 30), (x + 230, y + 90)], fill=TRIM + (a,))
        return cone
    return None


def draw_door(base, open_amt):
    # Door frame on left wall
    fx0, fy0, fx1, fy1 = 168, 148, 278, 348
    d = ImageDraw.Draw(base)
    d.rectangle([fx0 - 8, fy0 - 8, fx1 + 8, fy1 + 4], fill=(12, 40, 48), outline=TRIM, width=3)
    # hinged left, swings open to the left (perspective squash)
    w = fx1 - fx0
    vis = max(8, int(w * (1.0 - 0.82 * open_amt)))
    door = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(door)
    x1 = fx0 + vis
    dd.rectangle([fx0, fy0, x1, fy1], fill=WOOD + (255,), outline=(40, 24, 16, 255), width=2)
    # panels
    pad = 10
    if vis > 28:
        dd.rectangle([fx0 + pad, fy0 + 16, x1 - 8, fy0 + 120], outline=WOOD_LT + (255,), width=2)
        dd.rectangle([fx0 + pad, fy0 + 140, x1 - 8, fy1 - 40], outline=WOOD_LT + (255,), width=2)
        dd.ellipse([x1 - 18, (fy0 + fy1) // 2 - 6, x1 - 6, (fy0 + fy1) // 2 + 6], fill=GOLD + (255,))
    # keypad on frame
    dd.rounded_rectangle([fx1 + 10, fy0 + 70, fx1 + 36, fy0 + 128], 4, fill=(20, 20, 24, 255), outline=TRIM + (255,), width=2)
    for r in range(3):
        for c in range(3):
            px = fx1 + 16 + c * 6
            py = fy0 + 80 + r * 12
            dd.ellipse([px, py, px + 4, py + 4], fill=TRIM + (255,))
    # warm interior seen through opening
    if open_amt > 0.08:
        gap = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(gap)
        gd.rectangle([x1, fy0, fx1, fy1], fill=GOLD + (int(90 * open_amt),))
        base.alpha_composite(gap)
    base.alpha_composite(door)


def draw_person(base, x, y, scale=1.0):
    p = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(p)
    s = scale
    # silhouette
    d.ellipse([x - 12 * s, y - 78 * s, x + 12 * s, y - 54 * s], fill=(12, 16, 18, 230))
    d.rounded_rectangle([x - 16 * s, y - 54 * s, x + 16 * s, y - 8 * s], 8, fill=(12, 16, 18, 230))
    d.line([(x - 8 * s, y - 8 * s), (x - 14 * s, y + 28 * s)], fill=(12, 16, 18, 230), width=int(7 * s))
    d.line([(x + 8 * s, y - 8 * s), (x + 16 * s, y + 28 * s)], fill=(12, 16, 18, 230), width=int(7 * s))
    d.line([(x - 12 * s, y - 40 * s), (x - 28 * s, y - 18 * s)], fill=(12, 16, 18, 230), width=int(6 * s))
    d.line([(x + 12 * s, y - 40 * s), (x + 26 * s, y - 22 * s)], fill=(12, 16, 18, 230), width=int(6 * s))
    base.alpha_composite(p)


def caption(draw, text):
    f = font(20, True)
    # shadow
    draw.text((W // 2 + 1, H - 22), text, fill=(0, 20, 28), font=f, anchor="mb")
    draw.text((W // 2, H - 23), text, fill=WHITE, font=f, anchor="mb")


def stage(t):
    # 0-0.22 light on
    # 0.22-0.48 fan spin
    # 0.48-0.72 door open
    # 0.72-1.0 motion + person
    light = span(t, 0.04, 0.18)
    if t > 0.92:
        light = 1.0 - 0.35 * span(t, 0.92, 1.0)
    fan_on = span(t, 0.22, 0.32)
    door = span(t, 0.48, 0.64)
    if t > 0.88:
        door = 1.0 - span(t, 0.88, 0.98)
    detect = span(t, 0.70, 0.80)
    if t > 0.90:
        detect = 1.0 - span(t, 0.90, 1.0)
    person_x = lerp(40, 250, span(t, 0.68, 0.86))
    person_vis = 1.0 if 0.68 <= t <= 0.92 else 0.0
    if t < 0.22:
        cap = "The light turns on"
    elif t < 0.48:
        cap = "The fan starts"
    elif t < 0.70:
        cap = "The door opens"
    else:
        cap = "Motion is sensed"
    return light, fan_on, door, detect, person_x, person_vis, cap


def draw_frame(i):
    t = i / N
    light, fan_on, door, detect, px, pvis, cap = stage(t)

    img = Image.new("RGBA", (W, H), NIGHT + (255,))
    d = ImageDraw.Draw(img)
    sky(d)
    house_shell(d, light)
    window_glow(img, light)

    # interior furniture hints
    d.rounded_rectangle([720, 248, 980, 300], 8, fill=mix((30, 24, 20), (80, 60, 40), light))
    d.ellipse([1040, 250, 1120, 300], fill=mix((28, 36, 40), (60, 80, 70), light))

    glow = draw_light(d, 640, 168, light)
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(6)))

    ang = t * 2 * pi * (0.2 + 4.8 * fan_on)
    blades = draw_fan(d, 980, 168, ang, fan_on > 0.2)
    if fan_on > 0.5:
        blades = blades.filter(ImageFilter.GaussianBlur(0.8))
    img.alpha_composite(blades)

    cone = draw_pir(d, 300, 168, detect)
    if cone:
        img.alpha_composite(cone.filter(ImageFilter.GaussianBlur(4)))

    draw_door(img, door)

    if pvis:
        draw_person(img, px, 340, 1.0)

    d = ImageDraw.Draw(img)
    caption(d, cap)
    return img.convert("RGB")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for i in range(N):
        draw_frame(i).save(OUT / f"f{i:04d}.png")
        if i % 48 == 0:
            print(f"frame {i}/{N}")
    print(f"wrote {N} frames")


if __name__ == "__main__":
    main()
