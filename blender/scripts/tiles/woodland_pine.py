"""SM_Tile_PineForest_A/_B: dense pines (large + small) with rocks on a dark needle floor.

Large pines ring the rim so neighboring pine tiles merge; small and large pines fill the interior.
Variant B groups its rocks into a mossy outcrop and leans toward smaller pines.
"""
import math
import random

from lib import hexgrid, materials, palette
from lib.scatter import Noise2D
from props import kit
from props import trees as tree_kit
from props import woodland_props
from tiles import common
from tiles import woodland_common as woodland

HEIGHT_AMPLITUDE = 0.12
RING_INSET_RANGE = (0.9, 1.35)
RING_ALONG_JITTER = 0.2
LARGE_SCALE_RANGE = (0.88, 1.05)
SMALL_SCALE_RANGE = (0.85, 1.1)
INTERIOR_MIN_INSET = 2.3
SPACING_FACTOR = 0.82

BLOB_RADIUS = 7.4
BLOB_WOBBLE = 0.1
NEEDLE_FOOTPRINT_FACTOR = 1.05
NEEDLE_NOISE = 0.4
NEEDLE_NOISE_FREQUENCY = 0.4
FLOOR_PATCH_FREQUENCY = 0.3
SOIL_PATCH_THRESHOLD = 0.22
MOSS_PATCH_THRESHOLD = -0.3
FLOOR_SWATCH = ("Moss", palette.SHADE_EXTRA_DARK)
SOIL_PATCH_SWATCH = ("Soil", palette.SHADE_BASE)
MOSS_PATCH_SWATCH = ("Moss", palette.SHADE_DARK)
NEEDLE_SWATCHES = (("Soil", palette.SHADE_BASE), ("Soil", palette.SHADE_DARK), ("Wood", palette.SHADE_DARK),
                   ("Moss", palette.SHADE_EXTRA_DARK), ("DryGrass", palette.SHADE_DARK))

ROCK_MIN_INSET = 1.8
ROCK_TREE_CLEARANCE = 0.45
ROCK_ATTEMPTS = 800
OUTCROP_SPREAD = 1.1
PEBBLE_RADIUS_RANGE = (0.22, 0.35)
BOULDER_TRIANGLES = 24
PEBBLE_TRIANGLES = 20

VARIANTS = {
    woodland.VARIANT_A: {
        "ring_count": 14,
        "interior_large": 8,
        "interior_small": 8,
        "boulders": 3,
        "boulder_radius": (0.5, 0.8),
        "outcrop": False,
        "pebbles": 2,
    },
    woodland.VARIANT_B: {
        "ring_count": 14,
        "interior_large": 5,
        "interior_small": 11,
        "boulders": 3,
        "boulder_radius": (0.55, 0.9),
        "outcrop": True,
        "pebbles": 3,
    },
}


def _large_footprint(scale):
    return tree_kit.pine_footprint(tree_kit.PINE_LARGE, scale)


def _small_footprint(scale):
    return tree_kit.pine_footprint(tree_kit.PINE_SMALL, scale)


