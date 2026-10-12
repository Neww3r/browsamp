"""Shared Blender helpers: scene setup, stage↔world mapping, lights and procedural materials.

World convention: the camera looks along +Y. World X is stage right, world Z is stage up,
fronts of objects sit on the y = 0 plane facing -Y. One world unit = 100 stage pixels, and
the stage centre (800, 500) is the world origin.
"""

import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

ART = Path(__file__).resolve().parent.parent
LAYOUT = json.loads((ART / "layout.json").read_text())
STAGE_W, STAGE_H = LAYOUT["stage"]["w"], LAYOUT["stage"]["h"]
TEX = ART / "tex"
OUT = ART / "out"
DPR = 2  # rendered pixels per stage pixel


# ---------------------------------------------------------------- scene


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = "GPU"
    except Exception:
        sc.cycles.device = "CPU"
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 8
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.image_settings.color_depth = "8"
    sc.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            sc.view_settings.look = look
            break
        except TypeError:
            pass
    world = bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.012, 0.011, 0.010, 1)
    bg.inputs["Strength"].default_value = 1.0
    return sc


def render_settings(width_px, height_px, samples=128, transparent=False):
    sc = bpy.context.scene
    sc.render.resolution_x = width_px
    sc.render.resolution_y = height_px
    sc.render.resolution_percentage = 100
    sc.cycles.samples = samples
    sc.render.film_transparent = transparent


def camera(center_px=(STAGE_W / 2, STAGE_H / 2), width_px=STAGE_W):
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = width_px / 100
    cam_data.sensor_fit = "HORIZONTAL"
    cam_data.clip_end = 200
    cam = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam)
    x, z = w(*center_px)
    cam.location = (x, -40, z)
    cam.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.camera = cam
    return cam


def w(px, py):
    """Stage pixel → world (x, z)."""
    return (px - STAGE_W / 2) / 100, (STAGE_H / 2 - py) / 100


def u(px):
    """Stage pixels → world units."""
    return px / 100


