"""SM_Tile_GoosebayLodge: the start tile. A cozy log lodge with a porch beside a lake, dock, rowboat and pines."""
import math
import random

from mathutils import Matrix, Vector

from lib import hexgrid, palette
from props import buildings, kit, water_props
from tiles import settlement_common as town
from tiles import water_common

LAKE_DISTANCE = 3.7
LAKE_RADIUS = 3.4
LAKE_WOBBLE = 0.15
LAKE_DEPTH = 0.75
LAKE_STRETCH = 1.25
LODGE_DISTANCE = 4.2
DOCK_LENGTH = 2.2
DOCK_WIDTH = 0.95
DOCK_ANGLE_OFFSET = 0.45
BOAT_ALONG = 1.6
BOAT_SIDE = 0.95
PINE_COUNT = 5
PINE_MIN_HEIGHT = 2.6
PINE_MAX_HEIGHT = 3.3
PINE_SPACING = 1.9
PINE_LAKE_CLEARANCE = 1.0
TREE_COUNT = 2
BUSH_COUNT = 3
REED_CLUMPS = 3
CATTAIL_CLUMPS = 2
BANK_PLANT_INSET = 0.3
LILY_PADS = 4
FIREWOOD_LENGTH = 1.1
FIREWOOD_SIZE = 0.24
FIREWOOD_STACK = ((-0.55, 0.5), (0.55, 0.5), (0.0, 1.35))  # (shift across, lift) in log sizes
CAMPFIRE_STONES = 6
CAMPFIRE_RADIUS = 0.5
CAMPFIRE_DISTANCE = 2.4
CAMPFIRE_LOG_LIFT = 0.08
CAMPFIRE_LOG_SIZE = 0.12
SCATTER_ATTEMPTS = 4000


