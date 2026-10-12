"""The three amp scenes: a head sitting on the top of its cabinet, in front of a wall that sets
the mood. Knobs are not modelled here (they are filmstrip overlays); everything printed comes
from art/tex (see art/textures.py)."""

import math

import bpy

import lib
from lib import box, front_plane, u, w

DEPTH = 2.6  # head depth
RECESS = 0.12  # how far panels and cloth sit behind the front frame
CAB_TOP = 745  # stage y of the cabinet top


def amp_by_id(amp_id):
    return next(a for a in lib.LAYOUT["amps"] if a["id"] == amp_id)


def rect_world(r):
    x0, z1 = w(r["x"], r["y"])
    x1, z0 = w(r["x"] + r["w"], r["y"] + r["h"])
    return x0, z0, x1, z1


def cutter(name, r, depth):
    x0, z0, x1, z1 = rect_world(r)
    o = box(name, x0, z0, x1, z1, -1, depth, lib.mat_plastic("Cut", (1, 0, 0)))
    o.hide_render = True
    o.display_type = "WIRE"
    return o


def shell(name, outer, openings, mat, bevel_w=0.1, depth=DEPTH, front_bevel=0.035):
    """A box with rectangular recesses cut into its front. An opening is a rect, or a
    (rect, depth) pair for a deeper cavity."""
    x0, z0, x1, z1 = rect_world(outer)
    o = box(name, x0, z0, x1, z1, 0.0, depth, mat)
    for i, r in enumerate(openings):
        r, d = r if isinstance(r, tuple) else (r, RECESS)
        m = o.modifiers.new(f"Cut{i}", "BOOLEAN")
        m.operation = "DIFFERENCE"
        m.solver = "EXACT"
        m.object = cutter(f"{name}Cut{i}", r, d)
    lib.bevel(o, front_bevel if openings else bevel_w, 4)
    return o


def piping(name, r, mat, inset=-4, radius=0.024):
    """Round piping running around a rectangle (stage px), just proud of the front."""
    x0, z0, x1, z1 = rect_world({"x": r["x"] + inset, "y": r["y"] + inset, "w": r["w"] - 2 * inset, "h": r["h"] - 2 * inset})
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 6
    sp = cu.splines.new("POLY")
    pts = [(x0, -radius * 0.4, z0), (x1, -radius * 0.4, z0), (x1, -radius * 0.4, z1), (x0, -radius * 0.4, z1)]
    sp.points.add(len(pts) - 1)
    for p, co in zip(sp.points, pts):
        p.co = (*co, 1)
    sp.use_cyclic_u = True
    o = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(mat)
    return o


def handle(leather, metal):
    head_top = w(0, lib.LAYOUT["amps"][0]["head"]["y"])[1]
    box("Strap", -1.9, head_top - 0.02, 1.9, head_top + 0.2, 1.0, 1.6, leather, 0.06)
    for x in (-2.05, 2.05):
        box(f"StrapEnd{x}", x - 0.22, head_top - 0.02, x + 0.22, head_top + 0.12, 0.9, 1.7, metal, 0.04)


def corners(head, metal, size=0.4):
    x0, z0, x1, z1 = rect_world(head)
    for cx, cz, sx, sz in ((x0, z1, 1, -1), (x1, z1, -1, -1), (x0, z0, 1, 1), (x1, z0, -1, 1)):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=size * 0.5, segments=48, ring_count=24)
        o = bpy.context.active_object
        o.name = "Corner"
        o.scale = (1, 0.28, 1)
        o.location = (cx + sx * size * 0.12, -0.02, cz + sz * size * 0.12)
        bpy.ops.object.transform_apply(scale=True)
        lib._smooth(o, 80)
        o.data.materials.append(metal)


def feet(rubber):
    head_bottom = w(0, 740)[1]
    for x in (-5.4, 5.4):
        box("Foot", x - 0.35, head_bottom - 0.06, x + 0.35, head_bottom + 0.02, 0.4, 2.2, rubber, 0.02)


def cabinet(body, cloth, piping_mat=None):
    top = w(0, CAB_TOP)[1]
    outer = {"x": 130, "y": CAB_TOP, "w": 1340, "h": 700}
    grille = {"x": 185, "y": CAB_TOP + 55, "w": 1230, "h": 600}
    shell("Cab", outer, [grille], body, depth=3.2)
    x0, z0, x1, z1 = rect_world(grille)
    front_plane("CabCloth", x0, z0, x1, z1, RECESS - 0.006, cloth)
    if piping_mat:
        piping("CabPiping", grille, piping_mat)
    return top


