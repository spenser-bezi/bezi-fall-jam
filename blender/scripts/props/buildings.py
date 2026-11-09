"""Settlement prop kit: houses, chapel (no steeple), lodge cabin, fences, dirt paths and square paving.

Buildings are modeled along local X (ridge direction) with the front (door) wall facing local -Y.
"""
import math

from mathutils import Matrix, Vector

from lib import hexgrid, materials, palette, shapes

MATERIAL = materials.PALETTE_MATERIAL
WALL_SINK = 0.15
FACADE_OFFSET = 0.02
DECOR_HEIGHT_MARGIN = 0.1

ROOF_OVERHANG = 0.28
ROOF_END_OVERHANG = 0.22
ROOF_THICKNESS = 0.18
CHIMNEY_SIZE = 0.38
CHIMNEY_RISE = 0.35
DOOR_HALF_WIDTH = 0.28
DOOR_HEIGHT = 1.0
WINDOW_HALF_SIZE = 0.2
WINDOW_GLOW = ("HarvestGold", palette.SHADE_LIGHT)

HOUSE_STYLES = {
    "small": {"length": 3.0, "width": 2.4, "wall": 1.55, "ridge": 2.55},
    "tall": {"length": 2.6, "width": 2.3, "wall": 2.25, "ridge": 3.05},
    "long": {"length": 3.8, "width": 2.3, "wall": 1.45, "ridge": 2.4},
}
RED_ROOF = "MapleRed"
NAVY_ROOF = "NavyRoof"

CHAPEL_LENGTH = 4.4
CHAPEL_WIDTH = 2.6
CHAPEL_WALL = 1.95
CHAPEL_RIDGE = 3.05
CHAPEL_APSE_LENGTH = 1.3
CHAPEL_APSE_WIDTH = 1.8
CHAPEL_APSE_WALL = 1.5
CHAPEL_APSE_RIDGE = 2.2
CHAPEL_WINDOW_HALF_WIDTH = 0.13
CHAPEL_WINDOW_HALF_HEIGHT = 0.35
CHAPEL_ROSE_HALF_SIZE = 0.22

LODGE_LENGTH = 4.8
LODGE_WIDTH = 3.4
LODGE_WALL = 1.8
LODGE_RIDGE = 3.05
LODGE_CORNER_SIZE = 0.26
LODGE_CHIMNEY_WIDTH = 0.7
LODGE_CHIMNEY_DEPTH = 0.55
LODGE_CHIMNEY_TOP = 3.4
LODGE_PORCH_DEPTH = 1.3
LODGE_PORCH_HEIGHT = 0.22
LODGE_PORCH_EDGE_HEIGHT = 1.55
LODGE_PORCH_POST_SIZE = 0.14

FENCE_POST_SIZE = 0.12
FENCE_POST_HEIGHT = 0.75
FENCE_POST_SINK = 0.1
FENCE_RAIL_SIZE = 0.07
FENCE_RAIL_HEIGHTS = (0.3, 0.58)

PATH_STEP = 0.9
PATH_END_TAPER = 0.55
PAVING_WOBBLE = 0.08
PAVING_KERB_FRACTION = 0.16
CHAPEL_CROSS_HALF_WIDTH = 0.05
CHAPEL_CROSS_HALF_HEIGHT = 0.26
CHAPEL_CROSS_ARM = 0.17


def extrude_yz(profile, x_min, x_max, skip_edges=(0,), caps=True):
    """Extrudes a CCW (y, z) profile along X. Face order: side faces by edge (minus skip_edges), then caps."""
    count = len(profile)
    vertices = [(x_min, y, z) for y, z in profile] + [(x_max, y, z) for y, z in profile]
    faces = []
    for k in range(count):
        if k in skip_edges:
            continue
        n = (k + 1) % count
        faces.append((k, n, count + n, count + k))
    if caps:
        faces.append(tuple(count + k for k in range(count)))
        faces.append(tuple(reversed(range(count))))
    return shapes.Part(vertices, faces)


def box(size_x, size_y, size_z):
    """Box centered on X/Y standing on z = 0, without a bottom face (10 tris)."""
    half_y = size_y * 0.5
    return extrude_yz([(-half_y, 0.0), (half_y, 0.0), (half_y, size_z), (-half_y, size_z)],
                      -size_x * 0.5, size_x * 0.5)


