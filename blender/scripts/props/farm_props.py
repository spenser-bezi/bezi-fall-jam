"""Farmland prop kit: ridged corn rows, corn stubble, scarecrow, pumpkins, vines, crates, cart, square hay bales,
red barn, small silo and a cheap post-and-rail fence.

Every prop bakes into a MeshBuilder. Vertex color R carries the sway weight: crops and leaves sway, buildings,
fences and wooden props stay at 0. Tall props are scaled down so they stay under the 3.5 m decor limit.
"""
import math

from mathutils import Matrix, Vector

from lib import hexgrid, materials, palette, shapes
from props import kit

MATERIAL = materials.PALETTE_MATERIAL
DECOR_HEIGHT_MARGIN = 0.1
GROUND_SINK = 0.12

CORN_SEGMENT_LENGTH = 1.25
CORN_BASE_HALF_WIDTH = 0.3
CORN_MID_HALF_WIDTH = 0.5
CORN_MID_HEIGHT = 1.0
CORN_TOP_HEIGHTS = (1.6, 2.2)
CORN_END_TOP_FACTOR = 0.72
CORN_TOP_JITTER = 0.12
CORN_TOP_SIDE_JITTER = 0.08
CORN_MID_SWAY = 0.4
CORN_TOP_SWAY = 1.0
CORN_STALK_COLORS = (("DryGrass", palette.SHADE_BASE), ("DryGrass", palette.SHADE_DARK), ("Moss", palette.SHADE_LIGHT))
CORN_LEAF_COLORS = (("HarvestGold", palette.SHADE_BASE), ("HarvestGold", palette.SHADE_LIGHT),
                    ("Mustard", palette.SHADE_BASE), ("HarvestGold", palette.SHADE_BASE))

STUBBLE_SEGMENT_LENGTH = 1.25
STUBBLE_HALF_WIDTH = 0.22
STUBBLE_HEIGHT = 0.28
STUBBLE_SWAY = 0.2

SCARECROW_POST_HEIGHT = 2.05
SCARECROW_POST_SIZE = 0.1
SCARECROW_ARM_HEIGHT = 1.45
SCARECROW_ARM_SPAN = 1.5
SCARECROW_ARM_SIZE = 0.08
SCARECROW_SHIRT_SIZE = (0.5, 0.3, 0.65)
SCARECROW_SHIRT_BOTTOM = 0.95
SCARECROW_HEAD_RADIUS = 0.22
SCARECROW_HEAD_Z = 1.85
SCARECROW_HAT_BRIM_RADIUS = 0.36
SCARECROW_HAT_BRIM_HEIGHT = 0.05
SCARECROW_HAT_HEIGHT = 0.42
SCARECROW_HAT_RADIUS = 0.2
SCARECROW_SWAY = 0.15

PUMPKIN_SEGMENTS = 7
PUMPKIN_SQUASH = 0.66
PUMPKIN_TOP_FLATTEN = 0.8
PUMPKIN_SINK_FACTOR = 0.2
PUMPKIN_STEM_SIDES = 4
PUMPKIN_STEM_RADIUS_FACTOR = 0.16
PUMPKIN_STEM_HEIGHT_FACTOR = 0.5
PUMPKIN_TRIANGLES = 3 * PUMPKIN_SEGMENTS + PUMPKIN_STEM_SIDES

VINE_LIFT = 0.05
VINE_SWAY = 0.3
LEAF_SEGMENTS = (5, 2)
LEAF_SQUASH = 0.38
LEAF_SWAY = 0.45
LEAF_TRIANGLES = 2 * LEAF_SEGMENTS[0]

CRATE_SIZE = 0.75
CRATE_HEIGHT = 0.55
CRATE_TRIANGLES = 10

CART_BED_SIZE = (1.7, 1.05, 0.32)
CART_BED_Z = 0.42
CART_WHEEL_RADIUS = 0.42
CART_WHEEL_WIDTH = 0.1
CART_WHEEL_SIDES = 6
CART_HANDLE_LENGTH = 1.0
CART_HANDLE_SIZE = 0.07
CART_LEG_SIZE = 0.1
CART_LOAD_RADIUS = 0.3

