"""Windmill obstacle (GDD 5.8 Low-Mid): SM_Windmill_Base tower + separate SM_Windmill_Blades rotor.

The base pivots at its base center and marks the rotor hub with the SOCKET_Blades child empty. The blades pivot at
the hub and spin about Blender Y (Unity Z, the flight direction), so geese fly through the gaps between the sails.
A_Windmill_Spin turns the rotor 360 degrees over 96 frames (linear, loops seamlessly).
"""
import math
import random

from mathutils import Matrix, Vector

from obstacles import checks, common, preview_sheets
from obstacles.common import BASE, DARK, LIGHT

BAND_NOTE = "Low-Mid: hub at 13 m, sail tips sweep 4.5-21.5 m"

TOWER_SIDES = 8
TOWER_FACE_ANGLE = 3.0 * math.pi / TOWER_SIDES  # puts a flat octagon face toward +Y (the approaching flock)
PLINTH_RADIUS = 3.55
PLINTH_HEIGHT = 1.0
TOWER_BASE_RADIUS = 3.2
TOWER_TOP_RADIUS = 2.0
TOWER_TOP_Z = 11.0
STAGE_Z = 3.2
STAGE_RADIUS = 3.9
STAGE_THICKNESS = 0.3
CAP_PROFILE = ((2.45, 11.0), (2.45, 11.4), (2.3, 12.4), (1.75, 13.5), (0.9, 14.25), (0.0, 14.55))
CAP_COLOR = "MapleRed"
HUB_Z = 13.0
HUB_Y = 3.1
AXLE_RADIUS = 0.38
AXLE_SIDES = 6
DOOR = (1.3, 2.3)
WINDOW = (0.75, 1.1)
WINDOW_HEIGHTS = (6.3, 9.2)
FACADE_DEPTH = 0.16

BLADE_COUNT = 4
BLADE_RADIUS = 8.5
BLADE_ANGLE_OFFSET = math.pi * 0.25  # X pose at rest
SPAR_WIDTH = 0.38
SPAR_DEPTH = 0.3
SAIL_START = 1.5
SAIL_END = 8.2
SAIL_WIDTH = 1.9
SAIL_THICKNESS = 0.12
SAIL_SLATS = 4
SLAT_WIDTH = 0.16
HUB_CAP_PROFILE = ((0.62, -0.25), (0.62, 0.35), (0.35, 0.65), (0.0, 0.75))
HUB_CAP_SIDES = 8

SPIN_CLIP = common.SpinClip("A_Windmill_Spin", 96)

RULES = {
    "SM_Windmill_Base": common.AssetRules(common.PIVOT_BASE, (13.5, 16.0), sockets=("SOCKET_Blades",),
                                          band_note=BAND_NOTE, verify_fbx=True,
                                          extra={"attach": ("obstacle.windmill_blades", "SOCKET_Blades")}),
    "SM_Windmill_Blades": common.AssetRules(common.PIVOT_HUB, (13.0, 18.0), spin=SPIN_CLIP,
                                            band_note=BAND_NOTE + "; gaps ~5 m wide at mid-radius (goose 2.5 m)"),
}


def _tower_radius(z):
    return TOWER_BASE_RADIUS + (TOWER_TOP_RADIUS - TOWER_BASE_RADIUS) * min(1.0, max(0.0, z / TOWER_TOP_Z))


def _facade(builder, color, shade, width, height, z_center):
    """Adds a door/window plate on the +Y octagon face at a height, following the taper."""
    apothem = _tower_radius(z_center) * math.cos(math.pi / TOWER_SIDES)
    taper = math.atan2(TOWER_BASE_RADIUS - TOWER_TOP_RADIUS, TOWER_TOP_Z)
    plate = common.box(-width * 0.5, width * 0.5, -FACADE_DEPTH, FACADE_DEPTH, -height * 0.5, height * 0.5)
    matrix = Matrix.Translation((0.0, apothem, z_center)) @ Matrix.Rotation(taper, 4, "X")
    common.add(builder, plate, color, shade, matrix)


