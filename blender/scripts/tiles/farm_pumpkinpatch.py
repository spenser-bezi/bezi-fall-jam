"""SM_Tile_PumpkinPatch_A/_B: plowed PlowedRows field with vine rows, chunky orange pumpkins and leaf clumps.

A: a small dirt yard inside the patch holds a cart loaded with pumpkins.
B: the yard holds a stack of crates and a scarecrow.
Both get hay at the field edge and a few hedgerow bushes on the grass rim. Rows run at a multiple of 60 degrees.
Exports SOCKET_Snack_Pumpkin_01..03 empties above three well-spread pumpkins.
"""
import math
import random

from mathutils import Vector

from lib import hexgrid, materials, palette
from props import farm_props
from tiles import common
from tiles import farm_common as farm
from tiles import woodland_common as woodland

HEIGHT_AMPLITUDE = 0.08
FIELD_HEIGHT_FACTOR = 0.3
BLOB_CENTER_JITTER = 0.35
BLOB_RADIUS = 6.3
BLOB_WOBBLE = 0.08
ROW_SPACING = 1.7
ROW_HALF_LENGTH = hexgrid.TILE_RADIUS
ROW_END_MARGIN = 0.35
ROW_MIN_LENGTH = 1.0
VINE_STEP = 1.25
VINE_WIGGLE = 0.16
VINE_HALF_WIDTH = 0.2
YARD_RADIUS = 1.75
YARD_DISTANCE = (2.2, 3.0)
YARD_COLOR = ("DryGrass", palette.SHADE_DARK)
PUMPKIN_SPACING = 1.5
PUMPKIN_RADIUS_RANGE = (0.42, 0.6)
PUMPKIN_BIG_RADIUS = 0.78
PUMPKIN_BIG_CHANCE = 0.15
PUMPKIN_LATERAL_JITTER = 0.15
PUMPKIN_MIN_INSET = 1.6
LEAF_RADIUS_RANGE = (0.35, 0.5)
LEAF_OFFSET = 0.75
SOCKET_COUNT = 3
SOCKET_HOVER = 0.7
SOCKET_NAME = "SOCKET_Snack_Pumpkin_{:02d}"
CRATE_STACK_OFFSET = 0.8
CART_YARD_CLEARANCE = 1.6

VARIANTS = {
    woodland.VARIANT_A: {
        "yard_prop": "cart",
        "pumpkins": 14,
        "leaf_clumps": 6,
        "round_bales": 1,
        "square_stacks": 1,
        "hedge_bushes": 4,
    },
    woodland.VARIANT_B: {
        "yard_prop": "crates",
        "pumpkins": 14,
        "leaf_clumps": 6,
        "round_bales": 2,
        "square_stacks": 0,
        "hedge_bushes": 5,
    },
}


