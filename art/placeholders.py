"""Flat placeholder art with the same names, sizes and geometry as the Blender renders, for
working on the UI without Blender. Printing (labels, graduations) comes from art/textures.py.

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
C = L["canvas"]
FRAMES = L["frames"]
PAD = L["knobStrip"]["pad"]
COLS = L["knobStrip"]["cols"]
SWEEP = 300  # degrees of knob travel, as in art/blender/knobs.py
BG_SCALES = (1, 1.5, 2, 3)  # as in art/build.py
OVERLAY_SCALES = (1, 2, 3)
FORCE = "--force" in sys.argv
written, skipped = [], []


def save(img: Image.Image, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / name).exists() and not FORCE:
        skipped.append(name)
        return
    img.save(OUT / name, "WEBP", quality=86, method=4)
    written.append(name)


def save_background(img: Image.Image, name: str) -> None:
    """img covers the canvas at 1 px per stage px; every srcset width is written."""
    for k in BG_SCALES:
        w = round(C["w"] * k)
        save(img.resize((w, round(C["h"] * k)), Image.LANCZOS) if k != 1 else img, f"{name}-{w}.webp")


def save_overlay(img_3x: Image.Image, name: str) -> None:
    for k in OVERLAY_SCALES:
        f = k / 3
        save(img_3x.resize((max(1, round(img_3x.width * f)), max(1, round(img_3x.height * f))), Image.LANCZOS), f"{name}@{k}.webp")


def tex(name: str) -> Image.Image:
    """A texture from art/tex, brought back to stage pixels."""
    img = Image.open(TEX / name)
    return img.resize((round(img.width / textures.DPR), round(img.height / textures.DPR)), Image.LANCZOS)


def at(x, y):
    """Stage coordinates → canvas image coordinates."""
    return x - C["x"], y - C["y"]


def rect(r, dx=0, dy=0):
    x0, y0 = at(r["x"], r["y"])
    return [x0 + dx, y0 + dy, x0 + r["w"] - dx, y0 + r["h"] - dy]


def rgb(c, k=1.0):
    return tuple(int(max(0, min(1, v * k)) * 255) for v in c)


def vgradient(top, bottom):
    img = Image.new("RGB", (C["w"], C["h"]))
    d = ImageDraw.Draw(img)
    for y in range(C["h"]):
        t = y / (C["h"] - 1)
        d.line([(0, y), (C["w"], y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    return img


def drop_shadow(img, box, radius, blur, offset=(8, 20), alpha=190):
    shadow = Image.new("L", img.size, 0)
    x0, y0, x1, y1 = box
    ImageDraw.Draw(shadow).rounded_rectangle([x0 + offset[0], y0 + offset[1], x1 + offset[0], y1 + offset[1]], radius, fill=alpha)
    img.paste((0, 0, 0), mask=shadow.filter(ImageFilter.GaussianBlur(blur)))


def amp_bg(a, body, cloth, panel, wall):
    img = vgradient(*wall)
    d = ImageDraw.Draw(img)
    d.rectangle([*at(130, 745), *at(1470, C["y"] + C["h"])], fill=body)
    d.rectangle([*at(185, 800), *at(1415, C["y"] + C["h"])], fill=cloth)
    box = rect(a["head"])
    drop_shadow(img, box, 26, 28, (10, 30))
    d.rounded_rectangle(box, 18, fill=body)
    d.rectangle(rect(a["grille"]), fill=cloth)
    d.rectangle(rect(a["panel"]), fill=panel)
    img = img.convert("RGBA")
    img.alpha_composite(tex(f"panel-{a['id']}.png"), at(a["panel"]["x"], a["panel"]["y"]))
    jx, jy = at(a["jewel"]["x"], a["jewel"]["y"])
    ImageDraw.Draw(img).ellipse([jx - 17, jy - 17, jx + 17, jy + 17], fill=(150, 20, 15) if a["id"] != "obsidian" else (20, 60, 170))
    return img.convert("RGB")


def board(scene):
    img = vgradient((44, 32, 24), (20, 15, 12))
    d = ImageDraw.Draw(img)
    d.rectangle([*at(250, 215), *at(1350, 775)], fill=(20, 20, 21))
    for y in (205, 765):
        d.rectangle([*at(240, y), *at(1360, y + 22)], fill=(150, 152, 156))
    P = L["pedal"]
    img = img.convert("RGBA")
    for p in L["pedals"]:
        if p["scene"] != scene:
            continue
        x0, y0 = at(p["cx"] - P["w"] // 2, p["cy"] - P["h"] // 2)
        box = (x0, y0, x0 + P["w"], y0 + P["h"])
        drop_shadow(img, box, 20, 20)
        ImageDraw.Draw(img).rounded_rectangle(box, 20, fill=rgb(p["color"]))
        img.alpha_composite(tex(f"pedal-{p['id']}.png"), (x0, y0))
        lx, ly = at(p["cx"] + P["led"]["dx"], p["cy"] + P["led"]["dy"])
        ImageDraw.Draw(img).ellipse([lx - 8, ly - 8, lx + 8, ly + 8], fill=(120, 20, 15))
    return img.convert("RGB")


def cab_bg():
    img = vgradient((34, 33, 32), (14, 14, 14))
    d = ImageDraw.Draw(img)
    S = L["cab"]["speaker"]
    cx, cy = at(S["cx"], S["cy"])
    r = S["r"]
    for k, col in ((1.18, (18, 18, 18)), (1.16, (46, 46, 48)), (1.0, (30, 29, 28)), (0.92, (58, 54, 50)), (0.29, (36, 34, 32))):
        d.ellipse([cx - r * k, cy - r * k, cx + r * k, cy + r * k], fill=col)
    for i in range(8):
        a = 2 * math.pi * (i + 0.5) / 8
        bx, by = cx + math.cos(a) * r * 1.1, cy + math.sin(a) * r * 1.1
        d.ellipse([bx - 9, by - 9, bx + 9, by + 9], fill=(190, 190, 194))
    return img


def knob_sheet(name, size_px, cap, skirt, pointer):
    """One frame per value, laid out in a COLS-wide grid, with room for the shadow (PAD)."""
    fs = round(size_px * PAD * 3)
    sheet = Image.new("RGBA", (fs * COLS, fs * math.ceil(FRAMES / COLS)))
    for f in range(FRAMES):
        s = fs * 2
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        c, r = s / 2, s / 2 / PAD
        d.ellipse([c - r + s * 0.03, c - r + s * 0.05, c + r + s * 0.03, c + r + s * 0.05], fill=(0, 0, 0, 120))
        d.ellipse([c - r, c - r, c + r, c + r], fill=skirt)
        rc = r * 0.7
        d.ellipse([c - rc, c - rc, c + rc, c + rc], fill=cap)
        ang = math.radians(-SWEEP / 2 + SWEEP * f / (FRAMES - 1) - 90)
        dx, dy = math.cos(ang), math.sin(ang)
        d.line([(c + dx * r * 0.2, c + dy * r * 0.2), (c + dx * r * 0.9, c + dy * r * 0.9)], fill=pointer, width=int(s * 0.03))
        sheet.paste(img.resize((fs, fs), Image.LANCZOS), ((f % COLS) * fs, (f // COLS) * fs))
    save_overlay(sheet, f"knob-{name}")


def disc(size_px, colors, travel=0):
    s = round(size_px * 3)
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = s / 2
    for k, col in colors:
        r = c * k
        d.ellipse([c - r, c - r + travel, c + r, c + r + travel], fill=col)
    return img


def toggle(on):
    s = 110 * 3
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = s / 2
    d.ellipse([c - 30, c - 30, c + 30, c + 30], fill=(200, 200, 205))
    d.line([(c, c), (c, c - 120 if on else c + 120)], fill=(225, 225, 230), width=22)
    return img


def mic(body, head):
    """Same frame as the renders: 320x360 stage px, capsule 34 px above the bottom centre,
    body leaning up and to the right."""
    w, h, tip = 320 * 3, 360 * 3, 34 * 3
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x0, y0 = w / 2, h - tip
    lean = math.radians(28)
    d.line([(x0, y0), (x0 + math.sin(lean) * 840, y0 - math.cos(lean) * 840)], fill=body, width=96)
    d.line([(x0, y0), (x0 + math.sin(lean) * 160, y0 - math.cos(lean) * 160)], fill=head, width=114)
    return img


if __name__ == "__main__":
    textures.main()
    a = {x["id"]: x for x in L["amps"]}
    save_background(amp_bg(a["sunset"], (176, 132, 64), (70, 34, 22), (200, 200, 205), ((70, 44, 26), (26, 16, 10))), "amp-sunset")
    save_background(amp_bg(a["brixton"], (18, 17, 16), (24, 23, 22), (196, 152, 72), ((50, 24, 18), (14, 10, 9))), "amp-brixton")
    save_background(amp_bg(a["obsidian"], (30, 31, 34), (60, 18, 12), (16, 16, 18), ((22, 26, 34), (8, 8, 10))), "amp-obsidian")
    save_background(board("pre"), "board-pre")
    save_background(board("post"), "board-post")
    save_background(cab_bg(), "cab")
    knob_sheet("clean", 84, (214, 214, 218), (20, 20, 22), (30, 30, 30))
    knob_sheet("crunch", 84, (205, 168, 84), (20, 18, 16), (30, 22, 10))
    knob_sheet("highgain", 84, (24, 24, 26), (196, 198, 204), (235, 70, 50))
    knob_sheet("pedal", 66, (26, 26, 26), (14, 14, 14), (240, 240, 240))
    knob_sheet("header", 58, (180, 182, 186), (120, 122, 126), (240, 160, 60))
    r = L["pedal"]["footswitch"]["r"] * 2 * PAD
    for down in (False, True):
        save_overlay(disc(r, [(0.66, (170, 170, 175)), (0.4, (225, 225, 230) if not down else (190, 190, 195))]), f"footswitch-{'down' if down else 'up'}")
    for on in (False, True):
        save_overlay(toggle(on), f"toggle-{'on' if on else 'off'}")
    save_overlay(mic((24, 24, 26), (70, 70, 74)), "mic-dynamic")
    save_overlay(mic((190, 186, 176), (150, 146, 136)), "mic-ribbon")
    print(f"{len(written)} written, {len(skipped)} kept (use --force to replace them) in {OUT}")
