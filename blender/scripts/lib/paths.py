"""Filesystem locations used by the art pipeline."""
import os

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART_ROOT = os.path.dirname(SCRIPTS_DIR)
SOURCE_DIR = os.path.join(ART_ROOT, "source")
RENDERS_DIR = os.path.join(ART_ROOT, "renders")
TEXTURES_DIR = os.path.join(ART_ROOT, "textures")
UNITY_ART_DIR = os.path.normpath(
    os.path.join(ART_ROOT, "..", "bezi-fall-jam-unity", "Assets", "_Project", "Art"))


def ensure_dir(path):
    """Creates the directory if needed and returns it."""
    os.makedirs(path, exist_ok=True)
    return path


def asset_render_dir(asset_id):
    """Returns (and creates) the preview/validation output folder for an asset."""
    return ensure_dir(os.path.join(RENDERS_DIR, asset_id.replace(".", "_")))
