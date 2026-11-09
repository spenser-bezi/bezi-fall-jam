"""SM_Tile_Orchard_A/_B: apple trees in loose rows over mowed grass stripes, fallen apples and a fence bit.

Rows run parallel to a hex side (Blender X), so every 60 degree rotation lines them up with another side and
neighbors at any rotation still look planted on purpose. Rows stay inside an organic blob with a grass rim.
Exports SOCKET_Snack_Apple_01..03 empties just above three well-spread tree crowns.
"""
import math
import random

from mathutils import Vector

from lib import hexgrid, materials, palette
from props import kit
from props import trees as tree_kit
from props import woodland_props
from tiles import common
from tiles import woodland_common as woodland

HEIGHT_AMPLITUDE = 0.06
BLOB_RADIUS = 7.0
BLOB_WOBBLE = 0.08
ROW_NORMAL = Vector((0.0, 1.0, 0.0))
ROW_DIRECTION = Vector((1.0, 0.0, 0.0))
STRIP_NAME = "GreenRows"
STRIP_BANDS = 10
TREE_ROW_BAND_OFFSET = 1.5
ROW_POSITION_JITTER = 0.22
ALONG_POSITION_JITTER = 0.3
ROW_MIN_INSET = 1.5
CANOPY_RADIUS_RANGE = (1.15, 1.35)
FRUIT_COUNT = 5
FALLEN_APPLE_DISTANCE = (0.7, 1.6)
FALLEN_APPLE_MIN_INSET = 1.3
FALLEN_APPLE_TRIANGLES = 8
FENCE_SPANS = 2
FENCE_OUTSIDE_OFFSET = 0.7
FENCE_MIN_INSET = 1.4
FENCE_TREE_CLEARANCE = 1.6
FENCE_ATTEMPTS = 200
FENCE_TRIANGLES = 80
HAY_TRIANGLES = 28
HAY_MIN_INSET = 1.8
HAY_TREE_CLEARANCE = 1.5
SOCKET_COUNT = 3
SOCKET_HOVER = 0.4
SOCKET_NAME = "SOCKET_Snack_Apple_{:02d}"

VARIANTS = {
    woodland.VARIANT_A: {
        "row_spacing": 3.5,
        "row_offset_fraction": 0.0,
        "tree_spacing": 3.3,
        "skip_chance": 0.1,
        "fallen_apples": 6,
        "hay_bales": 0,
    },
    woodland.VARIANT_B: {
        "row_spacing": 3.3,
        "row_offset_fraction": 0.25,
        "tree_spacing": 3.1,
        "skip_chance": 0.16,
        "fallen_apples": 5,
        "hay_bales": 1,
    },
}


def _pick_spread(points, count):
    """Greedy farthest-point pick so sockets are spread across the tile."""
    if not points:
        return []
    chosen = [min(points, key=lambda p: p[0] ** 2 + p[1] ** 2)]
    while len(chosen) < min(count, len(points)):
        chosen.append(max((p for p in points if p not in chosen),
                          key=lambda p: min(math.hypot(p[0] - c[0], p[1] - c[1]) for c in chosen)))
    return chosen


