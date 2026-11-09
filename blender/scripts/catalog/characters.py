"""Character assets (WS4 owner)."""
from registry import CHARACTER_TRIANGLE_BUDGET, AssetSpec

GOOSE_CATEGORY = "Characters/Goose"
GOOSE_SEED = 5001

ASSETS = [
    AssetSpec("character.goose", "SK_Goose", "characters.goose", GOOSE_CATEGORY, "character",
              CHARACTER_TRIANGLE_BUDGET, GOOSE_SEED, animated=True),
]

GROUPS = {
    "characters": ["character.goose"],
}
