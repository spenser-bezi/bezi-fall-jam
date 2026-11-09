"""Water-side prop kit: dock, rowboat, footbridge, lily pads, cattails, shore pines, bog patches."""
import math

from mathutils import Matrix, Vector

from lib import hexgrid, materials, palette, shapes
from props import buildings

MATERIAL = materials.PALETTE_MATERIAL

DOCK_DECK_THICKNESS = 0.14
DOCK_DECK_TOP_ABOVE_WATER = 0.42
DOCK_SHORE_OVERLAP = 0.6
DOCK_POST_SIZE = 0.16
DOCK_POST_BOTTOM = -0.7
DOCK_POST_RISE = 0.25
DOCK_POST_INSET = 0.12

BOAT_LENGTH = 2.1
BOAT_WIDTH = 0.95
BOAT_HEIGHT = 0.42
BOAT_DRAFT = 0.12
BOAT_BOTTOM_SCALE = 0.6
BOAT_FLOOR_SCALE = 0.8
BOAT_FLOOR_HEIGHT = 0.16
BOAT_SEAT_WIDTH = 0.22
BOAT_SEAT_HEIGHT = 0.3

BRIDGE_DECK_THICKNESS = 0.16
BRIDGE_ARCH_RISE = 0.45
BRIDGE_SEGMENTS = 3
BRIDGE_RAIL_HEIGHT = 0.75
BRIDGE_RAIL_SIZE = 0.08
BRIDGE_POST_SIZE = 0.12
BRIDGE_DECK_SINK = 0.05

LILY_PAD_SIDES = 6
LILY_PAD_MIN_RADIUS = 0.22
LILY_PAD_MAX_RADIUS = 0.38
LILY_PAD_LIFT = 0.025
LILY_PAD_SPREAD = 0.9
LILY_PAD_NOTCH = 0.35

CATTAIL_STEM_SIDES = 3
CATTAIL_STEM_RADIUS = 0.035
CATTAIL_MIN_HEIGHT = 1.0
CATTAIL_MAX_HEIGHT = 1.5
CATTAIL_HEAD_SIDES = 4
CATTAIL_HEAD_RADIUS = 0.08
CATTAIL_HEAD_LENGTH = 0.3
CATTAIL_SPREAD = 0.3
CATTAILS_PER_CLUMP = 3
CATTAIL_SINK = 0.1

PINE_TRUNK_SIDES = 4
PINE_TRUNK_RADIUS = 0.13
PINE_TRUNK_HEIGHT = 0.5
PINE_CONE_SIDES = 6
PINE_LOWER_TIER_FRACTION = 0.68
PINE_UPPER_TIER_START = 0.38
PINE_RADIUS_FACTOR = 0.36
PINE_TIER_SHRINK = 0.7
PINE_DECOR_MARGIN = 0.1

BOG_PATCH_POINTS = 7
BOG_PATCH_WOBBLE = 0.25
BOG_PATCH_LIFT = 0.02


def _placement(x, y, z, rotation):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(rotation, 4, "Z")


def _flat(name, shade=palette.SHADE_BASE):
    uv = palette.flat_uv(name, shade)
    return lambda face, centroid: uv


def add_dock(builder, rng, shore_x, shore_y, direction_angle, length, width, water_z):
    """Adds a plank dock starting on the shore and reaching over the water along direction_angle."""
    deck_top = water_z + DOCK_DECK_TOP_ABOVE_WATER
    placement = _placement(shore_x, shore_y, 0.0, direction_angle)
    deck = buildings.extrude_yz([(-width * 0.5, 0.0), (width * 0.5, 0.0), (width * 0.5, DOCK_DECK_THICKNESS),
                                 (-width * 0.5, DOCK_DECK_THICKNESS)], -DOCK_SHORE_OVERLAP, length)
    top_threshold = DOCK_DECK_THICKNESS - 1e-3
    builder.add_part(deck, placement @ Matrix.Translation((0.0, 0.0, deck_top - DOCK_DECK_THICKNESS)), MATERIAL,
                     lambda face, centroid: palette.flat_uv("Wood", palette.SHADE_LIGHT if centroid.z > top_threshold
                                                            else palette.SHADE_DARK))
    half = DOCK_POST_SIZE * 0.5
    for along in (length * 0.45, length - DOCK_POST_INSET):
        for side in (-1.0, 1.0):
            post = buildings.box(DOCK_POST_SIZE, DOCK_POST_SIZE, deck_top + DOCK_POST_RISE - DOCK_POST_BOTTOM)
            offset = Matrix.Translation((along, side * (width * 0.5 + half), DOCK_POST_BOTTOM))
            builder.add_part(post, placement @ offset, MATERIAL, _flat("Wood", palette.SHADE_EXTRA_DARK))
    return deck_top


