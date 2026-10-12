"""Knob models and their filmstrips.

Each knob is modelled at the origin with its axis pointing at the camera (-Y), rotated over
the 300° sweep, and rendered on a transparent background with a shadow catcher so every
frame carries its own drop shadow. Frames go to art/out/knob-<style>/NNNN.png.
"""

import math

import bmesh
import bpy

import lib

SWEEP = 300

# Diameter in stage pixels each style is rendered for.
STYLES = {
    "chicken": 84,
    "goldcap": 84,
    "knurled": 84,
    "pedal": 66,
    "header": 58,
}


def _hull(points):
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def prism(name, outline_xz, y_front, depth, mat, bevel_w=0.0, segments=5):
    """Extrudes a closed XZ outline from y_front towards +Y (away from the camera)."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    verts = [bm.verts.new((x, y_front, z)) for x, z in outline_xz]
    face = bm.faces.new(verts)
    ret = bmesh.ops.extrude_face_region(bm, geom=[face])
    moved = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, depth, 0), verts=moved)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(o)
    if bevel_w:
        lib.bevel(o, bevel_w, segments)
    o.data.materials.append(mat)
    return o


def fluted(name, r_out, r_in, flutes, y_front, depth, mat, bevel_w=0.0, sharpness=0.5):
    n = flutes * 10
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        k = (0.5 + 0.5 * math.cos(flutes * a)) ** sharpness
        r = r_in + (r_out - r_in) * k
        pts.append((r * math.cos(a), r * math.sin(a)))
    return prism(name, pts, y_front, depth, mat, bevel_w, 3)


def circle_pts(cx, cz, r, n=48):
    return [(cx + r * math.cos(2 * math.pi * i / n), cz + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def parent_all(objs):
    root = bpy.data.objects.new("Knob", None)
    bpy.context.collection.objects.link(root)
    for o in objs:
        o.parent = root
    return root


# ---------------------------------------------------------------- styles


def build_chicken(d):
    cream = lib.M("Bakelite").set(Base_Color=(0.80, 0.73, 0.57, 1), Roughness=0.3, Coat_Weight=0.5, Coat_Roughness=0.08, Subsurface_Weight=0.08).mat
    ink = lib.mat_plastic("Ink", (0.03, 0.025, 0.02), 0.5)
    objs = [lib.cylinder("Skirt", d * 0.40, 0.07, -0.07, mat=cream, bevel_w=0.03)]
    # Teardrop: the hull of a round body and a small pointer tip.
    wing = _hull(circle_pts(0, -d * 0.04, d * 0.30, 64) + circle_pts(0, d * 0.43, d * 0.05, 24))
    objs.append(prism("Wing", wing, -0.33, 0.27, cream, bevel_w=0.07, segments=6))
    line = [(-d * 0.013, d * 0.06), (d * 0.013, d * 0.06), (d * 0.013, d * 0.44), (-d * 0.013, d * 0.44)]
    objs.append(prism("Line", line, -0.335, 0.01, ink))
    return objs


def build_goldcap(d):
    black = lib.mat_plastic("Black", (0.012, 0.012, 0.012), 0.32, coat=0.4)
    gold = lib.mat_metal("Gold", (0.86, 0.66, 0.30), 0.22, aniso=0.8, brushed_axis="Y")
    ink = lib.mat_plastic("Ink", (0.02, 0.015, 0.01), 0.45)
    white = lib.mat_plastic("White", (0.85, 0.83, 0.78), 0.35)
    objs = [
        fluted("Skirt", d * 0.47, d * 0.45, 40, -0.12, 0.12, black, 0.012),
        fluted("Body", d * 0.40, d * 0.375, 28, -0.36, 0.26, black, 0.02),
        lib.cylinder("Cap", d * 0.30, 0.03, -0.39, mat=gold, bevel_w=0.012),
    ]
    line = [(-d * 0.014, d * 0.02), (d * 0.014, d * 0.02), (d * 0.014, d * 0.27), (-d * 0.014, d * 0.27)]
    objs.append(prism("Line", line, -0.395, 0.01, ink))
    dot = [(x, z) for x, z in circle_pts(0, d * 0.43, d * 0.022, 16)]
    objs.append(prism("Dot", dot, -0.125, 0.008, white))
    return objs


def build_knurled(d):
    alu = lib.mat_metal("Alu", (0.80, 0.81, 0.83), 0.2, aniso=0.85, brushed_axis="Y")
    side = lib.M("Knurl").set(Base_Color=(0.7, 0.71, 0.73, 1), Metallic=1, Roughness=0.35)
    wave = side.node("ShaderNodeTexWave", wave_type="RINGS", rings_direction="Y", wave_profile="SAW")
    wave.inputs["Scale"].default_value = 40
    side.link(side.mapping("Object"), wave.inputs["Vector"])
    side.to("Normal", side.bump(wave.outputs["Fac"], 0.8, 0.01))
    black = lib.mat_plastic("Insert", (0.01, 0.01, 0.011), 0.25, coat=0.6)
    red = lib.mat_emission("Red", (1.0, 0.12, 0.05), 3.0)
    objs = [
        fluted("Body", d * 0.42, d * 0.405, 60, -0.40, 0.40, side.mat, 0.0, 0.3),
        lib.cylinder("Face", d * 0.405, 0.06, -0.43, mat=alu, bevel_w=0.035, segments=6),
        lib.cylinder("Insert", d * 0.27, 0.02, -0.445, mat=black, bevel_w=0.008),
    ]
    line = [(-d * 0.016, d * 0.06), (d * 0.016, d * 0.06), (d * 0.016, d * 0.25), (-d * 0.016, d * 0.25)]
    objs.append(prism("Line", line, -0.449, 0.006, red))
    return objs


def build_pedal(d):
    black = lib.mat_plastic("Black", (0.018, 0.018, 0.018), 0.42, coat=0.2)
    white = lib.mat_plastic("White", (0.9, 0.9, 0.88), 0.4)
    objs = [
        fluted("Body", d * 0.44, d * 0.41, 22, -0.30, 0.30, black, 0.025),
        lib.cylinder("Top", d * 0.36, 0.03, -0.32, mat=black, bevel_w=0.015),
    ]
    line = [(-d * 0.022, d * 0.10), (d * 0.022, d * 0.10), (d * 0.022, d * 0.42), (-d * 0.022, d * 0.42)]
    objs.append(prism("Line", line, -0.324, 0.006, white))
    return objs


def build_header(d):
    alu = lib.mat_metal("Alu", (0.72, 0.72, 0.74), 0.22, aniso=0.8, brushed_axis="Y")
    rim = lib.mat_plastic("Rim", (0.02, 0.02, 0.02), 0.35, coat=0.3)
    accent = lib.mat_emission("Accent", (1.0, 0.6, 0.18), 6.0)
    objs = [
        fluted("Rim", d * 0.47, d * 0.45, 30, -0.18, 0.18, rim, 0.015),
        lib.cylinder("Face", d * 0.36, 0.05, -0.22, mat=alu, bevel_w=0.025, segments=5),
    ]
    line = [(-d * 0.025, d * 0.1), (d * 0.025, d * 0.1), (d * 0.025, d * 0.34), (-d * 0.025, d * 0.34)]
    objs.append(prism("Line", line, -0.223, 0.004, accent))
    return objs


BUILDERS = {
    "chicken": build_chicken,
    "goldcap": build_goldcap,
    "knurled": build_knurled,
    "pedal": build_pedal,
    "header": build_header,
}


def render_style(style, samples=64, frames=None):
    size_px = STYLES[style]
    pad = lib.LAYOUT["knobStrip"]["pad"]
    n_frames = frames or lib.LAYOUT["frames"]
    frame_px = round(size_px * pad * lib.DPR)
    lib.reset()
    lib.render_settings(frame_px, frame_px, samples, transparent=True)
    cam = lib.camera((lib.STAGE_W / 2, lib.STAGE_H / 2), size_px * pad)
    cam.location.x, cam.location.z = 0, 0
    lib.studio()

    catcher = lib.front_plane("Catcher", -3, -3, 3, 3, 0.0, lib.mat_plastic("Catcher", (0.5, 0.5, 0.5)))
    catcher.is_shadow_catcher = True

    d = size_px / 100
    root = parent_all(BUILDERS[style](d))
    out = lib.OUT / f"knob-{style}"
    for f in range(n_frames):
        t = f / (n_frames - 1)
        root.rotation_euler = (0, math.radians(-SWEEP / 2 + SWEEP * t), 0)
        lib.render(out / f"{f:04d}.png")
