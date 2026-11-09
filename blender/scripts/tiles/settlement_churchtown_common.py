"""Church Town layout: a paved square (steeple obstacle socket at its center), a steeple-less chapel and houses."""
import math
import random

from mathutils import Vector

from lib import hexgrid
from props import buildings
from tiles import settlement_common as town
from tiles import water_common

SQUARE_RADIUS = 1.9
SQUARE_OFFSET = 1.8
SQUARE_LIFT = 0.05
SQUARE_SIDES = 10
CHAPEL_GAP = 0.45
HOUSE_RING_RADIUS = 4.9
HOUSE_MIN_RING_RADIUS = 3.6
HOUSE_RING_STEP = 0.2
PATH_END_INSET = 0.3
TREE_COUNT = 3
BUSH_COUNT = 4
CHAPEL_FRONT = "front"
CHAPEL_SIDE = "side"


def build_churchtown(spec, seed, chapel_mode, house_angles_deg, house_styles, roofs):
    """Builds a church-town tile.

    chapel_mode: CHAPEL_FRONT (door gable faces the square) or CHAPEL_SIDE (long wall along the square).
    house_angles_deg: house directions around the square, relative to the chapel direction.
    """
    rng = random.Random(seed)
    grass = hexgrid.GrassPainter(seed)
    base_height = town.settlement_height(seed)
    chapel_angle = rng.uniform(0.0, 2.0 * math.pi)
    chapel_dir = Vector((math.cos(chapel_angle), math.sin(chapel_angle), 0.0))
    square = -chapel_dir * SQUARE_OFFSET

    def height(x, y):
        distance = math.hypot(x - square.x, y - square.y)
        blend = min(1.0, max(0.0, (distance - SQUARE_RADIUS) / SQUARE_RADIUS))
        return base_height(x, y) * blend

    def decorate(builder):
        settlement = town.Settlement(height)
        buildings.add_paving(builder, rng, square.x, square.y, SQUARE_RADIUS, height, SQUARE_LIFT, SQUARE_SIDES)
        settlement.add_footprint(tuple(square.xy), SQUARE_RADIUS)

        tangent = Vector((-chapel_dir.y, chapel_dir.x, 0.0))
        if chapel_mode == CHAPEL_FRONT:
            distance = SQUARE_RADIUS + CHAPEL_GAP + buildings.CHAPEL_LENGTH * 0.5
            chapel = square + chapel_dir * distance
            rotation = chapel_angle + math.pi
            square_edge = square + chapel_dir * (SQUARE_RADIUS - PATH_END_INSET)
            chapel_door = chapel - chapel_dir * (buildings.CHAPEL_LENGTH * 0.5 + 0.3)
        else:
            distance = SQUARE_RADIUS + CHAPEL_GAP + buildings.CHAPEL_WIDTH * 0.5 + buildings.ROOF_OVERHANG
            chapel = square + chapel_dir * distance
            rotation = chapel_angle + math.pi * 0.5
            chapel_door = chapel + tangent * (buildings.CHAPEL_LENGTH * 0.5 + 0.4)
            square_edge = square + tangent * (SQUARE_RADIUS - PATH_END_INSET)
        radius = buildings.add_chapel(builder, rng, chapel.x, chapel.y, height(chapel.x, chapel.y), rotation)
        settlement.add_footprint(tuple(chapel.xy), radius * 0.75)
        settlement.add_path(builder, town.curved_path(chapel_door, square_edge, 0.3))

        for index, angle_deg in enumerate(house_angles_deg):
            angle = chapel_angle + math.radians(angle_deg) + rng.uniform(-0.12, 0.12)
            style = house_styles[index % len(house_styles)]
            ring = HOUSE_RING_RADIUS
            while True:
                position = (square.x + ring * math.cos(angle), square.y + ring * math.sin(angle))
                if town.fits_on_tile(position, 2.3) or ring <= HOUSE_MIN_RING_RADIUS:
                    break
                ring -= HOUSE_RING_STEP
            rotation = town.facing_rotation(position, square) + rng.uniform(-0.2, 0.2)
            settlement.add_house(builder, rng, position, rotation, roofs[index % len(roofs)], style)
            house_door = town.house_door_point(position, rotation, style)
            towards = (town.planar(house_door) - square).normalized()
            settlement.add_path(builder, town.curved_path(house_door, square + towards * (SQUARE_RADIUS - PATH_END_INSET),
                                                          0.25 * rng.choice((-1, 1))))
        settlement.add_trees(builder, rng, TREE_COUNT)
        settlement.add_bushes(builder, rng, BUSH_COUNT)

    obj = water_common.assemble_tile(spec, rng, grass.style, height, decorate)
    town.add_steeple_socket(obj, tuple(square.xy), height)
    return obj