def _flat(name, shade=palette.SHADE_BASE):
    uv = palette.flat_uv(name, shade)
    return lambda face, centroid: uv


def add_beam(builder, placement, start, end, size, color_name, shade=palette.SHADE_BASE):
    """Adds a square-section beam (no end caps, 8 tris) between two local points."""
    start, end = Vector(start), Vector(end)
    direction = end - start
    half = size * 0.5
    beam = extrude_yz([(-half, -half), (half, -half), (half, half), (-half, half)], 0.0, direction.length,
                      skip_edges=(), caps=False)
    rotation = Vector((1.0, 0.0, 0.0)).rotation_difference(direction.normalized()).to_matrix().to_4x4()
    builder.add_part(beam, placement @ Matrix.Translation(start) @ rotation, MATERIAL, _flat(color_name, shade))


def facade_quad(builder, placement, center, right, up, half_width, half_height, color_name, shade):
    """Adds a flat quad (door, window) facing right x up, centered at a local point."""
    center, right, up = Vector(center), Vector(right), Vector(up)
    corners = [center - right * half_width - up * half_height, center + right * half_width - up * half_height,
               center + right * half_width + up * half_height, center - right * half_width + up * half_height]
    builder.add_part(shapes.Part(corners, [(0, 1, 2, 3)]), placement, MATERIAL, _flat(color_name, shade))


def _placement(x, y, z, rotation, scale=1.0):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(rotation, 4, "Z") @ Matrix.Scale(scale, 4)


def _fit_scale(base_z, top):
    return min(1.0, (hexgrid.MAX_DECOR_HEIGHT - DECOR_HEIGHT_MARGIN - base_z) / top)


def add_gable_block(builder, placement, length, width, wall, ridge, wall_color, roof_color, wall_shade=None):
    """Adds a pentagonal wall block plus a two-slab overhanging gable roof (34 tris)."""
    half_w = width * 0.5
    walls = extrude_yz([(-half_w, -WALL_SINK), (half_w, -WALL_SINK), (half_w, wall), (0.0, ridge), (-half_w, wall)],
                       -length * 0.5, length * 0.5)
    shade = palette.SHADE_BASE if wall_shade is None else wall_shade
    builder.add_part(walls, placement, MATERIAL, _flat(wall_color, shade))

    slope = (ridge - wall) / half_w
    eave_y = half_w + ROOF_OVERHANG
    eave_z = wall - ROOF_OVERHANG * slope
    x_min, x_max = -length * 0.5 - ROOF_END_OVERHANG, length * 0.5 + ROOF_END_OVERHANG
    left = extrude_yz([(-eave_y, eave_z), (0.0, ridge), (0.0, ridge + ROOF_THICKNESS),
                       (-eave_y, eave_z + ROOF_THICKNESS)], x_min, x_max, skip_edges=(1,))
    right = extrude_yz([(0.0, ridge), (eave_y, eave_z), (eave_y, eave_z + ROOF_THICKNESS),
                        (0.0, ridge + ROOF_THICKNESS)], x_min, x_max, skip_edges=(3,))
    top_light = palette.flat_uv(roof_color, palette.SHADE_BASE)
    trim = palette.flat_uv(roof_color, palette.SHADE_DARK)
    builder.add_part(left, placement, MATERIAL, lambda face, centroid: top_light if face == 1 else trim)
    builder.add_part(right, placement, MATERIAL, lambda face, centroid: top_light if face == 2 else trim)
    return ridge + ROOF_THICKNESS


