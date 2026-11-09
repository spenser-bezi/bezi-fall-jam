"""Shared settlement-tile helpers: house rings around a center, internal dirt paths, gardens and greenery.

Paths only connect doors to an internal hub (green, square or lane), so nothing ends at the rim and the tile
reads correctly at all 6 rotations.
"""
import math

from mathutils import Vector

from lib import edge_sockets, hexgrid
from lib.scatter import scatter_points
from props import buildings, kit
from tiles import common, water_common

GROUND_AMPLITUDE = 0.035
PATH_HALF_WIDTH = 0.5
PATH_LIFT = 0.05
PATH_LIFT_STEP = 0.004
PATH_BEND = 0.6
DOOR_STEP_OUT = 0.45
HOUSE_MIN_INSET = 0.6
TREE_MIN_RADIUS = 0.8
TREE_MAX_RADIUS = 1.05
TREE_SPACING = 2.3
TREE_COLORS = ("MapleRed", "Mustard", "Pumpkin")
BUILDING_CLEARANCE = 0.5
PATH_CLEARANCE = 0.9
BUSH_MIN_RADIUS = 0.38
BUSH_MAX_RADIUS = 0.55
BUSH_MIN_INSET = 0.9
BUSH_SPACING = 1.3
SCATTER_ATTEMPTS = 4000
FENCE_POST_SPACING = 1.5
STEEPLE_SOCKET_NAME = "SOCKET_Prop_Steeple_01"


def settlement_height(seed):
    """Nearly flat rolling ground so houses and paths sit cleanly."""
    return common.gentle_height(seed, amplitude=GROUND_AMPLITUDE)


def facing_rotation(position, target):
    """Rotation that turns a building's front (local -Y) toward target."""
    direction = planar(target) - planar(position)
    angle = math.atan2(direction.y, direction.x)
    return angle + math.pi * 0.5


def local_to_world(position, rotation, local):
    """Transforms a planar local offset by a building placement."""
    cos_r, sin_r = math.cos(rotation), math.sin(rotation)
    return Vector((position[0] + local[0] * cos_r - local[1] * sin_r,
                   position[1] + local[0] * sin_r + local[1] * cos_r, 0.0))


def house_door_point(position, rotation, style):
    """World point just outside a house's door (where its path starts)."""
    dims = buildings.HOUSE_STYLES[style]
    door_x = -dims["length"] * 0.5 * 0.35
    return local_to_world(position, rotation, (door_x, -dims["width"] * 0.5 - DOOR_STEP_OUT))


def planar(point):
    """Returns a z = 0 Vector from any 2D/3D point-like value."""
    return Vector((point[0], point[1], 0.0))


def curved_path(start, end, bend):
    """Three-point path from start to end, bowed sideways by bend metres."""
    start, end = planar(start), planar(end)
    middle = (start + end) * 0.5
    direction = (end - start).normalized()
    middle += Vector((-direction.y, direction.x, 0.0)) * bend
    return [tuple(start.xy), tuple(middle.xy), tuple(end.xy)]


def distance_to_polyline(x, y, points):
    """Planar distance from (x, y) to a polyline of (x, y) points."""
    point = Vector((x, y, 0.0))
    best = float("inf")
    for a, b in zip(points, points[1:]):
        a, b = Vector((a[0], a[1], 0.0)), Vector((b[0], b[1], 0.0))
        segment = b - a
        u = 0.0 if segment.length_squared == 0.0 else max(0.0, min(1.0, (point - a).dot(segment) / segment.length_squared))
        best = min(best, (point - (a + segment * u)).length)
    return best


