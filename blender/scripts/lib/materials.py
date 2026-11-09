"""Material slots shared by every asset. Unity remaps these slots by name."""
import bpy

from . import palette

PALETTE_MATERIAL = "M_Palette_Fall"
WATER_MATERIAL = "M_Water"
GLOW_MATERIAL = "M_Glow"
ALLOWED_MATERIALS = {PALETTE_MATERIAL, WATER_MATERIAL, GLOW_MATERIAL}

PALETTE_ROUGHNESS = 0.9
SPECULAR_LEVEL = 0.15
WATER_ROUGHNESS = 0.15
GLOW_STRENGTH = 3.0


def _set_input(node, names, value):
    for name in names if isinstance(names, (list, tuple)) else [names]:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return


def get_material(name):
    """Returns the named pipeline material, creating its preview shader if needed."""
    material = bpy.data.materials.get(name)
    if material is not None:
        return material
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    _set_input(bsdf, "Roughness", PALETTE_ROUGHNESS)
    _set_input(bsdf, ["Specular IOR Level", "Specular"], SPECULAR_LEVEL)

    if name == PALETTE_MATERIAL:
        texture = nodes.new("ShaderNodeTexImage")
        texture.image = palette.load_atlas()
        texture.interpolation = "Closest"
        texture.location = (-400, 200)
        material.node_tree.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
    elif name == WATER_MATERIAL:
        _set_input(bsdf, "Base Color", (*palette.swatch_linear("LakeTeal"), 1.0))
        _set_input(bsdf, "Roughness", WATER_ROUGHNESS)
    elif name == GLOW_MATERIAL:
        _set_input(bsdf, "Base Color", (*palette.swatch_linear("HarvestGold"), 1.0))
        _set_input(bsdf, ["Emission Color", "Emission"], (*palette.swatch_linear("HarvestGold"), 1.0))
        _set_input(bsdf, "Emission Strength", GLOW_STRENGTH)
    return material


def relink_atlas_images():
    """Points every atlas image at the canonical texture path (needed after appending)."""
    for image in bpy.data.images:
        if image.name.startswith(palette.ATLAS_NAME):
            image.filepath = palette.ATLAS_PATH
            image.reload()
