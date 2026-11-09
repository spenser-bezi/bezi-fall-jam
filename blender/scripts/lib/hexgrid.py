"""Hex tile standard: flat-top hex math and the shared base ground (rim, edge band, skirt).

Blender space: Z up, corners on +/-X. Unity mapping (to confirm with the orientation test):
Blender (x, y) -> Unity (-x, -y), so Unity +Z (flight direction, side 0) is Blender -Y.
Side indices run clockwise seen from above: 0 = Unity +Z, 1 = NE, 2 = SE, 3 = -Z, 4 = SW, 5 = NW.
"""
import math

from mathutils import Vector

from . import materials, palette
from .scatter import Noise2D

SQRT3 = math.sqrt(3.0)
TILE_RADIUS = 10.0
APOTHEM = TILE_RADIUS * SQRT3 * 0.5
SUBDIVISIONS = 8
LATTICE_SPACING = TILE_RADIUS / SUBDIVISIONS
SKIRT_DEPTH = 2.0
EDGE_BAND_RINGS = 1
DEFAULT_JITTER_FRACTION = 0.28
SIDE0_ANGLE_DEG = 270.0
SIDE_COUNT = 6
MAX_CANOPY_OVERHANG = 0.6
MAX_DECOR_HEIGHT = 3.5
SNAP_THRESHOLD = 0.4 * TILE_RADIUS / SUBDIVISIONS
GRASS_NOISE_SEED_OFFSET = 7
GRASS_PATCH_FREQUENCY = 0.16
GRASS_LIGHT_THRESHOLD = 0.22
GRASS_DARK_THRESHOLD = -0.26
GRASS_FADE_START = 1.2
GRASS_FADE_END = 3.0
SIDE_NORMAL_ANGLES = [math.radians(30.0 + 60.0 * k) for k in range(SIDE_COUNT)]


def lattice_position(i, j, spacing=LATTICE_SPACING):
    """Returns the planar position of triangular-lattice point (i, j)."""
    return Vector((spacing * (i + j * 0.5), spacing * (j * SQRT3 * 0.5), 0.0))


def lattice_ring(i, j):
    """Returns the hex ring (0 = center, SUBDIVISIONS = rim) of a lattice point."""
    return max(abs(i), abs(j), abs(i + j))


def inset_distance(x, y):
    """Perpendicular distance from (x, y) to the hex rim; positive inside, negative outside."""
    return APOTHEM - max(x * math.cos(a) + y * math.sin(a) for a in SIDE_NORMAL_ANGLES)


def side_angle(side):
    """Blender-space angle (radians) of the outward normal of a side index."""
    return math.radians(SIDE0_ANGLE_DEG - 60.0 * side)


def side_midpoint(side):
    """Blender-space midpoint of a side on the rim."""
    angle = side_angle(side)
    return Vector((APOTHEM * math.cos(angle), APOTHEM * math.sin(angle), 0.0))


def neighbor_center(side):
    """Blender-space center of the neighboring tile across a side."""
    return side_midpoint(side) * 2.0


def axial_center(q, r):
    """Blender-space center of the flat-top tile at axial coordinate (q, r)."""
    return Vector((1.5 * TILE_RADIUS * q, SQRT3 * TILE_RADIUS * (r + q * 0.5), 0.0))


def corner(index):
    """Blender-space corner of the hex (corner 0 on +X, counter-clockwise)."""
    angle = math.radians(60.0 * index)
    return Vector((TILE_RADIUS * math.cos(angle), TILE_RADIUS * math.sin(angle), 0.0))


def rim_style():
    """Edge band color: plain Moss on every land tile so any two tiles meet on identical grass."""
    return materials.PALETTE_MATERIAL, palette.flat_uv("Moss", palette.SHADE_BASE)