def render(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------- lights


def _aim(obj, direction):
    obj.rotation_euler = Vector(direction).normalized().to_track_quat("-Z", "Y").to_euler()


def sun(name, direction, strength, color=(1, 1, 1), angle_deg=8):
    d = bpy.data.lights.new(name, "SUN")
    d.energy = strength
    d.color = color
    d.angle = math.radians(angle_deg)
    o = bpy.data.objects.new(name, d)
    bpy.context.collection.objects.link(o)
    _aim(o, direction)
    return o


def area(name, location, target, size, power, color=(1, 1, 1), visible=False, shape="RECTANGLE", size_y=None):
    d = bpy.data.lights.new(name, "AREA")
    d.energy = power
    d.color = color
    d.shape = shape
    d.size = size
    d.size_y = size_y if size_y is not None else size
    o = bpy.data.objects.new(name, d)
    bpy.context.collection.objects.link(o)
    o.location = location
    _aim(o, Vector(target) - Vector(location))
    o.visible_camera = visible
    return o


def spot(name, location, target, power, angle_deg=50, blend=0.8, color=(1, 1, 1), radius=0.5):
    d = bpy.data.lights.new(name, "SPOT")
    d.energy = power
    d.color = color
    d.spot_size = math.radians(angle_deg)
    d.spot_blend = blend
    d.shadow_soft_size = radius
    o = bpy.data.objects.new(name, d)
    bpy.context.collection.objects.link(o)
    o.location = location
    _aim(o, Vector(target) - Vector(location))
    return o


def studio(key=3.2, warmth=(1.0, 0.95, 0.88), card=1.4):
    """Key/fill/top lighting shared by backgrounds and knob filmstrips so they match.

    Suns are directional (position-independent); the big soft boxes are far away so that
    reflections in chrome look the same wherever an object sits on the stage.
    """
    reflection_card(card)
    sun("Key", (0.45, 0.75, -0.6), key, warmth, angle_deg=12)
    sun("Fill", (-0.6, 0.8, -0.1), key * 0.18, (0.85, 0.9, 1.0), angle_deg=30)
    area("Softbox", (-14, -28, 16), (0, 0, 0), 22, 9000, warmth, size_y=8)
    area("Strip", (16, -26, 2), (0, 0, 0), 4, 2500, (0.9, 0.93, 1.0), size_y=26)


def reflection_card(strength=1.4):
    """A big emissive card behind the camera. Front-facing chrome mirrors whatever is behind
    the viewer; without this it would reflect the black void and render black."""
    m = M("Card")
    sep = m.node("ShaderNodeSeparateXYZ")
    m.link(m.coord.outputs["Object"], sep.inputs["Vector"])
    # A flat panel facing the camera mirrors the card 1:1, so the pattern must vary on the
    # scale of a panel: soft slanted light bands like studio strip lights.
    phase = m.math("ADD", m.math("MULTIPLY", sep.outputs["Z"], 0.9), m.math("MULTIPLY", sep.outputs["X"], 0.16))
    fac = m.math("ADD", m.math("MULTIPLY", m.math("SINE", phase), 0.5), 0.5)
    col = m.ramp(fac, [(0.0, (0.03, 0.03, 0.03)), (0.55, (0.3, 0.3, 0.3)), (1.0, (1.0, 1.0, 1.0))])
    em = m.node("ShaderNodeEmission")
    m.link(col, em.inputs["Color"])
    em.inputs["Strength"].default_value = strength
    out = m.nt.nodes["Material Output"]
    m.link(em.outputs["Emission"], out.inputs["Surface"])
    bpy.ops.mesh.primitive_plane_add(size=1)
    o = bpy.context.active_object
    o.name = "ReflectionCard"
    o.rotation_euler = (math.radians(-90), 0, 0)
    o.location = (0, -60, 0)
    o.scale = (120, 70, 1)
    bpy.ops.object.transform_apply(rotation=True, scale=True)
    o.data.materials.append(m.mat)
    o.visible_camera = False
    o.visible_shadow = False
    return o


# ---------------------------------------------------------------- geometry


def _smooth(obj, angle=35):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))
    except Exception:
        for p in obj.data.polygons:
            p.use_smooth = True
    obj.select_set(False)


def bevel(obj, width, segments=4):
    m = obj.modifiers.new("Bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE"
    m.harden_normals = False
    _smooth(obj)
    return obj


def box(name, x0, z0, x1, z1, y0, y1, mat, bevel_w=0.0, segments=4):
    """Axis-aligned box from world bounds (x right, z up, y depth)."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.active_object
    o.name = name
    o.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    o.scale = (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
    bpy.ops.object.transform_apply(scale=True)
    if bevel_w:
        bevel(o, bevel_w, segments)
    o.data.materials.append(mat)
    return o


def box_px(name, rect, y0, y1, mat, bevel_w=0.0, segments=4):
    x0, z0 = w(rect["x"], rect["y"])
    x1, z1 = w(rect["x"] + rect["w"], rect["y"] + rect["h"])
    return box(name, x0, z1, x1, z0, y0, y1, mat, bevel_w, segments)


def front_plane(name, x0, z0, x1, z1, y, mat):
    """Plane facing the camera with UVs 0..1 left→right, bottom→top."""
    bpy.ops.mesh.primitive_plane_add(size=1)
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = (math.radians(90), 0, 0)
    o.location = ((x0 + x1) / 2, y, (z0 + z1) / 2)
    o.scale = (abs(x1 - x0), abs(z1 - z0), 1)
    bpy.ops.object.transform_apply(rotation=True, scale=True)
    o.data.materials.append(mat)
    return o


def cylinder(name, radius, depth, y_front, x=0.0, z=0.0, mat=None, verts=96, bevel_w=0.0, segments=4):
    """Cylinder whose axis points at the camera; its front face sits at y = y_front."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth)
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = (math.radians(90), 0, 0)
    o.location = (x, y_front + depth / 2, z)
    bpy.ops.object.transform_apply(rotation=True)
    if bevel_w:
        bevel(o, bevel_w, segments)
    else:
        _smooth(o)
    if mat:
        o.data.materials.append(mat)
    return o


def cone(name, r_back, r_front, depth, y_front, x=0.0, z=0.0, mat=None, verts=96, bevel_w=0.0):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r_back, radius2=r_front, depth=depth)
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = (math.radians(90), 0, 0)
    o.location = (x, y_front + depth / 2, z)
    bpy.ops.object.transform_apply(rotation=True)
    if bevel_w:
        bevel(o, bevel_w)
    else:
        _smooth(o)
    if mat:
        o.data.materials.append(mat)
    return o


