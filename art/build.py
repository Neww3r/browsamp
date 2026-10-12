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


def pack_knob(style):
    frames = sorted((OUT / f"knob-{style}").glob("*.png"))
    if not frames:
        return
    cols = L["knobStrip"]["cols"]
    first = Image.open(frames[0])
    fw, fh = first.size
    # Fast previews have fewer frames: repeat them so the grid always holds L["frames"].
    n = L["frames"]
    picks = [frames[min(len(frames) - 1, i * len(frames) // n)] for i in range(n)]
    rows = (n + cols - 1) // cols
    sheet = Image.new("RGBA", (fw * cols, fh * rows), (0, 0, 0, 0))
    for i, f in enumerate(picks):
        sheet.paste(Image.open(f), ((i % cols) * fw, (i // cols) * fh))
    PUBLIC.mkdir(parents=True, exist_ok=True)
    sheet.save(PUBLIC / f"knob-{style}.webp", "WEBP", quality=90, method=6, alpha_quality=95)
    print(f"packed knob-{style}.webp ({len(frames)} renders, {fw}px frames)")


def pack_image(name, quality=86):
    src = OUT / f"{name}.png"
    if not src.exists():
        return
    PUBLIC.mkdir(parents=True, exist_ok=True)
    img = Image.open(src)
    if img.mode == "RGBA" and img.getchannel("A").getextrema() == (255, 255):
        img = img.convert("RGB")
    img.save(PUBLIC / f"{name}.webp", "WEBP", quality=quality, method=6)
    print(f"packed {name}.webp {img.size}")


def pack_all():
    for d in sorted(OUT.glob("knob-*")):
        if d.is_dir():
            pack_knob(d.name[5:])
    for f in sorted(OUT.glob("*.png")):
        pack_image(f.stem)


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