SQUARE_BALE_SIZE = (1.1, 0.6, 0.55)
SQUARE_BALE_TRIANGLES = 10
ROUND_BALE_TRIANGLES = 4 * kit.HAY_SIDES - 4

BARN_LENGTH = 4.6
BARN_WIDTH = 3.2
BARN_WALL = 1.75
BARN_KNEE_HEIGHT = 2.55
BARN_KNEE_FRACTION = 0.62
BARN_RIDGE = 3.0
BARN_ROOF_THICKNESS = 0.14
BARN_ROOF_OVERHANG = 0.22
BARN_ROOF_END_OVERHANG = 0.18
BARN_DOOR_HALF_WIDTH = 0.65
BARN_DOOR_HEIGHT = 1.45
BARN_LOFT_HALF_SIZE = 0.28
BARN_TRIM_THICKNESS = 0.06
FACADE_OFFSET = 0.02

SILO_SIDES = 8
SILO_RADIUS = 0.78
SILO_HEIGHT = 2.45
SILO_DOME_RADIUS = 0.86
SILO_DOME_HEIGHT = 0.75
SILO_BAND_HEIGHTS = (0.8, 1.6)

FENCE_POST_SIZE = 0.12
FENCE_POST_HEIGHT = 0.85
FENCE_RAIL_SIZE = 0.07
FENCE_RAIL_HEIGHTS = (0.35, 0.68)
FENCE_POST_TRIANGLES = 10
FENCE_RAIL_TRIANGLES = 8


def _placement(x, y, z, rotation=0.0, scale=1.0):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(rotation, 4, "Z") @ Matrix.Scale(scale, 4)


def _flat(name, shade=palette.SHADE_BASE):
    uv = palette.flat_uv(name, shade)
    return lambda face, centroid: uv


def _fit_scale(base_z, local_top):
    """Uniform scale that keeps a prop's top below the decor height limit."""
    return min(1.0, (hexgrid.MAX_DECOR_HEIGHT - DECOR_HEIGHT_MARGIN - base_z) / local_top)


def extrude_profile(profile, x_min, x_max, skip_edges=(), caps=True):
    """Extrudes a (y, z) profile along X. The profile must run clockwise seen from +X (y right, z up),
    which makes side faces point outward. Face order: side faces by edge (minus skip_edges), then caps."""
    count = len(profile)
    vertices = [(x_min, y, z) for y, z in profile] + [(x_max, y, z) for y, z in profile]
    faces = []
    for k in range(count):
        if k in skip_edges:
            continue
        n = (k + 1) % count
        faces.append((k, count + k, count + n, n))
    if caps:
        faces.append(tuple(range(count)))
        faces.append(tuple(count + k for k in reversed(range(count))))
    return shapes.Part(vertices, faces)


def open_box(size_x, size_y, size_z):
    """Box centered on X/Y standing on z = 0 without a bottom face (10 tris)."""
    half_y = size_y * 0.5
    return extrude_profile([(-half_y, 0.0), (-half_y, size_z), (half_y, size_z), (half_y, 0.0)],
                           -size_x * 0.5, size_x * 0.5, skip_edges=(3,))


def add_beam(builder, start, end, size, uv_for_face, sway=0.0):
    """Adds a square-section beam without end caps (8 tris) between two world points."""
    start, end = Vector(start), Vector(end)
    direction = end - start
    half = size * 0.5
    beam = extrude_profile([(-half, -half), (-half, half), (half, half), (half, -half)], 0.0, direction.length,
                           caps=False)
    rotation = Vector((1.0, 0.0, 0.0)).rotation_difference(direction.normalized()).to_matrix().to_4x4()
    builder.add_part(beam, Matrix.Translation(start) @ rotation, MATERIAL, uv_for_face,
                     (lambda local: sway) if sway else None)


