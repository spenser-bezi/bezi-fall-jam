"""SM_Tile_River_Bend: river socket 0 -> 2 sweeping around side 1, with reeds, rocks and bank trees."""
import random

from lib import edge_sockets, hexgrid
from props import water_props
from tiles import common, water_common
from tiles import water_river_common as river

SOCKET_SIDES = (0, 2)
CONTROL_LENGTH = 4.2
REED_ARC_FRACTIONS = (0.2, 0.45, 0.62, 0.82)
LILY_ARC_FRACTION = 0.5
LILY_PADS = 3
LILY_LATERAL = 0.55
SNACK_ARC_FRACTIONS = (0.32, 0.7)
TREE_COUNT = 5
BUSH_COUNT = 4
ROCK_COUNT = 4


def build(spec, seed):
    """Builds the bend river tile."""
    rng = random.Random(seed)
    grass = hexgrid.GrassPainter(seed)
    base_height = common.gentle_height(seed)
    centerline = river.Centerline(river.socket_to_socket_points(SOCKET_SIDES[0], SOCKET_SIDES[1], CONTROL_LENGTH))
    channel = river.RiverChannel(centerline)

    def height(x, y):
        depth = channel.ground_depth(x, y)
        return base_height(x, y) if depth is None else depth

    def decorate(builder):
        channel.add_water(builder)
        river.add_bank_reeds(builder, rng, channel, height,
                             [centerline.length * fraction for fraction in REED_ARC_FRACTIONS])
        center, left, scale = channel.cross_section(centerline.length * LILY_ARC_FRACTION)
        lily = center - left * (LILY_LATERAL * scale)
        water_props.add_lily_pads(builder, rng, lily.x, lily.y, edge_sockets.WATER_LEVEL, LILY_PADS)
        river.scatter_land_decor(builder, rng, height,
                                 lambda x, y, clearance: channel.bank_offset(x, y) > clearance,
                                 TREE_COUNT, BUSH_COUNT, ROCK_COUNT)

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
