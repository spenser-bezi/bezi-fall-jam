"""SM_Tile_Marsh_A: boggy marsh of small pools with cranberry-red bog patches, cattails, reeds and dry grass."""
import math
import random

from lib import hexgrid, materials, palette
from lib.scatter import Noise2D, scatter_points
from props import kit, water_props
from tiles import common, water_common

POOL_COUNT = 3
POOL_RING_RADIUS = 3.7
POOL_MIN_RADIUS = 1.9
POOL_MAX_RADIUS = 2.5
POOL_WOBBLE = 0.24
POOL_DEPTH = 0.55
POOL_SLOPE_WIDTH = 0.8
BOG_PATCHES_PER_POOL = 2
BOG_PATCH_MIN_RADIUS = 0.35
BOG_PATCH_MAX_RADIUS = 0.6
BOG_PATCH_RADIUS_FRACTION = 0.45
CATTAIL_CLUMPS = 5
REED_CLUMPS = 4
BANK_PLANT_INSET = 0.25
DRY_GRASS_FREQUENCY = 0.3
DRY_GRASS_THRESHOLD = 0.12
DRY_GRASS_MIN_INSET = 2.2
TREE_COUNT = 2
BUSH_COUNT = 5
ROCK_COUNT = 2
LAND_CLEARANCE = 0.9


def build(spec, seed):
    """Builds the marsh tile."""
    rng = random.Random(seed)
    grass = hexgrid.GrassPainter(seed)
    dry_noise = Noise2D(seed + 5)
    base_height = common.gentle_height(seed, amplitude=0.05)
    start = rng.uniform(0.0, 2.0 * math.pi)
    pools = []
    for k in range(POOL_COUNT):
        angle = start + 2.0 * math.pi * k / POOL_COUNT + rng.uniform(-0.3, 0.3)
        center = (POOL_RING_RADIUS * math.cos(angle), POOL_RING_RADIUS * math.sin(angle))
        pools.append(water_common.PondShape(center, rng.uniform(POOL_MIN_RADIUS, POOL_MAX_RADIUS), seed + 20 + k,
                                            wobble=POOL_WOBBLE, depth=POOL_DEPTH, slope_width=POOL_SLOPE_WIDTH))

    def pool_inset(x, y):
        return max(pool.inset(x, y) for pool in pools)

    def height(x, y):
        depths = [d for d in (pool.ground_depth(x, y) for pool in pools) if d is not None]
        return min(depths) if depths else base_height(x, y)

    def face_style(centroid, face_rng):
        wet = hexgrid.inset_distance(centroid.x, centroid.y) > DRY_GRASS_MIN_INSET
        if wet and dry_noise.sample(centroid.x, centroid.y, DRY_GRASS_FREQUENCY) > DRY_GRASS_THRESHOLD:
            shade = palette.SHADE_BASE if face_rng.random() < 0.7 else palette.SHADE_DARK
            return materials.PALETTE_MATERIAL, palette.flat_uv("DryGrass", shade)
        return grass.style(centroid, face_rng)

    def snap(position):
        nearest = max(pools, key=lambda pool: pool.inset(position.x, position.y))
        return nearest.snap(position)

    def decorate(builder):
        for pool in pools:
            pool.add_water(builder)
            pool.add_foam(builder)
            for _ in range(BOG_PATCHES_PER_POOL):
                angle = rng.uniform(0.0, 2.0 * math.pi)
                point = pool.point(angle, -pool.radius(angle) * (1.0 - BOG_PATCH_RADIUS_FRACTION))
                water_props.add_bog_patch(builder, rng, point.x, point.y, water_common.WATER_LEVEL,
                                          rng.uniform(BOG_PATCH_MIN_RADIUS, BOG_PATCH_MAX_RADIUS))
        for k in range(CATTAIL_CLUMPS + REED_CLUMPS):
            pool = pools[k % POOL_COUNT]
            angle = rng.uniform(0.0, 2.0 * math.pi)
            point = pool.point(angle, -BANK_PLANT_INSET)
            if k < CATTAIL_CLUMPS:
                water_props.add_cattail_clump(builder, rng, point.x, point.y, height(point.x, point.y))
            else:
                kit.add_reed_clump(builder, rng, point.x, point.y, height(point.x, point.y))

        trees = []
        for _ in range(4000):
            if len(trees) >= TREE_COUNT:
                break
            radius = rng.uniform(0.8, 1.0)
            x, y = rng.uniform(-hexgrid.TILE_RADIUS, hexgrid.TILE_RADIUS), rng.uniform(-hexgrid.TILE_RADIUS,
                                                                                       hexgrid.TILE_RADIUS)
            if not water_common.tree_clear_of_rim(x, y, kit.tree_max_canopy_radius(radius)):
                continue
            if pool_inset(x, y) > -1.2 or any(math.hypot(x - tx, y - ty) < 3.0 for tx, ty, _ in trees):
                continue
            trees.append((x, y, radius))
        for x, y, radius in trees:
            kit.add_deciduous_tree(builder, rng, x, y, height(x, y), radius, "Mustard")
        blockers = [(x, y) for x, y, _ in trees]
        bushes = scatter_points(rng, BUSH_COUNT, hexgrid.TILE_RADIUS, 1.4,
                                lambda x, y: hexgrid.inset_distance(x, y) >= 0.9 and pool_inset(x, y) < -LAND_CLEARANCE,
                                existing=blockers)
        for x, y in bushes:
            kit.add_bush(builder, rng, x, y, height(x, y), rng.uniform(0.35, 0.55), "DryGrass")
        rocks = scatter_points(rng, ROCK_COUNT, hexgrid.TILE_RADIUS, 1.2,
                               lambda x, y: hexgrid.inset_distance(x, y) >= 1.5 and -0.6 < pool_inset(x, y) < 0.0,
                               existing=blockers + bushes)
        for x, y in rocks:
            kit.add_rock(builder, rng, x, y, height(x, y), rng.uniform(0.25, 0.4))

    obj = water_common.assemble_tile(spec, rng, face_style, height, decorate, snap)
    water_common.add_water_snack_sockets(obj, [tuple(pool.center.xy) for pool in pools[:2]])
    return obj
