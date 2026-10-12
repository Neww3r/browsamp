"""Art pipeline: textures (Pillow) → renders (Blender) → web assets in public/art.

    npm run art                      # everything
    npm run art -- knobs amp-sunset  # some targets
    npm run art -- --fast knobs      # quick low-sample preview renders
    npm run art -- --pack            # only re-pack existing renders
"""

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
PUBLIC = ROOT.parent / "public" / "art"
BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"
L = json.loads((ROOT / "layout.json").read_text())


def run_blender(targets, fast):
    cmd = [BLENDER, "-b", "--factory-startup", "-P", str(ROOT / "blender" / "render.py"), "--", *targets]
    if fast:
        cmd.append("--fast")
    print(" ".join(cmd), flush=True)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    errors = [l for l in proc.stdout.splitlines() + proc.stderr.splitlines() if "Error" in l or "Traceback" in l or "[browsamp]" in l]
    print("\n".join(errors))
    if proc.returncode != 0:
        print(proc.stdout[-4000:], proc.stderr[-4000:])
        raise SystemExit("Blender failed")


# Scene backgrounds cover the extended canvas; one file per width, the UI picks with srcset.
BG_SCALES = (1, 1.5, 2, 3)
# Overlays (knob sheets, switches, mics) come in @1, @2 and @3 pixel densities.
OVERLAY_SCALES = (1, 2, 3)
RENDER_SCALE = 3  # must match lib.SCALE


def resized(img, factor):
    if abs(factor - 1) < 1e-6:
        return img
    return img.resize((max(1, round(img.width * factor)), max(1, round(img.height * factor))), Image.LANCZOS)


def save_webp(img, name, quality):
    PUBLIC.mkdir(parents=True, exist_ok=True)
    if img.mode == "RGBA" and img.getchannel("A").getextrema() == (255, 255):
        img = img.convert("RGB")
    img.save(PUBLIC / name, "WEBP", quality=quality, method=6, alpha_quality=95)


def pack_background(name):
    src = Image.open(OUT / f"{name}.png")
    canvas_w = L["canvas"]["w"]
    for k in BG_SCALES:
        w = round(canvas_w * k)
        save_webp(resized(src, w / src.width), f"{name}-{w}.webp", 84 if k > 2 else 86)
    print(f"packed {name} ({src.width}px source)")


def pack_overlay(name):
    src = Image.open(OUT / f"{name}.png")
    for k in OVERLAY_SCALES:
        save_webp(resized(src, k / RENDER_SCALE), f"{name}@{k}.webp", 90)
    print(f"packed {name}")


def pack_knob(style):
    frames = sorted((OUT / f"knob-{style}").glob("*.png"))
    if not frames:
        return
    cols = L["knobStrip"]["cols"]
    n = L["frames"]
    # Fast previews have fewer frames: repeat them so the grid always holds L["frames"].
    picks = [Image.open(frames[min(len(frames) - 1, i * len(frames) // n)]) for i in range(n)]
    fw = picks[0].width
    rows = (n + cols - 1) // cols
    for k in OVERLAY_SCALES:
        f = round(fw * k / RENDER_SCALE)
        sheet = Image.new("RGBA", (f * cols, f * rows), (0, 0, 0, 0))
        for i, fr in enumerate(picks):
            sheet.paste(fr.resize((f, f), Image.LANCZOS), ((i % cols) * f, (i // cols) * f))
        save_webp(sheet, f"knob-{style}@{k}.webp", 90)
    print(f"packed knob-{style} ({len(frames)} renders, {fw}px frames)")


BACKGROUNDS = ("amp-", "board-", "cab")


def pack_all():
    for d in sorted(OUT.glob("knob-*")):
        if d.is_dir():
            pack_knob(d.name[5:])
    for f in sorted(OUT.glob("*.png")):
        if f.stem.startswith(BACKGROUNDS):
            pack_background(f.stem)
        else:
            pack_overlay(f.stem)


def main():
    args = sys.argv[1:]
    fast = "--fast" in args
    targets = [a for a in args if not a.startswith("--")]
    if "--pack" not in args:
        subprocess.run([sys.executable, str(ROOT / "textures.py")], check=True)
        run_blender(targets, fast)
    pack_all()


if __name__ == "__main__":
    main()
