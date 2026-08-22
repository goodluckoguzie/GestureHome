#!/usr/bin/env python3
"""Stack flowchart: laptop → USB → Arduino → actuators."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1152, 520
INK = (0, 64, 80)
MINT = (0, 237, 181)
WHITE = (255, 255, 255)
PANEL = (0, 40, 48)
LINE = (0, 200, 160)
GOLD = (248, 210, 55)
OUT = Path(__file__).resolve().parents[1] / "media" / "arch" / "stack-flow.png"


def font(size, bold=False):
    paths = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    )
    for path in paths:
        p = Path(path)
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def rounded(draw, box, fill, outline=None, width=3, radius=18):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def arrow(draw, x0, y0, x1, y1, label="", label_above=True):
    draw.line([(x0, y0), (x1, y1)], fill=MINT, width=4)
    # arrow head
    draw.polygon([(x1, y1), (x1 - 14, y1 - 8), (x1 - 14, y1 + 8)], fill=MINT)
    if label:
        f = font(18, bold=True)
        bbox = draw.textbbox((0, 0), label, font=f)
        tw = bbox[2] - bbox[0]
        tx = (x0 + x1) / 2 - tw / 2
        ty = y0 - 28 if label_above else y0 + 12
        draw.text((tx, ty), label, fill=MINT, font=f)


def draw_laptop(draw, cx, cy):
    # screen
    rounded(draw, [cx - 110, cy - 90, cx + 110, cy + 20], PANEL, MINT, 3, 12)
    # webcam dot
    draw.ellipse([cx - 6, cy - 82, cx + 6, cy - 70], fill=MINT)
    # on-screen hand keypoints hint
    pts = [
        (cx - 40, cy - 10),
        (cx - 20, cy - 40),
        (cx, cy - 55),
        (cx + 18, cy - 38),
        (cx + 36, cy - 12),
    ]
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=(56, 189, 248), width=2)
    for x, y in pts:
        draw.ellipse([x - 4, y - 4, x + 4, y + 4], fill=GOLD)
    # base
    draw.polygon(
        [(cx - 120, cy + 28), (cx + 120, cy + 28), (cx + 95, cy + 48), (cx - 95, cy + 48)],
        fill=PANEL,
        outline=MINT,
    )
    draw.line([(cx - 40, cy + 38), (cx + 40, cy + 38)], fill=LINE, width=2)


def draw_arduino(draw, cx, cy):
    rounded(draw, [cx - 95, cy - 70, cx + 95, cy + 70], (0, 90, 70), MINT, 3, 14)
    # pin dots
    for i, x in enumerate(range(cx - 70, cx + 75, 28)):
        draw.ellipse([x - 5, cy - 48, x + 5, cy - 38], fill=GOLD if i % 2 == 0 else MINT)
        draw.ellipse([x - 5, cy + 38, x + 5, cy + 48], fill=MINT if i % 2 == 0 else GOLD)
    # chip
    rounded(draw, [cx - 28, cy - 22, cx + 28, cy + 22], PANEL, WHITE, 2, 6)
    draw.text((cx - 18, cy - 10), "UNO", fill=WHITE, font=font(16, bold=True))


def draw_bulb(draw, cx, cy):
    draw.ellipse([cx - 28, cy - 48, cx + 28, cy - 4], outline=GOLD, width=3)
    draw.ellipse([cx - 18, cy - 38, cx + 18, cy - 14], fill=(255, 220, 120, 180) if False else (80, 60, 20))
    draw.ellipse([cx - 18, cy - 38, cx + 18, cy - 14], outline=GOLD, width=2)
    draw.rectangle([cx - 12, cy - 4, cx + 12, cy + 10], outline=MINT, width=2)
    draw.line([(cx - 8, cy + 14), (cx + 8, cy + 14)], fill=MINT, width=2)
    draw.line([(cx - 6, cy + 20), (cx + 6, cy + 20)], fill=MINT, width=2)


def draw_door(draw, cx, cy):
    rounded(draw, [cx - 30, cy - 50, cx + 30, cy + 30], PANEL, MINT, 3, 8)
    draw.ellipse([cx + 14, cy - 10, cx + 22, cy - 2], fill=GOLD)
    # hinge marks
    draw.line([(cx - 30, cy - 30), (cx - 22, cy - 30)], fill=LINE, width=2)
    draw.line([(cx - 30, cy + 10), (cx - 22, cy + 10)], fill=LINE, width=2)


def draw_fan(draw, cx, cy):
    draw.ellipse([cx - 34, cy - 34, cx + 34, cy + 34], outline=MINT, width=3)
    draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=MINT)
    for ang in (0, 90, 180, 270):
        # simple blades as rounded rects around center
        if ang == 0:
            draw.ellipse([cx + 6, cy - 28, cx + 28, cy - 6], outline=MINT, width=2)
        elif ang == 90:
            draw.ellipse([cx + 6, cy + 6, cx + 28, cy + 28], outline=MINT, width=2)
        elif ang == 180:
            draw.ellipse([cx - 28, cy + 6, cx - 6, cy + 28], outline=MINT, width=2)
        else:
            draw.ellipse([cx - 28, cy - 28, cx - 6, cy - 6], outline=MINT, width=2)


def draw_pir(draw, cx, cy):
    rounded(draw, [cx - 36, cy - 28, cx + 36, cy + 28], PANEL, MINT, 3, 10)
    draw.ellipse([cx - 18, cy - 16, cx + 18, cy + 16], outline=GOLD, width=3)
    draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=GOLD)


def label(draw, text, cx, y, size=20, color=WHITE, bold=True):
    f = font(size, bold=bold)
    bbox = draw.textbbox((0, 0), text, font=f)
    tw = bbox[2] - bbox[0]
    draw.text((cx - tw / 2, y), text, fill=color, font=f)


def main():
    im = Image.new("RGB", (W, H), INK)
    draw = ImageDraw.Draw(im)

    # soft top bar
    draw.rectangle([0, 0, W, 8], fill=MINT)

    # --- Laptop ---
    lx, ly = 170, 230
    rounded(draw, [40, 70, 300, 430], (0, 36, 44), MINT, 3, 20)
    draw_laptop(draw, lx, ly - 20)
    label(draw, "Laptop", lx, 330, 24)
    label(draw, "Camera + MediaPipe", lx, 362, 16, MINT, bold=False)
    label(draw, "home_controller.py", lx, 388, 15, GOLD, bold=False)

    # --- USB arrow ---
    arrow(draw, 310, 230, 430, 230, "USB 9600")

    # --- Arduino ---
    ax, ay = 560, 230
    rounded(draw, [440, 70, 680, 430], (0, 36, 44), MINT, 3, 20)
    draw_arduino(draw, ax, ay - 10)
    label(draw, "Arduino kit", ax, 330, 24)
    label(draw, "gesture_home.ino", ax, 362, 16, MINT, bold=False)

    # --- Fan-out wires to actuators ---
    targets = [
        (820, 110, "Light", draw_bulb),
        (980, 110, "Door", draw_door),
        (820, 320, "Fan", draw_fan),
        (980, 320, "Security", draw_pir),
    ]
    # hub point on right of arduino card
    hx, hy = 690, 230
    draw.ellipse([hx - 6, hy - 6, hx + 6, hy + 6], fill=MINT)

    for tx, ty, name, icon in targets:
        # wire
        mx = (hx + tx) / 2
        draw.line([(hx, hy), (mx, hy), (mx, ty), (tx - 70, ty)], fill=MINT, width=3)
        draw.polygon(
            [(tx - 70, ty), (tx - 82, ty - 7), (tx - 82, ty + 7)],
            fill=MINT,
        )
        # actuator card
        rounded(draw, [tx - 70, ty - 70, tx + 70, ty + 70], (0, 36, 44), MINT, 3, 16)
        icon(draw, tx, ty - 8)
        label(draw, name, tx, ty + 40, 18)

    label(draw, "actuators", 900, 470, 16, MINT, bold=False)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT, "PNG")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