def _row_stations(start, end, segment_length):
    start, end = Vector((start[0], start[1], 0.0)), Vector((end[0], end[1], 0.0))
    count = max(1, math.ceil((end - start).length / segment_length))
    return [start.lerp(end, k / count) for k in range(count + 1)]


def add_corn_row(builder, rng, start, end, height_at):
    """Adds a ridged corn row strip (stalk band below, golden leaf ridge above) between two planar points.

    The ridge top zigzags in height for a chunky stalk silhouette and dips at both ends. Returns the list of
    (x, y, top_z) ridge points, useful for snack sockets. Triangles: 8 per segment + 6 for the end caps.
    """
    stations = _row_stations(start, end, CORN_SEGMENT_LENGTH)
    forward = (stations[-1] - stations[0]).normalized()
    left = Vector((-forward.y, forward.x, 0.0))
    profile_count = 5
    vertices, sways, tops = [], [], []
    for k, point in enumerate(stations):
        ground = height_at(point.x, point.y)
        top = CORN_TOP_HEIGHTS[k % 2] + rng.uniform(-CORN_TOP_JITTER, CORN_TOP_JITTER)
        if k in (0, len(stations) - 1):
            top *= CORN_END_TOP_FACTOR
        side = rng.uniform(-CORN_TOP_SIDE_JITTER, CORN_TOP_SIDE_JITTER)
        profile = [(-CORN_BASE_HALF_WIDTH, -GROUND_SINK, 0.0), (-CORN_MID_HALF_WIDTH, CORN_MID_HEIGHT, CORN_MID_SWAY),
                   (side, top, CORN_TOP_SWAY), (CORN_MID_HALF_WIDTH, CORN_MID_HEIGHT, CORN_MID_SWAY),
                   (CORN_BASE_HALF_WIDTH, -GROUND_SINK, 0.0)]
        for offset, z, sway in profile:
            vertices.append(point + left * offset + Vector((0.0, 0.0, ground + z)))
            sways.append(sway)
        tops.append((point.x + left.x * side, point.y + left.y * side, ground + top))

    base = len(builder.vertices)
    for position, sway in zip(vertices, sways):
        builder.add_vertex(position, sway=sway)
    for k in range(len(stations) - 1):
        stalk = palette.flat_uv(*rng.choice(CORN_STALK_COLORS))
        leaf = palette.flat_uv(*rng.choice(CORN_LEAF_COLORS))
        for edge in range(profile_count - 1):
            a, b = base + k * profile_count + edge, base + k * profile_count + edge + 1
            uv = stalk if edge in (0, profile_count - 2) else leaf
            builder.add_face([a, a + profile_count, b + profile_count, b], MATERIAL, uv)
    first = [base + k for k in range(profile_count)]
    last = [base + (len(stations) - 1) * profile_count + k for k in reversed(range(profile_count))]
    cap = palette.flat_uv("Mustard", palette.SHADE_DARK)
    builder.add_face(first, MATERIAL, cap)
    builder.add_face(last, MATERIAL, cap)
    return tops


def corn_row_triangles(length):
    """Triangle cost of add_corn_row for a row of the given length."""
    return 8 * max(1, math.ceil(length / CORN_SEGMENT_LENGTH)) + 6


def add_stubble_row(builder, rng, start, end, height_at):
    """Adds a low harvested-stubble ridge (2 quads per segment, no caps) between two planar points."""
    stations = _row_stations(start, end, STUBBLE_SEGMENT_LENGTH)
    forward = (stations[-1] - stations[0]).normalized()
    left = Vector((-forward.y, forward.x, 0.0))
    base = len(builder.vertices)
    for point in stations:
        ground = height_at(point.x, point.y)
        builder.add_vertex(point + left * STUBBLE_HALF_WIDTH + Vector((0.0, 0.0, ground - GROUND_SINK)))
        builder.add_vertex(point + Vector((0.0, 0.0, ground + STUBBLE_HEIGHT * rng.uniform(0.8, 1.2))),
                           sway=STUBBLE_SWAY)
        builder.add_vertex(point - left * STUBBLE_HALF_WIDTH + Vector((0.0, 0.0, ground - GROUND_SINK)))
    for k in range(len(stations) - 1):
        a = base + 3 * k
        uv = palette.flat_uv("DryGrass", rng.choice((palette.SHADE_BASE, palette.SHADE_LIGHT)))
        builder.add_face([a, a + 1, a + 4, a + 3], MATERIAL, uv)
        builder.add_face([a + 1, a + 2, a + 5, a + 4], MATERIAL, uv)


