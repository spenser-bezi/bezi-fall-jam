"""SM_Tile_Lake_A: self-contained autumn lake with a grass rim, dock + rowboat, reeds, lily pads and shore trees."""
import math
import random

from lib import hexgrid
from lib.scatter import scatter_points
from props import kit, water_props
from tiles import common, water_common

LAKE_CENTER_OFFSET = 0.7
LAKE_RADIUS = 5.0
LAKE_STRETCH = 1.15
LAKE_DEPTH = 0.8
DOCK_LENGTH = 2.6
DOCK_WIDTH = 1.0
BOAT_SIDE_OFFSET = 1.05
BOAT_ALONG_FRACTION = 0.7
REED_CLUMPS = 5
REED_BANK_INSET = 0.3
REED_DOCK_CLEARANCE = 0.7
LILY_CLUSTER_RADIUS_FRACTION = 0.55
LILY_PADS = 5
TREE_COUNT = 4
TREE_MIN_RADIUS = 0.85
TREE_MAX_RADIUS = 1.1
TREE_SHORE_CLEARANCE = 1.0
TREE_SPACING = 2.4
TREE_COLORS = ("MapleRed", "Pumpkin", "Mustard", "MapleRed")
BUSH_COUNT = 4
BUSH_MIN_RADIUS = 0.4
BUSH_MAX_RADIUS = 0.6
BUSH_MIN_INSET = 0.9
ROCK_COUNT = 3
ROCK_MIN_RADIUS = 0.3
ROCK_MAX_RADIUS = 0.55
SNACK_RADIUS_FRACTION = 0.4
DOCK_CLEARANCE = 2.0


def build(spec, seed):
    """Builds the dock lake tile."""
    rng = random.Random(seed)
    grass = hexgrid.GrassPainter(seed)
    base_height = common.gentle_height(seed)
    offset_angle = rng.uniform(0.0, 2.0 * math.pi)
    center = (LAKE_CENTER_OFFSET * math.cos(offset_angle), LAKE_CENTER_OFFSET * math.sin(offset_angle))
    lake = water_common.PondShape(center, LAKE_RADIUS, seed + 11, depth=LAKE_DEPTH,
                                  stretch=(rng.uniform(0.0, math.pi), LAKE_STRETCH))

    def height(x, y):
        depth = lake.ground_depth(x, y)
        return base_height(x, y) if depth is None else depth

    dock_angle = offset_angle + math.pi * rng.uniform(0.7, 1.3)

    def decorate(builder):
        lake.add_water(builder)
        lake.add_foam(builder)

        shore = lake.point(dock_angle)
        inward = dock_angle + math.pi
        water_props.add_dock(builder, rng, shore.x, shore.y, inward, DOCK_LENGTH, DOCK_WIDTH,
                             water_common.WATER_LEVEL)
        along = DOCK_LENGTH * BOAT_ALONG_FRACTION
        side = rng.choice((-1.0, 1.0))
        boat_x = shore.x + along * math.cos(inward) + side * BOAT_SIDE_OFFSET * math.cos(inward + math.pi / 2)
        boat_y = shore.y + along * math.sin(inward) + side * BOAT_SIDE_OFFSET * math.sin(inward + math.pi / 2)
        water_props.add_rowboat(builder, rng, boat_x, boat_y, water_common.WATER_LEVEL, inward + rng.uniform(-0.3, 0.3))

        for k in range(REED_CLUMPS):
            angle = dock_angle + 2.0 * math.pi * (k + 0.5) / (REED_CLUMPS + 1) + rng.uniform(-0.2, 0.2)
            point = lake.point(angle, -REED_BANK_INSET)
            if math.hypot(point.x - shore.x, point.y - shore.y) < REED_DOCK_CLEARANCE + DOCK_WIDTH:
                continue
            kit.add_reed_clump(builder, rng, point.x, point.y, height(point.x, point.y))

        lily_angle = dock_angle + math.pi + rng.uniform(-0.6, 0.6)
        lily = lake.point(lily_angle, -lake.radius(lily_angle) * (1.0 - LILY_CLUSTER_RADIUS_FRACTION))
        water_props.add_lily_pads(builder, rng, lily.x, lily.y, water_common.WATER_LEVEL, LILY_PADS)

        dock_point = (shore.x, shore.y)
        trees = []
        for _ in range(4000):
            if len(trees) >= TREE_COUNT:
                break
            radius = rng.uniform(TREE_MIN_RADIUS, TREE_MAX_RADIUS)
            x, y = rng.uniform(-hexgrid.TILE_RADIUS, hexgrid.TILE_RADIUS), rng.uniform(-hexgrid.TILE_RADIUS,
                                                                                       hexgrid.TILE_RADIUS)
            if not water_common.tree_clear_of_rim(x, y, kit.tree_max_canopy_radius(radius)):
                continue
            if lake.inset(x, y) > -TREE_SHORE_CLEARANCE:
                continue
            if math.hypot(x - dock_point[0], y - dock_point[1]) < DOCK_CLEARANCE + radius:
                continue
            if any(math.hypot(x - tx, y - ty) < TREE_SPACING for tx, ty, _ in trees):
                continue
            trees.append((x, y, radius))
        for index, (x, y, radius) in enumerate(trees):
            kit.add_deciduous_tree(builder, rng, x, y, height(x, y), radius, TREE_COLORS[index % len(TREE_COLORS)])

        blockers = [(x, y) for x, y, _ in trees] + [dock_point]
        bushes = scatter_points(rng, BUSH_COUNT, hexgrid.TILE_RADIUS, 1.4,
                                lambda x, y: hexgrid.inset_distance(x, y) >= BUSH_MIN_INSET and lake.inset(x, y) < -0.6,
                                existing=blockers)
        for x, y in bushes:
            kit.add_bush(builder, rng, x, y, height(x, y), rng.uniform(BUSH_MIN_RADIUS, BUSH_MAX_RADIUS))
        rocks = scatter_points(rng, ROCK_COUNT, hexgrid.TILE_RADIUS, 1.2,
                               lambda x, y: -0.6 < lake.inset(x, y) < 0.1 and hexgrid.inset_distance(x, y) > 1.2,
                               existing=blockers + bushes)
        for x, y in rocks:
            kit.add_rock(builder, rng, x, y, height(x, y), rng.uniform(ROCK_MIN_RADIUS, ROCK_MAX_RADIUS))

    obj = water_common.assemble_tile(spec, rng, grass.style, height, decorate, lake.snap)
    snack_points = []
    for angle in (dock_angle + math.pi * 0.6, dock_angle - math.pi * 0.6):
        point = lake.point(angle, -lake.radius(angle) * (1.0 - SNACK_RADIUS_FRACTION))
        snack_points.append((point.x, point.y))
    water_common.add_water_snack_sockets(obj, snack_points)
    return obj
