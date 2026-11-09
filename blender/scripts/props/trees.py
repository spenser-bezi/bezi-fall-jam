"""Woodland tree kit: chunky autumn deciduous trees (round / tall / lumpy), pines (small / large), apple trees.

Every tree is baked into a MeshBuilder, scaled down when needed so its top stays under the decor height limit,
and writes the sway weight into vertex color R (0 at trunks, rising toward canopy tips).
Footprint helpers return the planar canopy radius (jitter included) so tiles can respect the rim overhang limit.
"""
import math

from mathutils import Matrix, Vector

from lib import hexgrid, materials, palette, shapes
from props import kit

MATERIAL = materials.PALETTE_MATERIAL
DECOR_HEIGHT_MARGIN = 0.12

TRUNK_SIDES = 4
TRUNK_SINK = 0.15
TRUNK_RADIUS_FACTOR = 0.11
TRUNK_MIN_RADIUS = 0.11
TRUNK_TOP_FACTOR = 0.7
TRUNK_COLOR = ("Wood", palette.SHADE_DARK)

KIND_ROUND = "round"
KIND_TALL = "tall"
KIND_LUMPY = "lumpy"
DECIDUOUS_KINDS = (KIND_ROUND, KIND_TALL, KIND_LUMPY)

CANOPY_JITTER = 0.12
CANOPY_CENTER_FACTOR = 0.62
CANOPY_SWAY_BASE = 0.45
CANOPY_SWAY_RANGE = 0.55
ROUND_SEGMENTS = (7, 4)
ROUND_SQUASH = 0.76
ROUND_TRUNK_HEIGHT = 0.75
TALL_SEGMENTS = (6, 4)
TALL_SQUASH = 1.45
TALL_TRUNK_HEIGHT = 0.6
LUMPY_SEGMENTS = (6, 4)
LUMPY_SQUASH = 0.78
LUMPY_TRUNK_HEIGHT = 0.7
LUMPY_LOBE_SEGMENTS = (5, 3)
LUMPY_LOBE_SCALE = 0.62
LUMPY_LOBE_OFFSET = 0.5
LUMPY_LOBE_LIFT = 0.3

PINE_SMALL = "small"
PINE_LARGE = "large"
PINE_SIDES = 6
PINE_TRUNK_RADIUS = 0.14
PINE_TRUNK_FRACTION = 0.16
PINE_TIER_OVERLAP = 0.42
PINE_TIER_SHRINK = 0.27
PINE_SHAPES = {
    PINE_SMALL: {"height": 2.2, "radius": 0.85, "tiers": 2},
    PINE_LARGE: {"height": 3.35, "radius": 1.3, "tiers": 3},
}
PINE_COLOR = "Pine"
PINE_TOP_LIGHT_CHANCE = 0.45

APPLE_SEGMENTS = (6, 4)
APPLE_SQUASH = 0.88
APPLE_TRUNK_HEIGHT = 0.85
APPLE_CANOPY_COLORS = (("Moss", palette.SHADE_BASE), ("Moss", palette.SHADE_BASE), ("Moss", palette.SHADE_LIGHT),
                       ("LightMoss", palette.SHADE_BASE), ("Moss", palette.SHADE_DARK), ("Mustard", palette.SHADE_DARK))
FRUIT_SIZE = 0.3
FRUIT_COLOR = "MapleRed"
FRUIT_SWAY = 0.8
FRUIT_LOWEST_RING = 2


def deciduous_footprint(kind, canopy_radius):
    """Planar canopy radius (jitter included) of a deciduous tree kind."""
    if kind == KIND_LUMPY:
        lobe_reach = canopy_radius * (LUMPY_LOBE_OFFSET + LUMPY_LOBE_SCALE * (1.0 + CANOPY_JITTER))
        return max(canopy_radius * (1.0 + CANOPY_JITTER), lobe_reach)
    return canopy_radius * (1.0 + CANOPY_JITTER)


def pine_footprint(size, scale=1.0):
    """Planar radius of a pine's lowest tier."""
    return PINE_SHAPES[size]["radius"] * scale


