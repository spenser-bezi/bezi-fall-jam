"""SM_Tile_SeamTest_Field: field-biome seam test (striped field, hedgerow, pond with M_Water + foam ring)."""
import math
import random

from mathutils import Matrix, Vector

from lib import hexgrid, materials, palette, shapes
from lib.scatter import Noise2D
from props import kit
from tiles import common

POND_DISTANCE = 5.0
POND_RADIUS = 2.0
POND_DEPTH = 0.6
POND_SLOPE_WIDTH = 0.6
POND_FLAT_MARGIN = 1.5
WATER_LEVEL = -0.12
WATER_POINTS = 14
FOAM_LEVEL = -0.10
FOAM_WIDTH = 0.75
FOAM_SEGMENTS = 16
FIELD_DISTANCE = 2.4
FIELD_RADIUS = 3.9
FIELD_WOBBLE = 0.15
FIELD_WOBBLE_FREQUENCY = 2.0
FIELD_MIN_INSET = 1.4
FIELD_HEIGHT_AMPLITUDE = 0.03
POND_BED_FOAM_FRACTION = 1.0
HEDGE_STEP = 1.5
HEDGE_OFFSET = 0.5
HEDGE_SKIP_CHANCE = 0.4
HEDGE_MAX_BUSHES = 9
HEDGE_MIN_INSET = 0.9
HEDGE_POND_CLEARANCE = 0.8
HEDGE_MIN_RADIUS = 0.42
HEDGE_MAX_RADIUS = 0.6
HAY_BALE_COUNT = 2
HAY_FIELD_FRACTION = 0.55
HAY_ATTEMPTS = 200
REED_CLUMPS = 3
REED_RING_FACTOR = 0.85
REED_ANGLE_STEP = 0.8
POND_ROCKS = 2
POND_ROCK_RING_FACTOR = 1.25
POND_ROCK_ANGLE_STEP = 0.7
POND_ROCK_MIN_RADIUS = 0.3
POND_ROCK_MAX_RADIUS = 0.5