def add_house(builder, rng, x, y, base_z, rotation, roof_color, style="small", wall_color="WallCream"):
    """Adds a cottage (walls, gable roof, chimney, door, lit windows). Returns its footprint radius."""
    dims = HOUSE_STYLES[style]
    length, width, wall, ridge = dims["length"], dims["width"], dims["wall"], dims["ridge"]
    chimney_x = length * 0.25 * rng.choice((-1.0, 1.0))
    chimney_top = ridge + CHIMNEY_RISE
    scale = _fit_scale(base_z, max(chimney_top, ridge + ROOF_THICKNESS))
    placement = _placement(x, y, base_z, rotation, scale)
    add_gable_block(builder, placement, length, width, wall, ridge, wall_color, roof_color,
                    rng.choice((palette.SHADE_BASE, palette.SHADE_BASE, palette.SHADE_LIGHT)))

    chimney_y = width * 0.22
    chimney_base = wall + (ridge - wall) * (1.0 - chimney_y / (width * 0.5)) - 0.1
    chimney = box(CHIMNEY_SIZE, CHIMNEY_SIZE, chimney_top - chimney_base)
    builder.add_part(chimney, placement @ Matrix.Translation((chimney_x, chimney_y, chimney_base)), MATERIAL,
                     _flat("Brick", palette.SHADE_BASE))

    half_w, half_l = width * 0.5, length * 0.5
    front = (-half_w - FACADE_OFFSET)
    door_x = -half_l * 0.35
    facade_quad(builder, placement, (door_x, front, DOOR_HEIGHT * 0.5), (1, 0, 0), (0, 0, 1),
                DOOR_HALF_WIDTH, DOOR_HEIGHT * 0.5, "Wood", palette.SHADE_DARK)
    window_z = min(wall - 0.45, 1.05)
    facade_quad(builder, placement, (half_l * 0.4, front, window_z), (1, 0, 0), (0, 0, 1),
                WINDOW_HALF_SIZE, WINDOW_HALF_SIZE, *WINDOW_GLOW)
    facade_quad(builder, placement, (0.0, half_w + FACADE_OFFSET, window_z), (-1, 0, 0), (0, 0, 1),
                WINDOW_HALF_SIZE, WINDOW_HALF_SIZE, *WINDOW_GLOW)
    gable_z = wall + (ridge - wall) * 0.3 if style == "tall" else window_z
    facade_quad(builder, placement, (half_l + FACADE_OFFSET, 0.0, gable_z), (0, 1, 0), (0, 0, 1),
                WINDOW_HALF_SIZE, WINDOW_HALF_SIZE, *WINDOW_GLOW)
    return math.hypot(half_l + ROOF_END_OVERHANG, half_w + ROOF_OVERHANG) * scale


def add_chapel(builder, rng, x, y, base_z, rotation):
    """Adds a small stone chapel with an apse and no steeple; the door gable faces local +X."""
    scale = _fit_scale(base_z, CHAPEL_RIDGE + ROOF_THICKNESS)
    placement = _placement(x, y, base_z, rotation, scale)
    add_gable_block(builder, placement, CHAPEL_LENGTH, CHAPEL_WIDTH, CHAPEL_WALL, CHAPEL_RIDGE, "WallCream",
                    "Slate", palette.SHADE_LIGHT)
    apse = placement @ Matrix.Translation((-CHAPEL_LENGTH * 0.5 - CHAPEL_APSE_LENGTH * 0.5 + 0.2, 0.0, 0.0))
    add_gable_block(builder, apse, CHAPEL_APSE_LENGTH, CHAPEL_APSE_WIDTH, CHAPEL_APSE_WALL, CHAPEL_APSE_RIDGE,
                    "Stone", "Slate", palette.SHADE_LIGHT)

    half_w, half_l = CHAPEL_WIDTH * 0.5, CHAPEL_LENGTH * 0.5
    gable = half_l + FACADE_OFFSET
    facade_quad(builder, placement, (gable, 0.0, 0.6), (0, 1, 0), (0, 0, 1), 0.38, 0.6, "Wood", palette.SHADE_DARK)
    facade_quad(builder, placement, (gable, 0.0, CHAPEL_WALL + 0.2), (0, 1, 0), (0, 0, 1),
                CHAPEL_ROSE_HALF_SIZE, CHAPEL_ROSE_HALF_SIZE, *WINDOW_GLOW)
    cross_z = CHAPEL_WALL + 0.73
    facade_quad(builder, placement, (gable + FACADE_OFFSET, 0.0, cross_z), (0, 1, 0), (0, 0, 1),
                CHAPEL_CROSS_HALF_WIDTH, CHAPEL_CROSS_HALF_HEIGHT, "HarvestGold", palette.SHADE_BASE)
    facade_quad(builder, placement, (gable + FACADE_OFFSET, 0.0, cross_z + CHAPEL_CROSS_HALF_HEIGHT * 0.35),
                (0, 1, 0), (0, 0, 1), CHAPEL_CROSS_ARM, CHAPEL_CROSS_HALF_WIDTH, "HarvestGold", palette.SHADE_BASE)
    for along in (-half_l * 0.5, half_l * 0.25):
        facade_quad(builder, placement, (along, -half_w - FACADE_OFFSET, 1.05), (1, 0, 0), (0, 0, 1),
                    CHAPEL_WINDOW_HALF_WIDTH, CHAPEL_WINDOW_HALF_HEIGHT, *WINDOW_GLOW)
        facade_quad(builder, placement, (along, half_w + FACADE_OFFSET, 1.05), (-1, 0, 0), (0, 0, 1),
                    CHAPEL_WINDOW_HALF_WIDTH, CHAPEL_WINDOW_HALF_HEIGHT, *WINDOW_GLOW)
    return math.hypot(half_l + CHAPEL_APSE_LENGTH, half_w + ROOF_OVERHANG) * scale


