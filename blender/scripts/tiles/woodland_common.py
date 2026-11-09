"""Helpers shared by the woodland tiles (forest, pine forest, orchard, hills).

Covers variant selection, the organic interior content blob, rim-ring and interior tree placement that respects
the trunk inset / canopy overhang rules, triangle budget guarding and socket empties.
"""
import math
import random
from dataclasses import dataclass

import bpy
from mathutils import Vector

from lib import hexgrid
from lib.builder import MeshBuilder
from lib.scatter import Noise2D

SNAP_PROBE_STEPS = 6
SNAP_PROBE_SHRINK = 0.8

VARIANT_A = "A"
VARIANT_B = "B"
TRUNK_MIN_INSET = 0.8
GROUND_TRIANGLES = 6 * hexgrid.SUBDIVISIONS ** 2 + 2 * 6 * hexgrid.SUBDIVISIONS
SOCKET_DISPLAY_SIZE = 0.6
DEFAULT_PLACEMENT_ATTEMPTS = 4000
BLOB_WOBBLE_FREQUENCY = 1.6
BLOB_MIN_INSET = 1.3


def variant_of(spec):
    """Returns 'A' or 'B' from the mesh name suffix (SM_Tile_Forest_B -> 'B')."""
    return VARIANT_B if spec.mesh_name.endswith("_" + VARIANT_B) else VARIANT_A


