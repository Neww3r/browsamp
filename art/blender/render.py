"""Blender entry point.

    Blender -b --factory-startup -P art/blender/render.py -- <target> [<target> ...] [--fast]

Targets: knob-<style>, amp-<id>, board-<pre|post>, footswitch, cab, mic-<dynamic|ribbon>,
or the groups `knobs`, `amps`, `pedals` and `cabinet`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import amps  # noqa: E402
import cab  # noqa: E402
import knobs  # noqa: E402
import pedals  # noqa: E402
import lib  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
fast = "--fast" in args
targets = [a for a in args if not a.startswith("--")] or ["knobs", "amps", "pedals", "cabinet"]

expanded = []
for t in targets:
    if t == "knobs":
        expanded += [f"knob-{s}" for s in knobs.STYLES]
    elif t == "amps":
        expanded += [f"amp-{a['id']}" for a in lib.LAYOUT["amps"]]
    elif t == "pedals":
        expanded += ["board-pre", "board-post", "footswitch"]
    elif t == "cabinet":
        expanded += ["cab", "mic-dynamic", "mic-ribbon"]
    else:
        expanded.append(t)

for t in expanded:
    print(f"[browsamp] rendering {t}", flush=True)
    if t.startswith("knob-"):
        knobs.render_style(t[5:], samples=24 if fast else 64, frames=8 if fast else None)
    elif t.startswith("amp-"):
        amps.render_amp(t[4:], samples=32 if fast else 160)
    elif t.startswith("board-"):
        pedals.render_board(t[6:], samples=32 if fast else 160)
    elif t == "footswitch":
        for pressed in (False, True):
            pedals.render_footswitch(pressed, samples=24 if fast else 64)
    elif t == "cab":
        cab.render_cab(samples=32 if fast else 160)
    elif t.startswith("mic-"):
        cab.render_mic(t[4:], samples=24 if fast else 96)
    else:
        raise SystemExit(f"unknown target {t}")
