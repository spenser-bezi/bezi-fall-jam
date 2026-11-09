"""Woodland small-prop kit: boulders, stumps, logs, low bushes, fallen apples and a short fence bit."""
import math

from mathutils import Matrix

from lib import materials, palette, shapes
from props import kit

MATERIAL = materials.PALETTE_MATERIAL

BOULDER_SEGMENTS = (6, 3)
BOULDER_SQUASH = 0.72
BOULDER_JITTER = 0.22
BOULDER_SINK_FACTOR = 0.3
BOULDER_MOSS_TOP_CHANCE = 0.45
BOULDER_MOSS_MIN_Z = 0.25

STUMP_SIDES = 6
STUMP_RADIUS = 0.32
STUMP_TOP_FACTOR = 0.85
STUMP_HEIGHT = 0.38
STUMP_SINK = 0.08

LOG_SIDES = 5
LOG_RADIUS = 0.22
LOG_LENGTH = 1.7
LOG_SINK = 0.05

LOW_BUSH_SEGMENTS = (5, 3)
LOW_BUSH_SQUASH = 0.7
LOW_BUSH_JITTER = 0.16
LOW_BUSH_SINK_FACTOR = 0.35
LOW_BUSH_SWAY = 0.35

APPLE_RADIUS = 0.17
APPLE_SQUASH = 0.85
APPLE_SEGMENTS = (4, 2)
APPLE_REST_FACTOR = 0.6

FENCE_POST_SIDES = 4
FENCE_POST_RADIUS = 0.09
FENCE_POST_HEIGHT = 0.95
FENCE_POST_SINK = 0.1
FENCE_RAIL_HEIGHTS = (0.42, 0.75)
FENCE_RAIL_THICKNESS = 0.08
FENCE_RAIL_DEPTH = 0.05
FENCE_SPAN = 1.6
FENCE_LEAN = 0.06


def _placement(x, y, z, rotation, scale=1.0):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(rotation, 4, "Z") @ Matrix.Scale(scale, 4)


