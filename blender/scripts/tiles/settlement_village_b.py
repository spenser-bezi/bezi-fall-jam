"""SM_Tile_Village_B: five cottages along a short internal S-lane (the lane ends at houses, never at the rim)."""
import math
import random

from mathutils import Vector

from lib import hexgrid
from props import buildings, kit
from tiles import settlement_common as town
from tiles import water_common

LANE_HALF_LENGTH = 3.6
LANE_BEND = 0.6
LANE_SAMPLES = 9
END_HOUSE_GAP = 1.7
HOUSE_OVERLAP_RADIUS = 1.45
SIDE_HOUSES = ((0.25, 1.0, "small", buildings.NAVY_ROOF), (0.5, -1.0, "tall", buildings.RED_ROOF),
               (0.75, 1.0, "small", buildings.RED_ROOF))
END_HOUSES = (("long", buildings.RED_ROOF), ("tall", buildings.NAVY_ROOF))
SIDE_HOUSE_LATERAL = 2.8
GARDEN_CANDIDATES = ((0.5, 1.0), (0.2, -1.0), (0.8, -1.0))
GARDEN_LATERAL = 3.0
GARDEN_WIDTH = 2.2
GARDEN_DEPTH = 1.6
GARDEN_RADIUS = 1.4
LANE_FENCES = (((0.06, 0.16, 0.26), -1.0), ((0.74, 0.84, 0.94), -1.0))
LANE_FENCE_LATERAL = 1.3
TREE_COUNT = 4
BUSH_COUNT = 5


def build(spec, seed):
    """Builds the lane village tile."""
    rng = random.Random(seed)
    grass = hexgrid.GrassPainter(seed)
    height = town.settlement_height(seed)
    axis_angle = rng.uniform(0.0, math.pi)
    axis = Vector((math.cos(axis_angle), math.sin(axis_angle), 0.0))
    lateral = Vector((-axis.y, axis.x, 0.0))
    bend = LANE_BEND * rng.choice((-1.0, 1.0))
    lane = []
    for k in range(LANE_SAMPLES):
        u = k / (LANE_SAMPLES - 1)
        point = axis * (LANE_HALF_LENGTH * (2.0 * u - 1.0)) + lateral * (bend * math.sin(2.0 * math.pi * u))
        lane.append(point)

    def lane_frame(fraction):
        index = min(LANE_SAMPLES - 2, int(fraction * (LANE_SAMPLES - 1)))
        u = fraction * (LANE_SAMPLES - 1) - index
        point = lane[index].lerp(lane[index + 1], u)
        forward = (lane[index + 1] - lane[index]).normalized()
        return point, Vector((-forward.y, forward.x, 0.0))

    def decorate(builder):
        settlement = town.Settlement(height)
        settlement.add_path(builder, [tuple(p.xy) for p in lane], half_width=town.PATH_HALF_WIDTH * 1.15)
        for end_index, (style, roof) in enumerate(END_HOUSES):
            end = lane[0] if end_index == 0 else lane[-1]
            outward = -axis if end_index == 0 else axis
            position = tuple((end + outward * END_HOUSE_GAP).xy)
            settlement.add_house(builder, rng, position, town.facing_rotation(position, end), roof, style)
        for fraction, side, style, roof in SIDE_HOUSES:
            point, left = lane_frame(fraction)
            position = tuple((point + left * (side * SIDE_HOUSE_LATERAL)).xy)
            if settlement.overlaps(position, HOUSE_OVERLAP_RADIUS):
                continue
            rotation = town.facing_rotation(position, point) + rng.uniform(-0.15, 0.15)
            settlement.add_house(builder, rng, position, rotation, roof, style)
            door = town.house_door_point(position, rotation, style)
            settlement.add_path(builder, [tuple(door.xy), tuple(point.xy)], half_width=town.PATH_HALF_WIDTH * 0.8)

        for fraction, side in GARDEN_CANDIDATES:
            point, left = lane_frame(fraction)
            garden = tuple((point + left * (side * GARDEN_LATERAL)).xy)
            if town.fits_on_tile(garden, GARDEN_RADIUS) and not settlement.overlaps(garden, GARDEN_RADIUS):
                settlement.add_garden_fence(builder, garden, town.facing_rotation(garden, point), GARDEN_WIDTH,
                                            GARDEN_DEPTH)
                kit.add_round_hay_bale(builder, rng, garden[0], garden[1], height(*garden))
                break
        for fractions, side in LANE_FENCES:
            posts = []
            for fraction in fractions:
                point, left = lane_frame(fraction)
                posts.append(tuple((point + left * (side * LANE_FENCE_LATERAL)).xy))
            buildings.add_fence(builder, posts, height)
            for post in posts:
                settlement.add_footprint(post, 0.6)
        settlement.add_trees(builder, rng, TREE_COUNT)
        settlement.add_bushes(builder, rng, BUSH_COUNT)

    return water_common.assemble_tile(spec, rng, grass.style, height, decorate)