def add_lodge(builder, rng, x, y, base_z, rotation):
    """Adds the Goosebay lodge: log cabin, green roof, stone chimney and a covered front porch (local -Y)."""
    scale = _fit_scale(base_z, LODGE_CHIMNEY_TOP)
    placement = _placement(x, y, base_z, rotation, scale)
    half_w, half_l = LODGE_WIDTH * 0.5, LODGE_LENGTH * 0.5
    add_gable_block(builder, placement, LODGE_LENGTH, LODGE_WIDTH, LODGE_WALL, LODGE_RIDGE, "Wood", "Pine",
                    palette.SHADE_BASE)
    for cx in (-half_l, half_l):
        for cy in (-half_w, half_w):
            corner = box(LODGE_CORNER_SIZE, LODGE_CORNER_SIZE, LODGE_WALL + WALL_SINK)
            builder.add_part(corner, placement @ Matrix.Translation((cx, cy, -WALL_SINK)), MATERIAL,
                             _flat("Wood", palette.SHADE_DARK))

    chimney = box(LODGE_CHIMNEY_DEPTH, LODGE_CHIMNEY_WIDTH, LODGE_CHIMNEY_TOP + WALL_SINK)
    builder.add_part(chimney, placement @ Matrix.Translation((half_l + LODGE_CHIMNEY_DEPTH * 0.5 + 0.05,
                                                              half_w * 0.25, -WALL_SINK)),
                     MATERIAL, lambda face, centroid: palette.flat_uv("Stone", palette.SHADE_DARK if face % 2
                                                                      else palette.SHADE_BASE))

    porch_y = -half_w - LODGE_PORCH_DEPTH * 0.5
    porch = box(LODGE_LENGTH * 0.8, LODGE_PORCH_DEPTH, LODGE_PORCH_HEIGHT + WALL_SINK)
    builder.add_part(porch, placement @ Matrix.Translation((0.0, porch_y, -WALL_SINK)), MATERIAL,
                     _flat("Wood", palette.SHADE_LIGHT))
    porch_half = LODGE_LENGTH * 0.42
    edge_y = -half_w - LODGE_PORCH_DEPTH - 0.1
    porch_roof = extrude_yz([(edge_y, LODGE_PORCH_EDGE_HEIGHT), (-half_w, LODGE_WALL - 0.05),
                             (-half_w, LODGE_WALL + 0.07), (edge_y, LODGE_PORCH_EDGE_HEIGHT + 0.12)],
                            -porch_half, porch_half)
    builder.add_part(porch_roof, placement, MATERIAL,
                     lambda face, centroid: palette.flat_uv("Pine", palette.SHADE_LIGHT if face == 1
                                                            else palette.SHADE_DARK))
    for along in (-porch_half + 0.15, 0.0, porch_half - 0.15):
        post = box(LODGE_PORCH_POST_SIZE, LODGE_PORCH_POST_SIZE, LODGE_PORCH_EDGE_HEIGHT)
        builder.add_part(post, placement @ Matrix.Translation((along, edge_y + 0.15, 0.0)), MATERIAL,
                         _flat("Wood", palette.SHADE_DARK))

    front = -half_w - FACADE_OFFSET
    facade_quad(builder, placement, (0.0, front, 0.55 + LODGE_PORCH_HEIGHT * 0.5), (1, 0, 0), (0, 0, 1),
                0.32, 0.55, "Wood", palette.SHADE_EXTRA_DARK)
    for along in (-half_l * 0.55, half_l * 0.55):
        facade_quad(builder, placement, (along, front, 1.1), (1, 0, 0), (0, 0, 1), 0.3, 0.24, *WINDOW_GLOW)
    facade_quad(builder, placement, (0.0, half_w + FACADE_OFFSET, 1.1), (-1, 0, 0), (0, 0, 1), 0.3, 0.24,
                *WINDOW_GLOW)
    facade_quad(builder, placement, (-half_l - FACADE_OFFSET, 0.0, LODGE_WALL + 0.35), (0, -1, 0), (0, 0, 1),
                0.25, 0.25, *WINDOW_GLOW)
    return math.hypot(half_l + 0.6, half_w + LODGE_PORCH_DEPTH) * scale


