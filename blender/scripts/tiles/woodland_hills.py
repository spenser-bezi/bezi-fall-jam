"""SM_Tile_Hills_A/_B: raised grassy mounds in the interior (rim stays flat at z = 0), boulders and a few pines.

Mounds fade to zero before the outermost interior ring, so the edge band and rim are identical to every tile.
Sunny mound tops get lighter grass in snapped contour bands; the steepest flanks show a little stone scree.
"""
import math
import random

from mathutils import Vector

from lib import hexgrid, materials, palette
from lib.scatter import Noise2D
from props import kit
from props import trees as tree_kit
from props import woodland_props
from tiles import common
from tiles import woodland_common as woodland

BASE_HEIGHT_AMPLITUDE = 0.08
MOUND_FADE_START = 2.25
MOUND_FADE_END = 4.2
SLOPE_SAMPLE = 0.3
MOUND_PROFILE_EXPONENT = 0.75
ROCKY_SLOPE = 0.95
ROCKY_CHANCE = 0.5
TOP_FRACTION = 0.5
UPPER_FRACTION = 0.25
TOP_NOISE_FREQUENCY = 0.5
TOP_PATCH_THRESHOLD = 0.25
TOP_SWATCH = ("LightMoss", palette.SHADE_LIGHT)
TOP_PATCH_SWATCH = ("LightMoss", palette.SHADE_BASE)
UPPER_SWATCH = ("LightMoss", palette.SHADE_BASE)
ROCKY_SWATCH = ("Stone", palette.SHADE_DARK)

PINE_MIN_INSET = 1.2
PINE_SPACING = 2.2
PINE_MAX_BASE_Z = 0.9
PINE_SCALE_RANGE = (0.85, 1.05)
BOULDER_MIN_INSET = 1.5
BOULDER_SPACING = 1.6
BUSH_MIN_INSET = 1.3
BUSH_RADIUS_RANGE = (0.4, 0.6)
PEBBLE_RADIUS_RANGE = (0.2, 0.32)
PLACEMENT_ATTEMPTS = 2000
BOULDER_TRIANGLES = 24
PINE_TRIANGLES = 30
BUSH_TRIANGLES = 20
PEBBLE_TRIANGLES = 20

VARIANTS = {
    woodland.VARIANT_A: {
        # (distance from center, angle offset (rad), radius, peak height)
        "mounds": ((2.6, 0.0, 3.8, 2.1), (3.0, 2.6, 3.2, 1.4), (3.3, 4.4, 2.6, 0.9)),
        "pines": 8,
        "small_pine_chance": 0.4,
        "boulders": 5,
        "boulder_radius": (0.5, 0.95),
        "bushes": 4,
        "pebbles": 3,
    },
    woodland.VARIANT_B: {
        "mounds": ((0.6, 0.0, 4.4, 2.5), (3.0, 3.3, 2.4, 1.0)),
        "pines": 7,
        "small_pine_chance": 0.5,
        "boulders": 7,
        "boulder_radius": (0.45, 1.05),
        "bushes": 3,
        "pebbles": 4,
    },
}


