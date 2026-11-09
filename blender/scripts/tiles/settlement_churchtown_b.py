"""SM_Tile_ChurchTown_B: chapel alongside the square (steeple socket at its center) and four houses."""
from props import buildings
from tiles import settlement_churchtown_common as churchtown

HOUSE_ANGLES_DEG = (75.0, 145.0, 215.0, 285.0)
HOUSE_STYLES = ("tall", "small", "long", "small")
ROOFS = (buildings.NAVY_ROOF, buildings.RED_ROOF, buildings.NAVY_ROOF, buildings.RED_ROOF)


def build(spec, seed):
    """Builds Church Town B."""
    return churchtown.build_churchtown(spec, seed, churchtown.CHAPEL_SIDE, HOUSE_ANGLES_DEG, HOUSE_STYLES, ROOFS)