def apple_tree_footprint(canopy_radius):
    """Planar canopy radius of an apple tree, fruit included."""
    return canopy_radius * (1.0 + CANOPY_JITTER) + FRUIT_SIZE * 0.5


def _placement(x, y, z, rotation, scale=1.0):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(rotation, 4, "Z") @ Matrix.Scale(scale, 4)


def _fit_scale(base_z, local_top):
    """Uniform scale that keeps a prop's top below the decor height limit."""
    return min(1.0, (hexgrid.MAX_DECOR_HEIGHT - DECOR_HEIGHT_MARGIN - base_z) / local_top)


def _add_trunk(builder, placement, radius, height):
    trunk = shapes.prism(TRUNK_SIDES, radius, height + TRUNK_SINK, top_radius=radius * TRUNK_TOP_FACTOR,
                         cap_top=False, angle_offset=math.pi / TRUNK_SIDES)
    builder.add_part(trunk, placement @ Matrix.Translation((0.0, 0.0, -TRUNK_SINK)), MATERIAL,
                     lambda face, centroid: palette.flat_uv(*TRUNK_COLOR))


def _canopy_sway(total_height):
    return lambda local: CANOPY_SWAY_BASE + CANOPY_SWAY_RANGE * max(0.0, local.z) / total_height


def add_deciduous(builder, rng, x, y, base_z, canopy_radius, color_name, kind=KIND_ROUND):
    """Adds a trunk + faceted canopy deciduous tree and returns its world top height."""
    if kind == KIND_TALL:
        segments, squash, trunk_height = TALL_SEGMENTS, TALL_SQUASH, TALL_TRUNK_HEIGHT
    elif kind == KIND_LUMPY:
        segments, squash, trunk_height = LUMPY_SEGMENTS, LUMPY_SQUASH, LUMPY_TRUNK_HEIGHT
    else:
        segments, squash, trunk_height = ROUND_SEGMENTS, ROUND_SQUASH, ROUND_TRUNK_HEIGHT
    half_height = canopy_radius * squash
    canopy_center = trunk_height + half_height * CANOPY_CENTER_FACTOR
    local_top = canopy_center + half_height * (1.0 + CANOPY_JITTER)
    scale = _fit_scale(base_z, local_top)
    placement = _placement(x, y, base_z, rng.uniform(0.0, 2.0 * math.pi), scale)

    _add_trunk(builder, placement, max(TRUNK_MIN_RADIUS, canopy_radius * TRUNK_RADIUS_FACTOR), canopy_center)
    canopy = shapes.blob(segments[0], segments[1], canopy_radius, squash, CANOPY_JITTER, rng)
    sway = _canopy_sway(local_top)
    builder.add_part(canopy, placement @ Matrix.Translation((0.0, 0.0, canopy_center)), MATERIAL,
                     lambda face, centroid: palette.flat_uv(color_name, kit.random_shade(rng)),
                     lambda local: sway(local + Vector((0.0, 0.0, canopy_center))))

    if kind == KIND_LUMPY:
        lobe_radius = canopy_radius * LUMPY_LOBE_SCALE
        lobe_offset = Vector((canopy_radius * LUMPY_LOBE_OFFSET, 0.0,
                              canopy_center + canopy_radius * LUMPY_LOBE_LIFT * squash))
        lobe = shapes.blob(LUMPY_LOBE_SEGMENTS[0], LUMPY_LOBE_SEGMENTS[1], lobe_radius, squash, CANOPY_JITTER, rng)
        builder.add_part(lobe, placement @ Matrix.Translation(lobe_offset), MATERIAL,
                         lambda face, centroid: palette.flat_uv(color_name, kit.random_shade(rng, 0.35, 0.1)),
                         lambda local: sway(local + lobe_offset))
    return base_z + local_top * scale


