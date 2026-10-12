"""Flat placeholder art with the same names and geometry as the Blender renders, for working
on the UI without Blender. Labels, graduations and logos come from art/textures.py, so the
placeholders carry the same printing as the real renders.

    python3 art/placeholders.py           # only fills in missing files in public/art
    python3 art/placeholders.py --force   # replaces everything, real renders included
    python3 art/placeholders.py --out DIR # writes to another folder (e.g. to preview them)
"""

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import textures

ROOT = Path(__file__).resolve().parent
OUT = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else ROOT.parent / "public" / "art"
TEX = ROOT / "tex"
L = json.loads((ROOT / "layout.json").read_text())
W, H = L["stage"]["w"], L["stage"]["h"]
FRAMES = L["frames"]
PAD = L["knobStrip"]["pad"]
COLS = L["knobStrip"]["cols"]
SWEEP = 300  # degrees of knob travel, as in art/blender/knobs.py
FORCE = "--force" in sys.argv
written, skipped = [], []


def save(img: Image.Image, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / name).exists() and not FORCE:
        skipped.append(name)
        return
    img.save(OUT / name, "WEBP", quality=88, method=6)
    written.append(name)


def tex(name: str, scale: float = 1 / textures.DPR) -> Image.Image:
    """A texture from art/tex, brought back to stage pixels."""
    img = Image.open(TEX / name)
    return img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)


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


def drop_shadow(img, box, radius, blur, offset=(8, 20), alpha=190):
    shadow = Image.new("L", img.size, 0)
    x0, y0, x1, y1 = box
    ImageDraw.Draw(shadow).rounded_rectangle([x0 + offset[0], y0 + offset[1], x1 + offset[0], y1 + offset[1]], radius, fill=alpha)
    img.paste((0, 0, 0), mask=shadow.filter(ImageFilter.GaussianBlur(blur)))