def panel_plate(amp, mat, print_mat):
    x0, z0, x1, z1 = rect_world(amp["panel"])
    box("Panel", x0, z0, x1, z1, RECESS - 0.03, RECESS + 0.02, mat, 0.012)
    front_plane("Print", x0, z0, x1, z1, RECESS - 0.0305, print_mat)


def logo_plane(amp, mat, y):
    img = bpy.data.images.load(str(lib.TEX / f"logo-{amp['id']}.png"), check_existing=True)
    wpx, hpx = img.size[0] / lib.DPR, img.size[1] / lib.DPR
    cx, cz = w(amp["logo"]["x"], amp["logo"]["y"])
    return front_plane("Logo", cx - u(wpx) / 2, cz - u(hpx) / 2, cx + u(wpx) / 2, cz + u(hpx) / 2, y, mat)


def jewel(pos, color, metal, r=0.17):
    x, z = w(pos["x"], pos["y"])
    lib.cylinder("JewelBezel", r * 1.35, 0.08, -0.05, x, z, metal, bevel_w=0.03)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=64, ring_count=32, location=(x, -0.04, z))
    o = bpy.context.active_object
    o.scale = (1, 0.7, 1)
    lib._smooth(o, 80)
    o.data.materials.append(lib.mat_glass_jewel("Jewel", color))


def toggle(pos_px, metal, lever):
    x, z = w(*pos_px)
    lib.cylinder("Nut", 0.1, 0.06, RECESS - 0.09, x, z, metal, verts=6, bevel_w=0.01)
    lib.cylinder("Bushing", 0.06, 0.1, RECESS - 0.13, x, z, metal, bevel_w=0.01)
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.035, radius2=0.05, depth=0.42, location=(x, RECESS - 0.3, z + 0.08))
    o = bpy.context.active_object
    o.rotation_euler = (math.radians(90 - 25), 0, 0)
    lib._smooth(o, 80)
    o.data.materials.append(lever)


def wall(mat, y=5.0):
    front_plane("Wall", -14, -9, 14, 9, y, mat)


# ---------------------------------------------------------------- materials for walls


def mat_wood_planks():
    m = lib.M("Planks")
    brick = m.node("ShaderNodeTexBrick")
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Mortar Size"].default_value = 0.008
    brick.inputs["Brick Width"].default_value = 3.5
    brick.inputs["Row Height"].default_value = 0.55
    brick.offset = 0.37
    m.link(m.mapping("Object", (1, 1, 1), (math.radians(90), math.radians(90), 0)), brick.inputs["Vector"])
    grain = m.noise(m.mapping("Object", (1, 1, 14)), 3, 8, 0.6, 3.0)
    col = m.ramp(grain.outputs["Fac"], [(0.3, (0.045, 0.02, 0.008)), (0.7, (0.13, 0.065, 0.025))])
    tint = m.mix(brick.outputs["Fac"], col, (0.01, 0.006, 0.004))
    m.to("Base Color", m.mix(m.math("MULTIPLY", brick.outputs["Color"], 0.3), tint, (0.05, 0.03, 0.015)))
    m.set(Roughness=0.55, Coat_Weight=0.25, Coat_Roughness=0.3)
    m.to("Normal", m.bump(m.math("ADD", brick.outputs["Fac"], m.math("MULTIPLY", grain.outputs["Fac"], 0.2)), 0.5, 0.05))
    return m.mat


def mat_brick():
    m = lib.M("Brick")
    brick = m.node("ShaderNodeTexBrick")
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Mortar Size"].default_value = 0.03
    brick.inputs["Brick Width"].default_value = 1.0
    brick.inputs["Row Height"].default_value = 0.34
    brick.inputs["Color1"].default_value = (0.075, 0.03, 0.02, 1)
    brick.inputs["Color2"].default_value = (0.04, 0.018, 0.013, 1)
    brick.inputs["Mortar"].default_value = (0.022, 0.02, 0.018, 1)
    brick.inputs["Mortar Smooth"].default_value = 0.3
    m.link(m.mapping("Object", (1, 1, 1), (math.radians(90), 0, 0)), brick.inputs["Vector"])
    n = m.noise(m.mapping("Object"), 9, 8, 0.65)
    blotch = m.noise(m.mapping("Object"), 1.6, 4, 0.5)
    col = m.mix(m.math("MULTIPLY", n.outputs["Fac"], 0.6), brick.outputs["Color"], (0.02, 0.015, 0.012), "MULTIPLY")
    col = m.mix(m.math("MULTIPLY", blotch.outputs["Fac"], 0.7), col, (0.01, 0.008, 0.007), "MULTIPLY")
    m.to("Base Color", col)
    m.set(Roughness=0.9)
    m.to("Normal", m.bump(m.math("ADD", m.math("SUBTRACT", 1.0, brick.outputs["Fac"]), m.math("MULTIPLY", n.outputs["Fac"], 0.3)), 0.8, 0.08))
    return m.mat


