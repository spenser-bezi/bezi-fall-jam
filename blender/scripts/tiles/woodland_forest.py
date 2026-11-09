"""SM_Tile_Forest_A/_B: dense mixed autumn deciduous forest on a leaf-litter floor.

A ring of broad trees just inside the rim overhangs the seam so a same-type cluster reads as one canopy;
interior trees fill the middle. Variant B opens a small clearing with a fallen log and a stump.
"""
import math
import random

from lib import hexgrid, materials, palette
from lib.scatter import Noise2D
from props import trees as tree_kit
from props import woodland_props
from tiles import common
from tiles import woodland_common as woodland

RING_INSET_RANGE = (1.15, 1.6)
RING_ALONG_JITTER = 0.18
ROUND_SIZE_RANGE = (1.55, 1.95)
INTERIOR_MIN_INSET = 3.4
INTERIOR_SPACING_FACTOR = 0.8
LUMPY_SIZE_FACTOR = 0.85
TALL_SIZE_RANGE = (0.95, 1.15)
HEIGHT_AMPLITUDE = 0.1

BLOB_RADIUS = 7.2
BLOB_WOBBLE = 0.1
LITTER_FOOTPRINT_FACTOR = 0.8
LITTER_NOISE = 0.45
LITTER_NOISE_FREQUENCY = 0.35
FLOOR_PATCH_FREQUENCY = 0.28
FLOOR_PATCH_THRESHOLD = 0.18
FLOOR_DRIFT_THRESHOLD = -0.3

CLEARING_DISTANCE = 2.8
CLEARING_RADIUS = 2.7
BUSH_RADIUS_RANGE = (0.4, 0.6)
ROCK_RADIUS_RANGE = (0.35, 0.55)
EXTRA_MIN_INSET = 1.6
EXTRA_TREE_CLEARANCE = 0.55
EXTRA_ATTEMPTS = 600
BUSH_TRIANGLES = 20
ROCK_TRIANGLES = 24
STUMP_TRIANGLES = 16
LOG_TRIANGLES = 16

FLOOR_SWATCH = ("Moss", palette.SHADE_DARK)
FLOOR_PATCH_SWATCH = ("DryGrass", palette.SHADE_DARK)

VARIANTS = {
    woodland.VARIANT_A: {
        "ring_count": 12,
        "interior_count": 6,
        "colors": ("MapleRed", "Mustard", "Pumpkin", "MapleRed", "HarvestGold", "Pumpkin"),
        "lumpy_chance": 0.22,
        "tall_chance": 0.18,
        "clearing": False,
        "bushes": 3,
        "rocks": 2,
        "stumps": 1,
        "litter": (("Mustard", palette.SHADE_DARK), ("Mustard", palette.SHADE_BASE),
                   ("MapleRed", palette.SHADE_DARK), ("Pumpkin", palette.SHADE_DARK),
                   ("DryGrass", palette.SHADE_DARK)),
    },
    woodland.VARIANT_B: {
        "ring_count": 12,
        "interior_count": 5,
        "colors": ("Pumpkin", "Mustard", "MapleRed", "HarvestGold", "Brick", "Mustard"),
        "lumpy_chance": 0.25,
        "tall_chance": 0.22,
        "clearing": True,
        "bushes": 3,
        "rocks": 1,
        "stumps": 1,
        "litter": (("Pumpkin", palette.SHADE_DARK), ("Mustard", palette.SHADE_DARK),
                   ("HarvestGold", palette.SHADE_DARK), ("Brick", palette.SHADE_BASE),
                   ("DryGrass", palette.SHADE_BASE)),
    },
}


def _round_footprint(size):
    return tree_kit.deciduous_footprint(tree_kit.KIND_ROUND, size)


def _assign_kinds(rng, trees, variant):
    """Gives each planned tree a kind and color; lumpy and tall trees get sizes that fit their footprint."""
    colors = variant["colors"]
    for index, tree in enumerate(trees):
        roll = rng.random()
        inset = hexgrid.inset_distance(tree.x, tree.y)
        if roll < variant["lumpy_chance"]:
            tree.kind = tree_kit.KIND_LUMPY
            tree.size = woodland.max_size_for_inset(
                inset, lambda size: tree_kit.deciduous_footprint(tree_kit.KIND_LUMPY, size),
                tree.size * LUMPY_SIZE_FACTOR)
        elif roll < variant["lumpy_chance"] + variant["tall_chance"]:
            tree.kind = tree_kit.KIND_TALL
            tree.size = rng.uniform(*TALL_SIZE_RANGE)
        else:
            tree.kind = tree_kit.KIND_ROUND
        tree.footprint = tree_kit.deciduous_footprint(tree.kind, tree.size)
        tree.color = colors[(index + rng.randrange(len(colors))) % len(colors)]


