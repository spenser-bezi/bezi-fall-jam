"""SM_Tile_Cornfield_A/_B: golden ridged corn rows over a CornRows-striped field, hay at the field edge.

A: one big corn patch with a small clearing for the scarecrow.
B: the field is split along a snapped line into a corn half and a harvested half (FieldRows stripes, stubble rows
   and round bales).
Rows run at a multiple of 60 degrees so they always line up with a hex side, whatever the tile rotation.
Exports SOCKET_Snack_Corn_01..03 empties just above three well-spread corn ridge tops.
"""
import math
import random

from mathutils import Vector

from lib import hexgrid
from props import farm_props, kit
from tiles import common
from tiles import farm_common as farm
from tiles import woodland_common as woodland

HEIGHT_AMPLITUDE = 0.08
FIELD_HEIGHT_FACTOR = 0.3
BLOB_CENTER_JITTER = 0.35
ROW_END_MARGIN = 0.45
ROW_MIN_LENGTH = 1.2
ROW_HALF_LENGTH = hexgrid.TILE_RADIUS
CLEARING_RADIUS = 1.5
SCARECROW_DISTANCE = (2.0, 3.2)
HAY_MIN_INSET = 1.35
HAY_ATTEMPTS = 300
STUBBLE_BALE_COUNT = 2
STUBBLE_BALE_CLEARANCE = 0.9
SOCKET_COUNT = 3
SOCKET_HOVER = 0.6
SOCKET_NAME = "SOCKET_Snack_Corn_{:02d}"
SOCKET_MIN_SPACING = 3.0

VARIANTS = {
    woodland.VARIANT_A: {
        "blob_radius": 6.25,
        "blob_wobble": 0.08,
        "row_spacing": 1.6,
        "split": False,
        "scarecrow": True,
        "round_bales": 2,
        "square_stacks": 1,
        "hedge_bushes": 5,
    },
    woodland.VARIANT_B: {
        "blob_radius": 6.3,
        "blob_wobble": 0.08,
        "row_spacing": 1.55,
        "split": True,
        "scarecrow": False,
        "round_bales": 1,
        "square_stacks": 1,
        "hedge_bushes": 5,
    },
}


def build(spec, seed):
    """Builds a cornfield tile (variant from the mesh name suffix) with corn snack sockets."""
    variant = VARIANTS[woodland.variant_of(spec)]
    rng = random.Random(seed)
    grass = hexgrid.GrassPainter(seed)
    base_height = common.gentle_height(seed, amplitude=HEIGHT_AMPLITUDE)
    center = (rng.uniform(-BLOB_CENTER_JITTER, BLOB_CENTER_JITTER), rng.uniform(-BLOB_CENTER_JITTER, BLOB_CENTER_JITTER))
    blob = woodland.ContentBlob(seed + 5, variant["blob_radius"], variant["blob_wobble"], center)
    row_angle = math.radians(60.0 * rng.randrange(3))
    corn = farm.StripedPatch("CornRows", row_angle, variant["row_spacing"], blob.center.copy())

    lines = []
    if variant["split"]:
        split_offset = rng.uniform(-0.8, 0.8)
        split = farm.SplitLine(blob.center + corn.normal * split_offset, corn.normal)
        lines.append(split)
        harvested = farm.StripedPatch("FieldRows", row_angle, variant["row_spacing"], blob.center.copy())
        patches = [(corn, lambda x, y: split.side(x, y) >= 0.0), (harvested, lambda x, y: split.side(x, y) < 0.0)]
    else:
        split = None
        patches = [(corn, lambda x, y: True)]

    clearing = None
    if variant["scarecrow"]:
        angle, distance = rng.uniform(0.0, 2.0 * math.pi), rng.uniform(*SCARECROW_DISTANCE)
        clearing = Vector((blob.center.x + distance * math.cos(angle), blob.center.y + distance * math.sin(angle), 0))
        # Center the clearing on a furrow (between two rows) so the scarecrow stands in an open strip.
        clearing.x, clearing.y = corn.align(clearing.x, clearing.y, on_row=False)

    def height(x, y):
        value = base_height(x, y)
        return value * FIELD_HEIGHT_FACTOR if blob.contains(x, y) else value

    def in_corn(x, y):
        if not blob.contains(x, y):
            return False
        if split is not None and split.side(x, y) < 0.0:
            return False
        return clearing is None or math.hypot(x - clearing.x, y - clearing.y) > CLEARING_RADIUS

    def in_harvested(x, y):
        return split is not None and blob.contains(x, y) and split.side(x, y) < 0.0

    face_style = farm.field_face_style(blob, patches, grass)
    snap = farm.fold_free_snap(rng, height, farm.combined_snap(blob, lines))
    ridge_tops = []
    obstacles = farm.Obstacles()

    def decorate(builder):
        budget = spec.triangle_budget
        half_extent = variant["blob_radius"] * (1.0 + variant["blob_wobble"])
        if clearing is not None:
            farm_props.add_scarecrow(builder, rng, clearing.x, clearing.y, height(clearing.x, clearing.y), corn.angle)
            obstacles.add(clearing.x, clearing.y, CLEARING_RADIUS)

        for offset in corn.row_offsets(half_extent):
            for start, end in farm.row_runs(in_corn, blob.center, corn.direction, corn.normal, offset,
                                            ROW_HALF_LENGTH, ROW_END_MARGIN, ROW_MIN_LENGTH):
                if not woodland.fits_budget(builder, farm_props.corn_row_triangles((end - start).length), budget):
                    continue
                ridge_tops.extend(farm_props.add_corn_row(builder, rng, start, end, height))

        if split is not None:
            for offset in corn.row_offsets(half_extent):
                for start, end in farm.row_runs(in_harvested, blob.center, corn.direction, corn.normal, offset,
                                                ROW_HALF_LENGTH, ROW_END_MARGIN, ROW_MIN_LENGTH):
                    cost = farm_props.stubble_row_triangles((end - start).length)
                    if woodland.fits_budget(builder, cost, budget):
                        farm_props.add_stubble_row(builder, rng, start, end, height)
            placed = 0
            for _ in range(HAY_ATTEMPTS):
                if placed >= STUBBLE_BALE_COUNT:
                    break
                x = blob.center.x + rng.uniform(-half_extent, half_extent)
                y = blob.center.y + rng.uniform(-half_extent, half_extent)
                if (not in_harvested(x, y) or hexgrid.inset_distance(x, y) < HAY_MIN_INSET + 0.4
                        or abs(split.side(x, y)) < 1.0 or not obstacles.clear(x, y, STUBBLE_BALE_CLEARANCE)):
                    continue
                # Bales sit in a furrow so they do not intersect the stubble ridges.
                x, y = corn.align(x, y, on_row=False)
                if woodland.fits_budget(builder, farm_props.ROUND_BALE_TRIANGLES, budget):
                    kit.add_round_hay_bale(builder, rng, x, y, height(x, y))
                    obstacles.add(x, y, STUBBLE_BALE_CLEARANCE)
                    placed += 1

        farm.add_edge_hay(builder, rng, blob, height, obstacles, variant["round_bales"], variant["square_stacks"],
                          budget)
        farm.add_hedgerow(builder, rng, blob, height, variant["hedge_bushes"], obstacles, budget)

    tile = common.assemble_tile(spec, rng, face_style, height, decorate, snap)
    spaced = [top for top in ridge_tops if hexgrid.inset_distance(top[0], top[1]) > 2.0]
    farm.add_sockets(tile, SOCKET_NAME, farm.pick_spread(spaced, SOCKET_COUNT), SOCKET_HOVER)
    return tile