def add_pine(builder, rng, x, y, base_z, size=PINE_LARGE, scale=1.0):
    """Adds a stacked-cone pine (2 tiers small, 3 tiers large) and returns its world top height."""
    shape = PINE_SHAPES[size]
    height, radius, tiers = shape["height"] * scale, shape["radius"] * scale, shape["tiers"]
    fit = _fit_scale(base_z, height)
    placement = _placement(x, y, base_z, rng.uniform(0.0, 2.0 * math.pi), fit)

    trunk_height = height * PINE_TRUNK_FRACTION
    _add_trunk(builder, placement, PINE_TRUNK_RADIUS * scale, trunk_height + height * 0.1)
    crown_height = height - trunk_height
    tier_height = crown_height / (tiers - (tiers - 1) * PINE_TIER_OVERLAP)
    for tier in range(tiers):
        tier_radius = radius * (1.0 - PINE_TIER_SHRINK * tier)
        tier_base = trunk_height + tier * tier_height * (1.0 - PINE_TIER_OVERLAP)
        cone = shapes.cone(PINE_SIDES, tier_radius, tier_height, angle_offset=rng.uniform(0.0, math.pi))
        if tier == 0:
            cone.faces.append(tuple(reversed(range(PINE_SIDES))))
        is_top = tier == tiers - 1
        light_chance = PINE_TOP_LIGHT_CHANCE if is_top else kit.LIGHT_SHADE_CHANCE

        def tier_uv(face, centroid, chance=light_chance):
            return palette.flat_uv(PINE_COLOR, kit.random_shade(rng, chance, kit.DARK_SHADE_CHANCE))

        builder.add_part(cone, placement @ Matrix.Translation((0.0, 0.0, tier_base)), MATERIAL, tier_uv,
                         lambda local, base=tier_base: (base + local.z) / height)
    return base_z + height * fit


def _fruit_part():
    """A tiny tetrahedron centered on the origin (4 tris): reads as a fruit dot at game distance."""
    half = FRUIT_SIZE * 0.5
    vertices = [(0.0, 0.0, half)]
    for k in range(3):
        angle = 2.0 * math.pi * k / 3.0
        vertices.append((half * math.cos(angle), half * math.sin(angle), -half * 0.6))
    faces = [(0, 1, 2), (0, 2, 3), (0, 3, 1), (1, 3, 2)]
    return shapes.Part(vertices, faces)


def add_apple_tree(builder, rng, x, y, base_z, canopy_radius, fruit_count):
    """Adds a round green-gold apple tree dotted with red fruit and returns its world top height."""
    half_height = canopy_radius * APPLE_SQUASH
    canopy_center = APPLE_TRUNK_HEIGHT + half_height * CANOPY_CENTER_FACTOR
    local_top = canopy_center + half_height * (1.0 + CANOPY_JITTER)
    scale = _fit_scale(base_z, local_top)
    placement = _placement(x, y, base_z, rng.uniform(0.0, 2.0 * math.pi), scale)

    _add_trunk(builder, placement, max(TRUNK_MIN_RADIUS, canopy_radius * TRUNK_RADIUS_FACTOR), canopy_center)
    u_segments, v_segments = APPLE_SEGMENTS
    canopy = shapes.blob(u_segments, v_segments, canopy_radius, APPLE_SQUASH, CANOPY_JITTER, rng)
    canopy_matrix = placement @ Matrix.Translation((0.0, 0.0, canopy_center))
    sway = _canopy_sway(local_top)
    builder.add_part(canopy, canopy_matrix, MATERIAL,
                     lambda face, centroid: palette.flat_uv(*rng.choice(APPLE_CANOPY_COLORS)),
                     lambda local: sway(local + Vector((0.0, 0.0, canopy_center))))

    first_candidate = 1 + (FRUIT_LOWEST_RING - 1) * u_segments
    candidates = list(range(first_candidate, len(canopy.vertices) - 1))
    for vertex_index in rng.sample(candidates, min(fruit_count, len(candidates))):
        fruit_matrix = (canopy_matrix @ Matrix.Translation(canopy.vertices[vertex_index])
                        @ Matrix.Rotation(rng.uniform(0.0, 2.0 * math.pi), 4, "Z"))
        builder.add_part(_fruit_part(), fruit_matrix, MATERIAL,
                         lambda face, centroid: palette.flat_uv(FRUIT_COLOR, rng.choice(
                             (palette.SHADE_BASE, palette.SHADE_LIGHT))),
                         lambda local: FRUIT_SWAY)
    return base_z + local_top * scale
