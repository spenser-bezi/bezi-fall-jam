"""Asset registry: discovers asset specs from every module in scripts/catalog/.

Each catalog module (one per owner/workstream) defines:
    ASSETS = [AssetSpec(...), ...]
    GROUPS = {"group_name": ["asset.id", ...]}   # optional
Catalog modules import AssetSpec and the budget constants from this module.
"""
import importlib
import os
import pkgutil
from dataclasses import dataclass

from lib import paths

TILE_TRIANGLE_BUDGET = 1500
PROP_TRIANGLE_BUDGET = 600
OBSTACLE_TRIANGLE_BUDGET = 2000
CHARACTER_TRIANGLE_BUDGET = 1500
CATALOG_PACKAGE = "catalog"


@dataclass(frozen=True)
class AssetSpec:
    """Static description of one pipeline asset.

    kind: "tile" enables the hex tile checks and cluster renders; anything else gets generic checks.
    animated: export actions as FBX takes.
    """
    asset_id: str
    mesh_name: str
    module: str
    category: str
    kind: str
    triangle_budget: int
    seed: int
    animated: bool = False

    @property
    def blend_path(self):
        """Generated .blend source file."""
        return os.path.join(paths.SOURCE_DIR, self.category, self.mesh_name + ".blend")

    @property
    def staging_fbx_path(self):
        """FBX written next to the previews when Unity is not the export target."""
        return os.path.join(paths.asset_render_dir(self.asset_id), self.mesh_name + ".fbx")

    @property
    def unity_fbx_path(self):
        """FBX path inside the Unity project's owned art folder."""
        return os.path.join(paths.UNITY_ART_DIR, self.category, self.mesh_name + ".fbx")


def _load_catalog():
    assets, groups = {}, {}
    package_dir = os.path.join(paths.SCRIPTS_DIR, CATALOG_PACKAGE)
    for module_info in sorted(pkgutil.iter_modules([package_dir]), key=lambda m: m.name):
        module = importlib.import_module(f"{CATALOG_PACKAGE}.{module_info.name}")
        for spec in getattr(module, "ASSETS", []):
            if spec.asset_id in assets:
                raise ValueError(f"duplicate asset id {spec.asset_id} in catalog/{module_info.name}.py")
            assets[spec.asset_id] = spec
        for name, members in getattr(module, "GROUPS", {}).items():
            if name in groups:
                raise ValueError(f"duplicate group {name} in catalog/{module_info.name}.py")
            groups[name] = list(members)
    return assets, groups


ASSETS, GROUPS = _load_catalog()


def resolve(target):
    """Resolves an asset id or 'group:<name>' into a list of specs."""
    if target.startswith("group:"):
        return [ASSETS[asset_id] for asset_id in GROUPS[target.split(":", 1)[1]]]
    return [ASSETS[target]]
