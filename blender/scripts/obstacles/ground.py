"""Ground obstacles (GDD 5.8 Low / Low-Mid band): tree clusters, steeple, clock tower, tall silo, power lines.

All are 2-3x realistic scale with their pivot at the base center (z = 0), except SM_PowerWire, which is a 1 m span
along +X starting at its pivot so gameplay code can stretch it between two SOCKET_Wire_* empties by scaling X.
"""
import math
import random

from mathutils import Matrix, Vector

from lib import palette
from obstacles import checks, common, preview_sheets
from obstacles.common import BASE, DARK, LIGHT
from props import kit, trees

LOW_BAND = "Low band 4-12 m (blocks the snack lane)"
LOW_MID_BAND = "Low-Mid: rises from the ground through the Low band (12 m) into Mid"

# ---------------------------------------------------------------- tree clusters
TREE_KIT_SCALE = 3.3            # kit trees are capped at 3.5 m decor height; obstacles are ~3.3x that
TREE_SCALE_JITTER = 0.08
TREE_SINK_LIMIT = 0.2
TREE_CLUSTER_LAYOUTS = {
    # (x, y, canopy radius, color, kind) in kit space before TREE_KIT_SCALE; "pine" uses trees.add_pine
    "SM_TreeCluster_A": (
        (0.0, 0.0, 1.25, "Pumpkin", trees.KIND_ROUND),
        (-1.55, 0.55, 1.05, "MapleRed", trees.KIND_TALL),
        (1.5, 0.45, 1.0, "Mustard", trees.KIND_LUMPY),
        (0.45, -1.3, 0.95, "MapleRed", trees.KIND_ROUND),
        (-0.85, -1.05, 0.85, "Mustard", trees.KIND_ROUND),
    ),
    "SM_TreeCluster_B": (
        (0.0, 0.2, 1.1, "MapleRed", trees.KIND_TALL),
        (1.45, -0.4, 1.05, "Pumpkin", trees.KIND_LUMPY),
        (-1.4, -0.5, 0.0, "pine", trees.PINE_LARGE),
        (-0.3, 1.45, 0.95, "Mustard", trees.KIND_ROUND),
        (0.55, -1.45, 0.0, "pine", trees.PINE_SMALL),
        (1.2, 1.25, 0.8, "Pumpkin", trees.KIND_TALL),
    ),
}
CLUSTER_BUSHES = ((1.9, -1.4, 0.5), (-1.9, 0.9, 0.55), (0.2, 1.9, 0.45))
BUSH_COLOR = "Moss"

# ---------------------------------------------------------------- steeple
STEEPLE_PLINTH = (4.8, 1.2)          # width, height
STEEPLE_TOWER = (4.0, 11.0)          # width, top z
STEEPLE_CORNICE = (4.5, 0.45)
STEEPLE_BELFRY = (3.5, 3.2)
STEEPLE_SPIRE_HEIGHT = 6.4
STEEPLE_SPIRE_OVERHANG = 0.25
STEEPLE_CROSS = (0.22, 1.6, 0.95)    # bar thickness, upright height, arm width
STEEPLE_OPENING = (1.0, 1.9)         # louvred belfry opening width, height
STEEPLE_DOOR = (1.3, 2.4)
STEEPLE_SLIT = (0.45, 1.3)
STEEPLE_SLIT_HEIGHTS = (5.2, 8.4)
FACADE_DEPTH = 0.16

# ---------------------------------------------------------------- clock tower
CLOCK_PLINTH = (5.2, 1.0)
CLOCK_SHAFT = (4.4, 11.5)
CLOCK_BAND_HEIGHTS = (4.2, 8.0)
CLOCK_BAND_THICKNESS = 0.35
CLOCK_STAGE = (5.0, 3.4)
CLOCK_FACE_RADIUS = 1.35
CLOCK_FACE_SIDES = 8
CLOCK_HAND_WIDTH = 0.2
CLOCK_ROOF_HEIGHT = 3.6
CLOCK_ROOF_OVERHANG = 0.35
CLOCK_FINIAL = (0.3, 1.0)
CLOCK_WINDOW = (0.7, 1.4)