def mat_concrete():
    m = lib.M("Concrete")
    vec = m.mapping("Object")
    big = m.noise(vec, 0.8, 6, 0.6)
    fine = m.noise(vec, 40, 8, 0.7)
    col = m.ramp(m.math("ADD", m.math("MULTIPLY", big.outputs["Fac"], 0.7), m.math("MULTIPLY", fine.outputs["Fac"], 0.3)), [(0.35, (0.025, 0.027, 0.03)), (0.65, (0.075, 0.078, 0.085))])
    m.to("Base Color", col)
    m.set(Roughness=0.8)
    m.to("Normal", m.bump(fine.outputs["Fac"], 0.25, 0.02))
    return m.mat


def mat_red_cavity():
    """Back of the Obsidian grille: a red glow, brightest behind the logo."""
    m = lib.M("Cavity").set(Base_Color=(0.005, 0.005, 0.005, 1), Roughness=0.6)
    grad = m.node("ShaderNodeTexGradient", gradient_type="SPHERICAL")
    m.link(m.mapping("Object", (0.16, 1, 0.55)), grad.inputs["Vector"])
    strength = m.math("POWER", grad.outputs["Fac"], 1.6)
    m.set(Emission_Color=(1.0, 0.09, 0.03, 1))
    m.to("Emission Strength", m.math("MULTIPLY", strength, 9.0))
    return m.mat


# ---------------------------------------------------------------- the three amps


def build_sunset(a):
    tweed = lib.mat_tweed("Tweed")
    cloth = lib.mat_cloth("Oxblood", (0.06, 0.02, 0.013), (0.30, 0.17, 0.08), scale=30)
    chrome = lib.mat_metal("Chrome", (0.92, 0.92, 0.93), 0.1, aniso=0.5, brushed_axis="UV")
    grille = a["grille"]
    shell("Head", a["head"], [grille, a["panel"]], tweed)
    x0, z0, x1, z1 = rect_world(grille)
    front_plane("Cloth", x0, z0, x1, z1, RECESS - 0.006, cloth)
    piping("ClothPiping", grille, lib.mat_metal("Brass", (0.85, 0.66, 0.36), 0.25), inset=-3, radius=0.018)
    logo_plane(a, lib.mat_relief("LogoChrome", lib.TEX / "logo-sunset.png", (0.93, 0.88, 0.76), 1.0, 0.12, 1.4), RECESS - 0.06)
    panel_plate(a, chrome, lib.mat_print("PanelInk", lib.TEX / "panel-sunset.png", (0.02, 0.018, 0.015)))
    jewel(a["jewel"], (0.85, 0.06, 0.03), chrome)
    leather = lib.mat_plastic("Leather", (0.09, 0.045, 0.02), 0.5, coat=0.3)
    handle(leather, chrome)
    feet(lib.mat_plastic("Rubber", (0.02, 0.02, 0.02), 0.8))
    cabinet(tweed, cloth)
    wall(mat_wood_planks())
    lib.studio(key=2.3, warmth=(1.0, 0.9, 0.78))
    lib.spot("WallPool", (0, -2, 9), (0, 5, 2.5), 9000, 70, 0.9, (1.0, 0.72, 0.42), 1.0)
    lib.area("Rim", (0, 3.5, 5), (0, 0, 1), 6, 1200, (1.0, 0.8, 0.6), size_y=2)