def stubble_row_triangles(length):
    """Triangle cost of add_stubble_row for a row of the given length."""
    return 4 * max(1, math.ceil(length / STUBBLE_SEGMENT_LENGTH))


def add_scarecrow(builder, rng, x, y, base_z, rotation):
    """Adds a scarecrow: post, cross arm, flannel shirt, burlap head and a wide straw hat (about 70 tris)."""
    placement = _placement(x, y, base_z, rotation)
    sway = lambda local: SCARECROW_SWAY  # noqa: E731
    post = open_box(SCARECROW_POST_SIZE, SCARECROW_POST_SIZE, SCARECROW_POST_HEIGHT + GROUND_SINK)
    builder.add_part(post, placement @ Matrix.Translation((0.0, 0.0, -GROUND_SINK)), MATERIAL,
                     _flat("Wood", palette.SHADE_DARK))
    arm = open_box(SCARECROW_ARM_SPAN, SCARECROW_ARM_SIZE, SCARECROW_ARM_SIZE)
    builder.add_part(arm, placement @ Matrix.Translation((0.0, 0.0, SCARECROW_ARM_HEIGHT)), MATERIAL,
                     _flat("Wood", palette.SHADE_BASE))
    shirt = open_box(*SCARECROW_SHIRT_SIZE)
    builder.add_part(shirt, placement @ Matrix.Translation((0.0, 0.0, SCARECROW_SHIRT_BOTTOM)), MATERIAL,
                     lambda face, centroid: palette.flat_uv("MapleRed", palette.SHADE_DARK if face % 2
                                                            else palette.SHADE_BASE), sway)
    sleeves = open_box(SCARECROW_ARM_SPAN * 0.8, SCARECROW_SHIRT_SIZE[1] * 0.7, SCARECROW_SHIRT_SIZE[2] * 0.32)
    builder.add_part(sleeves, placement @ Matrix.Translation((0.0, 0.0, SCARECROW_ARM_HEIGHT - 0.1)), MATERIAL,
                     _flat("MapleRed", palette.SHADE_BASE), sway)
    head = shapes.blob(5, 3, SCARECROW_HEAD_RADIUS, 1.0)
    builder.add_part(head, placement @ Matrix.Translation((0.0, 0.0, SCARECROW_HEAD_Z)), MATERIAL,
                     _flat("WallCream", palette.SHADE_DARK), sway)
    brim_z = SCARECROW_HEAD_Z + SCARECROW_HEAD_RADIUS * 0.55
    brim = shapes.prism(6, SCARECROW_HAT_BRIM_RADIUS, SCARECROW_HAT_BRIM_HEIGHT, cap_bottom=True)
    builder.add_part(brim, placement @ Matrix.Translation((0.0, 0.0, brim_z)), MATERIAL,
                     _flat("HarvestGold", palette.SHADE_DARK), sway)
    crown = shapes.cone(6, SCARECROW_HAT_RADIUS, SCARECROW_HAT_HEIGHT)
    builder.add_part(crown, placement @ Matrix.Translation((0.0, 0.0, brim_z + SCARECROW_HAT_BRIM_HEIGHT)), MATERIAL,
                     _flat("HarvestGold", palette.SHADE_BASE), sway)


def pumpkin_part(radius):
    """Builds a squashed faceted pumpkin body (3 x segments tris) centered on its equator, flattened on top."""
    part = shapes.blob(PUMPKIN_SEGMENTS, 3, radius, PUMPKIN_SQUASH)
    part.vertices[-1].z *= PUMPKIN_TOP_FLATTEN
    return part


