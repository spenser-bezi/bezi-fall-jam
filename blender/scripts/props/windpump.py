"""Short farm windpump (<= 3.5 m): static lattice tower baked into the tile, plus a separate rotor object.

The rotor is its own mesh object (Rotor_01, Rotor_02, ...) parented to the tile, with its pivot at the hub and its
spin axis on local X. All windpumps on a tile face the same wind direction (+X), so the rotors keep an identity rest
rotation and share one looping action (A_Windpump_Spin: 360 degrees over 48 frames at 24 fps, linear) that keys
only rotation_euler[0].
"""
import math

import bpy
from mathutils import Matrix, Vector

from lib import hexgrid, materials, palette, shapes
from lib.builder import MeshBuilder
from props import farm_props

MATERIAL = materials.PALETTE_MATERIAL
DECOR_HEIGHT_MARGIN = 0.08

HUB_HEIGHT = 2.62
HUB_FORWARD = 0.34
TOWER_BASE_HALF = 0.5
TOWER_TOP_HALF = 0.13
TOWER_TOP_BELOW_HUB = 0.12
LEG_SIZE = 0.09
BRACE_SIZE = 0.06
BRACE_FRACTION = 0.42
PLATFORM_SIZE = 0.42
PLATFORM_THICKNESS = 0.08
HEAD_SIZE = (0.5, 0.2, 0.2)
TAIL_LENGTH = 0.95
TAIL_SIZE = 0.06
VANE_SIZE = (0.04, 0.62, 0.42)
PUMP_BOX_SIZE = (0.3, 0.3, 0.45)
TOWER_COLOR = ("Wood", palette.SHADE_DARK)
VANE_COLOR = ("MapleRed", palette.SHADE_BASE)

ROTOR_RADIUS = 0.7
ROTOR_BLADES = 8
BLADE_ROOT_RADIUS = 0.14
BLADE_ROOT_WIDTH = 0.12
BLADE_TIP_WIDTH = 0.25
BLADE_THICKNESS = 0.035
BLADE_PITCH_DEG = 28.0
HUB_SIDES = 6
HUB_RADIUS = 0.13
HUB_LENGTH = 0.2
BLADE_COLORS = (("WallCream", palette.SHADE_BASE), ("MapleRed", palette.SHADE_BASE))
HUB_COLOR = ("Slate", palette.SHADE_DARK)

ROTOR_NAME = "Rotor_{:02d}"
SPIN_ACTION_NAME = "A_Windpump_Spin"
SPIN_FPS = 24
SPIN_FRAME_START = 0
SPIN_FRAME_COUNT = 48
SPIN_AXIS_INDEX = 0


def rotor_tip_radius():
    """Largest distance of any rotor vertex from the hub (blade tip corner)."""
    return math.hypot(ROTOR_RADIUS, BLADE_TIP_WIDTH * 0.5)


def _oriented_convex(vertices, faces):
    """Returns a Part whose faces are flipped where needed so every normal points away from the centroid."""
    points = [Vector(v) for v in vertices]
    center = sum(points, Vector((0.0, 0.0, 0.0))) / len(points)
    oriented = []
    for face in faces:
        a, b, c = (points[i] for i in face[:3])
        face_center = sum((points[i] for i in face), Vector((0.0, 0.0, 0.0))) / len(face)
        oriented.append(face if (b - a).cross(c - a).dot(face_center - center) > 0.0 else tuple(reversed(face)))
    return shapes.Part(points, oriented)