def build(spec, seed):
    """Builds the field + pond seam-test tile."""
    rng = random.Random(seed)
    field_noise = Noise2D(seed + 3)
    grass = hexgrid.GrassPainter(seed)
    base_height = common.gentle_height(seed)

    pond_angle = rng.uniform(0.0, 2.0 * math.pi)
    pond_axis = Vector((math.cos(pond_angle), math.sin(pond_angle), 0.0))
    pond_center = pond_axis * POND_DISTANCE
    field_center = -pond_axis * FIELD_DISTANCE
    stripe_angle = rng.uniform(0.0, math.pi)
    stripe_direction = Vector((math.cos(stripe_angle), math.sin(stripe_angle), 0.0))

    def field_boundary(angle):
        return FIELD_RADIUS * (1.0 + FIELD_WOBBLE * field_noise.sample(
            math.cos(angle) * FIELD_WOBBLE_FREQUENCY, math.sin(angle) * FIELD_WOBBLE_FREQUENCY))

    def pond_distance(x, y):
        return math.hypot(x - pond_center.x, y - pond_center.y)

    def in_field(x, y):
        dx, dy = x - field_center.x, y - field_center.y
        return (math.hypot(dx, dy) < field_boundary(math.atan2(dy, dx))
                and hexgrid.inset_distance(x, y) > FIELD_MIN_INSET)

    def snap(position):
        position = hexgrid.snap_to_polar_contour(position, pond_center, lambda angle: POND_RADIUS)
        return hexgrid.snap_to_polar_contour(position, field_center, field_boundary)

    row_span = 2.0 * FIELD_RADIUS * (1.0 + FIELD_WOBBLE)
    row_origin = field_center.dot(stripe_direction) - row_span * 0.5

    def row_uv(position):
        return palette.strip_uv("FieldRows", (position.dot(stripe_direction) - row_origin) / row_span)

    def height(x, y):
        distance = pond_distance(x, y)
        if distance < POND_RADIUS:
            return -POND_DEPTH * min(1.0, (POND_RADIUS - distance) / POND_SLOPE_WIDTH)
        if distance < POND_RADIUS + POND_FLAT_MARGIN:
            return abs(base_height(x, y))
        if in_field(x, y):
            return FIELD_HEIGHT_AMPLITUDE * base_height(x, y) / common.DEFAULT_HEIGHT_AMPLITUDE
        return base_height(x, y)

    def face_style(centroid, face_rng):
        if pond_distance(centroid.x, centroid.y) < POND_RADIUS - FOAM_WIDTH * POND_BED_FOAM_FRACTION:
            return materials.PALETTE_MATERIAL, palette.flat_uv("DeepWater", palette.SHADE_DARK)
        if in_field(centroid.x, centroid.y):
            return materials.PALETTE_MATERIAL, row_uv
        return grass.style(centroid, face_rng)

    def add_pond(builder):
        outline = [(pond_center.x + POND_RADIUS * math.cos(2.0 * math.pi * k / WATER_POINTS),
                    pond_center.y + POND_RADIUS * math.sin(2.0 * math.pi * k / WATER_POINTS), WATER_LEVEL)
                   for k in range(WATER_POINTS)]
        builder.add_part(shapes.disc(outline), Matrix.Identity(4), materials.WATER_MATERIAL,
                         lambda face, centroid: palette.flat_uv("LakeTeal"))
        foam_inner = POND_RADIUS - FOAM_WIDTH
        foam_vertices = []
        for k in range(FOAM_SEGMENTS):
            angle = 2.0 * math.pi * k / FOAM_SEGMENTS
            for radius in (foam_inner, POND_RADIUS):
                foam_vertices.append((pond_center.x + radius * math.cos(angle),
                                      pond_center.y + radius * math.sin(angle), FOAM_LEVEL))
        foam_faces = []
        for k in range(FOAM_SEGMENTS):
            n = (k + 1) % FOAM_SEGMENTS
            foam_faces.append((2 * k, 2 * k + 1, 2 * n + 1, 2 * n))
        builder.add_part(shapes.Part(foam_vertices, foam_faces), Matrix.Identity(4), materials.PALETTE_MATERIAL,
                         lambda face, centroid: palette.flat_uv("ShoreFoam"))

    def decorate(builder):
        add_pond(builder)

        steps = int(2.0 * math.pi * FIELD_RADIUS / HEDGE_STEP)
        hedge_count = 0
        for k in range(steps):
            if hedge_count >= HEDGE_MAX_BUSHES:
                break
            if rng.random() < HEDGE_SKIP_CHANCE:
                continue
            angle = 2.0 * math.pi * k / steps
            radius = field_boundary(angle) + HEDGE_OFFSET
            x, y = field_center.x + radius * math.cos(angle), field_center.y + radius * math.sin(angle)
            if hexgrid.inset_distance(x, y) < HEDGE_MIN_INSET:
                continue
            if pond_distance(x, y) < POND_RADIUS + HEDGE_POND_CLEARANCE:
                continue
            kit.add_bush(builder, rng, x, y, height(x, y), rng.uniform(HEDGE_MIN_RADIUS, HEDGE_MAX_RADIUS))
            hedge_count += 1

        placed = 0
        for _ in range(HAY_ATTEMPTS):
            if placed >= HAY_BALE_COUNT:
                break
            angle = rng.uniform(0.0, 2.0 * math.pi)
            radius = rng.uniform(0.0, FIELD_RADIUS * HAY_FIELD_FRACTION)
            x, y = field_center.x + radius * math.cos(angle), field_center.y + radius * math.sin(angle)
            if in_field(x, y):
                kit.add_round_hay_bale(builder, rng, x, y, height(x, y))
                placed += 1

        for k in range(REED_CLUMPS):
            angle = pond_angle + math.pi * 0.5 + k * REED_ANGLE_STEP + rng.uniform(-0.2, 0.2)
            x = pond_center.x + POND_RADIUS * REED_RING_FACTOR * math.cos(angle)
            y = pond_center.y + POND_RADIUS * REED_RING_FACTOR * math.sin(angle)
            kit.add_reed_clump(builder, rng, x, y, height(x, y))

        for k in range(POND_ROCKS):
            angle = pond_angle - math.pi * 0.6 - k * POND_ROCK_ANGLE_STEP
            x = pond_center.x + POND_RADIUS * POND_ROCK_RING_FACTOR * math.cos(angle)
            y = pond_center.y + POND_RADIUS * POND_ROCK_RING_FACTOR * math.sin(angle)
            kit.add_rock(builder, rng, x, y, height(x, y), rng.uniform(POND_ROCK_MIN_RADIUS, POND_ROCK_MAX_RADIUS))

    return common.assemble_tile(spec, rng, face_style, height, decorate, snap)