class GrassPainter:
    """Low-frequency grass patches that fade to plain Moss toward the rim (keeps seams invisible)."""

    def __init__(self, seed):
        self.noise = Noise2D(seed + GRASS_NOISE_SEED_OFFSET)

    def style(self, centroid, rng=None):
        """Returns (material, uv) for a grass face at centroid."""
        inset = inset_distance(centroid.x, centroid.y)
        fade = min(1.0, max(0.0, (inset - GRASS_FADE_START) / (GRASS_FADE_END - GRASS_FADE_START)))
        value = self.noise.sample(centroid.x, centroid.y, GRASS_PATCH_FREQUENCY) * fade
        if value > GRASS_LIGHT_THRESHOLD:
            return materials.PALETTE_MATERIAL, palette.flat_uv("LightMoss", palette.SHADE_BASE)
        if value < GRASS_DARK_THRESHOLD:
            return materials.PALETTE_MATERIAL, palette.flat_uv("Moss", palette.SHADE_DARK)
        return rim_style()


def snap_to_polar_contour(position, center, boundary, threshold=SNAP_THRESHOLD):
    """Moves a vertex onto a closed contour around center if it is within threshold of it."""
    dx, dy = position.x - center.x, position.y - center.y
    distance = math.hypot(dx, dy)
    if distance < 1e-6:
        return position
    angle = math.atan2(dy, dx)
    target = boundary(angle)
    if abs(distance - target) < threshold:
        position.x, position.y = center.x + target * math.cos(angle), center.y + target * math.sin(angle)
    return position


def snap_to_lines(position, direction, spacing, threshold=SNAP_THRESHOLD):
    """Moves a vertex onto the nearest of a family of parallel lines (dot(p, direction) = k * spacing)."""
    projection = position.x * direction.x + position.y * direction.y
    nearest = round(projection / spacing) * spacing
    delta = nearest - projection
    if abs(delta) < threshold:
        position.x += direction.x * delta
        position.y += direction.y * delta
    return position


def build_ground(builder, rng, face_style, height_function, snap_function=None,
                 jitter_fraction=DEFAULT_JITTER_FRACTION):
    """Adds the standard hex ground: jittered interior, flat edge band, identical rim and soil skirt.

    face_style(centroid, rng) -> (material, uv) colors interior faces; edge band faces always use rim_style.
        uv may be a callable(vertex_position) -> uv for per-corner (planar-projected) mapping.
    height_function(x, y) -> z offsets interior vertices; rim and edge band stay at z = 0.
    snap_function(position) -> position optionally snaps interior vertices onto region contours.
    """
    n = SUBDIVISIONS
    interior_max_ring = n - 1 - EDGE_BAND_RINGS
    index = {}
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            ring = lattice_ring(i, j)
            if ring > n:
                continue
            position = lattice_position(i, j)
            if ring <= interior_max_ring:
                position.x += rng.uniform(-1.0, 1.0) * jitter_fraction * LATTICE_SPACING
                position.y += rng.uniform(-1.0, 1.0) * jitter_fraction * LATTICE_SPACING
                if snap_function is not None:
                    position = snap_function(position)
                position.z = height_function(position.x, position.y)
            index[(i, j)] = builder.add_vertex(position, ring=ring)

    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            for triangle in (((i, j), (i + 1, j), (i, j + 1)), ((i + 1, j), (i + 1, j + 1), (i, j + 1))):
                if not all(key in index for key in triangle):
                    continue
                ids = [index[key] for key in triangle]
                touches_rim = any(lattice_ring(*key) == n for key in triangle)
                centroid = sum((builder.vertices[k] for k in ids), Vector((0.0, 0.0, 0.0))) / 3.0
                material, uv = rim_style() if touches_rim else face_style(centroid, rng)
                if callable(uv):
                    uv = [uv(builder.vertices[k]) for k in ids]
                builder.add_face(ids, material, uv)

    rim = [vertex for key, vertex in index.items() if lattice_ring(*key) == n]
    rim.sort(key=lambda v: math.atan2(builder.vertices[v].y, builder.vertices[v].x))
    bottoms = {}
    for vertex in rim:
        top = builder.vertices[vertex]
        bottoms[vertex] = builder.add_vertex((top.x, top.y, -SKIRT_DEPTH), ring=n)
    skirt_top, skirt_bottom = palette.strip_uv("SoilSkirt", 0.0), palette.strip_uv("SoilSkirt", 1.0)
    for k, a in enumerate(rim):
        b = rim[(k + 1) % len(rim)]
        builder.add_face([a, bottoms[a], bottoms[b], b], materials.PALETTE_MATERIAL,
                         [skirt_top, skirt_bottom, skirt_bottom, skirt_top])