def add_rowboat(builder, rng, x, y, water_z, rotation, hull_color="MapleRed"):
    """Adds a small open rowboat floating at water_z (pointed bow on local +X)."""
    half_length, half_width = BOAT_LENGTH * 0.5, BOAT_WIDTH * 0.5
    outline = [(half_length, 0.0), (half_length * 0.45, half_width), (-half_length * 0.75, half_width),
               (-half_length, half_width * 0.6), (-half_length, -half_width * 0.6),
               (-half_length * 0.75, -half_width), (half_length * 0.45, -half_width)]  # counter-clockwise
    count = len(outline)
    bottom_z, top_z = -BOAT_DRAFT, BOAT_HEIGHT - BOAT_DRAFT
    floor_z = bottom_z + BOAT_FLOOR_HEIGHT
    vertices = ([(px * BOAT_BOTTOM_SCALE, py * BOAT_BOTTOM_SCALE, bottom_z) for px, py in outline]
                + [(px, py, top_z) for px, py in outline]
                + [(px * BOAT_FLOOR_SCALE, py * BOAT_FLOOR_SCALE, floor_z) for px, py in outline])
    faces = []
    for k in range(count):
        n = (k + 1) % count
        faces.append((k, n, count + n, count + k))                     # outer hull
    for k in range(count):
        n = (k + 1) % count
        faces.append((count + k, count + n, 2 * count + n, 2 * count + k))  # inner wall down to the floor
    faces.append(tuple(2 * count + k for k in range(count)))           # floor
    hull = shapes.Part(vertices, faces)
    placement = _placement(x, y, water_z, rotation)
    builder.add_part(hull, placement, MATERIAL,
                     lambda face, centroid: palette.flat_uv(hull_color, palette.SHADE_BASE) if face < count
                     else palette.flat_uv("Wood", palette.SHADE_LIGHT if face == 2 * count else palette.SHADE_DARK))
    seat = box(BOAT_SEAT_WIDTH, BOAT_WIDTH * BOAT_FLOOR_SCALE * 0.95, 0.06)
    builder.add_part(seat, placement @ Matrix.Translation((-0.1, 0.0, bottom_z + BOAT_SEAT_HEIGHT)), MATERIAL,
                     _flat("Wood", palette.SHADE_BASE))


def box(size_x, size_y, size_z):
    """Box centered on x/y standing on z = 0 (no bottom face)."""
    return buildings.box(size_x, size_y, size_z)


def add_footbridge(builder, x, y, rotation, span, width, base_z):
    """Adds an arched plank footbridge spanning local X (length span) with simple hand rails."""
    placement = _placement(x, y, base_z, rotation)
    half_span = span * 0.5
    stations = [-half_span + span * k / BRIDGE_SEGMENTS for k in range(BRIDGE_SEGMENTS + 1)]

    def deck_height(along):
        return BRIDGE_ARCH_RISE * (1.0 - (along / half_span) ** 2)

    for a, b in zip(stations, stations[1:]):
        za, zb = deck_height(a) - BRIDGE_DECK_SINK, deck_height(b) - BRIDGE_DECK_SINK
        half_w = width * 0.5
        vertices = [(a, -half_w, za), (b, -half_w, zb), (b, half_w, zb), (a, half_w, za),
                    (a, -half_w, za + BRIDGE_DECK_THICKNESS), (b, -half_w, zb + BRIDGE_DECK_THICKNESS),
                    (b, half_w, zb + BRIDGE_DECK_THICKNESS), (a, half_w, za + BRIDGE_DECK_THICKNESS)]
        faces = [(4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (3, 2, 1, 0)]
        builder.add_part(shapes.Part(vertices, faces), placement, MATERIAL,
                         lambda face, centroid: palette.flat_uv("Wood", palette.SHADE_LIGHT if face == 0
                                                                else palette.SHADE_DARK))
    rail_stations = (stations[0] + 0.15, 0.0, stations[-1] - 0.15)
    for side in (-1.0, 1.0):
        offset_y = side * (width * 0.5 - BRIDGE_POST_SIZE * 0.5)
        tops = []
        for along in rail_stations:
            floor = deck_height(along) - BRIDGE_DECK_SINK
            post = buildings.box(BRIDGE_POST_SIZE, BRIDGE_POST_SIZE, BRIDGE_RAIL_HEIGHT + 0.1)
            builder.add_part(post, placement @ Matrix.Translation((along, offset_y, floor)), MATERIAL,
                             _flat("Wood", palette.SHADE_EXTRA_DARK))
            tops.append(Vector((along, offset_y, floor + BRIDGE_RAIL_HEIGHT)))
        for start, end in zip(tops, tops[1:]):
            buildings.add_beam(builder, placement, start, end, BRIDGE_RAIL_SIZE, "Wood", palette.SHADE_BASE)


def add_lily_pads(builder, rng, x, y, water_z, count):
    """Adds a loose cluster of notched lily pads floating just above the water."""
    for _ in range(count):
        radius = rng.uniform(LILY_PAD_MIN_RADIUS, LILY_PAD_MAX_RADIUS)
        cx, cy = x + rng.uniform(-LILY_PAD_SPREAD, LILY_PAD_SPREAD), y + rng.uniform(-LILY_PAD_SPREAD, LILY_PAD_SPREAD)
        start = rng.uniform(0.0, 2.0 * math.pi)
        points = [(cx, cy, water_z + LILY_PAD_LIFT)]
        for k in range(LILY_PAD_SIDES + 1):
            angle = start + LILY_PAD_NOTCH + (2.0 * math.pi - 2.0 * LILY_PAD_NOTCH) * k / LILY_PAD_SIDES
            points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle), water_z + LILY_PAD_LIFT))
        faces = [(0, k, k + 1) for k in range(1, LILY_PAD_SIDES + 1)]
        shade = rng.choice((palette.SHADE_BASE, palette.SHADE_LIGHT))
        builder.add_part(shapes.Part(points, faces), Matrix.Identity(4), MATERIAL, _flat("LightMoss", shade))


