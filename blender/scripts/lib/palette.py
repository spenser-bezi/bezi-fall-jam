"""Fall palette: swatch definitions, UV lookup and the T_Palette_Fall atlas generator.

Atlas layout (256x256, 16x16 cells of 16 px, row 0 at the top):
- Rows 0-3: flat swatches for colors 0-15 (one column per color, one row per shade).
- Rows 4-7: flat swatches for colors 16-31.
- Rows 8-15: vertical gradient strips, one 16 px column per strip (top = t 0, bottom = t 1).
Unused cells are magenta so bad UVs are obvious in renders.
"""
import json
import os

import bpy

from . import paths

ATLAS_NAME = "T_Palette_Fall"
ATLAS_SIZE = 256
CELL_SIZE = 16
CELLS_PER_ROW = ATLAS_SIZE // CELL_SIZE
SHADES_PER_COLOR = 4
COLORS_PER_BLOCK = CELLS_PER_ROW
STRIP_FIRST_ROW = 8
STRIP_ROW_COUNT = 8
STRIP_INSET_PIXELS = 2
LIGHT_MIX = 0.22
DARK_FACTOR = 0.78
EXTRA_DARK_FACTOR = 0.58
UNUSED_COLOR = (1.0, 0.0, 1.0)

SHADE_BASE = 0
SHADE_LIGHT = 1
SHADE_DARK = 2
SHADE_EXTRA_DARK = 3

ATLAS_PATH = os.path.join(paths.TEXTURES_DIR, ATLAS_NAME + ".png")
SWATCH_MAP_PATH = os.path.join(paths.TEXTURES_DIR, ATLAS_NAME + ".json")

# GDD 12 palette first, then provisional additions (WS6 owns final values; UVs only reference cells).
COLORS = [
    ("Pumpkin", "E07A2F"),
    ("MapleRed", "B83A2A"),
    ("Mustard", "E3A936"),
    ("HarvestGold", "F2C46B"),
    ("Moss", "6E7F3A"),
    ("Pine", "2F4A3A"),
    ("LakeTeal", "5FB7B0"),
    ("ShoreFoam", "CFEDE4"),
    ("Soil", "5A4032"),
    ("CreamSky", "F4E3C3"),
    ("DuskLavender", "8A7FB5"),
    ("NightIndigo", "2B2F5A"),
    ("GooseCharcoal", "2A2A2E"),
    ("Chinstrap", "F4F1EA"),
    ("GooseTaupe", "8C7A66"),
    ("NavyRoof", "34416B"),
    ("WallCream", "EFE2C8"),
    ("Stone", "9A958C"),
    ("Wood", "8B5A3C"),
    ("DryGrass", "A8A04E"),
    ("LightMoss", "8FA046"),
    ("DeepWater", "3E8C93"),
    ("Slate", "5B6270"),
    ("Cranberry", "8E1F3A"),
    ("SkyBlue", "9CC6E0"),
    ("Cloud", "DADDE6"),
    ("StormGray", "5E6472"),
    ("Brick", "9C4A33"),
]
COLOR_INDEX = {name: index for index, (name, _) in enumerate(COLORS)}

# name, (top color, shade), (bottom color, shade)
STRIPS = [
    ("SoilSkirt", ("Soil", SHADE_BASE), ("Soil", SHADE_EXTRA_DARK)),
    ("FieldGold", ("HarvestGold", SHADE_LIGHT), ("Mustard", SHADE_DARK)),
    ("FieldGreen", ("LightMoss", SHADE_LIGHT), ("Moss", SHADE_BASE)),
    ("Plowed", ("Soil", SHADE_LIGHT), ("Soil", SHADE_DARK)),
    ("Water", ("LakeTeal", SHADE_BASE), ("DeepWater", SHADE_DARK)),
    ("Grass", ("LightMoss", SHADE_BASE), ("Moss", SHADE_DARK)),
]
STRIP_INDEX = {name: index for index, (name, _, _) in enumerate(STRIPS)}

# Repeating band patterns (Dorfromantik field rows): name, (color A, shade), (color B, shade), band count.
# Faces map planar coordinates along the strip with per-corner UVs, so rows stay crisp at any mesh density.
PATTERN_STRIPS = [
    ("FieldRows", ("HarvestGold", SHADE_LIGHT), ("Mustard", SHADE_BASE), 10),
    ("PlowedRows", ("Soil", SHADE_LIGHT), ("Soil", SHADE_BASE), 10),
    ("GreenRows", ("LightMoss", SHADE_BASE), ("Moss", SHADE_DARK), 10),
    ("CornRows", ("DryGrass", SHADE_LIGHT), ("Mustard", SHADE_DARK), 10),
]
for _pattern_index, (_pattern_name, _, _, _) in enumerate(PATTERN_STRIPS):
    STRIP_INDEX[_pattern_name] = len(STRIPS) + _pattern_index
STRIP_COLUMN_COUNT = len(STRIPS) + len(PATTERN_STRIPS)