def add_fence(builder, points, height_function, color_name="Wood"):
    """Adds a post-and-two-rail fence along a polyline of (x, y) points."""
    tops = []
    for x, y in points:
        base = height_function(x, y)
        post = box(FENCE_POST_SIZE, FENCE_POST_SIZE, FENCE_POST_HEIGHT + FENCE_POST_SINK)
        builder.add_part(post, Matrix.Translation((x, y, base - FENCE_POST_SINK)), MATERIAL,
                         _flat(color_name, palette.SHADE_DARK))
        tops.append((x, y, base))
    for (ax, ay, az), (bx, by, bz) in zip(tops, tops[1:]):
        for rail_height in FENCE_RAIL_HEIGHTS:
            add_beam(builder, Matrix.Identity(4), (ax, ay, az + rail_height), (bx, by, bz + rail_height),
                     FENCE_RAIL_SIZE, color_name, palette.SHADE_LIGHT)


def _resample(points, step):
    result = [Vector((points[0][0], points[0][1], 0.0))]
    for a, b in zip(points, points[1:]):
        a, b = Vector((a[0], a[1], 0.0)), Vector((b[0], b[1], 0.0))
        count = max(1, math.ceil((b - a).length / step))
        for k in range(1, count + 1):
            result.append(a.lerp(b, k / count))
    return result


def add_path(builder, points, half_width, height_function, lift, color=("Soil", palette.SHADE_LIGHT), closed=False):
    """Adds a flat dirt-path ribbon draped over the ground along a polyline (tapered ends unless closed)."""
    if closed:
        points = list(points) + [points[0]]
    samples = _resample(points, PATH_STEP)
    if closed:
        samples = samples[:-1]
    count = len(samples)
    vertices = []
    for k, point in enumerate(samples):
        if closed:
            before, after = samples[(k - 1) % count], samples[(k + 1) % count]
        else:
            before, after = samples[max(0, k - 1)], samples[min(count - 1, k + 1)]
        forward = (after - before).normalized()
        left = Vector((-forward.y, forward.x, 0.0))
        taper = PATH_END_TAPER if not closed and k in (0, count - 1) else 1.0
        for side in (-1.0, 1.0):
            p = point + left * (side * half_width * taper)
            vertices.append((p.x, p.y, height_function(p.x, p.y) + lift))
    segments = count if closed else count - 1
    faces = [(2 * k, 2 * ((k + 1) % count), 2 * ((k + 1) % count) + 1, 2 * k + 1) for k in range(segments)]
    builder.add_part(shapes.Part(vertices, faces), Matrix.Identity(4), MATERIAL, _flat(*color))


def add_paving(builder, rng, x, y, radius, height_function, lift, sides=10):
    """Adds a flat, slightly irregular stone-paved square with a darker kerb ring."""
    inner, outer = [], []
    for k in range(sides):
        angle = 2.0 * math.pi * k / sides
        r = radius * (1.0 + rng.uniform(-PAVING_WOBBLE, PAVING_WOBBLE))
        for ring, scale in ((inner, 1.0 - PAVING_KERB_FRACTION), (outer, 1.0)):
            px, py = x + r * scale * math.cos(angle), y + r * scale * math.sin(angle)
            ring.append((px, py, height_function(px, py) + lift))
    builder.add_part(shapes.disc(inner), Matrix.Identity(4), MATERIAL, _flat("Stone", palette.SHADE_LIGHT))
    vertices = inner + outer
    faces = [(k, sides + k, sides + (k + 1) % sides, (k + 1) % sides) for k in range(sides)]
    builder.add_part(shapes.Part(vertices, faces), Matrix.Identity(4), MATERIAL, _flat("Stone", palette.SHADE_BASE))