def build(spec, seed):
    """Builds the Goosebay Lodge start tile."""
    rng = random.Random(seed)
    grass = hexgrid.GrassPainter(seed)
    base_height = town.settlement_height(seed)
    lake_angle = rng.uniform(0.0, 2.0 * math.pi)
    lake_dir = Vector((math.cos(lake_angle), math.sin(lake_angle), 0.0))
    lake = water_common.PondShape(tuple((lake_dir * LAKE_DISTANCE).xy), LAKE_RADIUS, seed + 11, wobble=LAKE_WOBBLE,
                                  depth=LAKE_DEPTH, stretch=(lake_angle + math.pi * 0.5, LAKE_STRETCH))
    lodge = -lake_dir * LODGE_DISTANCE
    tangent = Vector((-lake_dir.y, lake_dir.x, 0.0))

    def height(x, y):
        depth = lake.ground_depth(x, y)
        return base_height(x, y) if depth is None else depth

    def decorate(builder):
        settlement = town.Settlement(height)
        lake.add_water(builder)
        lake.add_foam(builder)
        lodge_rotation = town.facing_rotation(tuple(lodge.xy), (0.0, 0.0)) + rng.uniform(-0.15, 0.15)
        radius = buildings.add_lodge(builder, rng, lodge.x, lodge.y, height(lodge.x, lodge.y), lodge_rotation)
        settlement.add_footprint(tuple(lodge.xy), radius * 0.8)

        dock_angle = lake_angle + math.pi + DOCK_ANGLE_OFFSET * rng.choice((-1.0, 1.0))
        shore = lake.point(dock_angle)
        inward = dock_angle + math.pi
        water_props.add_dock(builder, rng, shore.x, shore.y, inward, DOCK_LENGTH, DOCK_WIDTH,
                             water_common.WATER_LEVEL)
        settlement.add_footprint((shore.x, shore.y), 1.0)
        side = rng.choice((-1.0, 1.0))
        boat = (shore.x + BOAT_ALONG * math.cos(inward) + side * BOAT_SIDE * math.cos(inward + math.pi / 2),
                shore.y + BOAT_ALONG * math.sin(inward) + side * BOAT_SIDE * math.sin(inward + math.pi / 2))
        water_props.add_rowboat(builder, rng, boat[0], boat[1], water_common.WATER_LEVEL, inward + 0.3 * side,
                                hull_color="Pumpkin")
        porch = town.local_to_world(tuple(lodge.xy), lodge_rotation,
                                    (0.0, -buildings.LODGE_WIDTH * 0.5 - buildings.LODGE_PORCH_DEPTH - 0.5))
        land_end = lake.point(dock_angle, 0.6)
        settlement.add_path(builder, town.curved_path(porch, land_end, 0.4))

        campfire = lodge + tangent * (CAMPFIRE_DISTANCE * side * -1.0) + lake_dir * 2.2
        if settlement.is_free(campfire.x, campfire.y, 0.3) and lake.inset(campfire.x, campfire.y) < -0.8:
            for k in range(CAMPFIRE_STONES):
                angle = 2.0 * math.pi * k / CAMPFIRE_STONES
                kit.add_rock(builder, rng, campfire.x + CAMPFIRE_RADIUS * math.cos(angle),
                             campfire.y + CAMPFIRE_RADIUS * math.sin(angle), height(campfire.x, campfire.y), 0.16)
            for k in range(2):
                angle = rng.uniform(0.0, math.pi) + k * math.pi * 0.5
                half = Vector((math.cos(angle), math.sin(angle), 0.0)) * 0.35
                base = Vector((campfire.x, campfire.y, height(campfire.x, campfire.y) + CAMPFIRE_LOG_LIFT))
                buildings.add_beam(builder, Matrix.Identity(4), base - half, base + half, CAMPFIRE_LOG_SIZE, "Wood",
                                   palette.SHADE_BASE)
            settlement.add_footprint((campfire.x, campfire.y), 0.8)

        woodpile = town.local_to_world(tuple(lodge.xy), lodge_rotation,
                                       (-buildings.LODGE_LENGTH * 0.5 - 0.7, 0.4))
        along = Vector((math.cos(lodge_rotation + math.pi / 2), math.sin(lodge_rotation + math.pi / 2), 0.0))
        across = Vector((math.cos(lodge_rotation), math.sin(lodge_rotation), 0.0))
        ground = height(woodpile.x, woodpile.y)
        for shift, lift in FIREWOOD_STACK:
            center = Vector((woodpile.x, woodpile.y, ground + FIREWOOD_SIZE * lift)) + across * (shift * FIREWOOD_SIZE)
            buildings.add_beam(builder, Matrix.Identity(4), center - along * (FIREWOOD_LENGTH * 0.5),
                               center + along * (FIREWOOD_LENGTH * 0.5), FIREWOOD_SIZE, "Wood", palette.SHADE_DARK)
        settlement.add_footprint(tuple(woodpile.xy), 0.8)

        for k in range(REED_CLUMPS + CATTAIL_CLUMPS):
            angle = lake_angle + math.radians(-80.0 + 160.0 * k / (REED_CLUMPS + CATTAIL_CLUMPS - 1))
            point = lake.point(angle, -BANK_PLANT_INSET)
            if k % 2 == 1:
                water_props.add_cattail_clump(builder, rng, point.x, point.y, height(point.x, point.y))
            else:
                kit.add_reed_clump(builder, rng, point.x, point.y, height(point.x, point.y))
        lily = lake.point(lake_angle + 0.5, -lake.radius(lake_angle + 0.5) * 0.5)
        water_props.add_lily_pads(builder, rng, lily.x, lily.y, water_common.WATER_LEVEL, LILY_PADS)

        pines = []
        for _ in range(SCATTER_ATTEMPTS):
            if len(pines) >= PINE_COUNT:
                break
            pine_height = rng.uniform(PINE_MIN_HEIGHT, PINE_MAX_HEIGHT)
            x, y = rng.uniform(-hexgrid.TILE_RADIUS, hexgrid.TILE_RADIUS), rng.uniform(-hexgrid.TILE_RADIUS,
                                                                                       hexgrid.TILE_RADIUS)
            if not water_common.tree_clear_of_rim(x, y, water_props.pine_radius(pine_height)):
                continue
            if lake.inset(x, y) > -PINE_LAKE_CLEARANCE or not settlement.is_free(x, y, 0.6):
                continue
            if (Vector((x, y, 0.0)) - lake.center).dot(lake_dir) > 0.0 and rng.random() < 0.7:
                continue  # keep most pines behind the lodge, away from the far shore
            if any(math.hypot(x - px, y - py) < PINE_SPACING for px, py in pines):
                continue
            pines.append((x, y))
            water_props.add_shore_pine(builder, rng, x, y, height(x, y), pine_height)
        for x, y in pines:
            settlement.add_footprint((x, y), 0.6)
        settlement.add_trees(builder, rng, TREE_COUNT, lambda x, y: lake.inset(x, y) < -1.0)
        settlement.add_bushes(builder, rng, BUSH_COUNT, lambda x, y: lake.inset(x, y) < -0.6)

    return water_common.assemble_tile(spec, rng, grass.style, height, decorate, lake.snap)