# ---------------------------------------------------------------- tall silo
SILO_SIDES = 12
SILO_RADIUS = 2.5
SILO_HEIGHT = 13.0
SILO_BAND_HEIGHTS = (3.2, 6.4, 9.6)
SILO_BAND_THICKNESS = 0.3
SILO_BAND_OUTSET = 0.08
SILO_DOME_PROFILE = ((1.0, 0.0), (0.92, 0.9), (0.66, 1.75), (0.3, 2.3), (0.0, 2.5))
SILO_FOOTING = (2.75, 0.5)
SILO_LADDER_WIDTH = 0.7
SILO_LADDER_RAIL = 0.12
SILO_LADDER_RUNGS = 8
SILO_CHUTE = (0.9, 0.9, 1.5)

# ---------------------------------------------------------------- power lines
TOWER_HEIGHT = 11.5
TOWER_BASE_HALF = 1.6
TOWER_TOP_HALF = 0.45
TOWER_LEG_WIDTH = 0.28
TOWER_BRACE_WIDTH = 0.16
TOWER_BRACE_LEVELS = (0.0, 3.2, 6.2, 8.8, TOWER_HEIGHT - 0.6)
TOWER_ARM_Z = 10.4
TOWER_ARM_HALF = 3.4
TOWER_ARM_SECTION = 0.32
TOWER_INSULATOR = (0.22, 0.6)
TOWER_CAP_HEIGHT = 0.8
WIRE_ATTACH_Z = TOWER_ARM_Z - TOWER_INSULATOR[1]
TOWER_COLOR = "Slate"

WIRE_SEGMENTS = 8
WIRE_SIDES = 4
WIRE_RADIUS = 0.14
WIRE_SAG = 0.35
WIRE_COLOR = "GooseCharcoal"
PREVIEW_WIRE_SPAN = 24.0  # contact sheet shows the wire scaled to a typical tower-to-tower span

RULES = {
    "SM_TreeCluster_A": common.AssetRules(common.PIVOT_BASE, (8.0, 12.5), sway=True, band_note=LOW_BAND),
    "SM_TreeCluster_B": common.AssetRules(common.PIVOT_BASE, (8.0, 12.5), sway=True, band_note=LOW_BAND),
    "SM_Steeple": common.AssetRules(common.PIVOT_BASE, (16.0, 24.0), band_note=LOW_MID_BAND),
    "SM_ClockTower": common.AssetRules(common.PIVOT_BASE, (14.0, 22.0), band_note=LOW_MID_BAND),
    "SM_SiloTall": common.AssetRules(common.PIVOT_BASE, (13.0, 18.0), band_note=LOW_MID_BAND),
    "SM_PowerTower": common.AssetRules(common.PIVOT_BASE, (9.0, 13.0), sockets=("SOCKET_Wire_L", "SOCKET_Wire_R"),
                                       band_note=LOW_BAND + "; wires hang at ~9.8 m", verify_fbx=True),
    "SM_PowerWire": common.AssetRules(common.PIVOT_SPAN_START, (0.2, 1.0), band_note="spans between towers",
                                      extra={"preview_scale": (PREVIEW_WIRE_SPAN, 1.0, 1.0)}),
}


def _tree_cluster(builder, spec, rng):
    for x, y, radius, color, kind in TREE_CLUSTER_LAYOUTS[spec.mesh_name]:
        tree = common.new_builder()
        if color == "pine":
            trees.add_pine(tree, rng, 0.0, 0.0, 0.0, size=kind)
        else:
            trees.add_deciduous(tree, rng, 0.0, 0.0, 0.0, radius, color, kind)
        scale = TREE_KIT_SCALE * (1.0 + rng.uniform(-TREE_SCALE_JITTER, TREE_SCALE_JITTER))
        matrix = (Matrix.Translation((x * TREE_KIT_SCALE, y * TREE_KIT_SCALE, 0.0)) @ Matrix.Scale(scale, 4))
        common.merge_scaled(builder, tree, matrix)
    for x, y, radius in CLUSTER_BUSHES:
        bush = common.new_builder()
        kit.add_bush(bush, rng, 0.0, 0.0, 0.0, radius, BUSH_COLOR)
        common.merge_scaled(builder, bush, Matrix.Translation((x * TREE_KIT_SCALE, y * TREE_KIT_SCALE, 0.0))
                            @ Matrix.Scale(TREE_KIT_SCALE, 4))
    for vertex in builder.vertices:
        vertex.z = max(vertex.z, -TREE_SINK_LIMIT)  # scaled kit trunk/bush sinks would reach -0.5 m