def build(spec, seed):
    """Builds a dense pine forest tile (variant from the mesh name suffix)."""
    variant = VARIANTS[woodland.variant_of(spec)]
    rng = random.Random(seed)
    needle_noise = Noise2D(seed + 2)
    floor_noise = Noise2D(seed + 4)
    grass = hexgrid.GrassPainter(seed)
    height = common.gentle_height(seed, amplitude=HEIGHT_AMPLITUDE)
    blob = woodland.ContentBlob(seed + 5, BLOB_RADIUS, BLOB_WOBBLE)

    outcrop = None
    if variant["outcrop"]:
        angle = rng.uniform(0.0, 2.0 * math.pi)
        outcrop = (3.0 * math.cos(angle), 3.0 * math.sin(angle))

    def away_from_outcrop(x, y):
        return outcrop is None or math.hypot(x - outcrop[0], y - outcrop[1]) > OUTCROP_SPREAD + 1.4

    ring = woodland.place_rim_ring(rng, variant["ring_count"], RING_INSET_RANGE, RING_ALONG_JITTER,
                                   LARGE_SCALE_RANGE, _large_footprint)
    for tree in ring:
        tree.kind = tree_kit.PINE_LARGE
    large = woodland.place_interior(rng, variant["interior_large"], INTERIOR_MIN_INSET, LARGE_SCALE_RANGE,
                                    _large_footprint, SPACING_FACTOR, ring, accept=away_from_outcrop)
    for tree in large:
        tree.kind = tree_kit.PINE_LARGE
    small = woodland.place_interior(rng, variant["interior_small"], INTERIOR_MIN_INSET, SMALL_SCALE_RANGE,
                                    _small_footprint, SPACING_FACTOR, ring + large, accept=away_from_outcrop)
    for tree in small:
        tree.kind = tree_kit.PINE_SMALL
    pines = ring + large + small

    def face_style(centroid, face_rng):
        x, y = centroid.x, centroid.y
        distance, tree = woodland.nearest_tree_distance(pines, x, y)
        threshold = (tree.footprint * NEEDLE_FOOTPRINT_FACTOR
                     + NEEDLE_NOISE * needle_noise.sample(x, y, NEEDLE_NOISE_FREQUENCY))
        inside = blob.contains(x, y)
        if inside:
            floor_value = floor_noise.sample(x, y, FLOOR_PATCH_FREQUENCY)
            if floor_value > SOIL_PATCH_THRESHOLD:
                return materials.PALETTE_MATERIAL, palette.flat_uv(*SOIL_PATCH_SWATCH)
            if floor_value < MOSS_PATCH_THRESHOLD:
                return materials.PALETTE_MATERIAL, palette.flat_uv(*MOSS_PATCH_SWATCH)
        if distance < threshold:
            return materials.PALETTE_MATERIAL, palette.flat_uv(*face_rng.choice(NEEDLE_SWATCHES))
        if inside:
            return materials.PALETTE_MATERIAL, palette.flat_uv(*FLOOR_SWATCH)
        return grass.style(centroid, face_rng)

    def free_spot(clearance, center=None, spread=0.0):
        for _ in range(ROCK_ATTEMPTS):
            if center is not None:
                angle, radius = rng.uniform(0.0, 2.0 * math.pi), rng.uniform(0.0, spread)
                x, y = center[0] + radius * math.cos(angle), center[1] + radius * math.sin(angle)
            else:
                extent = hexgrid.APOTHEM - ROCK_MIN_INSET
                x, y = rng.uniform(-extent, extent), rng.uniform(-extent, extent)
            if hexgrid.inset_distance(x, y) < ROCK_MIN_INSET:
                continue
            if any(math.hypot(x - tree.x, y - tree.y) < tree.footprint * ROCK_TREE_CLEARANCE + clearance
                   for tree in pines):
                continue
            return x, y
        return None

    def decorate(builder):
        for tree in pines:
            tree_kit.add_pine(builder, rng, tree.x, tree.y, height(tree.x, tree.y), tree.kind, tree.size)
        budget = spec.triangle_budget
        for _ in range(variant["boulders"]):
            radius = rng.uniform(*variant["boulder_radius"])
            spot = free_spot(radius, outcrop, OUTCROP_SPREAD) if outcrop else free_spot(radius)
            if spot and woodland.fits_budget(builder, BOULDER_TRIANGLES, budget):
                woodland_props.add_boulder(builder, rng, spot[0], spot[1], height(*spot), radius)
        for _ in range(variant["pebbles"]):
            spot = free_spot(0.3)
            if spot and woodland.fits_budget(builder, PEBBLE_TRIANGLES, budget):
                kit.add_rock(builder, rng, spot[0], spot[1], height(*spot), rng.uniform(*PEBBLE_RADIUS_RANGE))

    snap = woodland.safe_snap(rng, height, blob.snap)
    return common.assemble_tile(spec, rng, face_style, height, decorate, snap)
