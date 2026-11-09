"""SM_Tile_SeamTest_Grove: dense-biome seam test (trees near the rim, canopy overhang, leaf litter)."""
import math
import random

from lib import hexgrid, materials, palette
from lib.scatter import Noise2D, scatter_points
from props import kit
from tiles import common

TREE_COUNT = 10
TREE_MIN_SPACING = 2.7
TREE_MIN_RADIUS = 1.0
TREE_MAX_RADIUS = 1.25
TREE_MIN_TRUNK_INSET = 0.8
TREE_COLORS = ("MapleRed", "Mustard", "Pumpkin")
BUSH_COUNT = 5
BUSH_MIN_RADIUS = 0.45
BUSH_MAX_RADIUS = 0.65
BUSH_MIN_INSET = 0.9
BUSH_TREE_CLEARANCE = 1.6
ROCK_COUNT = 3
ROCK_MIN_RADIUS = 0.35
ROCK_MAX_RADIUS = 0.6
ROCK_MIN_INSET = 1.2
LITTER_RADIUS = 1.5
LITTER_NOISE = 0.5
LITTER_NOISE_FREQUENCY = 0.35
LITTER_SWATCHES = (("Mustard", palette.SHADE_DARK), ("Mustard", palette.SHADE_DARK),
                   ("DryGrass", palette.SHADE_BASE), ("DryGrass", palette.SHADE_DARK),
                   ("MapleRed", palette.SHADE_DARK))
SCATTER_EXTENT = hexgrid.TILE_RADIUS


def build(spec, seed):
    """Builds the grove seam-test tile."""
    rng = random.Random(seed)
    litter_noise = Noise2D(seed + 2)
    grass = hexgrid.GrassPainter(seed)
    height = common.gentle_height(seed, amplitude=0.12)

    trees = []
    for _ in range(4000):
        if len(trees) >= TREE_COUNT:
            break
        radius = rng.uniform(TREE_MIN_RADIUS, TREE_MAX_RADIUS)
        x, y = rng.uniform(-SCATTER_EXTENT, SCATTER_EXTENT), rng.uniform(-SCATTER_EXTENT, SCATTER_EXTENT)
        min_inset = max(TREE_MIN_TRUNK_INSET, kit.tree_max_canopy_radius(radius) - hexgrid.MAX_CANOPY_OVERHANG)
        if hexgrid.inset_distance(x, y) < min_inset:
            continue
        if any(math.hypot(x - tx, y - ty) < TREE_MIN_SPACING for tx, ty, _ in trees):
            continue
        trees.append((x, y, radius))

    def face_style(centroid, face_rng):
        nearest = min(math.hypot(centroid.x - tx, centroid.y - ty) for tx, ty, _ in trees)
        threshold = LITTER_RADIUS + LITTER_NOISE * litter_noise.sample(centroid.x, centroid.y, LITTER_NOISE_FREQUENCY)
        if nearest < threshold:
            name, shade = face_rng.choice(LITTER_SWATCHES)
            return materials.PALETTE_MATERIAL, palette.flat_uv(name, shade)
        return grass.style(centroid, face_rng)

    def decorate(builder):
        for index, (x, y, radius) in enumerate(trees):
            kit.add_deciduous_tree(builder, rng, x, y, height(x, y), radius, TREE_COLORS[index % len(TREE_COLORS)])
        tree_points = [(x, y) for x, y, _ in trees]
        bushes = scatter_points(rng, BUSH_COUNT, SCATTER_EXTENT, BUSH_TREE_CLEARANCE,
                                lambda x, y: hexgrid.inset_distance(x, y) >= BUSH_MIN_INSET, existing=tree_points)
        for x, y in bushes:
            kit.add_bush(builder, rng, x, y, height(x, y), rng.uniform(BUSH_MIN_RADIUS, BUSH_MAX_RADIUS))
        rocks = scatter_points(rng, ROCK_COUNT, SCATTER_EXTENT, BUSH_TREE_CLEARANCE,
                               lambda x, y: hexgrid.inset_distance(x, y) >= ROCK_MIN_INSET,
                               existing=tree_points + bushes)
        for x, y in rocks:
            kit.add_rock(builder, rng, x, y, height(x, y), rng.uniform(ROCK_MIN_RADIUS, ROCK_MAX_RADIUS))

    return common.assemble_tile(spec, rng, face_style, height, decorate)