def add_pumpkin(builder, rng, x, y, base_z, radius, color_name="Pumpkin"):
    """Adds a chunky faceted pumpkin with a stem (25 tris). Returns its top height."""
    rest_z = base_z + radius * PUMPKIN_SQUASH * (1.0 - PUMPKIN_SINK_FACTOR)
    placement = _placement(x, y, rest_z, rng.uniform(0.0, 2.0 * math.pi))

    def pumpkin_uv(face, centroid):
        if centroid.z < -radius * 0.2:
            return palette.flat_uv(color_name, palette.SHADE_DARK)
        return palette.flat_uv(color_name, palette.SHADE_LIGHT if face % 2 else palette.SHADE_BASE)

    builder.add_part(pumpkin_part(radius), placement, MATERIAL, pumpkin_uv)
    top = radius * PUMPKIN_SQUASH
    stem = shapes.cone(PUMPKIN_STEM_SIDES, radius * PUMPKIN_STEM_RADIUS_FACTOR,
                       radius * PUMPKIN_STEM_HEIGHT_FACTOR + 0.08)
    builder.add_part(stem, placement @ Matrix.Translation((0.0, 0.0, top * 0.85)) @ Matrix.Rotation(
        rng.uniform(-0.3, 0.3), 4, "X"), MATERIAL, _flat("Moss", palette.SHADE_EXTRA_DARK))
    return rest_z + top + radius * PUMPKIN_STEM_HEIGHT_FACTOR


def add_vine(builder, rng, points, half_width, height_at):
    """Adds a flat wiggly vine ribbon draped over the ground along a polyline of planar points."""
    vertices = []
    count = len(points)
    for k, point in enumerate(points):
        before, after = points[max(0, k - 1)], points[min(count - 1, k + 1)]
        forward = Vector((after[0] - before[0], after[1] - before[1], 0.0)).normalized()
        left = Vector((-forward.y, forward.x, 0.0))
        width = half_width * (0.4 if k in (0, count - 1) else rng.uniform(0.8, 1.2))
        for side in (1.0, -1.0):
            px, py = point[0] + left.x * width * side, point[1] + left.y * width * side
            vertices.append((px, py, height_at(px, py) + VINE_LIFT))
    faces = []
    for k in range(count - 1):
        face = (2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2)
        a, b, c = (Vector(vertices[i]) for i in face[:3])
        faces.append(face if (b - a).cross(c - a).z > 0.0 else tuple(reversed(face)))
    part = shapes.Part(vertices, faces)
    builder.add_part(part, Matrix.Identity(4), MATERIAL,
                     lambda face, centroid: palette.flat_uv("Moss", rng.choice((palette.SHADE_DARK,
                                                                                 palette.SHADE_BASE))),
                     lambda local: VINE_SWAY)


def add_leaf_clump(builder, rng, x, y, base_z, radius):
    """Adds a flat faceted pumpkin-leaf clump (10 tris)."""
    leaf = shapes.blob(LEAF_SEGMENTS[0], LEAF_SEGMENTS[1], radius, LEAF_SQUASH, 0.15, rng)
    builder.add_part(leaf, _placement(x, y, base_z + radius * LEAF_SQUASH * 0.35, rng.uniform(0.0, 2.0 * math.pi)),
                     MATERIAL, lambda face, centroid: palette.flat_uv(
                         rng.choice(("Moss", "LightMoss", "Moss")), rng.choice((palette.SHADE_BASE, palette.SHADE_DARK))),
                     lambda local: LEAF_SWAY)


