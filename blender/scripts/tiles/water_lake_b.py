"""SM_Tile_Lake_B: self-contained pond with a small wooded island, cattails, reeds and lily pads (no dock)."""
import math
import random

from lib import hexgrid
from lib.scatter import Noise2D, scatter_points
from props import kit, water_props
from tiles import common, water_common

POND_CENTER_OFFSET = 0.5
POND_RADIUS = 5.3
POND_WOBBLE = 0.2
POND_DEPTH = 0.8
ISLAND_OFFSET = 1.4
ISLAND_RADIUS = 1.35
ISLAND_WOBBLE = 0.12
ISLAND_TOP = 0.22
ISLAND_TOP_WIDTH = 0.7
ISLAND_SLOPE_WIDTH = 0.9
ISLAND_TREE_RADIUS = 0.8
REED_CLUMPS = 4
CATTAIL_CLUMPS = 2
BANK_PLANT_INSET = 0.3
LILY_CLUSTERS = 2
LILY_PADS = 4
LILY_RADIUS_FRACTION = 0.72
TREE_COUNT = 4
TREE_MIN_RADIUS = 0.85
TREE_MAX_RADIUS = 1.1
TREE_SHORE_CLEARANCE = 0.9
TREE_SPACING = 2.4
TREE_COLORS = ("Mustard", "MapleRed", "Pumpkin", "Mustard")
BUSH_COUNT = 4
ROCK_COUNT = 3
SNACK_RADIUS_FRACTION = 0.62


def build(spec, seed):
    """Builds the island pond tile."""
    rng = random.Random(seed)
    grass = hexgrid.GrassPainter(seed)
    base_height = common.gentle_height(seed)
    offset_angle = rng.uniform(0.0, 2.0 * math.pi)
    center = (POND_CENTER_OFFSET * math.cos(offset_angle), POND_CENTER_OFFSET * math.sin(offset_angle))
    pond = water_common.PondShape(center, POND_RADIUS, seed + 11, wobble=POND_WOBBLE, depth=POND_DEPTH)
    island_angle = offset_angle + math.pi + rng.uniform(-0.5, 0.5)
    island_center = pond.center.copy()
    island_center.x += ISLAND_OFFSET * math.cos(island_angle)
    island_center.y += ISLAND_OFFSET * math.sin(island_angle)
    island_noise = Noise2D(seed + 13)

    def island_radius(angle):
        return ISLAND_RADIUS * (1.0 + ISLAND_WOBBLE * island_noise.sample(math.cos(angle) * 1.5, math.sin(angle) * 1.5))

    def island_inset(x, y):
        dx, dy = x - island_center.x, y - island_center.y
        return island_radius(math.atan2(dy, dx)) - math.hypot(dx, dy)

    def height(x, y):
        depth = pond.ground_depth(x, y)
        if depth is None:
            return base_height(x, y)
        inside = island_inset(x, y)
        if inside >= 0.0:
            return ISLAND_TOP * min(1.0, inside / ISLAND_TOP_WIDTH)
        return max(depth, POND_DEPTH * inside / ISLAND_SLOPE_WIDTH)

    def snap(position):
        position = pond.snap(position)
        return hexgrid.snap_to_polar_contour(position, island_center, island_radius,
                                             water_common.POND_SNAP_THRESHOLD)

    def decorate(builder):
        pond.add_water(builder)
        pond.add_foam(builder)
        water_common.add_island_foam(builder, island_center, island_radius)
        kit.add_deciduous_tree(builder, rng, island_center.x, island_center.y, ISLAND_TOP, ISLAND_TREE_RADIUS,
                               "MapleRed")
        rock_angle = rng.uniform(0.0, 2.0 * math.pi)
        rock_x = island_center.x + ISLAND_RADIUS * 0.7 * math.cos(rock_angle)
        rock_y = island_center.y + ISLAND_RADIUS * 0.7 * math.sin(rock_angle)
        kit.add_rock(builder, rng, rock_x, rock_y, height(rock_x, rock_y), 0.35)

        for k in range(REED_CLUMPS + CATTAIL_CLUMPS):
            angle = offset_angle + 2.0 * math.pi * k / (REED_CLUMPS + CATTAIL_CLUMPS) + rng.uniform(-0.25, 0.25)
            point = pond.point(angle, -BANK_PLANT_INSET)
            if k % 3 == 1:
                water_props.add_cattail_clump(builder, rng, point.x, point.y, height(point.x, point.y))
            else:
                kit.add_reed_clump(builder, rng, point.x, point.y, height(point.x, point.y))

        for k in range(LILY_CLUSTERS):
            angle = island_angle + math.pi * (0.55 + 0.9 * k) + rng.uniform(-0.2, 0.2)
            point = pond.point(angle, -pond.radius(angle) * (1.0 - LILY_RADIUS_FRACTION))
            water_props.add_lily_pads(builder, rng, point.x, point.y, water_common.WATER_LEVEL, LILY_PADS)

        trees = []
        for _ in range(4000):
            if len(trees) >= TREE_COUNT:
                break
            radius = rng.uniform(TREE_MIN_RADIUS, TREE_MAX_RADIUS)
            x, y = rng.uniform(-hexgrid.TILE_RADIUS, hexgrid.TILE_RADIUS), rng.uniform(-hexgrid.TILE_RADIUS,
                                                                                       hexgrid.TILE_RADIUS)
            if not water_common.tree_clear_of_rim(x, y, kit.tree_max_canopy_radius(radius)):
                continue
            if pond.inset(x, y) > -TREE_SHORE_CLEARANCE:
                continue
            if any(math.hypot(x - tx, y - ty) < TREE_SPACING for tx, ty, _ in trees):
                continue
            trees.append((x, y, radius))
        for index, (x, y, radius) in enumerate(trees):
            kit.add_deciduous_tree(builder, rng, x, y, height(x, y), radius, TREE_COLORS[index % len(TREE_COLORS)])

        blockers = [(x, y) for x, y, _ in trees]
        bushes = scatter_points(rng, BUSH_COUNT, hexgrid.TILE_RADIUS, 1.4,
                                lambda x, y: hexgrid.inset_distance(x, y) >= 0.9 and pond.inset(x, y) < -0.6,
                                existing=blockers)
        for x, y in bushes:
            kit.add_bush(builder, rng, x, y, height(x, y), rng.uniform(0.4, 0.6))
        rocks = scatter_points(rng, ROCK_COUNT, hexgrid.TILE_RADIUS, 1.2,
                               lambda x, y: -0.6 < pond.inset(x, y) < 0.1 and hexgrid.inset_distance(x, y) > 1.2,
                               existing=blockers + bushes)
        for x, y in rocks:
            kit.add_rock(builder, rng, x, y, height(x, y), rng.uniform(0.3, 0.5))

    obj = water_common.assemble_tile(spec, rng, grass.style, height, decorate, snap)
    snack_points = []
    for angle in (island_angle + math.pi * 0.5, island_angle - math.pi * 0.5):
        point = pond.point(angle, -pond.radius(angle) * (1.0 - SNACK_RADIUS_FRACTION))
        snack_points.append((point.x, point.y))
    water_common.add_water_snack_sockets(obj, snack_points)
    return obj