def build(spec, seed):
    """Builds a pumpkin patch tile (variant from the mesh name suffix) with pumpkin snack sockets."""
    variant = VARIANTS[woodland.variant_of(spec)]
    rng = random.Random(seed)
    grass = hexgrid.GrassPainter(seed)
    base_height = common.gentle_height(seed, amplitude=HEIGHT_AMPLITUDE)
    center = (rng.uniform(-BLOB_CENTER_JITTER, BLOB_CENTER_JITTER), rng.uniform(-BLOB_CENTER_JITTER, BLOB_CENTER_JITTER))
    blob = woodland.ContentBlob(seed + 5, BLOB_RADIUS, BLOB_WOBBLE, center)
    plowed = farm.StripedPatch("PlowedRows", math.radians(60.0 * rng.randrange(3)), ROW_SPACING, blob.center.copy())

    yard_angle, yard_distance = rng.uniform(0.0, 2.0 * math.pi), rng.uniform(*YARD_DISTANCE)
    yard = Vector((blob.center.x + yard_distance * math.cos(yard_angle),
                   blob.center.y + yard_distance * math.sin(yard_angle), 0.0))

    def in_yard(x, y, margin=0.0):
        return math.hypot(x - yard.x, y - yard.y) < YARD_RADIUS + margin

    def height(x, y):
        value = base_height(x, y)
        return value * FIELD_HEIGHT_FACTOR if blob.contains(x, y) else value

    def yard_style(centroid):
        if blob.contains(centroid.x, centroid.y) and in_yard(centroid.x, centroid.y):
            return materials.PALETTE_MATERIAL, palette.flat_uv(*YARD_COLOR)
        return None

    face_style = farm.field_face_style(blob, [(plowed, lambda x, y: True)], grass, yard_style)
    snap = farm.fold_free_snap(rng, height, farm.combined_snap(blob, extra=[farm.circle_contour(yard, YARD_RADIUS)]))
    pumpkin_tops = []
    obstacles = farm.Obstacles()

    def in_rows(x, y):
        return blob.contains(x, y) and not in_yard(x, y, 0.2)

    def decorate(builder):
        budget = spec.triangle_budget
        add_yard_props(builder, rng, variant["yard_prop"], yard, plowed, height, obstacles, budget)
        farm.add_edge_hay(builder, rng, blob, height, obstacles, variant["round_bales"], variant["square_stacks"],
                          budget)

        half_extent = BLOB_RADIUS * (1.0 + BLOB_WOBBLE)
        runs = []
        for offset in plowed.row_offsets(half_extent):
            runs.extend(farm.row_runs(in_rows, blob.center, plowed.direction, plowed.normal, offset,
                                      ROW_HALF_LENGTH, ROW_END_MARGIN, ROW_MIN_LENGTH))

        candidates = []
        for start, end in runs:
            length = (end - start).length
            steps = max(1, math.ceil(length / VINE_STEP))
            points = []
            for k in range(steps + 1):
                point = start.lerp(end, k / steps)
                wiggle = 0.0 if k in (0, steps) else rng.uniform(-VINE_WIGGLE, VINE_WIGGLE)
                points.append((point.x + plowed.normal.x * wiggle, point.y + plowed.normal.y * wiggle))
            if woodland.fits_budget(builder, 2 * steps, budget):
                farm_props.add_vine(builder, rng, points, VINE_HALF_WIDTH, height)
            along = rng.uniform(0.2, PUMPKIN_SPACING)
            while along < length:
                point = start + (end - start).normalized() * along
                lateral = rng.uniform(-PUMPKIN_LATERAL_JITTER, PUMPKIN_LATERAL_JITTER)
                candidates.append((point.x + plowed.normal.x * lateral, point.y + plowed.normal.y * lateral))
                along += PUMPKIN_SPACING * rng.uniform(0.8, 1.3)

        rng.shuffle(candidates)
        placed = []
        for x, y in candidates:
            if len(placed) >= variant["pumpkins"]:
                break
            radius = PUMPKIN_BIG_RADIUS if rng.random() < PUMPKIN_BIG_CHANCE else rng.uniform(*PUMPKIN_RADIUS_RANGE)
            if hexgrid.inset_distance(x, y) < PUMPKIN_MIN_INSET or not obstacles.clear(x, y, radius):
                continue
            if any(math.hypot(x - px, y - py) < PUMPKIN_SPACING * 0.8 for px, py in placed):
                continue
            if not woodland.fits_budget(builder, farm_props.PUMPKIN_TRIANGLES, budget):
                break
            top = farm_props.add_pumpkin(builder, rng, x, y, height(x, y), radius)
            pumpkin_tops.append((x, y, top))
            placed.append((x, y))
            obstacles.add(x, y, radius)

        leaves = 0
        for x, y in placed:
            if leaves >= variant["leaf_clumps"]:
                break
            side = rng.choice((-1.0, 1.0)) * LEAF_OFFSET
            lx, ly = x + plowed.direction.x * side, y + plowed.direction.y * side
            size = rng.uniform(*LEAF_RADIUS_RANGE)
            if not in_rows(lx, ly) or not obstacles.clear(lx, ly, size * 0.6):
                continue
            if not woodland.fits_budget(builder, farm_props.LEAF_TRIANGLES, budget):
                break
            farm_props.add_leaf_clump(builder, rng, lx, ly, height(lx, ly), size)
            leaves += 1

        farm.add_hedgerow(builder, rng, blob, height, variant["hedge_bushes"], obstacles, budget)

    tile = common.assemble_tile(spec, rng, face_style, height, decorate, snap)
    farm.add_sockets(tile, SOCKET_NAME, farm.pick_spread(pumpkin_tops, SOCKET_COUNT), SOCKET_HOVER)
    return tile


def add_yard_props(builder, rng, kind, yard, plowed, height_at, obstacles, budget):
    """Dresses the small dirt yard: a pumpkin cart (A) or a crate stack with a scarecrow (B)."""
    rotation = plowed.angle + rng.choice((0.0, math.pi))
    if kind == "cart":
        if woodland.fits_budget(builder, farm_props.cart_triangles(), budget):
            farm_props.add_cart(builder, rng, yard.x, yard.y, height_at(yard.x, yard.y), rotation)
        obstacles.add(yard.x, yard.y, CART_YARD_CLEARANCE)
        return
    direction = farm.unit(rotation)
    stack_x, stack_y = yard.x - direction.x * CRATE_STACK_OFFSET * 0.5, yard.y - direction.y * CRATE_STACK_OFFSET * 0.5
    base = height_at(stack_x, stack_y)
    side = farm.unit(rotation + math.pi * 0.5) * (farm_props.CRATE_SIZE * 0.55)
    farm_props.add_crate(builder, rng, stack_x - side.x, stack_y - side.y, base, rotation)
    top = farm_props.add_crate(builder, rng, stack_x + side.x, stack_y + side.y, base, rotation + 0.1)
    farm_props.add_pumpkin(builder, rng, stack_x - side.x, stack_y - side.y,
                           base + farm_props.CRATE_HEIGHT - 0.12, 0.3)
    farm_props.add_crate(builder, rng, stack_x + side.x, stack_y + side.y, base, rotation - 0.15, top - base)
    scarecrow_x = yard.x + direction.x * CRATE_STACK_OFFSET
    scarecrow_y = yard.y + direction.y * CRATE_STACK_OFFSET
    farm_props.add_scarecrow(builder, rng, scarecrow_x, scarecrow_y, height_at(scarecrow_x, scarecrow_y),
                             plowed.angle)
    obstacles.add(yard.x, yard.y, CART_YARD_CLEARANCE)