def add_crate(builder, rng, x, y, base_z, rotation, stack_z=0.0):
    """Adds an open-topped wooden crate (10 tris). Returns the crate's top height."""
    crate = open_box(CRATE_SIZE, CRATE_SIZE, CRATE_HEIGHT + GROUND_SINK)
    z = base_z + stack_z - (GROUND_SINK if stack_z == 0.0 else 0.0)
    builder.add_part(crate, _placement(x, y, z, rotation), MATERIAL,
                     lambda face, centroid: palette.flat_uv("Wood", palette.SHADE_LIGHT if face == 1
                                                            else kit.random_shade(rng, 0.1, 0.4)))
    return base_z + stack_z + CRATE_HEIGHT


def add_cart(builder, rng, x, y, base_z, rotation, load_count=3):
    """Adds a two-wheeled farm cart with a few pumpkins in the bed (about 130 tris with a load of 3)."""
    placement = _placement(x, y, base_z, rotation)
    length, width, depth = CART_BED_SIZE
    builder.add_part(open_box(length, width, depth), placement @ Matrix.Translation((0.0, 0.0, CART_BED_Z)), MATERIAL,
                     lambda face, centroid: palette.flat_uv("Wood", palette.SHADE_LIGHT if face == 1
                                                            else palette.SHADE_BASE))
    for side in (-1.0, 1.0):
        wheel = shapes.prism(CART_WHEEL_SIDES, CART_WHEEL_RADIUS, CART_WHEEL_WIDTH, cap_bottom=True)
        wheel_matrix = (placement @ Matrix.Translation((0.0, side * (width * 0.5 + CART_WHEEL_WIDTH * 0.5),
                                                        CART_WHEEL_RADIUS - 0.05))
                        @ Matrix.Rotation(math.radians(90.0), 4, "X")
                        @ Matrix.Translation((0.0, 0.0, -CART_WHEEL_WIDTH * 0.5)))
        builder.add_part(wheel, wheel_matrix, MATERIAL,
                         lambda face, centroid: palette.flat_uv("Wood", palette.SHADE_DARK if face < CART_WHEEL_SIDES
                                                                else palette.SHADE_EXTRA_DARK))
        handle_start = placement @ Vector((length * 0.5, side * width * 0.35, CART_BED_Z + depth * 0.5))
        handle_end = placement @ Vector((length * 0.5 + CART_HANDLE_LENGTH, side * width * 0.3, CART_HANDLE_SIZE))
        add_beam(builder, handle_start, handle_end, CART_HANDLE_SIZE, _flat("Wood", palette.SHADE_DARK))
    leg = open_box(CART_LEG_SIZE, width * 0.6, CART_BED_Z + GROUND_SINK)
    builder.add_part(leg, placement @ Matrix.Translation((length * 0.38, 0.0, -GROUND_SINK)), MATERIAL,
                     _flat("Wood", palette.SHADE_DARK))
    bed_top = base_z + CART_BED_Z + depth
    for k in range(load_count):
        along = (k - (load_count - 1) * 0.5) * (length / max(1, load_count))
        local = placement @ Vector((along, rng.uniform(-0.12, 0.12), 0.0))
        add_pumpkin(builder, rng, local.x, local.y, bed_top - 0.12, CART_LOAD_RADIUS * rng.uniform(0.85, 1.1))


def cart_triangles(load_count=3):
    """Triangle cost of add_cart."""
    return 10 + 2 * (4 * CART_WHEEL_SIDES - 4 + 8) + 10 + load_count * PUMPKIN_TRIANGLES


def add_square_hay_bale(builder, rng, x, y, base_z, rotation, stack_z=0.0):
    """Adds a rectangular straw bale (10 tris). Returns its top height."""
    length, width, height = SQUARE_BALE_SIZE
    bale = open_box(length, width, height + (GROUND_SINK if stack_z == 0.0 else 0.0))
    z = base_z + stack_z - (GROUND_SINK if stack_z == 0.0 else 0.0)
    builder.add_part(bale, _placement(x, y, z, rotation), MATERIAL,
                     lambda face, centroid: palette.flat_uv("HarvestGold", palette.SHADE_LIGHT if face == 1 else (
                         palette.SHADE_DARK if face in (0, 2) else palette.SHADE_BASE)))
    return base_z + stack_z + height