def _blade_part(angle):
    """One pitched, tapered blade (10 tris) radiating at angle around the X spin axis."""
    pitch = math.radians(BLADE_PITCH_DEG)
    vertices = []
    for radius, width in ((BLADE_ROOT_RADIUS, BLADE_ROOT_WIDTH), (ROTOR_RADIUS, BLADE_TIP_WIDTH)):
        for tangential in (-width * 0.5, width * 0.5):
            for axial in (-BLADE_THICKNESS * 0.5, BLADE_THICKNESS * 0.5):
                a = axial * math.cos(pitch) - tangential * math.sin(pitch)
                t = axial * math.sin(pitch) + tangential * math.cos(pitch)
                vertices.append((a, radius, t))
    faces = [(0, 2, 6, 4), (1, 5, 7, 3), (0, 4, 5, 1), (2, 3, 7, 6), (4, 6, 7, 5)]
    part = _oriented_convex(vertices, faces)
    rotation = Matrix.Rotation(angle, 4, "X")
    part.vertices = [rotation @ v for v in part.vertices]
    return part


def rotor_triangles():
    """Triangle count of one rotor."""
    return ROTOR_BLADES * 10 + 2 * HUB_SIDES + (HUB_SIDES - 2) + HUB_SIDES


def build_rotor_mesh(builder):
    """Adds the rotor (hub, nose cone, pitched blades) centered on the hub with its spin axis on local X."""
    hub_matrix = Matrix.Rotation(math.radians(90.0), 4, "Y") @ Matrix.Translation((0.0, 0.0, -HUB_LENGTH * 0.5))
    hub = shapes.prism(HUB_SIDES, HUB_RADIUS, HUB_LENGTH, cap_top=False, cap_bottom=True)
    builder.add_part(hub, hub_matrix, MATERIAL, lambda face, centroid: palette.flat_uv(*HUB_COLOR))
    nose = shapes.cone(HUB_SIDES, HUB_RADIUS, HUB_RADIUS * 1.1)
    builder.add_part(nose, Matrix.Rotation(math.radians(90.0), 4, "Y") @ Matrix.Translation((0.0, 0.0, HUB_LENGTH * 0.5)),
                     MATERIAL, lambda face, centroid: palette.flat_uv("Slate", palette.SHADE_BASE))
    for blade in range(ROTOR_BLADES):
        color = BLADE_COLORS[blade % len(BLADE_COLORS)]
        builder.add_part(_blade_part(2.0 * math.pi * blade / ROTOR_BLADES), Matrix.Identity(4), MATERIAL,
                         lambda face, centroid, c=color: palette.flat_uv(*c))


def hub_height(base_z):
    """World hub height for a windpump standing at base_z, clamped so the blade tips stay under 3.5 m."""
    return min(base_z + HUB_HEIGHT, hexgrid.MAX_DECOR_HEIGHT - DECOR_HEIGHT_MARGIN - rotor_tip_radius())