def box(length, depth, height):
    """Builds an axis-aligned box centered on x/y and standing on z = 0 (12 tris)."""
    hx, hy = length * 0.5, depth * 0.5
    vertices = [(-hx, -hy, 0.0), (hx, -hy, 0.0), (hx, hy, 0.0), (-hx, hy, 0.0),
                (-hx, -hy, height), (hx, -hy, height), (hx, hy, height), (-hx, hy, height)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return shapes.Part(vertices, faces)


def add_boulder(builder, rng, x, y, base_z, radius, mossy=True):
    """Adds a chunky faceted boulder; upward faces may carry a moss cap."""
    boulder = shapes.blob(BOULDER_SEGMENTS[0], BOULDER_SEGMENTS[1], radius, BOULDER_SQUASH, BOULDER_JITTER, rng)
    placement = _placement(x, y, base_z + radius * BOULDER_SQUASH * (1.0 - 2.0 * BOULDER_SINK_FACTOR),
                           rng.uniform(0.0, 2.0 * math.pi))
    moss_threshold = radius * BOULDER_SQUASH * BOULDER_MOSS_MIN_Z

    def boulder_uv(face, centroid):
        if mossy and centroid.z > moss_threshold and rng.random() < BOULDER_MOSS_TOP_CHANCE:
            return palette.flat_uv("Moss", palette.SHADE_DARK)
        return palette.flat_uv("Stone", kit.random_shade(rng, 0.3, 0.3))

    builder.add_part(boulder, placement, MATERIAL, boulder_uv)


def add_stump(builder, rng, x, y, base_z):
    """Adds a short cut stump with a pale ring top."""
    stump = shapes.prism(STUMP_SIDES, STUMP_RADIUS, STUMP_HEIGHT + STUMP_SINK, top_radius=STUMP_RADIUS * STUMP_TOP_FACTOR)
    placement = _placement(x, y, base_z - STUMP_SINK, rng.uniform(0.0, 2.0 * math.pi))
    builder.add_part(stump, placement, MATERIAL,
                     lambda face, centroid: palette.flat_uv(
                         "WallCream" if face == STUMP_SIDES else "Wood",
                         palette.SHADE_DARK if face == STUMP_SIDES else kit.random_shade(rng, 0.2, 0.4)))


def add_log(builder, rng, x, y, base_z, rotation=None):
    """Adds a fallen log lying on the ground."""
    log = shapes.prism(LOG_SIDES, LOG_RADIUS, LOG_LENGTH, cap_top=True, cap_bottom=True)
    rotation = rng.uniform(0.0, 2.0 * math.pi) if rotation is None else rotation
    placement = (_placement(x, y, base_z + LOG_RADIUS - LOG_SINK, rotation)
                 @ Matrix.Rotation(math.radians(90.0), 4, "Y") @ Matrix.Translation((0.0, 0.0, -LOG_LENGTH * 0.5)))
    builder.add_part(log, placement, MATERIAL,
                     lambda face, centroid: palette.flat_uv(
                         "WallCream" if face >= LOG_SIDES else "Wood",
                         palette.SHADE_DARK if face >= LOG_SIDES else kit.random_shade(rng, 0.2, 0.4)))


def add_low_bush(builder, rng, x, y, base_z, radius, color_name="Moss"):
    """Adds a cheap squat bush (20 tris)."""
    bush = shapes.blob(LOW_BUSH_SEGMENTS[0], LOW_BUSH_SEGMENTS[1], radius, LOW_BUSH_SQUASH, LOW_BUSH_JITTER, rng)
    placement = _placement(x, y, base_z + radius * LOW_BUSH_SQUASH * (1.0 - LOW_BUSH_SINK_FACTOR),
                           rng.uniform(0.0, 2.0 * math.pi))
    builder.add_part(bush, placement, MATERIAL,
                     lambda face, centroid: palette.flat_uv(color_name, rng.choice(
                         (palette.SHADE_DARK, palette.SHADE_BASE, palette.SHADE_DARK, palette.SHADE_EXTRA_DARK))),
                     lambda local: LOW_BUSH_SWAY)


def add_fallen_apple(builder, rng, x, y, base_z):
    """Adds a small red apple lying in the grass (8 tris)."""
    apple = shapes.blob(APPLE_SEGMENTS[0], APPLE_SEGMENTS[1], APPLE_RADIUS, APPLE_SQUASH)
    placement = _placement(x, y, base_z + APPLE_RADIUS * APPLE_SQUASH * APPLE_REST_FACTOR,
                           rng.uniform(0.0, 2.0 * math.pi))
    builder.add_part(apple, placement, MATERIAL,
                     lambda face, centroid: palette.flat_uv("MapleRed", rng.choice(
                         (palette.SHADE_BASE, palette.SHADE_LIGHT, palette.SHADE_DARK))))


def add_fence_bit(builder, rng, x, y, base_z, rotation, spans=2, height_at=None):
    """Adds a short rustic fence (spans + 1 posts, two rails per span) centered on (x, y) along rotation."""
    direction = (math.cos(rotation), math.sin(rotation))
    total = spans * FENCE_SPAN
    post_offsets = [-total * 0.5 + k * FENCE_SPAN for k in range(spans + 1)]
    for offset in post_offsets:
        px, py = x + direction[0] * offset, y + direction[1] * offset
        pz = base_z if height_at is None else height_at(px, py)
        post = shapes.prism(FENCE_POST_SIDES, FENCE_POST_RADIUS, FENCE_POST_HEIGHT + FENCE_POST_SINK,
                            top_radius=FENCE_POST_RADIUS * 0.8, angle_offset=math.pi / FENCE_POST_SIDES)
        lean = Matrix.Rotation(rng.uniform(-FENCE_LEAN, FENCE_LEAN), 4, "X")
        builder.add_part(post, _placement(px, py, pz - FENCE_POST_SINK, rotation) @ lean, MATERIAL,
                         lambda face, centroid: palette.flat_uv("Wood", kit.random_shade(rng, 0.2, 0.3)))
    for span in range(spans):
        center = -total * 0.5 + (span + 0.5) * FENCE_SPAN
        cx, cy = x + direction[0] * center, y + direction[1] * center
        cz = base_z if height_at is None else height_at(cx, cy)
        for rail_height in FENCE_RAIL_HEIGHTS:
            rail = box(FENCE_SPAN + FENCE_POST_RADIUS * 2.0, FENCE_RAIL_DEPTH, FENCE_RAIL_THICKNESS)
            placement = _placement(cx, cy, cz + rail_height + rng.uniform(-0.03, 0.03), rotation)
            builder.add_part(rail, placement, MATERIAL,
                             lambda face, centroid: palette.flat_uv("Wood", palette.SHADE_LIGHT if face == 1
                                                                    else palette.SHADE_BASE))