def _four_faces(builder, part_for_face, color, shade, half_width, z):
    """Adds one facade detail on each of the 4 sides of a square tower (front face toward +Y first)."""
    for side in range(4):
        rotation = Matrix.Rotation(side * math.pi * 0.5, 4, "Z")
        common.add(builder, part_for_face, color, shade,
                   rotation @ Matrix.Translation((0.0, half_width, z)))


def _square_stage(builder, rng, width, z0, height, color, choices=(BASE, BASE, LIGHT)):
    common.add(builder, common.centered_box(width, width, height, z0), color,
               uv_for_face=common.shaded(rng, color, choices))


def _steeple(builder, rng):
    plinth_w, plinth_h = STEEPLE_PLINTH
    tower_w, tower_top = STEEPLE_TOWER
    _square_stage(builder, rng, plinth_w, -0.1, plinth_h + 0.1, "Stone", (BASE, DARK))
    _square_stage(builder, rng, tower_w, plinth_h, tower_top - plinth_h, "WallCream")
    cornice_w, cornice_h = STEEPLE_CORNICE
    _square_stage(builder, rng, cornice_w, tower_top, cornice_h, "Stone", (BASE, LIGHT))
    belfry_w, belfry_h = STEEPLE_BELFRY
    belfry_z = tower_top + cornice_h
    _square_stage(builder, rng, belfry_w, belfry_z, belfry_h, "WallCream", (BASE, LIGHT))
    spire_z = belfry_z + belfry_h
    spire_radius = (belfry_w * 0.5 + STEEPLE_SPIRE_OVERHANG) * math.sqrt(2.0)
    common.add(builder, common.pyramid(4, spire_radius, STEEPLE_SPIRE_HEIGHT, angle_offset=math.pi * 0.25),
               "NavyRoof", matrix=Matrix.Translation((0.0, 0.0, spire_z)),
               uv_for_face=common.shaded(rng, "NavyRoof", (BASE, LIGHT, DARK)))

    bar, upright, arm = STEEPLE_CROSS
    cross_z = spire_z + STEEPLE_SPIRE_HEIGHT - 0.2
    common.add(builder, common.centered_box(bar, bar, upright, cross_z), "HarvestGold")
    common.add(builder, common.centered_box(arm, bar, bar, cross_z + upright * 0.55), "HarvestGold")

    opening_w, opening_h = STEEPLE_OPENING
    opening = common.box(-opening_w * 0.5, opening_w * 0.5, -FACADE_DEPTH, FACADE_DEPTH, -opening_h * 0.5,
                         opening_h * 0.5)
    _four_faces(builder, opening, "GooseCharcoal", BASE, belfry_w * 0.5, belfry_z + belfry_h * 0.5)
    slit_w, slit_h = STEEPLE_SLIT
    slit = common.box(-slit_w * 0.5, slit_w * 0.5, -FACADE_DEPTH, FACADE_DEPTH, -slit_h * 0.5, slit_h * 0.5)
    for z in STEEPLE_SLIT_HEIGHTS:
        _four_faces(builder, slit, "NavyRoof", DARK, tower_w * 0.5, z)
    door_w, door_h = STEEPLE_DOOR
    common.add(builder, common.box(-door_w * 0.5, door_w * 0.5, -FACADE_DEPTH, FACADE_DEPTH, 0.0, door_h), "Wood",
               DARK, Matrix.Translation((0.0, plinth_w * 0.5, 0.0)))


