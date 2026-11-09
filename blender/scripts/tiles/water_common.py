"""Shared water-tile helpers: organic pond/lake shapes (M_Water fan + shore foam ring) and water snack sockets.

Water follows Art Workflow 4.4 and the approved seam-test technique: a flat M_Water surface at the standard
level, the bed and shore slope in the palette ground mesh beneath it, and a flat ShoreFoam ring at the bank.
"""
import math

import bpy
from mathutils import Matrix, Vector

from lib import edge_sockets, hexgrid, materials, palette, shapes
from lib.builder import MeshBuilder
from lib.scatter import Noise2D

WATER_LEVEL = edge_sockets.WATER_LEVEL
FOAM_LEVEL = edge_sockets.FOAM_LEVEL
FOAM_WIDTH = 0.75
SUBMERGED_MARGIN = 0.02
OUTLINE_POINTS = 28
DEFAULT_WOBBLE = 0.16
DEFAULT_WOBBLE_FREQUENCY = 1.3
DEFAULT_DEPTH = 0.8
DEFAULT_SLOPE_WIDTH = 1.0
DEFAULT_MIN_INSET = 2.2
ISLAND_FOAM_WIDTH = 0.35
SNACK_HOVER_HEIGHT = 1.0
SNACK_SOCKET_PREFIX = "SOCKET_Snack_Water_"
POND_SNAP_THRESHOLD = 0.42
MAX_UNFOLD_PASSES = 4


def max_radius_in_hex(center, angle, min_inset):
    """Largest distance along a ray from center that stays at least min_inset inside the hex rim."""
    direction = Vector((math.cos(angle), math.sin(angle), 0.0))
    limit = float("inf")
    for normal_angle in hexgrid.SIDE_NORMAL_ANGLES:
        normal = Vector((math.cos(normal_angle), math.sin(normal_angle), 0.0))
        facing = direction.dot(normal)
        if facing > 1e-6:
            limit = min(limit, (hexgrid.APOTHEM - min_inset - center.dot(normal)) / facing)
    return limit


class PondShape:
    """A wobbly polar water body: depth profile, contour snapping, water fan and foam ring."""

    def __init__(self, center, base_radius, seed, wobble=DEFAULT_WOBBLE, wobble_frequency=DEFAULT_WOBBLE_FREQUENCY,
                 depth=DEFAULT_DEPTH, slope_width=DEFAULT_SLOPE_WIDTH, min_inset=DEFAULT_MIN_INSET, stretch=None):
        self.center = Vector((center[0], center[1], 0.0))
        self.base_radius = base_radius
        self.noise = Noise2D(seed)
        self.wobble = wobble
        self.wobble_frequency = wobble_frequency
        self.depth = depth
        self.slope_width = slope_width
        self.min_inset = min_inset
        self.stretch = stretch  # optional (angle, factor): elongates the pond along an axis

    def radius(self, angle):
        """Bank-top radius in a direction, clamped to keep the grass rim."""
        radius = self.base_radius * (1.0 + self.wobble * self.noise.sample(
            math.cos(angle) * self.wobble_frequency, math.sin(angle) * self.wobble_frequency))
        if self.stretch is not None:
            axis_angle, factor = self.stretch
            radius *= 1.0 + (factor - 1.0) * math.cos(angle - axis_angle) ** 2
        return min(radius, max_radius_in_hex(self.center, angle, self.min_inset))

    def polar(self, x, y):
        """Returns (distance, angle) of a point from the pond center."""
        dx, dy = x - self.center.x, y - self.center.y
        return math.hypot(dx, dy), math.atan2(dy, dx)

    def inset(self, x, y):
        """Signed distance inside the bank top (positive inside the water body)."""
        distance, angle = self.polar(x, y)
        return self.radius(angle) - distance

    def ground_depth(self, x, y):
        """Ground height inside the pond (<= 0), or None outside the bank top."""
        inside = self.inset(x, y)
        if inside <= 0.0:
            return None
        return -self.depth * min(1.0, inside / self.slope_width)

    def snap(self, position):
        """Snaps lattice verts near the bank top onto it."""
        return hexgrid.snap_to_polar_contour(position, self.center, self.radius, POND_SNAP_THRESHOLD)

    def point(self, angle, radius_offset=0.0, z=0.0):
        """Point on the bank contour (optionally offset inward by -radius_offset)."""
        radius = self.radius(angle) + radius_offset
        return Vector((self.center.x + radius * math.cos(angle), self.center.y + radius * math.sin(angle), z))

    def add_water(self, builder, notch=None):
        """Adds the M_Water fan. notch=(angle_from, angle_to, [replacement points CCW]) opens a river mouth."""
        outline = []
        for k in range(OUTLINE_POINTS):
            angle = 2.0 * math.pi * k / OUTLINE_POINTS
            if notch is not None and self._in_notch(angle, notch):
                continue
            outline.append((angle, self.point(angle, z=WATER_LEVEL)))
        if notch is not None:
            for point in notch[2]:
                outline.append((math.atan2(point.y - self.center.y, point.x - self.center.x), point))
        outline.sort(key=lambda item: item[0] % (2.0 * math.pi))
        points = [self.center + Vector((0.0, 0.0, WATER_LEVEL))] + [p for _, p in outline]
        faces = [(0, 1 + k, 1 + (k + 1) % len(outline)) for k in range(len(outline))]
        builder.add_part(shapes.Part(points, faces), Matrix.Identity(4), materials.WATER_MATERIAL,
                         lambda face, centroid: palette.flat_uv("LakeTeal"))

    @staticmethod
    def _in_notch(angle, notch):
        start, end = notch[0], notch[1]
        span = (end - start) % (2.0 * math.pi)
        return (angle - start) % (2.0 * math.pi) < span

    def add_foam(self, builder, gap=None):
        """Adds the flat shore-foam ring just inside the bank. gap=(angle_from, angle_to) leaves a mouth open."""
        vertices, faces = [], []
        for k in range(OUTLINE_POINTS):
            angle = 2.0 * math.pi * k / OUTLINE_POINTS
            vertices.append(self.point(angle, -FOAM_WIDTH, FOAM_LEVEL))
            vertices.append(self.point(angle, 0.0, FOAM_LEVEL))
        for k in range(OUTLINE_POINTS):
            mid = 2.0 * math.pi * (k + 0.5) / OUTLINE_POINTS
            if gap is not None and self._in_notch(mid, gap):
                continue
            n = (k + 1) % OUTLINE_POINTS
            faces.append((2 * k, 2 * k + 1, 2 * n + 1, 2 * n))
        used = sorted({index for face in faces for index in face})
        remap = {old: new for new, old in enumerate(used)}
        part = shapes.Part([vertices[i] for i in used], [tuple(remap[i] for i in face) for face in faces])
        builder.add_part(part, Matrix.Identity(4), materials.PALETTE_MATERIAL,
                         lambda face, centroid: palette.flat_uv("ShoreFoam"))


