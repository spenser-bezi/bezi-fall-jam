"""Low-flying crop-duster (GDD 5.8 High band, sometimes Mid): SM_Plane body + separate SM_Plane_Prop.

The body faces Blender -Y (Unity +Z) with its pivot at the bounds center and marks the spinner with the
SOCKET_Propeller child empty. The propeller pivots at the spinner base and spins about Blender Y (Unity Z) with the
looping A_Plane_PropSpin take. Gameplay code yaws the whole plane to cross the corridor.
"""
import math
import random

from mathutils import Matrix

from lib import palette
from obstacles import checks, common, preview_sheets
from obstacles.common import BASE, DARK, LIGHT

BAND_NOTE = "High band 26-40 m (spawn ~33 m); 12 m span, ~4 m tall"
BODY_COLOR = "HarvestGold"
TRIM_COLOR = "MapleRed"
COWL_COLOR = "Slate"
NOSE_TO_TAIL = Matrix.Rotation(math.pi * 0.5, 4, "X")  # lathe axis +Z -> Blender -Y (nose forward)

FUSELAGE_SIDES = 8
FUSELAGE_PROFILE = ((0.22, -5.0), (0.5, -3.6), (0.82, -1.4), (0.95, 0.4), (0.92, 1.9), (0.82, 2.7), (0.78, 3.4))
COWL_FIRST_BAND = 4
TRIM_BAND = 2
NOSE_Y = -FUSELAGE_PROFILE[-1][1]

WING_HALF_SPAN = 6.0
WING_TIP_START = 4.9
WING_LEADING_Y = -0.9
WING_CHORD = 2.0
WING_THICKNESS = 0.26
WING_Z = -0.6
TAIL_HALF_SPAN = 2.2
TAIL_LEADING_Y = 3.8
TAIL_CHORD = 1.0
TAIL_THICKNESS = 0.16
TAIL_Z = 0.15
FIN_Y = (3.7, 5.0)
FIN_TOP = 2.1
FIN_THICKNESS = 0.16
CANOPY = (0.95, (-0.2, 1.3), (0.55, 1.4))  # width, y range, z range
GEAR_X = 1.3
GEAR_TOP_Z = WING_Z
GEAR_WHEEL_Z = -1.75
GEAR_STRUT = 0.16
WHEEL_RADIUS = 0.42
WHEEL_WIDTH = 0.3
WHEEL_SIDES = 8
TAIL_WHEEL = (4.6, -0.55, 0.18)  # y, z, radius

SPINNER_PROFILE = ((0.45, 0.0), (0.38, 0.35), (0.2, 0.62), (0.0, 0.78))
PROP_RADIUS = 1.65
PROP_ROOT_WIDTH = 0.32
PROP_TIP_WIDTH = 0.24
PROP_THICKNESS = 0.14
PROP_TIP_LENGTH = 0.3
PROP_BLADES = 2
PROP_ROOT_Y = -0.12
SPIN_CLIP = common.SpinClip("A_Plane_PropSpin", 8, direction=-1.0)

RULES = {
    "SM_Plane": common.AssetRules(common.PIVOT_CENTER, (2.5, 5.0), max_dimension_range=(9.0, 14.0),
                                  sockets=("SOCKET_Propeller",), band_note=BAND_NOTE, verify_fbx=True,
                                  extra={"attach": ("obstacle.plane_prop", "SOCKET_Propeller")}),
    "SM_Plane_Prop": common.AssetRules(common.PIVOT_HUB, (2.0, 3.6), spin=SPIN_CLIP,
                                       band_note="mounts at SM_Plane/SOCKET_Propeller"),
}


def _fuselage_uv(rng):
    def uv(face, centroid):
        band = face // FUSELAGE_SIDES
        if band >= COWL_FIRST_BAND:
            return palette.flat_uv(COWL_COLOR, rng.choice((BASE, DARK)))
        if band == TRIM_BAND:
            return palette.flat_uv(TRIM_COLOR, BASE)
        return palette.flat_uv(BODY_COLOR, rng.choice((BASE, BASE, LIGHT)))
    return uv


def _wheel(builder, x, y, z, radius, width):
    wheel = common.lathe(((radius, -width * 0.5), (radius, width * 0.5)), WHEEL_SIDES)
    common.add(builder, wheel, "GooseCharcoal", BASE,
               Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.pi * 0.5, 4, "Y"))