def add_barn(builder, rng, x, y, base_z, rotation):
    """Adds a red gambrel-roof barn with cream trim, a big door on the +X gable and a hayloft window.

    Returns its planar footprint radius (roof overhang included).
    """
    scale = _fit_scale(base_z, BARN_RIDGE + BARN_ROOF_THICKNESS)
    placement = _placement(x, y, base_z, rotation, scale)
    half_w, half_l = BARN_WIDTH * 0.5, BARN_LENGTH * 0.5
    knee_y = half_w * BARN_KNEE_FRACTION
    walls = extrude_profile([(-half_w, -GROUND_SINK), (-half_w, BARN_WALL), (-knee_y, BARN_KNEE_HEIGHT),
                             (0.0, BARN_RIDGE), (knee_y, BARN_KNEE_HEIGHT), (half_w, BARN_WALL),
                             (half_w, -GROUND_SINK)], -half_l, half_l, skip_edges=(6,))
    builder.add_part(walls, placement, MATERIAL,
                     lambda face, centroid: palette.flat_uv("MapleRed", palette.SHADE_DARK if face in (0, 5)
                                                            else palette.SHADE_BASE))

    eave_y = half_w + BARN_ROOF_OVERHANG
    lower_slope = (BARN_KNEE_HEIGHT - BARN_WALL) / (half_w - knee_y)
    eave_z = BARN_WALL - BARN_ROOF_OVERHANG * lower_slope
    t = BARN_ROOF_THICKNESS
    outer = [(-eave_y, eave_z), (-knee_y, BARN_KNEE_HEIGHT), (0.0, BARN_RIDGE), (knee_y, BARN_KNEE_HEIGHT),
             (eave_y, eave_z)]
    profile = [(py, pz + t) for py, pz in outer] + [(py, pz) for py, pz in reversed(outer)]
    x_min, x_max = -half_l - BARN_ROOF_END_OVERHANG, half_l + BARN_ROOF_END_OVERHANG
    roof = extrude_profile(profile, x_min, x_max)
    roof_top = palette.flat_uv("Slate", palette.SHADE_BASE)
    roof_upper = palette.flat_uv("Slate", palette.SHADE_LIGHT)
    roof_trim = palette.flat_uv("Slate", palette.SHADE_DARK)
    builder.add_part(roof, placement, MATERIAL,
                     lambda face, centroid: roof_upper if face in (1, 2) else (roof_top if face in (0, 3)
                                                                                else roof_trim))

    gable = half_l + FACADE_OFFSET
    facade = Matrix.Translation((gable, 0.0, 0.0))
    door = shapes.Part([(0.0, BARN_DOOR_HALF_WIDTH, 0.0), (0.0, -BARN_DOOR_HALF_WIDTH, 0.0),
                        (0.0, -BARN_DOOR_HALF_WIDTH, BARN_DOOR_HEIGHT), (0.0, BARN_DOOR_HALF_WIDTH, BARN_DOOR_HEIGHT)],
                       [(1, 0, 3, 2)])
    builder.add_part(door, placement @ facade, MATERIAL, _flat("Wood", palette.SHADE_DARK))
    trim = palette.flat_uv("WallCream", palette.SHADE_BASE)
    for (y0, z0), (y1, z1) in (((-BARN_DOOR_HALF_WIDTH, 0.0), (BARN_DOOR_HALF_WIDTH, BARN_DOOR_HEIGHT)),
                               ((BARN_DOOR_HALF_WIDTH, 0.0), (-BARN_DOOR_HALF_WIDTH, BARN_DOOR_HEIGHT))):
        add_beam(builder, placement @ Vector((gable + 0.03, y0, z0 + 0.05)),
                 placement @ Vector((gable + 0.03, y1, z1 - 0.05)), BARN_TRIM_THICKNESS * scale,
                 lambda face, centroid: trim)
    loft_z = (BARN_WALL + BARN_KNEE_HEIGHT) * 0.5 + 0.1
    loft = shapes.Part([(0.0, BARN_LOFT_HALF_SIZE, loft_z - BARN_LOFT_HALF_SIZE),
                        (0.0, -BARN_LOFT_HALF_SIZE, loft_z - BARN_LOFT_HALF_SIZE),
                        (0.0, -BARN_LOFT_HALF_SIZE, loft_z + BARN_LOFT_HALF_SIZE),
                        (0.0, BARN_LOFT_HALF_SIZE, loft_z + BARN_LOFT_HALF_SIZE)], [(1, 0, 3, 2)])
    builder.add_part(loft, placement @ facade, MATERIAL, _flat("WallCream", palette.SHADE_BASE))
    side_door = shapes.Part([(-0.4, 0.0, 0.0), (0.4, 0.0, 0.0), (0.4, 0.0, 1.1), (-0.4, 0.0, 1.1)], [(0, 1, 2, 3)])
    builder.add_part(side_door, placement @ Matrix.Translation((-half_l * 0.35, -half_w - FACADE_OFFSET, 0.0)),
                     MATERIAL, _flat("WallCream", palette.SHADE_DARK))
    return math.hypot(half_l + BARN_ROOF_END_OVERHANG, eave_y) * scale