# ---------------------------------------------------------------- materials


class M:
    """Tiny node-graph builder around a Principled BSDF."""

    def __init__(self, name):
        self.mat = bpy.data.materials.new(name)
        self.mat.use_nodes = True
        self.nt = self.mat.node_tree
        self.bsdf = self.nt.nodes["Principled BSDF"]
        self._coord = None

    def node(self, kind, **props):
        n = self.nt.nodes.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def link(self, a, b):
        self.nt.links.new(a, b)

    def set(self, **inputs):
        for k, v in inputs.items():
            self.bsdf.inputs[k.replace("_", " ")].default_value = v
        return self

    @property
    def coord(self):
        if self._coord is None:
            self._coord = self.node("ShaderNodeTexCoord")
        return self._coord

    def mapping(self, space="Object", scale=(1, 1, 1), rotation=(0, 0, 0)):
        m = self.node("ShaderNodeMapping")
        m.inputs["Scale"].default_value = scale
        m.inputs["Rotation"].default_value = rotation
        self.link(self.coord.outputs[space], m.inputs["Vector"])
        return m.outputs["Vector"]

    def noise(self, vec, scale, detail=6, rough=0.55, distortion=0.0):
        n = self.node("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        n.inputs["Distortion"].default_value = distortion
        self.link(vec, n.inputs["Vector"])
        return n

    def ramp(self, fac, stops):
        r = self.node("ShaderNodeValToRGB")
        els = r.color_ramp.elements
        while len(els) > 1:
            els.remove(els[-1])
        els[0].position, els[0].color = stops[0][0], (*stops[0][1], 1)
        for pos, col in stops[1:]:
            e = els.new(pos)
            e.color = (*col, 1)
        self.link(fac, r.inputs["Fac"])
        return r.outputs["Color"]

    def math(self, op, a, b=None, clamp=False):
        n = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                self.link(v, n.inputs[i])
        return n.outputs[0]

    def mix(self, fac, a, b, blend="MIX"):
        n = self.node("ShaderNodeMix", data_type="RGBA", blend_type=blend)
        ins = [s for s in n.inputs if s.enabled]
        fac_s, a_s, b_s = ins[0], ins[1], ins[2]
        for sock, v in ((fac_s, fac), (a_s, a), (b_s, b)):
            if isinstance(v, (int, float)):
                sock.default_value = v
            elif isinstance(v, tuple):
                sock.default_value = (*v, 1) if len(v) == 3 else v
            else:
                self.link(v, sock)
        return [s for s in n.outputs if s.enabled][0]

    def bump(self, height, strength, distance=0.02, normal=None):
        b = self.node("ShaderNodeBump")
        b.inputs["Strength"].default_value = strength
        b.inputs["Distance"].default_value = distance
        self.link(height, b.inputs["Height"])
        if normal is not None:
            self.link(normal, b.inputs["Normal"])
        return b.outputs["Normal"]

    def image(self, path, vec=None, extension="CLIP", non_color=False):
        t = self.node("ShaderNodeTexImage")
        t.image = bpy.data.images.load(str(path), check_existing=True)
        if non_color:
            t.image.colorspace_settings.name = "Non-Color"
        t.extension = extension
        t.interpolation = "Cubic"
        self.link(vec if vec is not None else self.coord.outputs["UV"], t.inputs["Vector"])
        return t

    def to(self, name, socket):
        self.link(socket, self.bsdf.inputs[name])
        return self


def mat_plastic(name, color, rough=0.4, coat=0.0):
    return M(name).set(Base_Color=(*color, 1), Roughness=rough, Coat_Weight=coat).mat


def mat_metal(name, color, rough=0.25, aniso=0.0, brushed_axis=None, brush_scale=(1, 300, 300)):
    m = M(name).set(Base_Color=(*color, 1), Metallic=1.0, Roughness=rough, Anisotropic=aniso)
    if brushed_axis:
        # Fine streaks: noise stretched along the brushing direction modulates roughness.
        n = m.noise(m.mapping("Object", brush_scale), 1.0, detail=4)
        r = m.ramp(n.outputs["Fac"], [(0.3, (rough * 0.6,) * 3), (0.7, (rough * 1.4,) * 3)])
        m.to("Roughness", r)
        # "UV" brushes along U (straight streaks on a plate); an axis brushes concentrically around it.
        if brushed_axis == "UV":
            tan = m.node("ShaderNodeTangent", direction_type="UV_MAP")
        else:
            tan = m.node("ShaderNodeTangent", direction_type="RADIAL", axis=brushed_axis)
        m.link(tan.outputs["Tangent"], m.bsdf.inputs["Tangent"])
    return m.mat


def mat_tolex_levant(name, color=(0.018, 0.017, 0.016)):
    m = M(name).set(Base_Color=(*color, 1), Roughness=0.62, Specular_IOR_Level=0.45)
    vec = m.mapping("Object", (1, 1, 1))
    vor = m.node("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 26
    m.link(vec, vor.inputs["Vector"])
    fine = m.noise(vec, 90, 4)
    h = m.math("ADD", vor.outputs["Distance"], m.math("MULTIPLY", fine.outputs["Fac"], 0.35))
    m.to("Normal", m.bump(h, 0.55, 0.01))
    r = m.ramp(vor.outputs["Distance"], [(0.0, (0.5,) * 3), (0.6, (0.7,) * 3)])
    m.to("Roughness", r)
    return m.mat


def mat_tweed(name):
    """Lacquered diagonal tweed."""
    m = M(name)
    vec = m.mapping("Object", (1, 1, 1))
    wave = m.node("ShaderNodeTexWave", wave_type="BANDS", bands_direction="DIAGONAL", wave_profile="TRI")
    wave.inputs["Scale"].default_value = 9  # Wave multiplies by 10 internally: period ≈ 0.63 / scale
    wave.inputs["Distortion"].default_value = 1.2
    wave.inputs["Detail"].default_value = 3
    m.link(vec, wave.inputs["Vector"])
    wave2 = m.node("ShaderNodeTexWave", wave_type="BANDS", bands_direction="DIAGONAL", wave_profile="SIN")
    wave2.inputs["Scale"].default_value = 48
    m.link(m.mapping("Object", (1, 1, 1), (0, math.radians(90), 0)), wave2.inputs["Vector"])
    n = m.noise(vec, 14, 6)
    fac = m.math("MULTIPLY", m.math("ADD", wave.outputs["Fac"], m.math("MULTIPLY", n.outputs["Fac"], 0.6)), 0.65)
    col = m.ramp(fac, [(0.12, (0.12, 0.05, 0.01)), (0.45, (0.45, 0.26, 0.05)), (0.8, (0.66, 0.44, 0.12))])
    stripe = m.mix(wave2.outputs["Fac"], col, (0.16, 0.09, 0.035), "MULTIPLY")
    m.to("Base Color", m.mix(0.25, col, stripe))
    m.set(Roughness=0.42, Coat_Weight=0.85, Coat_Roughness=0.12, Coat_Tint=(1.0, 0.86, 0.6, 1))
    h = m.math("ADD", wave.outputs["Fac"], wave2.outputs["Fac"])
    m.to("Normal", m.bump(h, 0.25, 0.004))
    return m.mat


def mat_cloth(name, base, thread, scale=28, gold=None):
    """Woven grille cloth: horizontal and vertical threads with optional metallic flecks."""
    m = M(name)
    vec = m.mapping("Object", (1, 1, 1))
    wx = m.node("ShaderNodeTexWave", wave_type="BANDS", bands_direction="X", wave_profile="SIN")
    wz = m.node("ShaderNodeTexWave", wave_type="BANDS", bands_direction="Z", wave_profile="SIN")
    for wv in (wx, wz):
        wv.inputs["Scale"].default_value = scale
        wv.inputs["Distortion"].default_value = 0.4
        m.link(vec, wv.inputs["Vector"])
    weave = m.math("MULTIPLY", wx.outputs["Fac"], wz.outputs["Fac"])
    n = m.noise(vec, 6, 4)
    col = m.mix(m.math("MULTIPLY", weave, 1.3, clamp=True), base, thread)
    col = m.mix(m.math("MULTIPLY", n.outputs["Fac"], 0.35), col, (0, 0, 0), "MULTIPLY")
    m.to("Base Color", col)
    m.set(Roughness=0.85, Sheen_Weight=0.6, Sheen_Roughness=0.4)
    if gold:
        fleck = m.node("ShaderNodeTexVoronoi")
        fleck.inputs["Scale"].default_value = scale * 2.2
        m.link(vec, fleck.inputs["Vector"])
        mask = m.math("LESS_THAN", fleck.outputs["Distance"], 0.12)
        m.to("Base Color", m.mix(mask, col, gold))
        m.to("Metallic", m.math("MULTIPLY", mask, 0.9))
    m.to("Normal", m.bump(weave, 0.6, 0.004))
    return m.mat


def mat_hammered(name, color=(0.025, 0.026, 0.028)):
    m = M(name).set(Base_Color=(*color, 1), Metallic=0.55, Roughness=0.38)
    vor = m.node("ShaderNodeTexVoronoi", feature="SMOOTH_F1")
    vor.inputs["Scale"].default_value = 18
    m.link(m.mapping("Object"), vor.inputs["Vector"])
    m.to("Normal", m.bump(vor.outputs["Distance"], 0.35, 0.01))
    return m.mat


def mat_emission(name, color, strength):
    m = M(name).set(Base_Color=(0, 0, 0, 1), Emission_Color=(*color, 1), Emission_Strength=strength)
    return m.mat


def mat_glass_jewel(name, color):
    m = M(name).set(Base_Color=(*color, 1), Roughness=0.05, Transmission_Weight=0.9, IOR=1.5)
    vor = m.node("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 140
    m.link(m.mapping("Object"), vor.inputs["Vector"])
    m.to("Normal", m.bump(vor.outputs["Distance"], 0.6, 0.002))
    return m.mat


def mat_print(name, image_path, ink=(0.02, 0.02, 0.02), rough=0.35, metallic=0.0, emission=None):
    """Screen printing: an RGBA image whose alpha is the ink coverage, on a transparent plane."""
    m = M(name)
    t = m.image(image_path)
    m.set(Base_Color=(*ink, 1), Roughness=rough, Metallic=metallic)
    if emission:
        m.set(Emission_Color=(*emission[0], 1), Emission_Strength=emission[1])
    m.to("Alpha", t.outputs["Alpha"])
    return m.mat


def mat_relief(name, image_path, base, metallic=1.0, rough=0.18, bump_strength=1.0):
    """Raised logo: alpha cuts the shape, a blurred copy of the mask drives the bevel bump."""
    m = M(name).set(Base_Color=(*base, 1), Metallic=metallic, Roughness=rough)
    t = m.image(image_path)
    soft = m.image(Path(str(image_path).replace(".png", "-soft.png")), non_color=True)
    m.to("Alpha", t.outputs["Alpha"])
    m.to("Normal", m.bump(soft.outputs["Alpha"], bump_strength, 0.03))
    return m.mat
