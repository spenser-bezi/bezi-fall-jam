"""Water and settlement tiles: lakes, connected river sockets, villages, church towns, Goosebay Lodge, marsh."""
from registry import TILE_TRIANGLE_BUDGET, AssetSpec

TILES = "Environment/Tiles"


def _tile(asset_id, mesh_name, module, seed):
    return AssetSpec(asset_id, mesh_name, module, TILES, "tile", TILE_TRIANGLE_BUDGET, seed)


ASSETS = [
    _tile("tile.lake_a", "SM_Tile_Lake_A", "tiles.water_lake_a", 3001),
    _tile("tile.lake_b", "SM_Tile_Lake_B", "tiles.water_lake_b", 3002),
    _tile("tile.village_a", "SM_Tile_Village_A", "tiles.settlement_village_a", 3101),
    _tile("tile.village_b", "SM_Tile_Village_B", "tiles.settlement_village_b", 3102),
    _tile("tile.churchtown_a", "SM_Tile_ChurchTown_A", "tiles.settlement_churchtown_a", 3201),
    _tile("tile.churchtown_b", "SM_Tile_ChurchTown_B", "tiles.settlement_churchtown_b", 3202),
    _tile("tile.goosebay_lodge", "SM_Tile_GoosebayLodge", "tiles.settlement_goosebay_lodge", 3301),
    _tile("tile.river_straight", "SM_Tile_River_Straight", "tiles.water_river_straight", 3401),
    _tile("tile.river_bend", "SM_Tile_River_Bend", "tiles.water_river_bend", 3402),
    _tile("tile.river_source", "SM_Tile_River_Source", "tiles.water_river_source", 3403),
    _tile("tile.marsh_a", "SM_Tile_Marsh_A", "tiles.water_marsh_a", 3501),
]

GROUPS = {
    "tiles_water_settlement": [spec.asset_id for spec in ASSETS],
    "tiles_lakes": ["tile.lake_a", "tile.lake_b", "tile.marsh_a"],
    "tiles_rivers": ["tile.river_straight", "tile.river_bend", "tile.river_source"],
    "tiles_settlements": ["tile.village_a", "tile.village_b", "tile.churchtown_a", "tile.churchtown_b",
                          "tile.goosebay_lodge"],
}
