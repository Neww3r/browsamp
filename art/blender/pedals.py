"""Pedalboard scenes (top-down): two pedals on a board, patched together, on a stage floor.
Knobs, footswitches (art/blender/switches.py) and LED glow are overlays; printing comes from
art/tex/pedal-*.png."""

import math

import bpy

import lib
from lib import box, front_plane, u, w

BOARD_Y = 1.2  # depth of the board surface (pedals stand on it, towards the camera)
ENCLOSURE_H = 0.62


def paint(name, color, flake=0.0, metallic=0.25):
    m = lib.M(name).set(Base_Color=(*color, 1), Metallic=metallic, Roughness=0.32, Coat_Weight=1.0, Coat_Roughness=0.08)
    if flake:
        vor = m.node("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = 260
        m.link(m.mapping("Object"), vor.inputs["Vector"])
        sparkle = m.math("POWER", vor.outputs["Distance"], 0.25)
        m.to("Roughness", m.math("MULTIPLY", sparkle, 0.45))
        m.to("Normal", m.bump(vor.outputs["Distance"], flake, 0.002))
    return m.mat


PAINTS = {
    "comp": lambda: paint("Comp", (0.008, 0.03, 0.17), flake=0.35, metallic=0.6),
    "od": lambda: paint("Od", (0.02, 0.13, 0.035), metallic=0.1),
    "delay": lambda: lib.mat_metal("Delay", (0.62, 0.63, 0.64), 0.32, aniso=0.6, brushed_axis="UV"),
    "reverb": lambda: paint("Reverb", (0.06, 0.01, 0.1), flake=0.35, metallic=0.6),
}


def pedal(p, chrome, rubber):
    P = lib.LAYOUT["pedal"]
    cx, cz = w(p["cx"], p["cy"])
    hw, hh = u(P["w"]) / 2, u(P["h"]) / 2
    top = BOARD_Y - ENCLOSURE_H
    body = box(f"Enclosure-{p['id']}", cx - hw, cz - hh, cx + hw, cz + hh, top, BOARD_Y, PAINTS[p["id"]](), 0.11, 6)
    body.name = p["id"]
    ink = (0.02, 0.02, 0.025) if p["id"] == "delay" else (0.92, 0.92, 0.9)
    front_plane(f"Print-{p['id']}", cx - hw + 0.02, cz - hh + 0.02, cx + hw - 0.02, cz + hh - 0.02, top - 0.0006, lib.mat_print(f"Ink-{p['id']}", lib.TEX / f"pedal-{p['id']}.png", ink, 0.4))
    # Pot nuts under every knob, LED bezel and the footswitch thread.
    for k in p["knobs"]:
        kx, kz = w(p["cx"] + k["dx"], p["cy"] + k["dy"])
        lib.cylinder("PotNut", 0.2, 0.03, top - 0.03, kx, kz, chrome, verts=6, bevel_w=0.008)
    lx, lz = w(p["cx"] + P["led"]["dx"], p["cy"] + P["led"]["dy"])
    lib.cylinder("LedBezel", 0.12, 0.05, top - 0.05, lx, lz, chrome, bevel_w=0.015)
    lens = lib.M("Lens").set(Base_Color=(0.5, 0.02, 0.01, 1), Roughness=0.15, Transmission_Weight=0.6, Coat_Weight=1)
    lib.cylinder("LedLens", 0.075, 0.07, top - 0.08, lx, lz, lens.mat, bevel_w=0.03)
    # Jacks on the sides (input on the left, output on the right).
    for side in (-1, 1):
        jx = cx + side * (hw + 0.05)
        jz = cz + u(120)
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.16, depth=0.18, location=(jx, BOARD_Y - 0.3, jz), rotation=(0, math.radians(90), 0))
        j = bpy.context.active_object
        lib._smooth(j)
        j.data.materials.append(chrome)
    # Rubber feet peeking out is invisible from the top; a soft contact shadow does the job.
    return (cx - hw - 0.14, cz + u(120)), (cx + hw + 0.14, cz + u(120))


def cable(name, pts, mat, radius=0.07):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 6
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for bp, co in zip(sp.bezier_points, pts):
        bp.co = co
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    o = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(mat)
    return o


