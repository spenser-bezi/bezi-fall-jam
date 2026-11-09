"""Seam-test reference tiles (pipeline owner)."""
from registry import TILE_TRIANGLE_BUDGET, AssetSpec

TILES = "Environment/Tiles"

ASSETS = [
    AssetSpec("tile.base", "SM_Tile_Base", "tiles.base", TILES, "tile", TILE_TRIANGLE_BUDGET, 101),
    AssetSpec("tile.seamtest_grove", "SM_Tile_SeamTest_Grove", "tiles.seamtest_grove", TILES, "tile",
              TILE_TRIANGLE_BUDGET, 202),
    AssetSpec("tile.seamtest_field", "SM_Tile_SeamTest_Field", "tiles.seamtest_field", TILES, "tile",
              TILE_TRIANGLE_BUDGET, 303),
]

GROUPS = {
    "seam_test": ["tile.base", "tile.seamtest_grove", "tile.seamtest_field"],
}
