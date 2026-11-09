"""SM_Tile_Base: the plain grass reference tile every other tile must seam against."""
import random

from lib import hexgrid
from tiles import common


def build(spec, seed):
    """Builds the plain base tile."""
    rng = random.Random(seed)
    grass = hexgrid.GrassPainter(seed)
    return common.assemble_tile(spec, rng, grass.style, common.gentle_height(seed))