def plug(x, z, direction, chrome, black):
    """Right-angle plug: a barrel going into the jack and a moulded black body."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.11, depth=0.32, location=(x + direction * 0.16, BOARD_Y - 0.3, z), rotation=(0, math.radians(90), 0))
    b = bpy.context.active_object
    lib._smooth(b)
    b.data.materials.append(chrome)
    box("PlugBody", x + direction * 0.3 - 0.17, z - 0.17, x + direction * 0.3 + 0.17, z + 0.17, BOARD_Y - 0.5, BOARD_Y - 0.08, black, 0.06)
    return x + direction * 0.3, z


def mat_board_surface():
    m = lib.M("Velcro").set(Base_Color=(0.012, 0.012, 0.013, 1), Roughness=0.95, Sheen_Weight=0.8, Sheen_Roughness=0.3)
    n = m.noise(m.mapping("Object"), 220, 3, 0.8)
    m.to("Normal", m.bump(n.outputs["Fac"], 0.6, 0.003))
    return m.mat


def mat_floor():
    m = lib.M("Floor")
    brick = m.node("ShaderNodeTexBrick")
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Mortar Size"].default_value = 0.006
    brick.inputs["Brick Width"].default_value = 5.0
    brick.inputs["Row Height"].default_value = 0.9
    brick.offset = 0.31
    m.link(m.mapping("Object", (1, 1, 1), (math.radians(90), 0, 0)), brick.inputs["Vector"])
    grain = m.noise(m.mapping("Object", (0.08, 1, 1)), 6, 8, 0.6, 2.0)
    col = m.ramp(grain.outputs["Fac"], [(0.3, (0.022, 0.012, 0.007)), (0.7, (0.06, 0.035, 0.02))])
    col = m.mix(m.math("MULTIPLY", brick.outputs["Color"], 0.5), col, (0.04, 0.025, 0.015))
    m.to("Base Color", m.mix(brick.outputs["Fac"], col, (0.004, 0.003, 0.002)))
    m.set(Roughness=0.45, Coat_Weight=0.4, Coat_Roughness=0.25)
    m.to("Normal", m.bump(m.math("ADD", brick.outputs["Fac"], m.math("MULTIPLY", grain.outputs["Fac"], 0.25)), 0.4, 0.04))
    return m.mat


def render_board(scene, samples=160):
    lib.reset()
    bpy.context.scene.cycles.samples = samples
    lib.canvas_camera()
    chrome = lib.mat_metal("Chrome", (0.92, 0.92, 0.93), 0.1)
    rubber = lib.mat_plastic("Rubber", (0.012, 0.012, 0.012), 0.6)
    alu = lib.mat_metal("Rail", (0.55, 0.56, 0.58), 0.3, aniso=0.6, brushed_axis="UV")

    front_plane("Floor", -14, -9, 14, 9, BOARD_Y + 0.4, mat_floor())
    bx0, bz1 = w(250, 215)
    bx1, bz0 = w(1350, 775)
    box("Board", bx0, bz0, bx1, bz1, BOARD_Y, BOARD_Y + 0.4, mat_board_surface(), 0.05)
    box("RailTop", bx0 - 0.1, bz1 - 0.05, bx1 + 0.1, bz1 + 0.3, BOARD_Y - 0.12, BOARD_Y + 0.4, alu, 0.06)
    box("RailBottom", bx0 - 0.1, bz0 - 0.3, bx1 + 0.1, bz0 + 0.05, BOARD_Y - 0.12, BOARD_Y + 0.4, alu, 0.06)

    pedals = [p for p in lib.LAYOUT["pedals"] if p["scene"] == scene]
    jacks = [pedal(p, chrome, rubber) for p in pedals]
    black = lib.mat_plastic("PlugBlack", (0.015, 0.015, 0.015), 0.4)
    cable_mat = lib.M("Cable").set(Base_Color=(0.01, 0.01, 0.012, 1), Roughness=0.45, Coat_Weight=0.3).mat
    hi, lo = BOARD_Y - 0.3, BOARD_Y - 0.08  # plug height, resting on the board
    # Input from off-board left, patch between pedals, output off-board right.
    ix, iz = plug(*jacks[0][0], -1, chrome, black)
    cable("In", [(-13, lo, iz + 3.4), (ix - 2.4, lo, iz + 0.8), (ix, hi, iz)], cable_mat)
    ax, az = plug(*jacks[0][1], 1, chrome, black)
    bx, bz = plug(*jacks[1][0], -1, chrome, black)
    cable("Patch", [(ax, hi, az), ((ax + bx) / 2, lo, az + 1.3), (bx, hi, bz)], cable_mat)
    ox, oz = plug(*jacks[1][1], 1, chrome, black)
    cable("Out", [(ox, hi, oz), (ox + 2.4, lo, oz + 0.8), (13, lo, oz + 3.4)], cable_mat)

    # Glossy clear coats would mirror the full reflection card and wash the paint out.
    lib.studio(key=2.6, warmth=(1.0, 0.94, 0.86), card=0.45)
    lib.spot("Pool", (0, -6, 8), (0, BOARD_Y, 0.3), 9000, 70, 0.9, (1.0, 0.82, 0.62), 1.2)
    lib.render(lib.OUT / f"board-{scene}.png")