def _clock_face(builder, z, half_width):
    radius = CLOCK_FACE_RADIUS
    face = common.lathe(((radius, -FACADE_DEPTH), (radius, FACADE_DEPTH)), CLOCK_FACE_SIDES,
                        angle_offset=math.pi / CLOCK_FACE_SIDES)
    rim = common.lathe(((radius * 1.18, -FACADE_DEPTH * 0.5), (radius * 1.18, FACADE_DEPTH * 0.5)),
                       CLOCK_FACE_SIDES, angle_offset=math.pi / CLOCK_FACE_SIDES)
    hand_y0, hand_y1 = FACADE_DEPTH * 1.5, FACADE_DEPTH * 2.5
    hour = common.box(-CLOCK_HAND_WIDTH * 0.5, CLOCK_HAND_WIDTH * 0.5, hand_y0, hand_y1, 0.0, radius * 0.55)
    minute = common.box(-CLOCK_HAND_WIDTH * 0.4, CLOCK_HAND_WIDTH * 0.4, hand_y0, hand_y1, 0.0, radius * 0.85)
    upright = Matrix.Rotation(-math.pi * 0.5, 4, "X")  # lathe axis Z -> facade normal +Y
    for side in range(4):
        base = Matrix.Rotation(side * math.pi * 0.5, 4, "Z") @ Matrix.Translation((0.0, half_width, z))
        common.add(builder, rim, "HarvestGold", DARK, base @ upright)
        common.add(builder, face, "WallCream", LIGHT, base @ Matrix.Translation((0.0, FACADE_DEPTH * 0.5, 0.0))
                   @ upright)
        common.add(builder, hour, "GooseCharcoal", BASE, base @ Matrix.Rotation(math.radians(-60.0), 4, "Y"))
        common.add(builder, minute, "GooseCharcoal", BASE, base @ Matrix.Rotation(math.radians(35.0), 4, "Y"))


def _clock_tower(builder, rng):
    plinth_w, plinth_h = CLOCK_PLINTH
    shaft_w, shaft_top = CLOCK_SHAFT
    _square_stage(builder, rng, plinth_w, -0.1, plinth_h + 0.1, "Stone", (BASE, DARK))
    _square_stage(builder, rng, shaft_w, plinth_h, shaft_top - plinth_h, "Brick", (BASE, BASE, DARK, LIGHT))
    for z in CLOCK_BAND_HEIGHTS:
        _square_stage(builder, rng, shaft_w + 0.2, z, CLOCK_BAND_THICKNESS, "Stone", (BASE, LIGHT))
    stage_w, stage_h = CLOCK_STAGE
    _square_stage(builder, rng, stage_w + 0.3, shaft_top, 0.3, "Stone", (BASE, LIGHT))
    _square_stage(builder, rng, stage_w, shaft_top + 0.3, stage_h, "WallCream", (BASE, LIGHT))
    roof_z = shaft_top + 0.3 + stage_h
    _square_stage(builder, rng, stage_w + 0.3, roof_z, 0.3, "Stone", (BASE, LIGHT))
    roof_radius = (stage_w * 0.5 + CLOCK_ROOF_OVERHANG) * math.sqrt(2.0)
    common.add(builder, common.pyramid(4, roof_radius, CLOCK_ROOF_HEIGHT, angle_offset=math.pi * 0.25), "Slate",
               matrix=Matrix.Translation((0.0, 0.0, roof_z + 0.3)),
               uv_for_face=common.shaded(rng, "Slate", (BASE, LIGHT, DARK)))
    finial_w, finial_h = CLOCK_FINIAL
    common.add(builder, common.centered_box(finial_w, finial_w, finial_h, roof_z + 0.3 + CLOCK_ROOF_HEIGHT - 0.3),
               "HarvestGold")
    _clock_face(builder, shaft_top + 0.3 + stage_h * 0.5, stage_w * 0.5)
    window_w, window_h = CLOCK_WINDOW
    window = common.box(-window_w * 0.5, window_w * 0.5, -FACADE_DEPTH, FACADE_DEPTH, -window_h * 0.5, window_h * 0.5)
    for z in (CLOCK_BAND_HEIGHTS[0] - 1.4, CLOCK_BAND_HEIGHTS[1] - 1.4, shaft_top - 1.5):
        _four_faces(builder, window, "HarvestGold", LIGHT, shaft_w * 0.5, z)
    common.add(builder, common.box(-0.75, 0.75, -FACADE_DEPTH, FACADE_DEPTH, 0.0, 2.3), "Wood", DARK,
               Matrix.Translation((0.0, plinth_w * 0.5, 0.0)))


