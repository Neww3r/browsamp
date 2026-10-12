"""Flat placeholder art with the same names and geometry as the Blender renders.

Lets the UI run before (or without) a Blender render pass:
    python3 art/placeholders.py
"""

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "public" / "art"
L = json.loads((ROOT / "layout.json").read_text())
W, H = L["stage"]["w"], L["stage"]["h"]
FRAMES = L["frames"]
SWEEP = 300  # degrees of knob travel


def save(img: Image.Image, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    img.save(OUT / name, "WEBP", quality=88, method=6)


def rgb(c, k=1.0):
    return tuple(int(max(0, min(1, v * k)) * 255) for v in c)


def vgradient(size, top, bottom):
    w, h = size
    img = Image.new("RGB", size)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    return img


def amp_bg(a, cloth, body, panel, wall):
    img = vgradient((W, H), wall[0], wall[1])
    d = ImageDraw.Draw(img)
    d.rectangle([0, 760, W, H], fill=(28, 22, 18))
    hd = a["head"]
    x0, y0, x1, y1 = hd["x"], hd["y"], hd["x"] + hd["w"], hd["y"] + hd["h"]
    shadow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shadow).rounded_rectangle([x0 + 10, y0 + 30, x1 + 10, y1 + 30], 30, fill=180)
    img.paste((0, 0, 0), mask=shadow.filter(ImageFilter.GaussianBlur(28)))
    d.rounded_rectangle([x0, y0, x1, y1], 26, fill=body)
    d.rounded_rectangle([x0 + 40, y0 + 34, x1 - 40, y1 - 34], 14, fill=cloth)
    p = a["panel"]
    d.rounded_rectangle([p["x"], p["y"], p["x"] + p["w"], p["y"] + p["h"]], 8, fill=panel)
    d.rounded_rectangle([780, y0 - 34, 820 + 0, y0 + 4], 8, fill=(40, 30, 24))
    d.rounded_rectangle([640, y0 - 40, 960, y0 - 14], 12, fill=(48, 36, 28))
    return img