def _signed_area_xy(builder, face):
    a, b, c = (builder.vertices[i] for i in face[:3])
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)


def _paint_submerged(builder, ground_faces):
    """Gives every ground triangle that lies entirely below the water surface the bed color.

    Faces that break the surface keep their land color, so no dark bed triangles poke out along the banks.
    Purely geometric, so socket edge bands (identical geometry) get identical colors on every tile.
    """
    material, uv = edge_sockets.bed_style()
    material_index = builder.material_index(material)
    for face_index in range(ground_faces):
        indices, _, _ = builder.faces[face_index]
        if len(indices) != 3:
            continue
        if max(builder.vertices[i].z for i in indices) < WATER_LEVEL - SUBMERGED_MARGIN:
            builder.faces[face_index] = (indices, material_index, [tuple(uv)] * 3)


def assemble_tile(spec, rng, face_style, height_function, decorate=None, snap_function=None, socket_sides=()):
    """Builds ground (standard or socket-aware) + decoration into one object, like tiles.common.assemble_tile.

    Contour snapping can occasionally fold a lattice triangle over; any snapped vertex of a folded ground triangle
    is moved back to its unsnapped (jittered) position, so every ground face points up.
    """
    builder = MeshBuilder()
    unsnapped = {}

    def recording_snap(position):
        original = position.copy()
        snapped = snap_function(position) if snap_function is not None else position
        if (snapped.xy - original.xy).length > 0.0:
            unsnapped[len(builder.vertices)] = original
        return snapped

    edge_sockets.build_socket_ground(builder, rng, face_style, height_function, socket_sides, recording_snap)
    ground_faces = len(builder.faces)
    for _ in range(MAX_UNFOLD_PASSES):
        folded = [face for face, _, _ in builder.faces[:ground_faces]
                  if len(face) == 3 and _signed_area_xy(builder, face) <= 0.0]
        reverted = {index for face in folded for index in face if index in unsnapped}
        if not reverted:
            break
        for index in reverted:
            original = unsnapped.pop(index)
            builder.vertices[index] = Vector((original.x, original.y, height_function(original.x, original.y)))
    _paint_submerged(builder, ground_faces)
    if decorate is not None:
        decorate(builder)
    collection = bpy.data.collections.new(spec.mesh_name)
    bpy.context.scene.collection.children.link(collection)
    return builder.build_object(spec.mesh_name, collection)


def add_island_foam(builder, center, radius_function, width=ISLAND_FOAM_WIDTH, segments=OUTLINE_POINTS // 2):
    """Adds a foam ring just outside an island contour."""
    vertices, faces = [], []
    for k in range(segments):
        angle = 2.0 * math.pi * k / segments
        for offset in (0.0, width):
            radius = radius_function(angle) + offset
            vertices.append((center.x + radius * math.cos(angle), center.y + radius * math.sin(angle), FOAM_LEVEL))
    for k in range(segments):
        n = (k + 1) % segments
        faces.append((2 * k, 2 * k + 1, 2 * n + 1, 2 * n))
    builder.add_part(shapes.Part(vertices, faces), Matrix.Identity(4), materials.PALETTE_MATERIAL,
                     lambda face, centroid: palette.flat_uv("ShoreFoam"))


def add_water_snack_sockets(obj, points):
    """Adds SOCKET_Snack_Water_01.. empties hovering over the water at the given (x, y) points."""
    for index, (x, y) in enumerate(points, start=1):
        edge_sockets.add_socket_empty(obj, f"{SNACK_SOCKET_PREFIX}{index:02d}",
                                      (x, y, WATER_LEVEL + SNACK_HOVER_HEIGHT))


def tree_clear_of_rim(x, y, canopy_radius, min_trunk_inset=0.8):
    """True if a tree trunk/canopy at (x, y) respects the rim inset and canopy overhang limits."""
    return hexgrid.inset_distance(x, y) >= max(min_trunk_inset, canopy_radius - hexgrid.MAX_CANOPY_OVERHANG)