def hex_to_srgb(hex_code):
    """Converts an RRGGBB hex string to an sRGB float triple."""
    return tuple(int(hex_code[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def shade_srgb(rgb, shade):
    """Applies one of the four atlas shades to an sRGB color."""
    if shade == SHADE_LIGHT:
        return tuple(c + (1.0 - c) * LIGHT_MIX for c in rgb)
    if shade == SHADE_DARK:
        return tuple(c * DARK_FACTOR for c in rgb)
    if shade == SHADE_EXTRA_DARK:
        return tuple(c * EXTRA_DARK_FACTOR for c in rgb)
    return tuple(rgb)


def swatch_srgb(name, shade=SHADE_BASE):
    """Returns the sRGB color of a named swatch and shade."""
    return shade_srgb(hex_to_srgb(COLORS[COLOR_INDEX[name]][1]), shade)


def srgb_to_linear(value):
    """Converts one sRGB channel to linear."""
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def swatch_linear(name, shade=SHADE_BASE):
    """Returns the linear color of a named swatch, for shader inputs."""
    return tuple(srgb_to_linear(c) for c in swatch_srgb(name, shade))


def cell_of(name, shade=SHADE_BASE):
    """Returns the (column, row-from-top) atlas cell of a flat swatch."""
    index = COLOR_INDEX[name]
    column = index % COLORS_PER_BLOCK
    row = (index // COLORS_PER_BLOCK) * SHADES_PER_COLOR + shade
    return column, row


def flat_uv(name, shade=SHADE_BASE):
    """Returns the UV at the center of a flat swatch cell."""
    column, row = cell_of(name, shade)
    half = CELL_SIZE * 0.5
    return ((column * CELL_SIZE + half) / ATLAS_SIZE, 1.0 - (row * CELL_SIZE + half) / ATLAS_SIZE)


def strip_uv(name, t):
    """Returns the UV at position t (0 top .. 1 bottom) along a gradient strip."""
    column = STRIP_INDEX[name]
    t = min(1.0, max(0.0, t))
    top = STRIP_FIRST_ROW * CELL_SIZE + STRIP_INSET_PIXELS
    height = STRIP_ROW_COUNT * CELL_SIZE - 2 * STRIP_INSET_PIXELS
    return ((column * CELL_SIZE + CELL_SIZE * 0.5) / ATLAS_SIZE, 1.0 - (top + t * height) / ATLAS_SIZE)


def classify_uv(u, v):
    """Returns the atlas region a UV falls in: ('cell', col, row), ('strip', col) or None if unused."""
    column = min(max(int(u * CELLS_PER_ROW), 0), CELLS_PER_ROW - 1)
    row = min(max(int((1.0 - v) * CELLS_PER_ROW), 0), CELLS_PER_ROW - 1)
    if row >= STRIP_FIRST_ROW:
        return ("strip", column) if column < STRIP_COLUMN_COUNT else None
    color_index = (row // SHADES_PER_COLOR) * COLORS_PER_BLOCK + column
    return ("cell", column, row) if color_index < len(COLORS) else None


def _lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def generate_atlas():
    """Writes T_Palette_Fall.png and its JSON swatch map into blender/textures."""
    import numpy as np

    paths.ensure_dir(paths.TEXTURES_DIR)
    pixels = np.ones((ATLAS_SIZE, ATLAS_SIZE, 4), dtype=np.float32)
    pixels[:, :, :3] = UNUSED_COLOR
    swatch_map = {"size": ATLAS_SIZE, "cellSize": CELL_SIZE, "flat": {}, "strips": {}}

    for name, _ in COLORS:
        for shade in range(SHADES_PER_COLOR):
            column, row = cell_of(name, shade)
            y0, x0 = row * CELL_SIZE, column * CELL_SIZE
            pixels[y0:y0 + CELL_SIZE, x0:x0 + CELL_SIZE, :3] = swatch_srgb(name, shade)
            swatch_map["flat"].setdefault(name, []).append({"column": column, "row": row})

    strip_height = STRIP_ROW_COUNT * CELL_SIZE
    for name, top, bottom in STRIPS:
        column = STRIP_INDEX[name]
        top_rgb, bottom_rgb = swatch_srgb(*top), swatch_srgb(*bottom)
        x0 = column * CELL_SIZE
        for offset in range(strip_height):
            t = offset / (strip_height - 1)
            y = STRIP_FIRST_ROW * CELL_SIZE + offset
            pixels[y, x0:x0 + CELL_SIZE, :3] = _lerp(top_rgb, bottom_rgb, t)
        swatch_map["strips"][name] = {"column": column, "top": list(top), "bottom": list(bottom)}

    usable_top = STRIP_FIRST_ROW * CELL_SIZE + STRIP_INSET_PIXELS
    usable_height = strip_height - 2 * STRIP_INSET_PIXELS
    for name, color_a, color_b, band_count in PATTERN_STRIPS:
        column = STRIP_INDEX[name]
        rgb_a, rgb_b = swatch_srgb(*color_a), swatch_srgb(*color_b)
        x0 = column * CELL_SIZE
        for offset in range(strip_height):
            t = min(max((STRIP_FIRST_ROW * CELL_SIZE + offset - usable_top) / usable_height, 0.0), 0.999)
            y = STRIP_FIRST_ROW * CELL_SIZE + offset
            pixels[y, x0:x0 + CELL_SIZE, :3] = rgb_a if int(t * band_count) % 2 == 0 else rgb_b
        swatch_map["strips"][name] = {"column": column, "pattern": [list(color_a), list(color_b)],
                                      "bands": band_count}

    image = bpy.data.images.new(ATLAS_NAME + "_Generated", ATLAS_SIZE, ATLAS_SIZE, alpha=True)
    image.pixels.foreach_set(pixels[::-1].ravel())  # Blender stores the bottom row first
    image.filepath_raw = ATLAS_PATH
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)

    with open(SWATCH_MAP_PATH, "w") as handle:
        json.dump(swatch_map, handle, indent=2)
    print(f"[bezi-art] palette atlas written: {ATLAS_PATH}")


def load_atlas():
    """Loads (generating if missing) the atlas image with closest-pixel friendly settings."""
    if not os.path.exists(ATLAS_PATH):
        generate_atlas()
    image = bpy.data.images.get(ATLAS_NAME)
    if image is None:
        image = bpy.data.images.load(ATLAS_PATH)
        image.name = ATLAS_NAME
    image.filepath = ATLAS_PATH
    image.colorspace_settings.name = "sRGB"
    return image
