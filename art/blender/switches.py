"""Overlay switches, rendered like the knobs (tilted, transparent, own contact shadow):
pedal footswitches (up / pressed) and the amp power toggle (on / off)."""

import math

import bpy

import knobs
import lib


def _chrome(rough=0.06):
    return lib.M("Chrome").set(Base_Color=(0.93, 0.93, 0.95, 1), Metallic=1.0, Roughness=rough).mat


def render_footswitch(pressed, samples=64):
    """Archetype-style stomp switch: spun washer, knurled ring nut and a satin-chrome cap."""
    r = lib.LAYOUT["pedal"]["footswitch"]["r"]
    knobs.setup_object_render(r * 2, lib.LAYOUT["knobStrip"]["pad"], samples)
    R = lib.u(r)
    chrome = _chrome(0.14)
    knurl = knobs.mat_knurl("Ring", (0.84, 0.84, 0.86), 0.2, 54)
    spun = knobs.mat_spun("Washer", (0.8, 0.8, 0.82), 0.22)
    travel = 0.05 if pressed else 0.0
    knobs.lathe("Washer", knobs.rounded([(0, -0.025), (R * 0.98, -0.025), (R * 1.0, 0.0)], 0.01), spun)
    ring = knobs.rounded([(0, -0.11), (R * 0.8, -0.11), (R * 0.84, -0.08), (R * 0.84, -0.025)], 0.015)
    knobs.lathe("Ring", ring, knurl)
    cap_r, cap_h = R * 0.6, 0.26
    cap = [(cap_r * math.sin(t * math.pi / 2 / 14), -0.11 - cap_h + travel + cap_h * 0.55 * (1 - math.cos(t * math.pi / 2 / 14))) for t in range(15)]
    cap += [(cap_r, -0.11)]
    knobs.lathe("Cap", [(0, cap[0][1])] + cap[1:], chrome)
    lib.render(lib.OUT / f"footswitch-{'down' if pressed else 'up'}.png")


TOGGLE_PX = 110  # rendered box, stage pixels (room for the lever in both positions)


def render_toggle(on, samples=64):
    """Classic bat-handle toggle: hex nut, threaded bushing and a chrome lever."""
    knobs.setup_object_render(TOGGLE_PX, 1.0, samples)
    chrome = _chrome()
    spun = knobs.mat_spun("Bushing", (0.82, 0.82, 0.84), 0.22)
    knobs.lathe("Nut", [(0, -0.07), (0.15, -0.07), (0.16, -0.05), (0.16, 0.0)], chrome, segments=6)
    knobs.lathe("Bushing", knobs.rounded([(0, -0.17), (0.075, -0.17), (0.08, -0.15), (0.08, -0.07)], 0.01), spun)
    # Lever pivots in the bushing and leans up (on) or down (off), towards the viewer.
    lever = bpy.data.objects.new("Lever", None)
    bpy.context.collection.objects.link(lever)
    lever.location = (0, -0.15, 0)
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=0.032, radius2=0.05, depth=0.42, location=(0, 0, 0.21))
    bat = bpy.context.active_object
    lib._smooth(bat, 60)
    bat.data.materials.append(chrome)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.052, segments=32, ring_count=16, location=(0, 0, 0.42))
    tip = bpy.context.active_object
    lib._smooth(tip, 80)
    tip.data.materials.append(chrome)
    for o in (bat, tip):
        o.parent = lever
    # Lever axis is +Z; rotating by θ about X sends it to (0, -sin θ, cos θ): 30° leans it up
    # towards the camera (on), 150° down towards the camera (off).
    lever.rotation_euler = (math.radians(30 if on else 150), 0, 0)
    lib.render(lib.OUT / f"toggle-{'on' if on else 'off'}.png")
