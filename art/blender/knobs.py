"""Knob models and their filmstrips.

Each knob is modelled at the origin with its axis pointing at the camera (-Y), seen slightly
from above (lib.TILT) so its sides show, rotated over the 300° sweep and rendered on a
transparent background with a shadow catcher on the panel plane: every frame carries its
own contact shadow. The frame is centred on the knob's base, i.e. its position on the panel.
Frames go to art/out/knob-<style>/NNNN.png at lib.SCALE pixels per stage pixel.
"""

import math

import bmesh
import bpy

import lib

SWEEP = 300

# Diameter in stage pixels each style is rendered for.
STYLES = {
    "clean": 84,
    "crunch": 84,
    "highgain": 84,
    "pedal": 66,
    "header": 58,
}


# ---------------------------------------------------------------- geometry helpers


def lathe(name, profile, mat, segments=128, flutes=0, flute_depth=0.0, flute_from=0.0, flute_to=1.0):
    """Revolves an (r, y) profile (y grows away from the camera) around the knob axis.
    Optional flutes modulate the radius between profile fractions flute_from..flute_to."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    # A profile starting on the axis gets a single centre vertex instead of a collapsed ring.
    closed = profile[0][0] == 0
    centre = bm.verts.new((0, profile[0][1], 0)) if closed else None
    pts = profile[1:] if closed else profile
    n = len(pts)
    rings = []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        ring = []
        for j, (r, y) in enumerate(pts):
            rr = r
            t = (j + (1 if closed else 0)) / max(1, len(profile) - 1)
            if flutes and flute_from <= t <= flute_to:
                # Rounded scallops (sine-shaped grooves), not sharp crown points.
                rr = r - flute_depth * (0.5 - 0.5 * math.cos(flutes * a)) ** 0.6
            ring.append(bm.verts.new((rr * math.sin(a), y, rr * math.cos(a))))
        rings.append(ring)
    for i in range(segments):
        a, b = rings[i], rings[(i + 1) % segments]
        for j in range(n - 1):
            bm.faces.new((a[j], b[j], b[j + 1], a[j + 1]))
        if closed:
            bm.faces.new((centre, b[0], a[0]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(o)
    lib._smooth(o, 40)
    o.data.materials.append(mat)
    return o


def rounded(profile_pts, radius, steps=4):
    """Adds small fillets between consecutive straight segments of an (r, y) polyline."""
    out = [profile_pts[0]]
    for i in range(1, len(profile_pts) - 1):
        p0, p1, p2 = profile_pts[i - 1], profile_pts[i], profile_pts[i + 1]
        d0 = math.dist(p0, p1)
        d1 = math.dist(p1, p2)
        k = min(radius, d0 / 2, d1 / 2)
        a = (p1[0] + (p0[0] - p1[0]) * k / d0, p1[1] + (p0[1] - p1[1]) * k / d0)
        b = (p1[0] + (p2[0] - p1[0]) * k / d1, p1[1] + (p2[1] - p1[1]) * k / d1)
        for s in range(steps + 1):
            t = s / steps
            # quadratic Bézier a → p1 → b
            x = (1 - t) ** 2 * a[0] + 2 * (1 - t) * t * p1[0] + t * t * b[0]
            y = (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * p1[1] + t * t * b[1]
            out.append((x, y))
    out.append(profile_pts[-1])
    return out


def line_mark(name, r0, r1, width, y, mat, depth=0.004):
    """Pointer line from radius r0 to r1 at 12 o'clock, slightly proud of the surface at y."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, y - depth / 2, (r0 + r1) / 2))
    o = bpy.context.active_object
    o.name = name
    o.scale = (width, depth, r1 - r0)
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(mat)
    return o


# ---------------------------------------------------------------- materials


def mat_bakelite(color, rough=0.28):
    m = lib.M("Bakelite").set(Base_Color=(*color, 1), Roughness=rough, Coat_Weight=0.6, Coat_Roughness=0.12, Specular_IOR_Level=0.6)
    n = m.noise(m.mapping("Object"), 180, 4)
    m.to("Roughness", m.ramp(n.outputs["Fac"], [(0.3, (rough * 0.8,) * 3), (0.7, (rough * 1.3,) * 3)]))
    return m.mat


def mat_spun(name, color, rough=0.18):
    """Spun / turned metal: concentric anisotropic highlights around the knob axis."""
    m = lib.M(name).set(Base_Color=(*color, 1), Metallic=1.0, Roughness=rough, Anisotropic=0.9)
    tan = m.node("ShaderNodeTangent", direction_type="RADIAL", axis="Y")
    m.link(tan.outputs["Tangent"], m.bsdf.inputs["Tangent"])
    rings = m.node("ShaderNodeTexWave", wave_type="RINGS", rings_direction="Y", wave_profile="SIN")
    rings.inputs["Scale"].default_value = 140
    rings.inputs["Distortion"].default_value = 2
    rings.inputs["Detail"].default_value = 4
    m.link(m.mapping("Object"), rings.inputs["Vector"])
    m.to("Roughness", m.ramp(rings.outputs["Fac"], [(0.0, (rough * 0.7,) * 3), (1.0, (rough * 1.4,) * 3)]))
    return m.mat