def add_windpump_tower(builder, rng, x, y, base_z):
    """Adds the static windpump (lattice tower, platform, gearbox head, red tail vane, pump box).

    Returns the world hub position for the matching rotor object.
    """
    hub_z = hub_height(base_z)
    top_z = hub_z - TOWER_TOP_BELOW_HUB
    tower_uv = lambda face, centroid: palette.flat_uv(*TOWER_COLOR)  # noqa: E731
    corners = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
    bottoms = [Vector((x + sx * TOWER_BASE_HALF, y + sy * TOWER_BASE_HALF, base_z - farm_props.GROUND_SINK))
               for sx, sy in corners]
    tops = [Vector((x + sx * TOWER_TOP_HALF, y + sy * TOWER_TOP_HALF, top_z)) for sx, sy in corners]
    for bottom, top in zip(bottoms, tops):
        farm_props.add_beam(builder, bottom, top, LEG_SIZE, tower_uv)
    braces = [bottom.lerp(top, BRACE_FRACTION) for bottom, top in zip(bottoms, tops)]
    for k in range(len(braces)):
        farm_props.add_beam(builder, braces[k], braces[(k + 1) % len(braces)], BRACE_SIZE,
                            lambda face, centroid: palette.flat_uv("Wood", palette.SHADE_BASE))

    platform = farm_props.open_box(PLATFORM_SIZE, PLATFORM_SIZE, PLATFORM_THICKNESS)
    builder.add_part(platform, Matrix.Translation((x, y, top_z - PLATFORM_THICKNESS)), MATERIAL,
                     lambda face, centroid: palette.flat_uv("Wood", palette.SHADE_BASE))
    head = farm_props.open_box(*HEAD_SIZE)
    builder.add_part(head, Matrix.Translation((x + HUB_FORWARD * 0.35, y, top_z)), MATERIAL,
                     lambda face, centroid: palette.flat_uv("Slate", palette.SHADE_BASE))
    tail_start = Vector((x, y, top_z + HEAD_SIZE[2] * 0.5))
    tail_end = Vector((x - TAIL_LENGTH, y, top_z + HEAD_SIZE[2] * 0.5))
    farm_props.add_beam(builder, tail_start, tail_end, TAIL_SIZE,
                        lambda face, centroid: palette.flat_uv("Slate", palette.SHADE_DARK))
    vane = farm_props.open_box(VANE_SIZE[1], VANE_SIZE[0], VANE_SIZE[2])
    builder.add_part(vane, Matrix.Translation((tail_end.x, y, tail_end.z - VANE_SIZE[2] * 0.5)), MATERIAL,
                     lambda face, centroid: palette.flat_uv(*VANE_COLOR))
    pump = farm_props.open_box(*PUMP_BOX_SIZE)
    builder.add_part(pump, Matrix.Translation((x, y, base_z - farm_props.GROUND_SINK)), MATERIAL,
                     lambda face, centroid: palette.flat_uv("Slate", palette.SHADE_DARK))
    return Vector((x + HUB_FORWARD, y, hub_z))


def tower_triangles():
    """Triangle count of one static windpump tower."""
    return 4 * 8 + 4 * 8 + 10 + 10 + 8 + 10 + 10


def create_rotor(index, tile_object, hub_location):
    """Creates rotor object Rotor_<index> with its pivot at the hub, parented to the tile in the tile's collection."""
    builder = MeshBuilder()
    build_rotor_mesh(builder)
    collection = tile_object.users_collection[0]
    rotor = builder.build_object(ROTOR_NAME.format(index), collection)
    for other in tile_object.users_collection[1:]:
        other.objects.link(rotor)
    rotor.location = hub_location
    rotor.parent = tile_object
    rotor.matrix_parent_inverse = Matrix.Identity(4)
    return rotor


def spin_action():
    """Returns (creating if needed) the looping A_Windpump_Spin action: 360 degrees about local X, linear."""
    action = bpy.data.actions.get(SPIN_ACTION_NAME)
    if action is not None:
        return action
    action = bpy.data.actions.new(SPIN_ACTION_NAME)
    action.use_fake_user = True
    curve = action.fcurves.new("rotation_euler", index=SPIN_AXIS_INDEX)
    curve.keyframe_points.add(2)
    for point, (frame, value) in zip(curve.keyframe_points,
                                     ((SPIN_FRAME_START, 0.0), (SPIN_FRAME_START + SPIN_FRAME_COUNT, 2.0 * math.pi))):
        point.co = (frame, value)
        point.interpolation = "LINEAR"
        point.handle_left_type = point.handle_right_type = "VECTOR"
    curve.update()
    action.use_frame_range = True
    action.frame_start = SPIN_FRAME_START
    action.frame_end = SPIN_FRAME_START + SPIN_FRAME_COUNT
    action.use_cyclic = True
    return action


def assign_spin(rotors):
    """Assigns the shared spin action to every rotor and sets the scene to 24 fps over the loop range."""
    action = spin_action()
    for rotor in rotors:
        rotor.animation_data_create()
        rotor.animation_data.action = action
    scene = bpy.context.scene
    scene.render.fps = SPIN_FPS
    scene.render.fps_base = 1.0
    scene.frame_start = SPIN_FRAME_START
    scene.frame_end = SPIN_FRAME_START + SPIN_FRAME_COUNT
    return action