def _silo(builder, rng):
    footing_r, footing_h = SILO_FOOTING
    common.add(builder, common.lathe(((footing_r, -0.1), (footing_r, footing_h)), SILO_SIDES), "Stone", DARK)
    common.add(builder, common.lathe(((SILO_RADIUS, footing_h), (SILO_RADIUS, SILO_HEIGHT)), SILO_SIDES), "Brick",
               uv_for_face=common.shaded(rng, "Brick", (BASE, BASE, DARK, LIGHT)))
    for z in SILO_BAND_HEIGHTS:
        band_r = SILO_RADIUS + SILO_BAND_OUTSET
        common.add(builder, common.lathe(((band_r, z), (band_r, z + SILO_BAND_THICKNESS)), SILO_SIDES), "WallCream")
    dome = common.lathe([(SILO_RADIUS * 1.04 * r, SILO_HEIGHT + z) for r, z in SILO_DOME_PROFILE], SILO_SIDES)
    common.add(builder, dome, "Cloud", uv_for_face=common.shaded(rng, "Cloud", (BASE, LIGHT, DARK)))
    common.add(builder, common.centered_box(0.5, 0.5, 0.6, SILO_HEIGHT + 2.4), "MapleRed")

    ladder_y = SILO_RADIUS + 0.25
    for side in (-1.0, 1.0):
        x = side * SILO_LADDER_WIDTH * 0.5
        common.add(builder, common.beam((x, ladder_y, 0.0), (x, ladder_y, SILO_HEIGHT + 0.6), SILO_LADDER_RAIL),
                   "Slate", DARK)
    for rung in range(SILO_LADDER_RUNGS):
        z = 1.2 + rung * (SILO_HEIGHT - 1.4) / (SILO_LADDER_RUNGS - 1)
        common.add(builder, common.beam((-SILO_LADDER_WIDTH * 0.5, ladder_y, z), (SILO_LADDER_WIDTH * 0.5, ladder_y, z),
                                        SILO_LADDER_RAIL * 0.8), "Slate", BASE)
    chute_w, chute_d, chute_h = SILO_CHUTE
    common.add(builder, common.centered_box(chute_w, chute_d, chute_h, 0.0, x=SILO_RADIUS + chute_w * 0.3), "Wood")


def _power_tower(builder):
    corners = ((-1, -1), (1, -1), (1, 1), (-1, 1))

    def leg_point(corner, z):
        half = TOWER_BASE_HALF + (TOWER_TOP_HALF - TOWER_BASE_HALF) * z / TOWER_HEIGHT
        return Vector((corner[0] * half, corner[1] * half, z))

    for corner in corners:
        common.add(builder, common.beam(leg_point(corner, -0.15), leg_point(corner, TOWER_HEIGHT), TOWER_LEG_WIDTH),
                   TOWER_COLOR)
    for level, (z0, z1) in enumerate(zip(TOWER_BRACE_LEVELS, TOWER_BRACE_LEVELS[1:])):
        for side in range(4):
            a, b = corners[side], corners[(side + 1) % 4]
            start, end = (a, b) if (level + side) % 2 == 0 else (b, a)
            common.add(builder, common.beam(leg_point(start, z0 + 0.3), leg_point(end, z1), TOWER_BRACE_WIDTH),
                       TOWER_COLOR, DARK)
        for side in range(4):
            a, b = corners[side], corners[(side + 1) % 4]
            common.add(builder, common.beam(leg_point(a, z1), leg_point(b, z1), TOWER_BRACE_WIDTH), TOWER_COLOR,
                       LIGHT)
    common.add(builder, common.beam((-TOWER_ARM_HALF, 0.0, TOWER_ARM_Z), (TOWER_ARM_HALF, 0.0, TOWER_ARM_Z),
                                    TOWER_ARM_SECTION), TOWER_COLOR, LIGHT)
    for side in (-1.0, 1.0):
        common.add(builder, common.beam((side * TOWER_ARM_HALF * 0.55, 0.0, TOWER_ARM_Z),
                                        (side * TOWER_TOP_HALF, 0.0, TOWER_HEIGHT - 0.3), TOWER_BRACE_WIDTH),
                   TOWER_COLOR, DARK)
        radius, height = TOWER_INSULATOR
        insulator = common.lathe(((radius * 0.6, -height), (radius, -height * 0.55), (radius * 0.6, -height * 0.4),
                                  (radius, 0.0)), 6)
        common.add(builder, insulator, "WallCream", matrix=Matrix.Translation((side * (TOWER_ARM_HALF - 0.25), 0.0,
                                                                                 TOWER_ARM_Z)))
    common.add(builder, common.pyramid(4, TOWER_TOP_HALF * math.sqrt(2.0) + 0.1, TOWER_CAP_HEIGHT,
                                       angle_offset=math.pi * 0.25), TOWER_COLOR, LIGHT,
               Matrix.Translation((0.0, 0.0, TOWER_HEIGHT)))
    for corner in corners:
        foot = leg_point(corner, 0.0)
        common.add(builder, common.centered_box(0.6, 0.6, 0.35, -0.1, x=foot.x, y=foot.y), "Stone", DARK)