def _base(builder, rng):
    common.add(builder, common.lathe(((PLINTH_RADIUS, -0.1), (PLINTH_RADIUS, PLINTH_HEIGHT)), TOWER_SIDES,
                                     TOWER_FACE_ANGLE), "Stone", uv_for_face=common.shaded(rng, "Stone", (BASE, DARK)))
    tower = common.lathe(((TOWER_BASE_RADIUS, PLINTH_HEIGHT - 0.05), (_tower_radius(STAGE_Z), STAGE_Z),
                          (TOWER_TOP_RADIUS, TOWER_TOP_Z)), TOWER_SIDES, TOWER_FACE_ANGLE)
    common.add(builder, tower, "WallCream", uv_for_face=common.shaded(rng, "WallCream", (BASE, BASE, LIGHT, DARK)))
    stage = common.lathe(((STAGE_RADIUS, STAGE_Z), (STAGE_RADIUS, STAGE_Z + STAGE_THICKNESS)), TOWER_SIDES,
                         TOWER_FACE_ANGLE)
    common.add(builder, stage, "Wood", DARK)
    common.add(builder, common.lathe(CAP_PROFILE, TOWER_SIDES, TOWER_FACE_ANGLE), CAP_COLOR,
               uv_for_face=common.shaded(rng, CAP_COLOR, (BASE, LIGHT, DARK)))
    axle = common.lathe(((AXLE_RADIUS, 0.0), (AXLE_RADIUS, HUB_Y - 0.6)), AXLE_SIDES)
    common.add(builder, axle, "Wood", DARK,
               Matrix.Translation((0.0, 0.6, HUB_Z)) @ Matrix.Rotation(-math.pi * 0.5, 4, "X"))

    door_w, door_h = DOOR
    _facade(builder, "Wood", DARK, door_w, door_h, PLINTH_HEIGHT + door_h * 0.5 - 0.05)
    window_w, window_h = WINDOW
    for z in WINDOW_HEIGHTS:
        _facade(builder, "HarvestGold", LIGHT, window_w, window_h, z)


def _arm_matrix(angle):
    """Local frame of one blade arm: X along the arm (in the XZ plane), Y = spin axis, Z = across the arm."""
    direction = Vector((math.cos(angle), 0.0, math.sin(angle)))
    across = Vector((-direction.z, 0.0, direction.x))
    matrix = Matrix.Identity(4)
    for row in range(3):
        matrix[row][0], matrix[row][1], matrix[row][2] = direction[row], (0.0, 1.0, 0.0)[row], across[row]
    return matrix


def _blades(builder, rng):
    for blade in range(BLADE_COUNT):
        frame = _arm_matrix(BLADE_ANGLE_OFFSET + blade * 2.0 * math.pi / BLADE_COUNT)
        spar = common.box(0.0, BLADE_RADIUS, 0.0, SPAR_DEPTH, -SPAR_WIDTH * 0.5, SPAR_WIDTH * 0.5)
        common.add(builder, spar, "Wood", DARK, frame)
        sail_y0 = SPAR_DEPTH * 0.3
        sail = common.box(SAIL_START, SAIL_END, sail_y0, sail_y0 + SAIL_THICKNESS, SPAR_WIDTH * 0.5,
                          SPAR_WIDTH * 0.5 + SAIL_WIDTH)
        common.add(builder, sail, "WallCream", uv_for_face=common.shaded(rng, "WallCream", (BASE, LIGHT)),
                   matrix=frame)
        for slat in range(SAIL_SLATS):
            x = SAIL_START + (SAIL_END - SAIL_START) * (slat + 0.5) / SAIL_SLATS
            slat_part = common.box(x - SLAT_WIDTH * 0.5, x + SLAT_WIDTH * 0.5, sail_y0 + SAIL_THICKNESS,
                                   sail_y0 + SAIL_THICKNESS + SLAT_WIDTH * 0.6, SPAR_WIDTH * 0.5,
                                   SPAR_WIDTH * 0.5 + SAIL_WIDTH)
            common.add(builder, slat_part, "Wood", BASE, frame)
    hub = common.lathe(HUB_CAP_PROFILE, HUB_CAP_SIDES)
    common.add(builder, hub, CAP_COLOR, DARK, Matrix.Rotation(-math.pi * 0.5, 4, "X"))


def build(spec, seed):
    """Builds the windmill base (with SOCKET_Blades) or the spinning blade rotor (with A_Windmill_Spin)."""
    rng = random.Random(seed)
    builder = common.new_builder()
    if spec.mesh_name == "SM_Windmill_Base":
        _base(builder, rng)
        obj = common.finish(builder, spec)
        common.add_socket(obj, "SOCKET_Blades", (0.0, HUB_Y, HUB_Z))
        return obj
    _blades(builder, rng)
    obj = common.finish(builder, spec)
    common.add_spin_clip(obj, SPIN_CLIP)
    return obj


def validate(obj, spec):
    """Generic + obstacle checks; the rotor also checks its spin clip."""
    return checks.validate_asset(obj, spec, RULES[spec.mesh_name])


def export(obj, spec, filepath):
    """FBX export with fresh-Blender re-import verification (sockets / spin take)."""
    return checks.export_asset(obj, spec, RULES[spec.mesh_name], filepath)


def preview(spec, seed):
    """Auto-framed contact sheet with goose-size marker and altitude bands (the base previews with its rotor)."""
    return preview_sheets.contact_sheet(spec, RULES[spec.mesh_name])
