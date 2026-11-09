"""SM_Tile_Farm_A/_B: red barn, short silo (<= 3.5 m, the tall silo is an obstacle), straw yard, hay bales,
a fenced mixed field patch (two striped halves with different row directions) and a shade tree.

A: gold FieldRows + GreenRows halves, round and square hay.
B: CornRows + PlowedRows halves with a few pumpkins, more square hay.
Field rows run at multiples of 60 degrees so they line up with a hex side at any tile rotation.
"""
import math
import random

from lib import hexgrid, materials, palette
from props import farm_props
from props import trees as tree_kit
from tiles import common
from tiles import farm_common as farm
from tiles import woodland_common as woodland

HEIGHT_AMPLITUDE = 0.08
FLAT_FACTOR = 0.3
YARD_DISTANCE = 4.0
YARD_RADIUS = 2.6
YARD_WOBBLE = 0.1
YARD_COLOR = ("DryGrass", palette.SHADE_LIGHT)
FIELD_DISTANCE = 3.2
FIELD_RADIUS = 3.9
FIELD_WOBBLE = 0.06
FIELD_SPLIT_JITTER = 0.5
ROW_SPACING = 1.25
SILO_GAP = 0.35
HAY_STACK_DISTANCE = (3.2, 4.4)
BARN_CLEARANCE = 2.7
SILO_CLEARANCE = 1.0
FENCE_OFFSET = 0.5
FENCE_ARC = math.radians(110.0)
FENCE_POST_SPACING = 1.6
FENCE_MIN_INSET = 1.2
TREE_RADIUS_RANGE = (0.95, 1.15)
TREE_MIN_INSET = 1.8
TREE_ATTEMPTS = 400
TREE_COLORS = ("MapleRed", "Mustard", "Pumpkin")
PUMPKIN_RADIUS_RANGE = (0.32, 0.45)
PUMPKIN_SPACING = 1.3
PUMPKIN_MIN_INSET = 1.6

VARIANTS = {
    woodland.VARIANT_A: {
        "strips": ("FieldRows", "PlowedRows"),
        "pumpkins": 0,
        "round_bales": 2,
        "square_stacks": 1,
        "trees": 2,
        "hedge_bushes": 3,
    },
    woodland.VARIANT_B: {
        "strips": ("CornRows", "PlowedRows"),
        "pumpkins": 4,
        "round_bales": 1,
        "square_stacks": 2,
        "trees": 1,
        "hedge_bushes": 3,
    },
}


def build(spec, seed):
    """Builds a farmstead tile (variant from the mesh name suffix)."""
    variant = VARIANTS[woodland.variant_of(spec)]
    rng = random.Random(seed)
    grass = hexgrid.GrassPainter(seed)
    base_height = common.gentle_height(seed, amplitude=HEIGHT_AMPLITUDE)
    farm_angle = rng.uniform(0.0, 2.0 * math.pi)
    yard_direction = farm.unit(farm_angle)
    yard = woodland.ContentBlob(seed + 9, YARD_RADIUS, YARD_WOBBLE, (yard_direction * YARD_DISTANCE).xy, 1.0)
    field = woodland.ContentBlob(seed + 5, FIELD_RADIUS, FIELD_WOBBLE, (-yard_direction * FIELD_DISTANCE).xy)

    first_angle = math.radians(60.0 * rng.randrange(3))
    patch_a = farm.StripedPatch(variant["strips"][0], first_angle, ROW_SPACING, field.center.copy())
    patch_b = farm.StripedPatch(variant["strips"][1], first_angle + math.radians(60.0), ROW_SPACING,
                                field.center.copy())
    split_normal = farm.unit(farm_angle + math.pi * 0.5)
    split = farm.SplitLine(field.center + split_normal * rng.uniform(-FIELD_SPLIT_JITTER, FIELD_SPLIT_JITTER),
                           split_normal)
    patches = [(patch_a, lambda x, y: split.side(x, y) >= 0.0), (patch_b, lambda x, y: split.side(x, y) < 0.0)]

    def height(x, y):
        value = base_height(x, y)
        return value * FLAT_FACTOR if field.contains(x, y) or yard.contains(x, y) else value

    def yard_style(centroid):
        if yard.contains(centroid.x, centroid.y):
            return materials.PALETTE_MATERIAL, palette.flat_uv(*YARD_COLOR)
        return None

    face_style = farm.field_face_style(field, patches, grass, yard_style)
    snap = farm.fold_free_snap(rng, height, farm.combined_snap(field, [split], extra=[yard.snap]))
    obstacles = farm.Obstacles()

    def decorate(builder):
        budget = spec.triangle_budget
        barn_rotation = farm_angle + math.pi * 0.5
        barn_axis = farm.unit(barn_rotation)
        barn_center = yard.center
        farm_props.add_barn(builder, rng, barn_center.x, barn_center.y, height(barn_center.x, barn_center.y),
                            barn_rotation)
        obstacles.add(barn_center.x, barn_center.y, BARN_CLEARANCE)
        silo_side = rng.choice((-1.0, 1.0))
        silo_distance = farm_props.BARN_LENGTH * 0.5 + farm_props.BARN_ROOF_END_OVERHANG + \
            farm_props.SILO_DOME_RADIUS + SILO_GAP
        silo = barn_center + barn_axis * (silo_side * silo_distance)
        farm_props.add_silo(builder, rng, silo.x, silo.y, height(silo.x, silo.y))
        obstacles.add(silo.x, silo.y, SILO_CLEARANCE)

        for _ in range(variant["square_stacks"]):
            for _ in range(farm.EDGE_ATTEMPTS):
                angle = farm_angle + rng.uniform(-math.pi * 0.6, math.pi * 0.6)
                spot = barn_center + farm.unit(angle) * rng.uniform(*HAY_STACK_DISTANCE)
                if (hexgrid.inset_distance(spot.x, spot.y) < farm.EDGE_INSET_RANGE[0] or field.contains(spot.x, spot.y)
                        or not obstacles.clear(spot.x, spot.y, farm.HAY_CLEARANCE)):
                    continue
                if woodland.fits_budget(builder, 3 * farm_props.SQUARE_BALE_TRIANGLES, budget):
                    farm.add_square_stack(builder, rng, spot.x, spot.y, angle, height)
                    obstacles.add(spot.x, spot.y, farm.HAY_CLEARANCE)
                break

        add_field_fence(builder, rng, field, farm_angle, height, obstacles, budget)
        farm.add_edge_hay(builder, rng, field, height, obstacles, variant["round_bales"], 0, budget)
        add_trees(builder, rng, variant["trees"], field, height, obstacles, budget)
        if variant["pumpkins"]:
            add_field_pumpkins(builder, rng, variant["pumpkins"], field, patch_b, split, height, obstacles, budget)
        farm.add_hedgerow(builder, rng, field, height, variant["hedge_bushes"], obstacles, budget)

    return common.assemble_tile(spec, rng, face_style, height, decorate, snap)