def _power_wire(builder):
    """1 m span on +X: ring k sits at x = k / segments and sags by a parabola (0 at both ends)."""
    rings = []
    for k in range(WIRE_SEGMENTS + 1):
        t = k / WIRE_SEGMENTS
        z = -WIRE_SAG * 4.0 * t * (1.0 - t)
        ring = []
        for side in range(WIRE_SIDES):
            angle = math.pi * 0.25 + 2.0 * math.pi * side / WIRE_SIDES
            ring.append(builder.add_vertex((t, WIRE_RADIUS * math.cos(angle), z + WIRE_RADIUS * math.sin(angle))))
        rings.append(ring)
    uv = palette.flat_uv(WIRE_COLOR, BASE)
    for a, b in zip(rings, rings[1:]):
        for side in range(WIRE_SIDES):
            n = (side + 1) % WIRE_SIDES
            builder.add_face((a[side], a[n], b[n], b[side]), common.MATERIAL, uv)
    builder.add_face(tuple(reversed(rings[0])), common.MATERIAL, uv)
    builder.add_face(tuple(rings[-1]), common.MATERIAL, uv)


BUILDERS = {
    "SM_Steeple": _steeple,
    "SM_ClockTower": _clock_tower,
    "SM_SiloTall": _silo,
}


def build(spec, seed):
    """Builds one ground obstacle (chosen by spec.mesh_name) and returns its mesh object."""
    rng = random.Random(seed)
    builder = common.new_builder()
    if spec.mesh_name in TREE_CLUSTER_LAYOUTS:
        _tree_cluster(builder, spec, rng)
    elif spec.mesh_name == "SM_PowerTower":
        _power_tower(builder)
    elif spec.mesh_name == "SM_PowerWire":
        _power_wire(builder)
    else:
        BUILDERS[spec.mesh_name](builder, rng)
    obj = common.finish(builder, spec)
    if spec.mesh_name == "SM_PowerTower":
        attach_x = TOWER_ARM_HALF - 0.25
        common.add_socket(obj, "SOCKET_Wire_L", (-attach_x, 0.0, WIRE_ATTACH_Z))
        common.add_socket(obj, "SOCKET_Wire_R", (attach_x, 0.0, WIRE_ATTACH_Z))
    return obj


def validate(obj, spec):
    """Generic + obstacle checks (pivot, height band, sockets, sway, winding)."""
    return checks.validate_asset(obj, spec, RULES[spec.mesh_name])


def export(obj, spec, filepath):
    """FBX export; the power tower is re-imported in a fresh Blender to verify its wire sockets."""
    return checks.export_asset(obj, spec, RULES[spec.mesh_name], filepath)


def preview(spec, seed):
    """Auto-framed contact sheet with goose-size marker and altitude bands."""
    return preview_sheets.contact_sheet(spec, RULES[spec.mesh_name])