def build_brixton(a):
    tolex = lib.mat_tolex_levant("Tolex")
    cloth = lib.mat_cloth("Basketweave", (0.006, 0.006, 0.006), (0.045, 0.04, 0.032), scale=24, gold=(0.5, 0.38, 0.16))
    gold = lib.mat_metal("GoldPanel", (0.83, 0.62, 0.27), 0.28, aniso=0.6, brushed_axis="UV")
    chrome = lib.mat_metal("Chrome", (0.92, 0.92, 0.93), 0.08)
    white = lib.mat_plastic("Piping", (0.82, 0.8, 0.74), 0.35, coat=0.3)
    grille = a["grille"]
    shell("Head", a["head"], [a["panel"], grille], tolex)
    x0, z0, x1, z1 = rect_world(grille)
    front_plane("Cloth", x0, z0, x1, z1, RECESS - 0.006, cloth)
    piping("PanelPiping", a["panel"], white)
    piping("ClothPiping", grille, white)
    logo_plane(a, lib.mat_relief("LogoWhite", lib.TEX / "logo-brixton.png", (0.86, 0.84, 0.78), 0.0, 0.3, 1.6), RECESS - 0.07)
    panel_plate(a, gold, lib.mat_print("PanelInk", lib.TEX / "panel-brixton.png", (0.015, 0.012, 0.008)))
    jewel(a["jewel"], (0.85, 0.05, 0.03), chrome)
    black = lib.mat_plastic("Lever", (0.02, 0.02, 0.02), 0.3, coat=0.5)
    for x in (1268, 1338):
        toggle((x, a["knobY"]), chrome, black)
    corners(a["head"], chrome)
    handle(lib.mat_plastic("Handle", (0.015, 0.015, 0.015), 0.45), chrome)
    feet(lib.mat_plastic("Rubber", (0.02, 0.02, 0.02), 0.8))
    cabinet(tolex, cloth, white)
    wall(mat_brick())
    lib.studio(key=2.6, warmth=(1.0, 0.93, 0.84))
    lib.spot("WallPool", (0, -1, 9), (0, 5, 2.0), 11000, 60, 0.85, (1.0, 0.68, 0.38), 0.8)
    lib.area("RimL", (-9, 3, 3), (0, 0, 0), 4, 900, (1.0, 0.7, 0.45))
    lib.area("RimR", (9, 3, 3), (0, 0, 0), 4, 900, (1.0, 0.7, 0.45))


def build_obsidian(a):
    steel = lib.mat_hammered("Hammered")
    frame = lib.mat_metal("Gunmetal", (0.11, 0.115, 0.12), 0.3, aniso=0.5, brushed_axis="UV")
    anod = lib.mat_metal("Anodized", (0.035, 0.036, 0.04), 0.32, aniso=0.7, brushed_axis="UV")
    grille_r = a["grille"]
    shell("Head", a["head"], [(grille_r, 0.5), a["panel"]], steel, front_bevel=0.05)
    x0, z0, x1, z1 = rect_world(grille_r)
    front_plane("Cavity", x0, z0, x1, z1, 0.49, mat_red_cavity())
    perforated = lib.M("Perforated").set(Base_Color=(0.03, 0.03, 0.032, 1), Metallic=0.8, Roughness=0.42)
    t = perforated.image(lib.TEX / "grille-hex.png")
    perforated.to("Alpha", t.outputs["Alpha"])
    front_plane("Grille", x0, z0, x1, z1, RECESS - 0.01, perforated.mat)
    logo_plane(a, lib.mat_relief("LogoAlu", lib.TEX / "logo-obsidian.png", (0.82, 0.83, 0.86), 1.0, 0.2, 1.2), RECESS - 0.05)
    panel_plate(a, anod, lib.mat_print("PanelInk", lib.TEX / "panel-obsidian.png", (0.75, 0.77, 0.8), 0.3, 0.3))
    px0, pz0, px1, pz1 = rect_world(a["panel"])
    box("Accent", px0 + 0.3, pz1 + 0.07, px1 - 0.3, pz1 + 0.1, -0.012, 0.01, lib.mat_emission("AccentRed", (1.0, 0.08, 0.03), 14))
    jewel(a["jewel"], (0.05, 0.25, 0.95), frame)
    corners(a["head"], frame, 0.34)
    handle(lib.mat_plastic("Handle", (0.012, 0.012, 0.012), 0.5), frame)
    feet(lib.mat_plastic("Rubber", (0.02, 0.02, 0.02), 0.8))
    cab_grille = lib.M("CabPerforated").set(Base_Color=(0.03, 0.03, 0.032, 1), Metallic=0.8, Roughness=0.42)
    cab_grille.to("Alpha", cab_grille.image(lib.TEX / "grille-hex-cab.png").outputs["Alpha"])
    cabinet(steel, cab_grille.mat)
    wall(mat_concrete())
    lib.studio(key=2.6, warmth=(0.92, 0.95, 1.0))
    lib.spot("WallPool", (0, -1, 9), (0, 5, 2.5), 6000, 55, 0.9, (0.55, 0.7, 1.0), 0.8)
    lib.area("RimL", (-9, 3, 2), (0, 0, 0), 4, 1400, (0.4, 0.6, 1.0))
    lib.area("RimR", (9, 3, 2), (0, 0, 0), 4, 1400, (1.0, 0.25, 0.15))


BUILDERS = {"sunset": build_sunset, "brixton": build_brixton, "obsidian": build_obsidian}


def render_amp(amp_id, samples=160):
    a = amp_by_id(amp_id)
    lib.reset()
    lib.render_settings(lib.STAGE_W * lib.DPR, lib.STAGE_H * lib.DPR, samples)
    lib.camera()
    BUILDERS[amp_id](a)
    lib.render(lib.OUT / f"amp-{amp_id}.png")
