"""SM_Tile_ChurchTown_A: chapel facing a little square (steeple socket at its center) and three houses."""
from props import buildings
from tiles import settlement_churchtown_common as churchtown

HOUSE_ANGLES_DEG = (95.0, 180.0, 265.0)
HOUSE_STYLES = ("small", "tall", "small")
ROOFS = (buildings.RED_ROOF, buildings.NAVY_ROOF, buildings.NAVY_ROOF)


def build(spec, seed):
    """Builds Church Town A."""
    return churchtown.build_churchtown(spec, seed, churchtown.CHAPEL_FRONT, HOUSE_ANGLES_DEG, HOUSE_STYLES, ROOFS)