def build(spec, seed):
    """Builds a dense autumn forest tile (variant from the mesh name suffix)."""
    variant = VARIANTS[woodland.variant_of(spec)]
    rng = random.Random(seed)
    litter_noise = Noise2D(seed + 2)
    floor_noise = Noise2D(seed + 4)
    grass = hexgrid.GrassPainter(seed)
    height = common.gentle_height(seed, amplitude=HEIGHT_AMPLITUDE)
    blob = woodland.ContentBlob(seed + 5, BLOB_RADIUS, BLOB_WOBBLE)

    clearing = None
    if variant["clearing"]:
        angle = rng.uniform(0.0, 2.0 * math.pi)
        clearing = (CLEARING_DISTANCE * math.cos(angle), CLEARING_DISTANCE * math.sin(angle))

    def outside_clearing(x, y):
        return clearing is None or math.hypot(x - clearing[0], y - clearing[1]) > CLEARING_RADIUS

    trees = woodland.place_rim_ring(rng, variant["ring_count"], RING_INSET_RANGE, RING_ALONG_JITTER,
                                    ROUND_SIZE_RANGE, _round_footprint)
    trees = [tree for tree in trees if outside_clearing(tree.x, tree.y)]
    trees += woodland.place_interior(rng, variant["interior_count"], INTERIOR_MIN_INSET, ROUND_SIZE_RANGE,
                                     _round_footprint, INTERIOR_SPACING_FACTOR, trees, accept=outside_clearing)
    _assign_kinds(rng, trees, variant)

    def face_style(centroid, face_rng):
        x, y = centroid.x, centroid.y
        distance, tree = woodland.nearest_tree_distance(trees, x, y)
        threshold = (tree.footprint * LITTER_FOOTPRINT_FACTOR
                     + LITTER_NOISE * litter_noise.sample(x, y, LITTER_NOISE_FREQUENCY))
        if distance < threshold:
            return materials.PALETTE_MATERIAL, palette.flat_uv(*face_rng.choice(variant["litter"]))
        if blob.contains(x, y) and outside_clearing(x, y):
            floor_value = floor_noise.sample(x, y, FLOOR_PATCH_FREQUENCY)
            if floor_value > FLOOR_PATCH_THRESHOLD:
                return materials.PALETTE_MATERIAL, palette.flat_uv(*FLOOR_PATCH_SWATCH)
            if floor_value < FLOOR_DRIFT_THRESHOLD:
                return materials.PALETTE_MATERIAL, palette.flat_uv(*variant["litter"][0])
            return materials.PALETTE_MATERIAL, palette.flat_uv(*FLOOR_SWATCH)
        return grass.style(centroid, face_rng)

    def free_spot(min_inset, clearance, inside_clearing=False):
        for _ in range(EXTRA_ATTEMPTS):
            if inside_clearing and clearing is not None:
                angle, radius = rng.uniform(0.0, 2.0 * math.pi), rng.uniform(0.0, CLEARING_RADIUS * 0.6)
                x, y = clearing[0] + radius * math.cos(angle), clearing[1] + radius * math.sin(angle)
            else:
                extent = hexgrid.APOTHEM - min_inset
                x, y = rng.uniform(-extent, extent), rng.uniform(-extent, extent)
            if hexgrid.inset_distance(x, y) < min_inset:
                continue
            if any(math.hypot(x - tree.x, y - tree.y) < tree.footprint * EXTRA_TREE_CLEARANCE + clearance
                   for tree in trees):
                continue
            return x, y
        return None

    def decorate(builder):
        for tree in trees:
            tree_kit.add_deciduous(builder, rng, tree.x, tree.y, height(tree.x, tree.y), tree.size, tree.color,
                                   tree.kind)
        budget = spec.triangle_budget
        if clearing is not None:
            spot = free_spot(EXTRA_MIN_INSET, 0.6, inside_clearing=True)
            if spot and woodland.fits_budget(builder, LOG_TRIANGLES, budget):
                woodland_props.add_log(builder, rng, spot[0], spot[1], height(*spot))
        for _ in range(variant["stumps"]):
            spot = free_spot(EXTRA_MIN_INSET, 0.4, inside_clearing=clearing is not None)
            if spot and woodland.fits_budget(builder, STUMP_TRIANGLES, budget):
                woodland_props.add_stump(builder, rng, spot[0], spot[1], height(*spot))
        for _ in range(variant["rocks"]):
            spot = free_spot(EXTRA_MIN_INSET, 0.5)
            if spot and woodland.fits_budget(builder, ROCK_TRIANGLES, budget):
                woodland_props.add_boulder(builder, rng, spot[0], spot[1], height(*spot),
                                           rng.uniform(*ROCK_RADIUS_RANGE))
        for _ in range(variant["bushes"]):
            spot = free_spot(EXTRA_MIN_INSET, 0.5)
            if spot and woodland.fits_budget(builder, BUSH_TRIANGLES, budget):
                woodland_props.add_low_bush(builder, rng, spot[0], spot[1], height(*spot),
                                            rng.uniform(*BUSH_RADIUS_RANGE))

    snap = woodland.safe_snap(rng, height, blob.snap)
    return common.assemble_tile(spec, rng, face_style, height, decorate, snap)