def add_field_fence(builder, rng, field, farm_angle, height_at, obstacles, budget):
    """Fences the side of the field patch that faces the farmyard."""
    facing = farm_angle
    arc_length = FENCE_ARC * (FIELD_RADIUS + FENCE_OFFSET)
    post_count = max(2, int(arc_length / FENCE_POST_SPACING) + 1)
    points = []
    for k in range(post_count):
        angle = facing - FENCE_ARC * 0.5 + FENCE_ARC * k / (post_count - 1)
        radius = field.boundary(angle) + FENCE_OFFSET
        x, y = field.center.x + radius * math.cos(angle), field.center.y + radius * math.sin(angle)
        if hexgrid.inset_distance(x, y) < FENCE_MIN_INSET or not obstacles.clear(x, y, 0.2):
            if len(points) >= 2:
                break
            points = []
            continue
        points.append((x, y))
    if len(points) >= 2 and woodland.fits_budget(builder, farm_props.fence_triangles(len(points)), budget):
        farm_props.add_fence(builder, rng, points, height_at)
        for x, y in points:
            obstacles.add(x, y, 0.3)


def add_trees(builder, rng, count, field, height_at, obstacles, budget):
    """Adds shade trees on free grass (trunks well inside the rim, canopies inside the overhang limit)."""
    placed = 0
    for _ in range(TREE_ATTEMPTS):
        if placed >= count:
            break
        x, y = rng.uniform(-hexgrid.APOTHEM, hexgrid.APOTHEM), rng.uniform(-hexgrid.APOTHEM, hexgrid.APOTHEM)
        inset = hexgrid.inset_distance(x, y)
        if inset < TREE_MIN_INSET or field.contains(x, y):
            continue
        radius = woodland.max_size_for_inset(inset, lambda r: tree_kit.deciduous_footprint(tree_kit.KIND_ROUND, r),
                                             rng.uniform(*TREE_RADIUS_RANGE))
        footprint = tree_kit.deciduous_footprint(tree_kit.KIND_ROUND, radius)
        if not obstacles.clear(x, y, footprint):
            continue
        field_distance = math.hypot(x - field.center.x, y - field.center.y)
        if field_distance < field.boundary(math.atan2(y - field.center.y, x - field.center.x)) + footprint * 0.6:
            continue
        if not woodland.fits_budget(builder, 40, budget):
            break
        tree_kit.add_deciduous(builder, rng, x, y, height_at(x, y), radius, rng.choice(TREE_COLORS))
        obstacles.add(x, y, footprint)
        placed += 1


def add_field_pumpkins(builder, rng, count, field, patch, split, height_at, obstacles, budget):
    """Scatters a few pumpkins on the rows of the plowed half of the field."""
    placed = 0
    for _ in range(farm.EDGE_ATTEMPTS):
        if placed >= count:
            break
        x = field.center.x + rng.uniform(-FIELD_RADIUS, FIELD_RADIUS)
        y = field.center.y + rng.uniform(-FIELD_RADIUS, FIELD_RADIUS)
        x, y = patch.align(x, y, on_row=True)
        radius = rng.uniform(*PUMPKIN_RADIUS_RANGE)
        if not field.contains(x, y) or split.side(x, y) > -radius or hexgrid.inset_distance(x, y) < PUMPKIN_MIN_INSET:
            continue
        if not obstacles.clear(x, y, PUMPKIN_SPACING * 0.5):
            continue
        if not woodland.fits_budget(builder, farm_props.PUMPKIN_TRIANGLES, budget):
            break
        farm_props.add_pumpkin(builder, rng, x, y, height_at(x, y), radius)
        obstacles.add(x, y, PUMPKIN_SPACING * 0.5)
        placed += 1