def smoothstep(edge0, edge1, value):
    """Hermite 0..1 ramp between edge0 and edge1."""
    t = min(1.0, max(0.0, (value - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def rim_fade(x, y, start, end):
    """0 at inset <= start, 1 at inset >= end: keeps interior effects off the edge band."""
    return smoothstep(start, end, hexgrid.inset_distance(x, y))


class ContentBlob:
    """Irregular, roughly round interior region (never a visible hex) with a polar outline for vertex snapping."""

    def __init__(self, seed, radius, wobble, center=(0.0, 0.0), min_inset=BLOB_MIN_INSET):
        self.noise = Noise2D(seed)
        self.radius = radius
        self.wobble = wobble
        self.center = Vector((center[0], center[1], 0.0))
        self.min_inset = min_inset

    def boundary(self, angle):
        """Outline radius at a polar angle around the blob center."""
        return self.radius * (1.0 + self.wobble * self.noise.sample(
            math.cos(angle) * BLOB_WOBBLE_FREQUENCY, math.sin(angle) * BLOB_WOBBLE_FREQUENCY))

    def contains(self, x, y):
        """True inside the outline and away from the rim."""
        dx, dy = x - self.center.x, y - self.center.y
        return (math.hypot(dx, dy) < self.boundary(math.atan2(dy, dx))
                and hexgrid.inset_distance(x, y) > self.min_inset)

    def snap(self, position, threshold=hexgrid.SNAP_THRESHOLD):
        """Snaps a lattice vertex onto the outline when close (smooth low-poly region edges)."""
        return hexgrid.snap_to_polar_contour(position, self.center, self.boundary, threshold)


def _flipped_ground_faces(builder):
    """Counts ground faces whose normal points down (snapping folded a triangle over)."""
    flipped = 0
    for indices, _, _ in builder.faces:
        if len(indices) != 3:
            continue
        a, b, c = (builder.vertices[k] for k in indices)
        if (b - a).cross(c - a).z <= 0.0:
            flipped += 1
    return flipped


def safe_snap(rng, height_function, snap_with_threshold):
    """Returns the snap function with the largest threshold that folds no ground triangle.

    Probes hexgrid.build_ground on a copy of rng's state, so the real build sees the identical jitter.
    snap_with_threshold(position, threshold) -> position.
    """
    threshold = hexgrid.SNAP_THRESHOLD
    for _ in range(SNAP_PROBE_STEPS):
        probe_rng = random.Random()
        probe_rng.setstate(rng.getstate())
        probe = MeshBuilder()

        def candidate(position, limit=threshold):
            return snap_with_threshold(position, limit)

        hexgrid.build_ground(probe, probe_rng, lambda centroid, face_rng: hexgrid.rim_style(), height_function,
                             candidate)
        if _flipped_ground_faces(probe) == 0:
            print(f"[bezi-art]   snap threshold {threshold:.3f} m")
            return candidate
        threshold *= SNAP_PROBE_SHRINK
    return None


@dataclass
class PlacedTree:
    """A planned tree: position, size parameter, kind and color, plus its planar footprint radius."""
    x: float
    y: float
    size: float
    footprint: float
    kind: str = ""
    color: str = ""


def perimeter_point(inset, t):
    """Point on the hex outline shrunk by inset, parameterized by t in [0, 6) (one unit per side)."""
    inner_radius = (hexgrid.APOTHEM - inset) * 2.0 / hexgrid.SQRT3
    side = int(math.floor(t)) % hexgrid.SIDE_COUNT
    fraction = t - math.floor(t)
    a = hexgrid.corner(side) * (inner_radius / hexgrid.TILE_RADIUS)
    b = hexgrid.corner((side + 1) % hexgrid.SIDE_COUNT) * (inner_radius / hexgrid.TILE_RADIUS)
    return a.x + (b.x - a.x) * fraction, a.y + (b.y - a.y) * fraction


def max_size_for_inset(inset, footprint_of_size, size):
    """Shrinks size until the footprint overhang beyond the rim stays within the limit at this inset."""
    while footprint_of_size(size) - inset > hexgrid.MAX_CANOPY_OVERHANG and size > 0.05:
        size *= 0.95
    return size


def place_rim_ring(rng, count, inset_range, along_jitter, size_range, footprint_of_size):
    """Evenly spaces trees around the rim (seam-closing canopies) with jitter, respecting overhang rules.

    footprint_of_size(size) -> planar canopy radius. Returns a list of PlacedTree.
    """
    phase = rng.uniform(0.0, hexgrid.SIDE_COUNT)
    trees = []
    for k in range(count):
        t = (phase + hexgrid.SIDE_COUNT * (k + rng.uniform(-along_jitter, along_jitter)) / count) % hexgrid.SIDE_COUNT
        inset = max(TRUNK_MIN_INSET, rng.uniform(*inset_range))
        x, y = perimeter_point(inset, t)
        actual_inset = hexgrid.inset_distance(x, y)
        size = max_size_for_inset(actual_inset, footprint_of_size, rng.uniform(*size_range))
        trees.append(PlacedTree(x, y, size, footprint_of_size(size)))
    return trees


def place_interior(rng, count, min_inset, size_range, footprint_of_size, spacing_factor, existing,
                   accept=None, attempts=DEFAULT_PLACEMENT_ATTEMPTS):
    """Dart-throws interior trees whose footprints overlap neighbors by at most (1 - spacing_factor).

    accept(x, y) optionally filters candidates. Returns new PlacedTree entries (existing is not modified).
    """
    placed = []
    extent = hexgrid.TILE_RADIUS - min_inset
    for _ in range(attempts):
        if len(placed) >= count:
            break
        x, y = rng.uniform(-extent, extent), rng.uniform(-extent, extent)
        inset = hexgrid.inset_distance(x, y)
        if inset < max(TRUNK_MIN_INSET, min_inset):
            continue
        if accept is not None and not accept(x, y):
            continue
        size = max_size_for_inset(inset, footprint_of_size, rng.uniform(*size_range))
        footprint = footprint_of_size(size)
        if any(math.hypot(x - other.x, y - other.y) < (footprint + other.footprint) * spacing_factor
               for other in list(existing) + placed):
            continue
        placed.append(PlacedTree(x, y, size, footprint))
    return placed


def nearest_tree_distance(trees, x, y):
    """Returns (distance, tree) of the tree trunk nearest to (x, y)."""
    best = min(trees, key=lambda tree: (tree.x - x) ** 2 + (tree.y - y) ** 2)
    return math.hypot(best.x - x, best.y - y), best


def fits_budget(builder, extra_triangles, budget):
    """True if adding extra_triangles keeps the tile under the triangle budget."""
    return builder.triangle_count() + extra_triangles <= budget


def add_socket(tile_object, name, location):
    """Adds a SOCKET_* empty parented to the tile object and linked into the tile's collection."""
    socket = bpy.data.objects.new(name, None)
    socket.empty_display_type = "ARROWS"
    socket.empty_display_size = SOCKET_DISPLAY_SIZE
    socket.location = location
    for collection in tile_object.users_collection:
        collection.objects.link(socket)
    socket.parent = tile_object
    return socket
