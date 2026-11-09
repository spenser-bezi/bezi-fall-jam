"""SM_Tile_Village_A: four cottages around a little village green, joined by internal dirt paths."""
import math
import random

from lib import hexgrid
from props import buildings, kit
from tiles import settlement_common as town
from tiles import water_common

HOUSE_COUNT = 4
HOUSE_RING_RADIUS = 4.9
HOUSE_STYLES = ("small", "tall", "long", "small")
ROOFS = (buildings.RED_ROOF, buildings.NAVY_ROOF, buildings.RED_ROOF, buildings.NAVY_ROOF)
GREEN_TREE_RADIUS = 1.05
GREEN_RING_RADIUS = 1.85
GREEN_RING_POINTS = 12
SPOKE_BEND = 0.2
GARDEN_WIDTH = 2.6
GARDEN_DEPTH = 1.8
GARDEN_DISTANCE = 2.9
HAY_BALES = 1
TREE_COUNT = 4
BUSH_COUNT = 5


def build(spec, seed):
    """Builds the village-green tile."""
    rng = random.Random(seed)
    grass = hexgrid.GrassPainter(seed)
    height = town.settlement_height(seed)
    hub = (0.0, 0.0)
    start = rng.uniform(0.0, 2.0 * math.pi)
    positions = town.ring_positions(hub, HOUSE_RING_RADIUS, HOUSE_COUNT, start, rng)

    def decorate(builder):
        settlement = town.Settlement(height)
        kit.add_deciduous_tree(builder, rng, hub[0], hub[1], height(*hub), GREEN_TREE_RADIUS, "MapleRed")
        ring = [(hub[0] + GREEN_RING_RADIUS * math.cos(2.0 * math.pi * k / GREEN_RING_POINTS),
                 hub[1] + GREEN_RING_RADIUS * math.sin(2.0 * math.pi * k / GREEN_RING_POINTS))
                for k in range(GREEN_RING_POINTS)]
        settlement.add_path(builder, ring, closed=True)
        settlement.add_footprint(hub, GREEN_TREE_RADIUS + 0.4)
        for index, position in enumerate(positions):
            style = HOUSE_STYLES[index % len(HOUSE_STYLES)]
            rotation = town.facing_rotation(position, hub) + rng.uniform(-0.25, 0.25)
            settlement.add_house(builder, rng, position, rotation, ROOFS[index % len(ROOFS)], style)
            door = town.house_door_point(position, rotation, style)
            angle = math.atan2(door.y - hub[1], door.x - hub[0])
            ring_end = (hub[0] + GREEN_RING_RADIUS * math.cos(angle), hub[1] + GREEN_RING_RADIUS * math.sin(angle))
            settlement.add_path(builder, town.curved_path(door, ring_end, SPOKE_BEND * rng.choice((-1, 1))))

        garden_angle = start + math.pi / HOUSE_COUNT
        garden_center = (positions[0][0] + GARDEN_DISTANCE * math.cos(garden_angle - 0.6),
                         positions[0][1] + GARDEN_DISTANCE * math.sin(garden_angle - 0.6))
        if town.fits_on_tile(garden_center, 1.8) and settlement.is_free(*garden_center, 1.0):
            garden_rotation = town.facing_rotation(garden_center, hub)
            settlement.add_garden_fence(builder, garden_center, garden_rotation, GARDEN_WIDTH, GARDEN_DEPTH)
            kit.add_round_hay_bale(builder, rng, garden_center[0], garden_center[1], height(*garden_center))
        settlement.add_trees(builder, rng, TREE_COUNT)
        settlement.add_bushes(builder, rng, BUSH_COUNT)

    return water_common.assemble_tile(spec, rng, grass.style, height, decorate)