def amp_bg(a, body, cloth, panel, wall):
    img = vgradient((W, H), *wall)
    d = ImageDraw.Draw(img)
    hd = a["head"]
    x0, y0, x1, y1 = hd["x"], hd["y"], hd["x"] + hd["w"], hd["y"] + hd["h"]
    d.rectangle([130, 745, 1470, H], fill=body)
    d.rectangle([185, 800, 1415, H], fill=cloth)
    drop_shadow(img, (x0, y0, x1, y1), 26, 28, (10, 30))
    d.rounded_rectangle([x0, y0, x1, y1], 18, fill=body)
    g, p = a["grille"], a["panel"]
    d.rectangle([g["x"], g["y"], g["x"] + g["w"], g["y"] + g["h"]], fill=cloth)
    d.rectangle([p["x"], p["y"], p["x"] + p["w"], p["y"] + p["h"]], fill=panel)
    d.rounded_rectangle([610, y0 - 22, 990, y0 + 2], 8, fill=(40, 30, 24))
    img = img.convert("RGBA")
    img.alpha_composite(tex(f"panel-{a['id']}.png"), (p["x"], p["y"]))
    logo = tex(f"logo-{a['id']}.png")
    img.alpha_composite(logo, (a["logo"]["x"] - logo.width // 2, a["logo"]["y"] - logo.height // 2))
    j = a["jewel"]
    ImageDraw.Draw(img).ellipse([j["x"] - 17, j["y"] - 17, j["x"] + 17, j["y"] + 17], fill=(150, 20, 15) if a["id"] != "obsidian" else (20, 60, 170))
    return img.convert("RGB")


def board(scene):
    img = vgradient((W, H), (44, 32, 24), (20, 15, 12))
    d = ImageDraw.Draw(img)
    d.rectangle([250, 215, 1350, 775], fill=(20, 20, 21))
    for y in (205, 765):
        d.rectangle([240, y, 1360, y + 22], fill=(150, 152, 156))
    P = L["pedal"]
    img = img.convert("RGBA")
    for p in L["pedals"]:
        if p["scene"] != scene:
            continue
        x0, y0 = p["cx"] - P["w"] // 2, p["cy"] - P["h"] // 2
        box = (x0, y0, x0 + P["w"], y0 + P["h"])
        drop_shadow(img, box, 20, 20)
        ImageDraw.Draw(img).rounded_rectangle(box, 20, fill=rgb(p["color"]))
        img.alpha_composite(tex(f"pedal-{p['id']}.png"), (x0, y0))
        lx, ly = p["cx"] + P["led"]["dx"], p["cy"] + P["led"]["dy"]
        ImageDraw.Draw(img).ellipse([lx - 8, ly - 8, lx + 8, ly + 8], fill=(120, 20, 15))
    return img.convert("RGB")


def cab_bg():
    img = vgradient((W, H), (34, 33, 32), (14, 14, 14))
    d = ImageDraw.Draw(img)
    S = L["cab"]["speaker"]
    cx, cy, r = S["cx"], S["cy"], S["r"]
    for k, col in ((1.18, (18, 18, 18)), (1.16, (46, 46, 48)), (1.0, (30, 29, 28)), (0.92, (58, 54, 50)), (0.29, (36, 34, 32))):
        d.ellipse([cx - r * k, cy - r * k, cx + r * k, cy + r * k], fill=col)
    for i in range(8):
        a = 2 * math.pi * (i + 0.5) / 8
        bx, by = cx + math.cos(a) * r * 1.1, cy + math.sin(a) * r * 1.1
        d.ellipse([bx - 9, by - 9, bx + 9, by + 9], fill=(190, 190, 194))
    return img


def knob_strip(name, size_px, cap, skirt, pointer, chicken=False):
    """One frame per value, laid out in a COLS-wide grid, with room for the shadow (PAD)."""
    fs = round(size_px * PAD * 2)
    frames = []
    for f in range(FRAMES):
        s = fs * 4
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        c, r = s / 2, s / 2 / PAD
        d.ellipse([c - r + s * 0.03, c - r + s * 0.05, c + r + s * 0.03, c + r + s * 0.05], fill=(0, 0, 0, 120))
        d.ellipse([c - r, c - r, c + r, c + r], fill=skirt)
        rc = r * (0.62 if chicken else 0.72)
        d.ellipse([c - rc, c - rc, c + rc, c + rc], fill=cap)
        ang = math.radians(-SWEEP / 2 + SWEEP * f / (FRAMES - 1) - 90)
        dx, dy = math.cos(ang), math.sin(ang)
        d.line([(c + dx * r * 0.2, c + dy * r * 0.2), (c + dx * r * 0.9, c + dy * r * 0.9)], fill=pointer, width=int(s * 0.03))
        frames.append(img.resize((fs, fs), Image.LANCZOS))
    sheet = Image.new("RGBA", (fs * COLS, fs * math.ceil(FRAMES / COLS)))
    for i, fr in enumerate(frames):
        sheet.paste(fr, ((i % COLS) * fs, (i // COLS) * fs))
    save(sheet, f"knob-{name}.webp")


def mic(name, body, head):
    """Same frame as the renders: 320x360 stage px, capsule 34 px above the bottom centre,
    body leaning up and to the right."""
    w, h, tip = 320 * 2, 360 * 2, 34 * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x0, y0 = w / 2, h - tip
    lean = math.radians(28)
    x1, y1 = x0 + math.sin(lean) * 560, y0 - math.cos(lean) * 560
    d.line([(x0, y0), (x1, y1)], fill=body, width=64)
    d.line([(x0, y0), (x0 + math.sin(lean) * 110, y0 - math.cos(lean) * 110)], fill=head, width=76)
    save(img, f"mic-{name}.webp")


def footswitch(down):
    r = L["pedal"]["footswitch"]["r"]
    s = round(r * 2 * PAD * 2)
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c, rr = s / 2, s / 2 / PAD
    d.ellipse([c - rr + 4, c - rr + 8, c + rr + 4, c + rr + 8], fill=(0, 0, 0, 110))
    d.ellipse([c - rr, c - rr, c + rr, c + rr], fill=(150, 150, 155))
    k = 0.8 if down else 1.0
    d.ellipse([c - rr * 0.55, c - rr * 0.55, c + rr * 0.55, c + rr * 0.55], fill=rgb((0.85, 0.85, 0.88), k))
    save(img, f"footswitch-{'down' if down else 'up'}.webp")


if __name__ == "__main__":
    textures.main()
    a = {x["id"]: x for x in L["amps"]}
    save(amp_bg(a["sunset"], (176, 132, 64), (70, 34, 22), (200, 200, 205), ((70, 44, 26), (26, 16, 10))), "amp-sunset.webp")
    save(amp_bg(a["brixton"], (18, 17, 16), (24, 23, 22), (196, 152, 72), ((50, 24, 18), (14, 10, 9))), "amp-brixton.webp")
    save(amp_bg(a["obsidian"], (30, 31, 34), (60, 18, 12), (16, 16, 18), ((22, 26, 34), (8, 8, 10))), "amp-obsidian.webp")
    save(board("pre"), "board-pre.webp")
    save(board("post"), "board-post.webp")
    save(cab_bg(), "cab.webp")
    knob_strip("chicken", 84, (226, 214, 186), (214, 202, 174), (40, 30, 20), chicken=True)
    knob_strip("goldcap", 84, (205, 168, 84), (20, 18, 16), (30, 22, 10))
    knob_strip("knurled", 84, (30, 31, 34), (196, 198, 204), (235, 70, 50))
    knob_strip("pedal", 66, (26, 26, 26), (14, 14, 14), (240, 240, 240))
    knob_strip("header", 58, (180, 182, 186), (24, 22, 20), (240, 160, 60))
    mic("dynamic", (24, 24, 26), (70, 70, 74))
    mic("ribbon", (190, 186, 176), (150, 146, 136))
    footswitch(False)
    footswitch(True)
    print(f"{len(written)} written, {len(skipped)} kept (use --force to replace them) in {OUT}")