class Settlement:
    """Collects building footprints and paths so greenery can avoid them."""

    def __init__(self, height):
        self.height = height
        self.footprints = []  # (x, y, radius)
        self.paths = []

    def add_house(self, builder, rng, position, rotation, roof, style):
        """Adds a house and records its footprint."""
        radius = buildings.add_house(builder, rng, position[0], position[1], self.height(*position), rotation, roof,
                                     style)
        self.footprints.append((position[0], position[1], radius))

    def add_footprint(self, position, radius):
        """Records an extra occupied disc (chapel, lodge, square...)."""
        self.footprints.append((position[0], position[1], radius))

    def add_path(self, builder, points, half_width=PATH_HALF_WIDTH, closed=False):
        """Adds a dirt path ribbon and records it."""
        lift = PATH_LIFT + PATH_LIFT_STEP * len(self.paths)
        buildings.add_path(builder, points, half_width, self.height, lift, closed=closed)
        self.paths.append(list(points) + ([points[0]] if closed else []))

    def overlaps(self, position, radius):
        """True if a disc overlaps any recorded footprint."""
        return any(math.hypot(position[0] - fx, position[1] - fy) < radius + r for fx, fy, r in self.footprints)

    def is_free(self, x, y, clearance):
        """True if (x, y) keeps clearance from every footprint and path."""
        if any(math.hypot(x - fx, y - fy) < radius + clearance for fx, fy, radius in self.footprints):
            return False
        return all(distance_to_polyline(x, y, path) >= PATH_CLEARANCE + clearance * 0.5 for path in self.paths)

    def add_trees(self, builder, rng, count, extra_ok=None):
        """Scatters autumn deciduous trees on free land, respecting the rim rules."""
        trees = []
        for _ in range(SCATTER_ATTEMPTS):
            if len(trees) >= count:
                break
            radius = rng.uniform(TREE_MIN_RADIUS, TREE_MAX_RADIUS)
            x, y = rng.uniform(-hexgrid.TILE_RADIUS, hexgrid.TILE_RADIUS), rng.uniform(-hexgrid.TILE_RADIUS,
                                                                                       hexgrid.TILE_RADIUS)
            if not water_common.tree_clear_of_rim(x, y, kit.tree_max_canopy_radius(radius)):
                continue
            if not self.is_free(x, y, radius * 0.6 + BUILDING_CLEARANCE):
                continue
            if extra_ok is not None and not extra_ok(x, y):
                continue
            if any(math.hypot(x - tx, y - ty) < TREE_SPACING for tx, ty, _ in trees):
                continue
            trees.append((x, y, radius))
        for index, (x, y, radius) in enumerate(trees):
            kit.add_deciduous_tree(builder, rng, x, y, self.height(x, y), radius, TREE_COLORS[index % len(TREE_COLORS)])
            self.footprints.append((x, y, radius * 0.5))
        return trees

    def add_bushes(self, builder, rng, count, extra_ok=None):
        """Scatters hedge bushes on free land."""
        points = scatter_points(rng, count, hexgrid.TILE_RADIUS, BUSH_SPACING,
                                lambda x, y: (hexgrid.inset_distance(x, y) >= BUSH_MIN_INSET
                                              and self.is_free(x, y, 0.3)
                                              and (extra_ok is None or extra_ok(x, y))))
        for x, y in points:
            kit.add_bush(builder, rng, x, y, self.height(x, y), rng.uniform(BUSH_MIN_RADIUS, BUSH_MAX_RADIUS))
            self.footprints.append((x, y, BUSH_MAX_RADIUS))
        return points

    def add_garden_fence(self, builder, center, rotation, width, depth, gap_side=True):
        """Adds an open-fronted rectangular garden fence (three sides) around a local rectangle."""
        half_w, half_d = width * 0.5, depth * 0.5
        corners = [(-half_w, -half_d), (-half_w, half_d), (half_w, half_d), (half_w, -half_d)]
        if not gap_side:
            corners.append(corners[0])
        points = []
        for (ax, ay), (bx, by) in zip(corners, corners[1:]):
            count = max(1, round(math.hypot(bx - ax, by - ay) / FENCE_POST_SPACING))
            for k in range(count):
                points.append((ax + (bx - ax) * k / count, ay + (by - ay) * k / count))
        points.append(corners[-1])
        world = [tuple(local_to_world(center, rotation, p).xy) for p in points]
        buildings.add_fence(builder, world, self.height)
        self.footprints.append((center[0], center[1], math.hypot(half_w, half_d) * 0.8))


def ring_positions(center, radius, count, start_angle, rng, angle_jitter=0.25, radius_jitter=0.35):
    """Evenly spread (jittered) positions around a hub."""
    positions = []
    for k in range(count):
        angle = start_angle + 2.0 * math.pi * k / count + rng.uniform(-angle_jitter, angle_jitter)
        distance = radius + rng.uniform(-radius_jitter, radius_jitter)
        positions.append((center[0] + distance * math.cos(angle), center[1] + distance * math.sin(angle)))
    return positions


def fits_on_tile(position, radius):
    """True if a footprint disc stays clear of the rim."""
    return hexgrid.inset_distance(*position) >= radius + HOUSE_MIN_INSET


def add_steeple_socket(obj, position, height):
    """Adds the SOCKET_Prop_Steeple_01 empty where the steeple obstacle spawns."""
    edge_sockets.add_socket_empty(obj, STEEPLE_SOCKET_NAME, (position[0], position[1], height(*position)))