def add_cattail_clump(builder, rng, x, y, base_z, count=CATTAILS_PER_CLUMP):
    """Adds a clump of cattails: thin stems with brown seed heads."""
    for _ in range(count):
        height = rng.uniform(CATTAIL_MIN_HEIGHT, CATTAIL_MAX_HEIGHT)
        px, py = x + rng.uniform(-CATTAIL_SPREAD, CATTAIL_SPREAD), y + rng.uniform(-CATTAIL_SPREAD, CATTAIL_SPREAD)
        placement = _placement(px, py, base_z - CATTAIL_SINK, rng.uniform(0.0, 2.0 * math.pi))
        stem = shapes.prism(CATTAIL_STEM_SIDES, CATTAIL_STEM_RADIUS, height, cap_top=False)
        builder.add_part(stem, placement, MATERIAL, _flat("DryGrass", palette.SHADE_DARK),
                         lambda local, h=height: local.z / h)
        head = shapes.prism(CATTAIL_HEAD_SIDES, CATTAIL_HEAD_RADIUS, CATTAIL_HEAD_LENGTH, cap_top=True,
                            cap_bottom=True)
        builder.add_part(head, placement @ Matrix.Translation((0.0, 0.0, height * 0.72)), MATERIAL,
                         _flat("Wood", palette.SHADE_DARK), lambda local: 0.8)


def add_shore_pine(builder, rng, x, y, base_z, height):
    """Adds a stacked-cone pine (trunk + tiers), capped to the decor height limit."""
    height = min(height, hexgrid.MAX_DECOR_HEIGHT - PINE_DECOR_MARGIN - base_z)
    placement = _placement(x, y, base_z, rng.uniform(0.0, 2.0 * math.pi))
    trunk = shapes.prism(PINE_TRUNK_SIDES, PINE_TRUNK_RADIUS, PINE_TRUNK_HEIGHT + 0.2, cap_top=False)
    builder.add_part(trunk, placement @ Matrix.Translation((0.0, 0.0, -0.1)), MATERIAL,
                     _flat("Wood", palette.SHADE_DARK))
    canopy = height - PINE_TRUNK_HEIGHT
    tiers = ((PINE_TRUNK_HEIGHT, PINE_TRUNK_HEIGHT + canopy * PINE_LOWER_TIER_FRACTION, canopy * PINE_RADIUS_FACTOR,
              palette.SHADE_BASE),
             (PINE_TRUNK_HEIGHT + canopy * PINE_UPPER_TIER_START, height,
              canopy * PINE_RADIUS_FACTOR * PINE_TIER_SHRINK, palette.SHADE_LIGHT))
    for bottom, top, radius, shade in tiers:
        span = top - bottom
        cone = shapes.cone(PINE_CONE_SIDES, radius, span, angle_offset=rng.uniform(0.0, 1.0))
        builder.add_part(cone, placement @ Matrix.Translation((0.0, 0.0, bottom)), MATERIAL,
                         _flat("Pine", shade), lambda local, s=span: 0.3 + 0.7 * local.z / s)


def pine_radius(height):
    """Planar radius of a shore pine of the given height (for rim clearance)."""
    return (height - PINE_TRUNK_HEIGHT) * PINE_RADIUS_FACTOR


def add_bog_patch(builder, rng, x, y, z, radius, color_name="Cranberry"):
    """Adds a flat, wobbly cranberry-red patch floating on the water (bog berries)."""
    start = rng.uniform(0.0, 2.0 * math.pi)
    points = []
    for k in range(BOG_PATCH_POINTS):
        angle = start + 2.0 * math.pi * k / BOG_PATCH_POINTS
        r = radius * (1.0 + rng.uniform(-BOG_PATCH_WOBBLE, BOG_PATCH_WOBBLE))
        points.append((x + r * math.cos(angle), y + r * math.sin(angle), z + BOG_PATCH_LIFT))
    shade = rng.choice((palette.SHADE_BASE, palette.SHADE_LIGHT))
    builder.add_part(shapes.disc(points), Matrix.Identity(4), MATERIAL, _flat(color_name, shade))
