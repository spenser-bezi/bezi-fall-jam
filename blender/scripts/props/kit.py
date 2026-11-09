"""Seam-test prop kit: deciduous tree, bush, rock, reed clump, round hay bale."""
import math

from mathutils import Matrix

from lib import hexgrid, materials, palette, shapes

TRUNK_SIDES = 5
TRUNK_RADIUS = 0.16
TRUNK_TOP_RADIUS = 0.11
TRUNK_HEIGHT = 0.8
TRUNK_SINK = 0.1
CANOPY_U_SEGMENTS = 7
CANOPY_V_SEGMENTS = 5
CANOPY_SQUASH = 1.05
CANOPY_JITTER = 0.12
CANOPY_CENTER_FACTOR = 0.75
DECOR_HEIGHT_MARGIN = 0.1

BUSH_U_SEGMENTS = 6
BUSH_V_SEGMENTS = 4
BUSH_SQUASH = 0.75
BUSH_JITTER = 0.15
BUSH_SINK_FACTOR = 0.35
BUSH_SWAY = 0.35

ROCK_U_SEGMENTS = 5
ROCK_V_SEGMENTS = 3
ROCK_SQUASH = 0.6
ROCK_JITTER = 0.25
ROCK_SINK_FACTOR = 0.25

REED_SIDES = 4
REED_RADIUS = 0.06
REED_MIN_HEIGHT = 0.9
REED_MAX_HEIGHT = 1.4
REED_SPREAD = 0.25
REEDS_PER_CLUMP = 3

HAY_SIDES = 8
HAY_RADIUS = 0.55
HAY_LENGTH = 1.0
HAY_SINK = 0.08

LIGHT_SHADE_CHANCE = 0.25
DARK_SHADE_CHANCE = 0.15
MATERIAL = materials.PALETTE_MATERIAL


def random_shade(rng, light_chance=LIGHT_SHADE_CHANCE, dark_chance=DARK_SHADE_CHANCE):
    """Picks base/light/dark shade for painterly per-face variation."""
    roll = rng.random()
    if roll < light_chance:
        return palette.SHADE_LIGHT
    if roll < light_chance + dark_chance:
        return palette.SHADE_DARK
    return palette.SHADE_BASE


def _placement(x, y, z, rotation, scale=1.0):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(rotation, 4, "Z") @ Matrix.Scale(scale, 4)


def tree_max_canopy_radius(canopy_radius):
    """Planar canopy radius including jitter, used to keep overhang inside the tile limit."""
    return canopy_radius * (1.0 + CANOPY_JITTER)


def add_deciduous_tree(builder, rng, x, y, base_z, canopy_radius, color_name):
    """Adds a trunk + faceted canopy tree, scaled down if needed to respect the decor height limit."""
    canopy_center = TRUNK_HEIGHT + canopy_radius * CANOPY_CENTER_FACTOR
    top = base_z + canopy_center + canopy_radius * CANOPY_SQUASH * (1.0 + CANOPY_JITTER)
    scale = min(1.0, (hexgrid.MAX_DECOR_HEIGHT - DECOR_HEIGHT_MARGIN - base_z) / (top - base_z))
    base = _placement(x, y, base_z, rng.uniform(0.0, 2.0 * math.pi), scale)

    trunk = shapes.prism(TRUNK_SIDES, TRUNK_RADIUS, canopy_center + TRUNK_SINK, top_radius=TRUNK_TOP_RADIUS,
                         cap_top=False)
    builder.add_part(trunk, base @ Matrix.Translation((0.0, 0.0, -TRUNK_SINK)), MATERIAL,
                     lambda face, centroid: palette.flat_uv("Wood", palette.SHADE_DARK))

    canopy = shapes.blob(CANOPY_U_SEGMENTS, CANOPY_V_SEGMENTS, canopy_radius, CANOPY_SQUASH, CANOPY_JITTER, rng)
    canopy_height = canopy_radius * CANOPY_SQUASH
    builder.add_part(canopy, base @ Matrix.Translation((0.0, 0.0, canopy_center)), MATERIAL,
                     lambda face, centroid: palette.flat_uv(color_name, random_shade(rng)),
                     lambda local: 0.5 + 0.5 * local.z / canopy_height)


def add_bush(builder, rng, x, y, base_z, radius, color_name="Moss"):
    """Adds a squat faceted bush, sunk into the ground."""
    bush = shapes.blob(BUSH_U_SEGMENTS, BUSH_V_SEGMENTS, radius, BUSH_SQUASH, BUSH_JITTER, rng)
    placement = _placement(x, y, base_z + radius * BUSH_SQUASH * (1.0 - BUSH_SINK_FACTOR),
                           rng.uniform(0.0, 2.0 * math.pi))
    builder.add_part(bush, placement, MATERIAL,
                     lambda face, centroid: palette.flat_uv(color_name, rng.choice(
                         (palette.SHADE_DARK, palette.SHADE_DARK, palette.SHADE_BASE, palette.SHADE_EXTRA_DARK))),
                     lambda local: BUSH_SWAY)


def add_rock(builder, rng, x, y, base_z, radius):
    """Adds a flattened, jittered low-poly rock."""
    rock = shapes.blob(ROCK_U_SEGMENTS, ROCK_V_SEGMENTS, radius, ROCK_SQUASH, ROCK_JITTER, rng)
    placement = _placement(x, y, base_z + radius * ROCK_SQUASH * (1.0 - 2.0 * ROCK_SINK_FACTOR),
                           rng.uniform(0.0, 2.0 * math.pi))
    builder.add_part(rock, placement, MATERIAL,
                     lambda face, centroid: palette.flat_uv("Stone", random_shade(rng, 0.3, 0.3)))


def add_reed_clump(builder, rng, x, y, base_z):
    """Adds a small clump of thin reed cones."""
    for _ in range(REEDS_PER_CLUMP):
        height = rng.uniform(REED_MIN_HEIGHT, REED_MAX_HEIGHT)
        reed = shapes.cone(REED_SIDES, REED_RADIUS, height)
        placement = _placement(x + rng.uniform(-REED_SPREAD, REED_SPREAD), y + rng.uniform(-REED_SPREAD, REED_SPREAD),
                               base_z - TRUNK_SINK, rng.uniform(0.0, 2.0 * math.pi))
        builder.add_part(reed, placement, MATERIAL,
                         lambda face, centroid: palette.flat_uv("DryGrass", palette.SHADE_DARK),
                         lambda local, h=height: local.z / h)


def add_round_hay_bale(builder, rng, x, y, base_z):
    """Adds a round hay bale lying on its side."""
    bale = shapes.prism(HAY_SIDES, HAY_RADIUS, HAY_LENGTH, cap_top=True, cap_bottom=True)
    placement = (_placement(x, y, base_z + HAY_RADIUS - HAY_SINK, rng.uniform(0.0, 2.0 * math.pi))
                 @ Matrix.Rotation(math.radians(90.0), 4, "X") @ Matrix.Translation((0.0, 0.0, -HAY_LENGTH * 0.5)))
    builder.add_part(bale, placement, MATERIAL,
                     lambda face, centroid: palette.flat_uv(
                         "HarvestGold", palette.SHADE_DARK if face >= HAY_SIDES else random_shade(rng, 0.3, 0.1)))