def knob_strip(name, cap, skirt, pointer, size=128, style="plain"):
    frames = []
    s = size * 4
    for f in range(FRAMES):
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        c = s / 2
        r = s * 0.44 / L["knobStrip"]["pad"]
        d.ellipse([c - r, c - r + s * 0.03, c + r, c + r + s * 0.03], fill=(0, 0, 0, 110))
        d.ellipse([c - r, c - r, c + r, c + r], fill=skirt)
        rc = r * (0.72 if style != "chicken" else 0.55)
        d.ellipse([c - rc, c - rc, c + rc, c + rc], fill=cap)
        ang = math.radians(-SWEEP / 2 + SWEEP * f / (FRAMES - 1) - 90)
        if style == "chicken":
            # pointer bar across the knob
            dx, dy = math.cos(ang), math.sin(ang)
            px, py = -dy, dx
            pts = [
                (c + dx * r * 0.98 + px * r * 0.12, c + dy * r * 0.98 + py * r * 0.12),
                (c + dx * r * 0.98 - px * r * 0.12, c + dy * r * 0.98 - py * r * 0.12),
                (c - dx * r * 0.6 - px * r * 0.22, c - dy * r * 0.6 - py * r * 0.22),
                (c - dx * r * 0.6 + px * r * 0.22, c - dy * r * 0.6 + py * r * 0.22),
            ]
            d.polygon(pts, fill=cap)
            d.line([(c, c), (c + dx * r * 0.92, c + dy * r * 0.92)], fill=pointer, width=int(s * 0.025))
        else:
            d.line([(c + math.cos(ang) * r * 0.25, c + math.sin(ang) * r * 0.25), (c + math.cos(ang) * r * 0.9, c + math.sin(ang) * r * 0.9)], fill=pointer, width=int(s * 0.04))
        frames.append(img.resize((size, size), Image.LANCZOS))
    cols = L["knobStrip"]["cols"]
    strip = Image.new("RGBA", (size * cols, size * ((FRAMES + cols - 1) // cols)))
    for i, fr in enumerate(frames):
        strip.paste(fr, ((i % cols) * size, (i // cols) * size))
    save(strip, f"knob-{name}.webp")


def board(scene):
    img = vgradient((W, H), (34, 30, 27), (16, 14, 13))
    d = ImageDraw.Draw(img)
    d.rectangle([140, 230, 1460, 760], fill=(26, 24, 22))
    P = L["pedal"]
    for p in L["pedals"]:
        if p["scene"] != scene:
            continue
        x0, y0 = p["cx"] - P["w"] / 2, p["cy"] - P["h"] / 2
        shadow = Image.new("L", (W, H), 0)
        ImageDraw.Draw(shadow).rounded_rectangle([x0 + 8, y0 + 20, x0 + P["w"] + 8, y0 + P["h"] + 20], 22, fill=200)
        img.paste((0, 0, 0), mask=shadow.filter(ImageFilter.GaussianBlur(20)))
        d.rounded_rectangle([x0, y0, x0 + P["w"], y0 + P["h"]], 20, fill=rgb(p["color"]))
    return img


def cab_bg():
    img = vgradient((W, H), (30, 26, 23), (14, 12, 11))
    d = ImageDraw.Draw(img)
    S = L["cab"]["speaker"]
    cx, cy, r = S["cx"], S["cy"], S["r"]
    d.ellipse([cx - r * 1.12, cy - r * 1.12, cx + r * 1.12, cy + r * 1.12], fill=(40, 38, 36))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(22, 21, 20))
    d.ellipse([cx - r * 0.9, cy - r * 0.9, cx + r * 0.9, cy + r * 0.9], fill=(38, 34, 30))
    d.ellipse([cx - r * 0.28, cy - r * 0.28, cx + r * 0.28, cy + r * 0.28], fill=(20, 18, 16))
    return img


def mic(name, color):
    s = 300
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if name == "dynamic":
        d.ellipse([50, 50, 250, 250], fill=(30, 30, 32))
        d.ellipse([70, 70, 230, 230], fill=color)
    else:
        d.rounded_rectangle([85, 40, 215, 260], 40, fill=(60, 50, 40))
        d.rounded_rectangle([100, 60, 200, 240], 30, fill=color)
    save(img, f"mic-{name}.webp")


def footswitch(down):
    s = 160
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([8, 8, s - 8, s - 8], fill=(150, 150, 155))
    k = 0.85 if down else 1.0
    d.ellipse([28, 28, s - 28, s - 28], fill=rgb((0.78, 0.78, 0.8), k))
    save(img, f"footswitch-{'down' if down else 'up'}.webp")


if __name__ == "__main__":
    a = L["amps"]
    save(amp_bg(a[0], (92, 60, 38), (196, 164, 104), (200, 200, 205), ((52, 38, 28), (24, 18, 14))), "amp-sunset.webp")
    save(amp_bg(a[1], (30, 28, 26), (18, 17, 16), (190, 150, 70), ((30, 24, 22), (12, 10, 10))), "amp-brixton.webp")
    save(amp_bg(a[2], (20, 21, 23), (36, 37, 40), (26, 27, 30), ((18, 20, 24), (8, 8, 10))), "amp-obsidian.webp")
    save(board("pre"), "board-pre.webp")
    save(board("post"), "board-post.webp")
    save(cab_bg(), "cab.webp")
    knob_strip("chicken", (232, 222, 196), (232, 222, 196, 0), (40, 30, 20), style="chicken")
    knob_strip("goldcap", (205, 168, 84), (20, 18, 16), (240, 230, 210))
    knob_strip("knurled", (40, 41, 44), (170, 172, 178), (235, 70, 50))
    knob_strip("pedal", (24, 24, 24), (14, 14, 14), (240, 240, 240))
    knob_strip("header", (52, 48, 44), (22, 20, 18), (224, 166, 69))
    mic("dynamic", (110, 110, 115))
    mic("ribbon", (170, 140, 90))
    footswitch(False)
    footswitch(True)
    print(f"placeholders written to {OUT}")
