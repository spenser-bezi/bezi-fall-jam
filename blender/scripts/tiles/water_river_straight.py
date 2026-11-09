"""SM_Tile_River_Straight: river socket 0 -> 3 with a gentle S-meander, footbridge, reeds and bank trees."""
import math
import random

from lib import edge_sockets, hexgrid
from props import water_props
from tiles import common, water_common
from tiles import water_river_common as river

SOCKET_SIDES = (0, 3)
CONTROL_LENGTH = 3.0
MEANDER = 1.2
BRIDGE_ARC_FRACTION = 0.5
BRIDGE_WIDTH = 1.3
BRIDGE_BANK_MARGIN = 1.4
BRIDGE_CLEARANCE = 2.0
REED_ARC_FRACTIONS = (0.22, 0.34, 0.66, 0.8)
SNACK_ARC_FRACTIONS = (0.3, 0.72)
TREE_COUNT = 5
BUSH_COUNT = 4
ROCK_COUNT = 3


def build(spec, seed):
    """Builds the straight river tile."""
    rng = random.Random(seed)
    grass = hexgrid.GrassPainter(seed)
    base_height = common.gentle_height(seed)
    centerline = river.Centerline(river.socket_to_socket_points(SOCKET_SIDES[0], SOCKET_SIDES[1], CONTROL_LENGTH,
                                                                MEANDER * rng.choice((-1.0, 1.0))))
    channel = river.RiverChannel(centerline)

    def height(x, y):
        depth = channel.ground_depth(x, y)
        return base_height(x, y) if depth is None else depth

    bridge_arc = centerline.length * BRIDGE_ARC_FRACTION
    bridge_center, bridge_left, bridge_scale = channel.cross_section(bridge_arc)

    def decorate(builder):
        channel.add_water(builder)
        span = 2.0 * edge_sockets.SOCKET_HALF_WIDTH * bridge_scale + BRIDGE_BANK_MARGIN
        water_props.add_footbridge(builder, bridge_center.x, bridge_center.y,
                                   math.atan2(bridge_left.y, bridge_left.x), span, BRIDGE_WIDTH, 0.0)
        river.add_bank_reeds(builder, rng, channel, height,
                             [centerline.length * fraction for fraction in REED_ARC_FRACTIONS])
        blockers = []
        for side in (-1.0, 1.0):
            foot = bridge_center + bridge_left * (side * span * 0.5)
            blockers.append((foot.x, foot.y))
        river.scatter_land_decor(builder, rng, height,
                                 lambda x, y, clearance: channel.bank_offset(x, y) > clearance,
                                 TREE_COUNT, BUSH_COUNT, ROCK_COUNT, blockers)

    obj = water_common.assemble_tile(spec, rng, grass.style, height, decorate, channel.snap, SOCKET_SIDES)
    snack_points = [tuple(centerline.sample(centerline.length * f).xy) for f in SNACK_ARC_FRACTIONS]
    return river.finish_river_tile(obj, SOCKET_SIDES, snack_points)


def validate(obj, spec):
    """Socket-aware validation hook."""
    return river.validate_river_tile(obj, spec, SOCKET_SIDES)


def export(obj, spec, filepath):
    """FBX export hook (keeps edge_river_mask as an FBX user property)."""
    return river.export_with_custom_props(obj, filepath)


def preview(spec, seed):
    """Contact sheet + socket-matched cluster sheet."""
    return river.river_preview(spec, seed)