def build(spec, seed):
    """Builds a hills tile with interior mounds (variant from the mesh name suffix)."""
    variant = VARIANTS[woodland.variant_of(spec)]
    rng = random.Random(seed)
    grass = hexgrid.GrassPainter(seed)
    top_noise = Noise2D(seed + 3)
    base_height = common.gentle_height(seed, amplitude=BASE_HEIGHT_AMPLITUDE)

    rotation = rng.uniform(0.0, 2.0 * math.pi)
    mounds = []
    for distance, angle_offset, radius, peak in variant["mounds"]:
        angle = rotation + angle_offset + rng.uniform(-0.2, 0.2)
        mounds.append((distance * math.cos(angle), distance * math.sin(angle), radius, peak))
    max_peak = max(peak for _, _, _, peak in mounds)

    def mound_height(x, y, faded=True):
        total = 0.0
        for cx, cy, radius, peak in mounds:
            distance = math.hypot(x - cx, y - cy)
            if distance < radius:
                bell = 0.5 * (1.0 + math.cos(math.pi * distance / radius))
                total = max(total, peak * bell ** MOUND_PROFILE_EXPONENT)
        return total * woodland.rim_fade(x, y, MOUND_FADE_START, MOUND_FADE_END) if faded else total

    def height(x, y):
        return base_height(x, y) + mound_height(x, y)

    def slope(x, y):
        dx = (mound_height(x + SLOPE_SAMPLE, y) - mound_height(x - SLOPE_SAMPLE, y)) / (2.0 * SLOPE_SAMPLE)
        dy = (mound_height(x, y + SLOPE_SAMPLE) - mound_height(x, y - SLOPE_SAMPLE)) / (2.0 * SLOPE_SAMPLE)
        return math.hypot(dx, dy)

    def face_style(centroid, face_rng):
        x, y = centroid.x, centroid.y
        if hexgrid.inset_distance(x, y) < MOUND_FADE_START:
            return grass.style(centroid, face_rng)
        elevation = mound_height(x, y, faded=False) / max_peak
        if slope(x, y) > ROCKY_SLOPE and face_rng.random() < ROCKY_CHANCE:
            return materials.PALETTE_MATERIAL, palette.flat_uv(*ROCKY_SWATCH)
        if elevation > TOP_FRACTION:
            if top_noise.sample(x, y, TOP_NOISE_FREQUENCY) > TOP_PATCH_THRESHOLD:
                return materials.PALETTE_MATERIAL, palette.flat_uv(*TOP_PATCH_SWATCH)
            return materials.PALETTE_MATERIAL, palette.flat_uv(*TOP_SWATCH)
        if elevation > UPPER_FRACTION:
            return materials.PALETTE_MATERIAL, palette.flat_uv(*UPPER_SWATCH)
        return grass.style(centroid, face_rng)

    occupied = []

    def free_spot(min_inset, spacing, accept=None):
        for _ in range(PLACEMENT_ATTEMPTS):
            extent = hexgrid.APOTHEM - min_inset
            x, y = rng.uniform(-extent, extent), rng.uniform(-extent, extent)
            if hexgrid.inset_distance(x, y) < min_inset:
                continue
            if accept is not None and not accept(x, y):
                continue
            if any(math.hypot(x - ox, y - oy) < spacing + other for ox, oy, other in occupied):
                continue
            return x, y
        return None

    def decorate(builder):
        budget = spec.triangle_budget
        for _ in range(variant["pines"]):
            size = tree_kit.PINE_SMALL if rng.random() < variant["small_pine_chance"] else tree_kit.PINE_LARGE
            scale = rng.uniform(*PINE_SCALE_RANGE)
            footprint = tree_kit.pine_footprint(size, scale)
            min_inset = max(PINE_MIN_INSET, footprint - hexgrid.MAX_CANOPY_OVERHANG)
            spot = free_spot(min_inset, PINE_SPACING, lambda x, y: height(x, y) < PINE_MAX_BASE_Z)
            if spot and woodland.fits_budget(builder, PINE_TRIANGLES, budget):
                tree_kit.add_pine(builder, rng, spot[0], spot[1], height(*spot), size, scale)
                occupied.append((spot[0], spot[1], footprint * 0.5))
        for _ in range(variant["boulders"]):
            radius = rng.uniform(*variant["boulder_radius"])
            spot = free_spot(BOULDER_MIN_INSET + radius, BOULDER_SPACING * 0.5 + radius)
            if spot and woodland.fits_budget(builder, BOULDER_TRIANGLES, budget):
                woodland_props.add_boulder(builder, rng, spot[0], spot[1], height(*spot) - radius * 0.1, radius)
                occupied.append((spot[0], spot[1], radius))
        for _ in range(variant["bushes"]):
            radius = rng.uniform(*BUSH_RADIUS_RANGE)
            spot = free_spot(BUSH_MIN_INSET, radius + 0.4)
            if spot and woodland.fits_budget(builder, BUSH_TRIANGLES, budget):
                woodland_props.add_low_bush(builder, rng, spot[0], spot[1], height(*spot), radius)
                occupied.append((spot[0], spot[1], radius))
        for _ in range(variant["pebbles"]):
            radius = rng.uniform(*PEBBLE_RADIUS_RANGE)
            spot = free_spot(BUSH_MIN_INSET, radius + 0.3)
            if spot and woodland.fits_budget(builder, PEBBLE_TRIANGLES, budget):
                kit.add_rock(builder, rng, spot[0], spot[1], height(*spot), radius)
                occupied.append((spot[0], spot[1], radius))

    top_contours = []
    for cx, cy, radius, peak in mounds:
        for fraction in (TOP_FRACTION, UPPER_FRACTION):
            bell = (fraction * max_peak / peak) ** (1.0 / MOUND_PROFILE_EXPONENT)
            cosine = 2.0 * bell - 1.0
            if -1.0 < cosine < 1.0:
                top_contours.append((Vector((cx, cy, 0.0)), radius * math.acos(cosine) / math.pi))

    def snap_with_threshold(position, threshold):
        for center, contour_radius in top_contours:
            hexgrid.snap_to_polar_contour(position, center, lambda angle, r=contour_radius: r, threshold)
        return position

    snap = woodland.safe_snap(rng, height, snap_with_threshold)
    return common.assemble_tile(spec, rng, face_style, height, decorate, snap)