def mat_knurl(name, color, rough=0.3, density=60):
    """Diamond knurling on a cylinder: two helical band patterns crossing each other."""
    m = lib.M(name).set(Base_Color=(*color, 1), Metallic=1.0, Roughness=rough)
    sep = m.node("ShaderNodeSeparateXYZ")
    m.link(m.coord.outputs["Object"], sep.inputs["Vector"])
    ang = m.math("ARCTAN2", sep.outputs["X"], sep.outputs["Z"])
    u = m.math("MULTIPLY", ang, density / (2 * math.pi))
    v = m.math("MULTIPLY", sep.outputs["Y"], density * 0.9)
    d1 = m.math("SINE", m.math("MULTIPLY", m.math("ADD", u, v), 2 * math.pi))
    d2 = m.math("SINE", m.math("MULTIPLY", m.math("SUBTRACT", u, v), 2 * math.pi))
    h = m.math("MULTIPLY", m.math("ABSOLUTE", d1), m.math("ABSOLUTE", d2))
    m.to("Normal", m.bump(h, 0.9, 0.006))
    m.to("Roughness", m.ramp(h, [(0.0, (rough * 1.6,) * 3), (1.0, (rough * 0.8,) * 3)]))
    return m.mat


# ---------------------------------------------------------------- styles
# Profiles are (radius, y) from the front face backwards; d is the knob diameter in units.


def build_clean(d):
    """Vintage: black skirted knob with a polished aluminium top."""
    black = mat_bakelite((0.012, 0.012, 0.013), 0.25)
    alu = mat_spun("Alu", (0.86, 0.86, 0.87), 0.12)
    white = lib.mat_plastic("Pointer", (0.9, 0.88, 0.82), 0.4)
    R = d / 2
    body = rounded([(0, -0.4), (R * 0.62, -0.4), (R * 0.66, -0.12), (R * 0.95, -0.09), (R * 0.97, 0.0)], 0.025)
    objs = [lathe("Body", body, black, flutes=48, flute_depth=0.012, flute_from=0.3, flute_to=0.62)]
    cap = rounded([(0, -0.425), (R * 0.5, -0.42), (R * 0.56, -0.395), (R * 0.58, -0.37)], 0.012)
    objs.append(lathe("Cap", cap, alu))
    objs.append(line_mark("SkirtLine", R * 0.7, R * 0.93, 0.022, -0.095, white))
    objs.append(line_mark("CapLine", R * 0.05, R * 0.48, 0.018, -0.426, lib.mat_plastic("Ink", (0.02, 0.02, 0.02), 0.5)))
    return objs


def build_crunch(d):
    """Brit style: fluted black body with a brushed gold cap."""
    black = mat_bakelite((0.01, 0.01, 0.011), 0.22)
    gold = mat_spun("Gold", (0.88, 0.66, 0.3), 0.2)
    ink = lib.mat_plastic("Ink", (0.02, 0.015, 0.01), 0.45)
    R = d / 2
    skirt = rounded([(0, -0.1), (R * 0.98, -0.1), (R * 1.0, -0.05), (R * 1.0, 0.0)], 0.02)
    body = rounded([(0, -0.38), (R * 0.8, -0.38), (R * 0.86, -0.34), (R * 0.88, -0.1)], 0.03)
    objs = [
        lathe("Skirt", skirt, black, flutes=64, flute_depth=0.006),
        lathe("Body", body, black, flutes=30, flute_depth=0.014, flute_from=0.25),
    ]
    cap = rounded([(0, -0.405), (R * 0.62, -0.4), (R * 0.68, -0.38), (R * 0.7, -0.37)], 0.012)
    objs.append(lathe("Cap", cap, gold))
    objs.append(line_mark("Line", R * 0.04, R * 0.6, 0.02, -0.406, ink))
    return objs


def build_highgain(d):
    """Machined aluminium with diamond knurling and a black anodised face."""
    knurl = mat_knurl("Knurl", (0.78, 0.79, 0.81), 0.3, 70)
    alu = mat_spun("Alu", (0.82, 0.83, 0.85), 0.16)
    black = lib.M("Anodised").set(Base_Color=(0.012, 0.012, 0.014, 1), Metallic=0.7, Roughness=0.28).mat
    red = lib.M("Red").set(Base_Color=(0.6, 0.02, 0.01, 1), Emission_Color=(1.0, 0.1, 0.04, 1), Emission_Strength=2.5, Roughness=0.4).mat
    R = d / 2
    body = [(R * 0.9, -0.4), (R * 0.92, -0.38), (R * 0.92, -0.04), (R * 0.88, 0.0)]
    objs = [lathe("Knurl", [(0, -0.4)] + body, knurl)]
    chamfer = rounded([(0, -0.45), (R * 0.62, -0.45), (R * 0.84, -0.41), (R * 0.9, -0.39)], 0.01)
    objs.append(lathe("Chamfer", chamfer, alu))
    face = [(0, -0.455), (R * 0.6, -0.455), (R * 0.61, -0.45)]
    objs.append(lathe("Face", face, black))
    objs.append(line_mark("Line", R * 0.12, R * 0.56, 0.024, -0.456, red))
    return objs