def add_silo(builder, rng, x, y, base_z):
    """Adds a short cream silo with a slate dome (kept under the decor limit). Returns its footprint radius."""
    top = SILO_HEIGHT + SILO_DOME_HEIGHT
    scale = _fit_scale(base_z, top)
    placement = _placement(x, y, base_z, rng.uniform(0.0, 2.0 * math.pi), scale)
    body = shapes.prism(SILO_SIDES, SILO_RADIUS, SILO_HEIGHT + GROUND_SINK, cap_top=False)
    builder.add_part(body, placement @ Matrix.Translation((0.0, 0.0, -GROUND_SINK)), MATERIAL,
                     lambda face, centroid: palette.flat_uv("WallCream", palette.SHADE_DARK if face % 3 == 0
                                                            else palette.SHADE_BASE))
    dome = shapes.cone(SILO_SIDES, SILO_DOME_RADIUS, SILO_DOME_HEIGHT)
    builder.add_part(dome, placement @ Matrix.Translation((0.0, 0.0, SILO_HEIGHT)), MATERIAL,
                     lambda face, centroid: palette.flat_uv("Slate", palette.SHADE_LIGHT if face % 2
                                                            else palette.SHADE_BASE))
    for band_z in SILO_BAND_HEIGHTS:
        band = shapes.prism(SILO_SIDES, SILO_RADIUS * 1.04, 0.1, cap_top=False)
        builder.add_part(band, placement @ Matrix.Translation((0.0, 0.0, band_z)), MATERIAL,
                         _flat("Stone", palette.SHADE_DARK))
    return SILO_DOME_RADIUS * scale


def add_fence(builder, rng, points, height_at):
    """Adds a post-and-two-rail fence along a polyline of planar points (10 tris per post, 16 per span)."""
    tops = []
    for x, y in points:
        base = height_at(x, y)
        post = open_box(FENCE_POST_SIZE, FENCE_POST_SIZE, FENCE_POST_HEIGHT + GROUND_SINK)
        builder.add_part(post, _placement(x, y, base - GROUND_SINK, rng.uniform(-0.15, 0.15)), MATERIAL,
                         _flat("Wood", palette.SHADE_DARK))
        tops.append((x, y, base))
    rail_uv = _flat("Wood", palette.SHADE_LIGHT)
    for (ax, ay, az), (bx, by, bz) in zip(tops, tops[1:]):
        for rail_height in FENCE_RAIL_HEIGHTS:
            add_beam(builder, (ax, ay, az + rail_height), (bx, by, bz + rail_height), FENCE_RAIL_SIZE, rail_uv)


def fence_triangles(post_count):
    """Triangle cost of add_fence for a polyline with post_count posts."""
    return post_count * FENCE_POST_TRIANGLES + max(0, post_count - 1) * 2 * FENCE_RAIL_TRIANGLES