def build(spec, seed):
    """Builds an apple orchard tile (variant from the mesh name suffix) with snack sockets."""
    variant = VARIANTS[woodland.variant_of(spec)]
    rng = random.Random(seed)
    grass = hexgrid.GrassPainter(seed)
    height = common.gentle_height(seed, amplitude=HEIGHT_AMPLITUDE)
    blob = woodland.ContentBlob(seed + 5, BLOB_RADIUS, BLOB_WOBBLE)

    row_spacing = variant["row_spacing"]
    band_width = row_spacing * 0.5
    row_offset = variant["row_offset_fraction"] * row_spacing
    stripe_span = band_width * STRIP_BANDS
    stripe_origin = row_offset - TREE_ROW_BAND_OFFSET * band_width - 2.0 * row_spacing

    def row_uv(position):
        return palette.strip_uv(STRIP_NAME, (position.dot(ROW_NORMAL) - stripe_origin) / stripe_span)

    def snap_with_threshold(position, threshold):
        # Stripes use planar per-corner UVs, so they stay crisp without snapping; only the outline snaps.
        return blob.snap(position, threshold)

    trees = []
    along_phase = rng.uniform(0.0, variant["tree_spacing"])
    row_count = int(hexgrid.APOTHEM * 2.0 / row_spacing) + 2
    for row in range(-row_count, row_count + 1):
        row_y = row_offset + row * row_spacing
        if abs(row_y) > BLOB_RADIUS:
            continue
        steps = int(hexgrid.TILE_RADIUS * 2.0 / variant["tree_spacing"]) + 2
        for step in range(-steps, steps + 1):
            if rng.random() < variant["skip_chance"]:
                continue
            x = along_phase + step * variant["tree_spacing"] + rng.uniform(-ALONG_POSITION_JITTER,
                                                                             ALONG_POSITION_JITTER)
            y = row_y + rng.uniform(-ROW_POSITION_JITTER, ROW_POSITION_JITTER)
            inset = hexgrid.inset_distance(x, y)
            if not blob.contains(x, y) or inset < ROW_MIN_INSET:
                continue
            radius = woodland.max_size_for_inset(inset, tree_kit.apple_tree_footprint,
                                                 rng.uniform(*CANOPY_RADIUS_RANGE))
            trees.append(woodland.PlacedTree(x, y, radius, tree_kit.apple_tree_footprint(radius)))

    def face_style(centroid, face_rng):
        if blob.contains(centroid.x, centroid.y):
            return materials.PALETTE_MATERIAL, row_uv
        return grass.style(centroid, face_rng)

    def clear_of_trees(x, y, clearance):
        return all(math.hypot(x - tree.x, y - tree.y) > clearance for tree in trees)

    tops = []

    def decorate(builder):
        budget = spec.triangle_budget
        for tree in trees:
            top = tree_kit.add_apple_tree(builder, rng, tree.x, tree.y, height(tree.x, tree.y), tree.size,
                                          FRUIT_COUNT)
            tops.append((tree.x, tree.y, top))

        for _ in range(FENCE_ATTEMPTS):
            angle = rng.uniform(0.0, 2.0 * math.pi)
            radius = blob.boundary(angle) + FENCE_OUTSIDE_OFFSET
            x, y = radius * math.cos(angle), radius * math.sin(angle)
            if hexgrid.inset_distance(x, y) < FENCE_MIN_INSET or not clear_of_trees(x, y, FENCE_TREE_CLEARANCE):
                continue
            rotation = angle + math.pi * 0.5
            ends_ok = all(hexgrid.inset_distance(x + sign * math.cos(rotation) * woodland_props.FENCE_SPAN,
                                                 y + sign * math.sin(rotation) * woodland_props.FENCE_SPAN)
                          >= FENCE_MIN_INSET for sign in (-1.0, 1.0))
            if ends_ok and woodland.fits_budget(builder, FENCE_TRIANGLES, budget):
                woodland_props.add_fence_bit(builder, rng, x, y, 0.0, rotation, FENCE_SPANS, height_at=height)
                break

        for _ in range(variant["hay_bales"]):
            for _ in range(FENCE_ATTEMPTS):
                extent = hexgrid.APOTHEM - HAY_MIN_INSET
                x, y = rng.uniform(-extent, extent), rng.uniform(-extent, extent)
                if hexgrid.inset_distance(x, y) >= HAY_MIN_INSET and clear_of_trees(x, y, HAY_TREE_CLEARANCE):
                    if woodland.fits_budget(builder, HAY_TRIANGLES, budget):
                        kit.add_round_hay_bale(builder, rng, x, y, height(x, y))
                    break

        placed = 0
        for _ in range(variant["fallen_apples"] * 20):
            if placed >= variant["fallen_apples"] or not trees:
                break
            tree = rng.choice(trees)
            angle, distance = rng.uniform(0.0, 2.0 * math.pi), rng.uniform(*FALLEN_APPLE_DISTANCE)
            x, y = tree.x + distance * math.cos(angle), tree.y + distance * math.sin(angle)
            if hexgrid.inset_distance(x, y) < FALLEN_APPLE_MIN_INSET:
                continue
            if not woodland.fits_budget(builder, FALLEN_APPLE_TRIANGLES, budget):
                break
            woodland_props.add_fallen_apple(builder, rng, x, y, height(x, y))
            placed += 1

    snap = woodland.safe_snap(rng, height, snap_with_threshold)
    tile = common.assemble_tile(spec, rng, face_style, height, decorate, snap)
    for index, (x, y, top) in enumerate(_pick_spread(tops, SOCKET_COUNT), start=1):
        woodland.add_socket(tile, SOCKET_NAME.format(index), (x, y, top + SOCKET_HOVER))
    return tile
