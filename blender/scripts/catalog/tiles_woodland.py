"""Woodland biome tiles: forest, pine forest, apple orchard and hills (A/B variants each)."""
from registry import TILE_TRIANGLE_BUDGET, AssetSpec

TILES = "Environment/Tiles"

ASSETS = [
    AssetSpec("tile.forest_a", "SM_Tile_Forest_A", "tiles.woodland_forest", TILES, "tile", TILE_TRIANGLE_BUDGET, 1101),
    AssetSpec("tile.forest_b", "SM_Tile_Forest_B", "tiles.woodland_forest", TILES, "tile", TILE_TRIANGLE_BUDGET, 1102),
    AssetSpec("tile.pineforest_a", "SM_Tile_PineForest_A", "tiles.woodland_pine", TILES, "tile",
              TILE_TRIANGLE_BUDGET, 1201),
    AssetSpec("tile.pineforest_b", "SM_Tile_PineForest_B", "tiles.woodland_pine", TILES, "tile",
              TILE_TRIANGLE_BUDGET, 1202),
    AssetSpec("tile.orchard_a", "SM_Tile_Orchard_A", "tiles.woodland_orchard", TILES, "tile",
              TILE_TRIANGLE_BUDGET, 1301),
    AssetSpec("tile.orchard_b", "SM_Tile_Orchard_B", "tiles.woodland_orchard", TILES, "tile",
              TILE_TRIANGLE_BUDGET, 1302),
    AssetSpec("tile.hills_a", "SM_Tile_Hills_A", "tiles.woodland_hills", TILES, "tile", TILE_TRIANGLE_BUDGET, 1401),
    AssetSpec("tile.hills_b", "SM_Tile_Hills_B", "tiles.woodland_hills", TILES, "tile", TILE_TRIANGLE_BUDGET, 1402),
]

GROUPS = {
    "tiles_woodland": [spec.asset_id for spec in ASSETS],
    "tiles_woodland_mix": ["tile.base", "tile.forest_a", "tile.pineforest_b", "tile.orchard_a", "tile.hills_b"],
}