def _body(builder, rng):
    fuselage = common.lathe(FUSELAGE_PROFILE, FUSELAGE_SIDES, angle_offset=math.pi / FUSELAGE_SIDES)
    common.add(builder, fuselage, BODY_COLOR, uv_for_face=_fuselage_uv(rng), matrix=NOSE_TO_TAIL)

    wing_y0, wing_y1 = WING_LEADING_Y, WING_LEADING_Y + WING_CHORD
    wing_z0, wing_z1 = WING_Z - WING_THICKNESS * 0.5, WING_Z + WING_THICKNESS * 0.5
    common.add(builder, common.box(-WING_TIP_START, WING_TIP_START, wing_y0, wing_y1, wing_z0, wing_z1), BODY_COLOR,
               uv_for_face=common.shaded(rng, BODY_COLOR, (BASE, LIGHT)))
    for side in (-1.0, 1.0):
        x0, x1 = sorted((side * WING_TIP_START, side * WING_HALF_SPAN))
        common.add(builder, common.box(x0, x1, wing_y0 + 0.15, wing_y1 - 0.1, wing_z0 + 0.02, wing_z1 - 0.02),
                   TRIM_COLOR)

    tail_y1 = TAIL_LEADING_Y + TAIL_CHORD
    common.add(builder, common.box(-TAIL_HALF_SPAN, TAIL_HALF_SPAN, TAIL_LEADING_Y, tail_y1,
                                   TAIL_Z - TAIL_THICKNESS * 0.5, TAIL_Z + TAIL_THICKNESS * 0.5), BODY_COLOR, LIGHT)
    common.add(builder, common.box(-FIN_THICKNESS * 0.5, FIN_THICKNESS * 0.5, FIN_Y[0], FIN_Y[1], 0.2, FIN_TOP),
               TRIM_COLOR)

    width, (y0, y1), (z0, z1) = CANOPY
    common.add(builder, common.box(-width * 0.5, width * 0.5, y0, y1, z0, z1), "SkyBlue", DARK)

    for side in (-1.0, 1.0):
        x = side * GEAR_X
        common.add(builder, common.beam((x * 0.7, 0.0, GEAR_TOP_Z), (x, -0.2, GEAR_WHEEL_Z), GEAR_STRUT),
                   "GooseCharcoal", BASE)
        _wheel(builder, x + side * (WHEEL_WIDTH * 0.5 + 0.02), -0.2, GEAR_WHEEL_Z, WHEEL_RADIUS, WHEEL_WIDTH)
    tail_y, tail_z, tail_radius = TAIL_WHEEL
    _wheel(builder, 0.0, tail_y, tail_z - 0.35, tail_radius, tail_radius * 0.8)
    common.add(builder, common.beam((0.0, tail_y - 0.15, tail_z), (0.0, tail_y, tail_z - 0.35), GEAR_STRUT * 0.8),
               "GooseCharcoal", BASE)


def _propeller(builder):
    spinner = common.lathe(SPINNER_PROFILE, FUSELAGE_SIDES)
    common.add(builder, spinner, TRIM_COLOR, matrix=NOSE_TO_TAIL)
    for blade in range(PROP_BLADES):
        rotation = Matrix.Rotation(math.pi * 0.25 + blade * 2.0 * math.pi / PROP_BLADES, 4, "Y")
        y0, y1 = PROP_ROOT_Y - PROP_THICKNESS * 0.5, PROP_ROOT_Y + PROP_THICKNESS * 0.5
        tip_start = PROP_RADIUS - PROP_TIP_LENGTH
        blade_part = common.box(0.0, tip_start, y0, y1, -PROP_ROOT_WIDTH * 0.5, PROP_ROOT_WIDTH * 0.5)
        tip_part = common.box(tip_start, PROP_RADIUS, y0, y1, -PROP_TIP_WIDTH * 0.5, PROP_TIP_WIDTH * 0.5)
        common.add(builder, blade_part, "GooseCharcoal", BASE, rotation)
        common.add(builder, tip_part, "HarvestGold", BASE, rotation)


def build(spec, seed):
    """Builds the plane body (with SOCKET_Propeller) or the propeller (with A_Plane_PropSpin)."""
    rng = random.Random(seed)
    builder = common.new_builder()
    if spec.mesh_name == "SM_Plane":
        _body(builder, rng)
        offset = common.recenter(builder)
        obj = common.finish(builder, spec)
        common.add_socket(obj, "SOCKET_Propeller", (-offset.x, NOSE_Y - offset.y, -offset.z))
        return obj
    _propeller(builder)
    obj = common.finish(builder, spec)
    common.add_spin_clip(obj, SPIN_CLIP)
    return obj


def validate(obj, spec):
    """Generic + obstacle checks; the propeller also checks its spin clip."""
    return checks.validate_asset(obj, spec, RULES[spec.mesh_name])


def export(obj, spec, filepath):
    """FBX export with fresh-Blender re-import verification (socket / spin take)."""
    return checks.export_asset(obj, spec, RULES[spec.mesh_name], filepath)


def preview(spec, seed):
    """Auto-framed contact sheet with a goose-size marker."""
    return preview_sheets.contact_sheet(spec, RULES[spec.mesh_name])
