"""Farmland biome tiles: cornfield, pumpkin patch, farm and wind farm (A/B variants each)."""
from registry import TILE_TRIANGLE_BUDGET, AssetSpec

TILES = "Environment/Tiles"

ASSETS = [
    AssetSpec("tile.cornfield_a", "SM_Tile_Cornfield_A", "tiles.farm_cornfield", TILES, "tile",
              TILE_TRIANGLE_BUDGET, 2101),
    AssetSpec("tile.cornfield_b", "SM_Tile_Cornfield_B", "tiles.farm_cornfield", TILES, "tile",
              TILE_TRIANGLE_BUDGET, 2102),
    AssetSpec("tile.pumpkinpatch_a", "SM_Tile_PumpkinPatch_A", "tiles.farm_pumpkinpatch", TILES, "tile",
              TILE_TRIANGLE_BUDGET, 2201),
    AssetSpec("tile.pumpkinpatch_b", "SM_Tile_PumpkinPatch_B", "tiles.farm_pumpkinpatch", TILES, "tile",
              TILE_TRIANGLE_BUDGET, 2202),
    AssetSpec("tile.farm_a", "SM_Tile_Farm_A", "tiles.farm_farmstead", TILES, "tile", TILE_TRIANGLE_BUDGET, 2301),
    AssetSpec("tile.farm_b", "SM_Tile_Farm_B", "tiles.farm_farmstead", TILES, "tile", TILE_TRIANGLE_BUDGET, 2302),
    AssetSpec("tile.windfarm_a", "SM_Tile_WindFarm_A", "tiles.farm_windfarm", TILES, "tile",
              TILE_TRIANGLE_BUDGET, 2401, animated=True),
    AssetSpec("tile.windfarm_b", "SM_Tile_WindFarm_B", "tiles.farm_windfarm", TILES, "tile",
              TILE_TRIANGLE_BUDGET, 2402, animated=True),
]

GROUPS = {
    "tiles_farmland": [spec.asset_id for spec in ASSETS],
    "tiles_farmland_mix": ["tile.base", "tile.cornfield_a", "tile.pumpkinpatch_b", "tile.farm_a", "tile.windfarm_b"],
}
