"""Screen-printing and logo masks (Pillow), consumed by the Blender scenes as image textures.

Everything is drawn at DPR pixels per stage pixel in the coordinate space of the object it
is printed on, using the same fonts as the web UI (from node_modules/@fontsource).
"""

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
TEX = ROOT / "tex"
FONTS = ROOT.parent / "node_modules" / "@fontsource"
L = json.loads((ROOT / "layout.json").read_text())
DPR = 2
SWEEP = 300

LABELS = {
    "gain": "Gain",
    "bass": "Bass",
    "mid": "Middle",
    "treble": "Treble",
    "presence": "Presence",
    "resonance": "Resonance",
    "master": "Master",
}


def font(family, weight, size_px):
    return ImageFont.truetype(str(FONTS / family / "files" / f"{family}-latin-{weight}-normal.woff"), int(size_px * DPR))


def text_center(d, xy, text, f, fill, tracking=0.0):
    """Draws text centred on xy, with optional letter spacing (in em)."""
    if not tracking:
        d.text(xy, text, font=f, fill=fill, anchor="mm")
        return
    widths = [f.getlength(c) for c in text]
    extra = f.size * tracking
    total = sum(widths) + extra * (len(text) - 1)
    x = xy[0] - total / 2
    for c, cw in zip(text, widths):
        d.text((x + cw / 2, xy[1]), c, font=f, fill=fill, anchor="mm")
        x += cw + extra


def knob_scale(d, cx, cy, radius, style, f_num, ink):
    """Printed graduation around a knob: numbers or ticks over the same 300° sweep."""
    def at(t, r):
        a = math.radians(-SWEEP / 2 + SWEEP * t - 90)
        return cx + math.cos(a) * r, cy + math.sin(a) * r

    if style == "numbers12":
        for i in range(12):
            text_center(d, at(i / 11, radius), str(i + 1), f_num, ink)
    elif style == "ticks":
        for i in range(11):
            t = i / 10
            long = i in (0, 5, 10)
            p0, p1 = at(t, radius - (9 if long else 5) * DPR), at(t, radius + 2 * DPR)
            d.line([p0, p1], fill=ink, width=int((2.2 if long else 1.5) * DPR))
    elif style == "dots":
        for i in range(11):
            x, y = at(i / 10, radius)
            r = (2.6 if i in (0, 10) else 1.7) * DPR
            d.ellipse([x - r, y - r, x + r, y + r], fill=ink)


AMP_PRINT = {
    "sunset": dict(font=("josefin-sans", 600, 13.5), tracking=0.16, ink=(24, 20, 16, 255), scale="numbers12", num=("josefin-sans", 600, 10), radius=55, frame=None),
    "brixton": dict(font=("oswald", 500, 14), tracking=0.18, ink=(16, 12, 6, 255), scale="dots", num=None, radius=50, frame=(16, 12, 6, 255)),
    "obsidian": dict(font=("oswald", 500, 13), tracking=0.3, ink=(214, 218, 224, 255), scale="ticks", num=None, radius=52, frame=None),
}


def panel_print(amp):
    spec = AMP_PRINT[amp["id"]]
    p = amp["panel"]
    img = Image.new("RGBA", (p["w"] * DPR, p["h"] * DPR), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font(*spec["font"])
    f_num = font(*spec["num"]) if spec["num"] else None
    for k in amp["knobs"]:
        cx, cy = (k["x"] - p["x"]) * DPR, (amp["knobY"] - p["y"]) * DPR
        text_center(d, (cx, cy + amp["labelDy"] * DPR), LABELS[k["key"]].upper(), f, spec["ink"], spec["tracking"])
        knob_scale(d, cx, cy, spec["radius"] * DPR, spec["scale"], f_num, spec["ink"])
    if spec["frame"]:
        m = 8 * DPR
        d.rounded_rectangle([m, m, img.width - m, img.height - m], radius=6 * DPR, outline=spec["frame"], width=int(2.5 * DPR))
    # Legend under the power toggle (the toggle itself is an overlay).
    f_small = font(*spec["font"][:2], 10.5)
    pw = amp["power"]
    text_center(d, ((pw["x"] - p["x"]) * DPR, (amp["knobY"] + amp["labelDy"] - p["y"]) * DPR), "POWER", f_small, spec["ink"], spec["tracking"])
    save_rgba(img, f"panel-{amp['id']}.png")


def hex_grille(w_px, h_px, cell=13, hole=0.72, name="grille-hex.png"):
    """Perforated steel: opaque metal with hexagonal holes (alpha 0)."""
    img = Image.new("RGBA", (w_px * DPR, h_px * DPR), (255, 255, 255, 255))
    d = ImageDraw.Draw(img)
    c = cell * DPR
    r = c * hole / math.sqrt(3)
    row = 0
    y = 0.0
    while y < img.height + c:
        x = (c / 2) if row % 2 else 0.0
        while x < img.width + c:
            pts = [(x + r * math.cos(math.radians(60 * i + 30)), y + r * math.sin(math.radians(60 * i + 30))) for i in range(6)]
            d.polygon(pts, fill=(255, 255, 255, 0))
            x += c
        y += c * math.sqrt(3) / 2
        row += 1
    save_rgba(img, name)


PEDAL_LABELS = {
    "compLevel": "Level", "compSustain": "Sustain", "compAttack": "Attack", "compBlend": "Blend",
    "odDrive": "Drive", "odLevel": "Level", "odTone": "Tone",
    "delayMix": "Mix", "delayTime": "Time", "delayFb": "Repeats", "delayTone": "Tone",
    "reverbMix": "Mix", "reverbDecay": "Decay", "reverbDamp": "Damping", "reverbPredelay": "Pre-delay",
}

PEDAL_INK = {
    "comp": (236, 240, 250, 255),
    "od": (240, 236, 218, 255),
    "delay": (22, 24, 28, 255),
    "reverb": (236, 226, 246, 255),
}


def pedal_print(p):
    P = L["pedal"]
    ink = PEDAL_INK[p["id"]]
    w, h = P["w"] * DPR, P["h"] * DPR
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    to = lambda dx, dy: ((P["w"] / 2 + dx) * DPR, (P["h"] / 2 + dy) * DPR)
    text_center(d, to(P["name"]["dx"], P["name"]["dy"]), p["name"].upper(), font("barlow", 600, 25), ink, 0.12)
    lf = font("barlow-semi-condensed", 600, 11)
    for k in p["knobs"]:
        text_center(d, to(k["dx"], k["dy"] - P["knobSize"] / 2 - 11), PEDAL_LABELS[k["key"]].upper(), lf, ink, 0.1)
    m = 14 * DPR
    d.rounded_rectangle([m, m, w - m, h - m], radius=12 * DPR, outline=ink[:3] + (90,), width=int(1.2 * DPR))
    save_rgba(img, f"pedal-{p['id']}.png")


def save_rgba(img, name):
    TEX.mkdir(parents=True, exist_ok=True)
    img.save(TEX / name)


def main():
    for amp in L["amps"]:
        panel_print(amp)
    hex_grille(1170, 235)
    hex_grille(1230, 600, name="grille-hex-cab.png")
    for p in L["pedals"]:
        pedal_print(p)
    print(f"textures written to {TEX}")


if __name__ == "__main__":
    main()