def build_pedal(d):
    """Classic overdrive-pedal knob: fluted black plastic with a white line."""
    black = mat_bakelite((0.014, 0.014, 0.014), 0.38)
    white = lib.mat_plastic("Pointer", (0.92, 0.92, 0.9), 0.4)
    R = d / 2
    skirt = rounded([(0, -0.08), (R * 0.96, -0.08), (R * 1.0, -0.03), (R * 1.0, 0.0)], 0.015)
    body = rounded([(0, -0.36), (R * 0.72, -0.36), (R * 0.8, -0.32), (R * 0.84, -0.08)], 0.03)
    objs = [
        lathe("Skirt", skirt, black, flutes=48, flute_depth=0.005),
        lathe("Body", body, black, flutes=22, flute_depth=0.016, flute_from=0.25),
    ]
    objs.append(line_mark("Line", R * 0.08, R * 0.78, 0.035, -0.362, white))
    return objs


def build_header(d):
    """Compact machined knob for the global controls: knurled aluminium skirt, black face and
    a bright amber index that stays readable at small sizes."""
    knurl = mat_knurl("Knurl", (0.72, 0.73, 0.75), 0.3, 50)
    black = lib.M("Anodised").set(Base_Color=(0.014, 0.014, 0.016, 1), Metallic=0.6, Roughness=0.3).mat
    alu = mat_spun("Alu", (0.82, 0.82, 0.84), 0.14)
    amber = lib.M("Amber").set(Base_Color=(1.0, 0.55, 0.12, 1), Emission_Color=(1.0, 0.58, 0.16, 1), Emission_Strength=6, Roughness=0.4).mat
    R = d / 2
    body = [(0, -0.26), (R * 0.9, -0.26), (R * 0.92, -0.24), (R * 0.92, -0.03), (R * 0.88, 0.0)]
    objs = [lathe("Knurl", body, knurl)]
    ring = rounded([(0, -0.29), (R * 0.72, -0.29), (R * 0.86, -0.27), (R * 0.9, -0.25)], 0.01)
    objs.append(lathe("Ring", ring, alu))
    objs.append(lathe("Face", [(0, -0.296), (R * 0.68, -0.296), (R * 0.7, -0.29)], black))
    objs.append(line_mark("Line", R * 0.14, R * 0.66, 0.05, -0.298, amber))
    return objs


BUILDERS = {
    "clean": build_clean,
    "crunch": build_crunch,
    "highgain": build_highgain,
    "pedal": build_pedal,
    "header": build_header,
}


def setup_object_render(size_px, pad, samples):
    """Transparent, shadow-catching setup for anything sitting on a panel. The camera is
    added by frame_object once the object exists."""
    frame_px = round(size_px * pad * lib.SCALE)
    lib.reset()
    lib.render_settings(frame_px, frame_px, samples, transparent=True)
    lib.studio()
    catcher = lib.front_plane("Catcher", -4, -4, 4, 4, 0.0, lib.mat_plastic("Catcher", (0.5, 0.5, 0.5)))
    catcher.is_shadow_catcher = True


def front_y(objs):
    """Depth of the part closest to the camera (the knob face, the switch cap)."""
    from mathutils import Vector

    return min((o.matrix_world @ Vector(c)).y for o in objs if o.type == "MESH" for c in o.bound_box)


def frame_object(size_px, pad, focus_y):
    """Tilted orthographic camera centred on the point of the axis at depth focus_y.

    Centring on the face (not the base) keeps what the eye reads as the knob, and the axis
    its pointer turns around, exactly on the position of the scale printed on the panel."""
    cam = lib.camera((lib.STAGE_W / 2, lib.STAGE_H / 2), size_px * pad, tilt_deg=lib.TILT)
    t = math.radians(lib.TILT)
    cam.location = (0, focus_y - 40 * math.cos(t), 40 * math.sin(t))
    return cam


def render_style(style, samples=64, frames=None):
    size_px = STYLES[style]
    n_frames = frames or lib.LAYOUT["frames"]
    setup_object_render(size_px, lib.LAYOUT["knobStrip"]["pad"], samples)
    root = bpy.data.objects.new("Knob", None)
    bpy.context.collection.objects.link(root)
    objs = BUILDERS[style](size_px / 100)
    for o in objs:
        o.parent = root
    frame_object(size_px, lib.LAYOUT["knobStrip"]["pad"], front_y(objs))
    out = lib.OUT / f"knob-{style}"
    for f in range(n_frames):
        t = f / (n_frames - 1)
        root.rotation_euler = (0, math.radians(-SWEEP / 2 + SWEEP * t), 0)
        lib.render(out / f"{f:04d}.png")
