"""Cabinet page: a 12" speaker seen from the front with the grille cloth off, and the two
microphones (rendered separately so they can be dragged over it)."""

import math

import bmesh
import bpy

import lib
from lib import front_plane, u, w

CONE_DEPTH = 1.6


def lathe(name, profile, mat, segments=192):
    """Revolves an (r, depth) profile around the camera axis; depth grows away from the camera."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    rings = []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        rings.append([bm.verts.new((r * math.cos(a), y, r * math.sin(a))) for r, y in profile])
    for i in range(segments):
        a, b = rings[i], rings[(i + 1) % segments]
        for j in range(len(profile) - 1):
            bm.faces.new((a[j], b[j], b[j + 1], a[j + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(o)
    for p in o.data.polygons:
        p.use_smooth = True
    o.data.materials.append(mat)
    return o


def mat_cone():
    m = lib.M("Cone")
    wave = m.node("ShaderNodeTexWave", wave_type="RINGS", rings_direction="Y", wave_profile="SIN")
    wave.inputs["Scale"].default_value = 0.9
    wave.inputs["Distortion"].default_value = 0.4
    m.link(m.mapping("Object"), wave.inputs["Vector"])
    fibre = m.noise(m.mapping("Object"), 60, 10, 0.75)
    col = m.ramp(fibre.outputs["Fac"], [(0.3, (0.012, 0.011, 0.01)), (0.7, (0.032, 0.029, 0.026))])
    m.to("Base Color", col)
    m.set(Roughness=0.85, Sheen_Weight=0.25)
    h = m.math("ADD", m.math("MULTIPLY", wave.outputs["Fac"], 0.6), fibre.outputs["Fac"])
    m.to("Normal", m.bump(h, 0.35, 0.02))
    return m.mat


def mat_baffle():
    m = lib.M("Baffle").set(Base_Color=(0.012, 0.012, 0.012, 1), Roughness=0.75)
    n = m.noise(m.mapping("Object"), 30, 8, 0.7)
    m.to("Normal", m.bump(n.outputs["Fac"], 0.3, 0.02))
    return m.mat


def render_cab(samples=160):
    S = lib.LAYOUT["cab"]["speaker"]
    lib.reset()
    lib.render_settings(lib.STAGE_W * lib.DPR, lib.STAGE_H * lib.DPR, samples)
    lib.camera()
    cx, cz = w(S["cx"], S["cy"])
    R = u(S["r"])

    # Baffle board with the speaker hole, slightly in front of the basket rim.
    baffle = front_plane("Baffle", -14, -9, 14, 9, 0.0, lib.mat_tolex_levant("Tolex", (0.012, 0.012, 0.012)))
    bpy.ops.mesh.primitive_cylinder_add(vertices=192, radius=R * 1.19, depth=2, location=(cx, 0, cz), rotation=(math.radians(90), 0, 0))
    cutter = bpy.context.active_object
    cutter.hide_render = True
    m = baffle.modifiers.new("Hole", "BOOLEAN")
    m.operation = "DIFFERENCE"
    m.object = cutter
    solid = baffle.modifiers.new("Thick", "SOLIDIFY")
    solid.thickness = 0.35
    solid.offset = 1

    steel = lib.M("Basket").set(Base_Color=(0.05, 0.05, 0.055, 1), Metallic=0.6, Roughness=0.4)
    hammer = steel.node("ShaderNodeTexVoronoi", feature="SMOOTH_F1")
    hammer.inputs["Scale"].default_value = 20
    steel.link(steel.mapping("Object"), hammer.inputs["Vector"])
    steel.to("Normal", steel.bump(hammer.outputs["Distance"], 0.25, 0.01))
    gasket = lib.mat_plastic("Gasket", (0.02, 0.02, 0.02), 0.85)
    surround = lib.M("Surround").set(Base_Color=(0.04, 0.037, 0.034, 1), Roughness=0.7, Sheen_Weight=0.5).mat
    cap = lib.M("DustCap").set(Base_Color=(0.018, 0.017, 0.016, 1), Roughness=0.8, Sheen_Weight=0.5).mat

    def place(o):
        o.location = (cx, 0, cz)
        return o

    place(lathe("Rim", [(R * 1.16, 0.36), (R * 1.16, 0.3), (R * 1.1, 0.28), (R * 1.04, 0.3), (R * 1.0, 0.36)], steel.mat))
    place(lathe("Gasket", [(R * 1.07, 0.27), (R * 1.07, 0.25), (R * 1.0, 0.25), (R * 1.0, 0.27)], gasket))
    # Half-roll surround, then the cone, then the dust cap dome.
    roll = [(R * (0.92 + 0.08 * (0.5 - 0.5 * math.cos(math.pi * t / 12))), 0.42 - 0.07 * math.sin(math.pi * t / 12)) for t in range(13)]
    place(lathe("Surround", roll[::-1], surround))
    cone = [(R * 0.92, 0.42), (R * 0.6, 0.42 + CONE_DEPTH * 0.45), (R * 0.3, 0.42 + CONE_DEPTH * 0.92), (R * 0.27, 0.42 + CONE_DEPTH)]
    place(lathe("Cone", cone, mat_cone()))
    dome = [(R * 0.29 * math.cos(t * math.pi / 2 / 10), 0.42 + CONE_DEPTH - R * 0.12 * math.sin(t * math.pi / 2 / 10)) for t in range(11)]
    place(lathe("DustCap", dome, cap))
    # Mounting bolts.
    chrome = lib.mat_metal("Bolt", (0.75, 0.75, 0.77), 0.25)
    for i in range(8):
        a = 2 * math.pi * (i + 0.5) / 8
        lib.cylinder("Bolt", 0.1, 0.06, 0.24, cx + math.cos(a) * R * 1.1, cz + math.sin(a) * R * 1.1, chrome, verts=6, bevel_w=0.015)

    lib.studio(key=2.4, warmth=(1.0, 0.94, 0.86))
    lib.spot("Pool", (cx - 2, -8, cz + 7), (cx, 1, cz), 7000, 55, 0.9, (1.0, 0.86, 0.7), 1.0)
    lib.render(lib.OUT / "cab.png")


# ---------------------------------------------------------------- microphones

# Mics are drawn in profile, leaning to the right like a mic on a boom aimed at the cone:
# the capsule sits at the bottom centre of the image (that point is the mic position on the
# speaker) and the body rises up and to the right.
MIC_W, MIC_H = 320, 360  # stage pixels
TIP_FROM_BOTTOM = 34  # stage pixels between the image bottom and the capsule centre
LEAN = math.radians(28)


def render_mic(kind, samples=96):
    lib.reset()
    lib.render_settings(MIC_W * lib.DPR, MIC_H * lib.DPR, samples, transparent=True)
    cam = lib.camera((lib.STAGE_W / 2, lib.STAGE_H / 2), MIC_W)
    # Frame so that the capsule (world origin) sits TIP_FROM_BOTTOM above the bottom edge.
    cam.location.x = 0
    cam.location.z = u(MIC_H / 2 - TIP_FROM_BOTTOM)
    lib.studio(key=2.8)

    root = bpy.data.objects.new("Mic", None)
    bpy.context.collection.objects.link(root)
    parts = []
    if kind == "dynamic":
        black = lib.mat_plastic("Body", (0.015, 0.015, 0.016), 0.35, coat=0.3)
        mesh = lib.M("Mesh").set(Base_Color=(0.12, 0.12, 0.13, 1), Metallic=0.9, Roughness=0.4)
        vor = mesh.node("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = 42
        mesh.link(mesh.mapping("Object"), vor.inputs["Vector"])
        holes = mesh.math("LESS_THAN", vor.outputs["Distance"], 0.32)
        mesh.to("Base Color", mesh.mix(holes, (0.12, 0.12, 0.13), (0.0, 0.0, 0.0)))
        mesh.to("Normal", mesh.bump(holes, -0.6, 0.004))
        # Built along +Z from the capsule at the origin.
        parts.append(_z_cyl("Grille", 0.34, 0.0, 0.55, mesh.mat, cap_round=True))
        parts.append(_z_cone("Neck", 0.36, 0.3, 0.55, 0.85, black))
        parts.append(_z_cyl("Body", 0.3, 0.85, 3.0, black))
        parts.append(_z_cyl("Xlr", 0.31, 3.0, 3.4, lib.mat_metal("Xlr", (0.7, 0.7, 0.72), 0.25)))
    else:
        nickel = lib.mat_metal("Nickel", (0.78, 0.76, 0.72), 0.22, aniso=0.5, brushed_axis="Z")
        slot = lib.M("Slots").set(Base_Color=(0.7, 0.68, 0.64, 1), Metallic=1, Roughness=0.3)
        wave = slot.node("ShaderNodeTexWave", wave_type="BANDS", bands_direction="Z", wave_profile="SAW")
        wave.inputs["Scale"].default_value = 2.2
        slot.link(slot.mapping("Object"), wave.inputs["Vector"])
        cut = slot.math("GREATER_THAN", wave.outputs["Fac"], 0.55)
        slot.to("Base Color", slot.mix(cut, (0.7, 0.68, 0.64), (0.0, 0.0, 0.0)))
        parts.append(_z_box("Head", 0.5, 0.36, 0.0, 1.25, slot.mat))
        parts.append(_z_cyl("Body", 0.34, 1.25, 3.0, nickel))
        parts.append(_z_cyl("Xlr", 0.35, 3.0, 3.35, lib.mat_metal("Xlr", (0.6, 0.6, 0.62), 0.3)))
    for p in parts:
        p.parent = root
    # Lean in the image plane, and turn the capsule slightly towards the cone for a 3/4 view.
    root.rotation_euler = (math.radians(-20), LEAN, 0)
    root.scale = (0.9, 0.9, 0.9)
    lib.render(lib.OUT / f"mic-{kind}.png")


def _z_cyl(name, r, z0, z1, mat, cap_round=False):
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=r, depth=z1 - z0, location=(0, 0, (z0 + z1) / 2))
    o = bpy.context.active_object
    o.name = name
    lib.bevel(o, 0.12 if cap_round else 0.02, 8 if cap_round else 3)
    o.data.materials.append(mat)
    return o


def _z_cone(name, r0, r1, z0, z1, mat):
    bpy.ops.mesh.primitive_cone_add(vertices=96, radius1=r0, radius2=r1, depth=z1 - z0, location=(0, 0, (z0 + z1) / 2))
    o = bpy.context.active_object
    o.name = name
    lib._smooth(o)
    o.data.materials.append(mat)
    return o


def _z_box(name, wx, wy, z0, z1, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, (z0 + z1) / 2))
    o = bpy.context.active_object
    o.name = name
    o.scale = (wx, wy, z1 - z0)
    bpy.ops.object.transform_apply(scale=True)
    lib.bevel(o, 0.08, 6)
    o.data.materials.append(mat)
    return o
