"""Edge sockets (Art Workflow 4.3): socket-aware hex ground, the canonical river cross-section and its checks.

Side-local coordinates of a side k: t = signed offset along the side from its midpoint (Blender CCW tangent),
inset = perpendicular distance in from the rim. A river socket is identical on every river side:

    rim (inset 0)        t: -1.5   -0.9   0.0   0.9   1.5      z:  0.0  -0.5  -0.6  -0.5  0.0
    band (inset 1.08)    t: -1.5   -0.9         0.9   1.5      z:  0.0  -0.5        -0.5  0.0
    water (M_Water)      t: +/-1.4 at z = -0.25
    foam (ShoreFoam)     t: +/-1.0 .. +/-1.4 at z = -0.23
    bed faces (|t| < 1.0) DeepWater dark, every other band face plain Moss (same as the standard rim).

The profile is symmetric, so a socket matches any other socket after any 60 degree rotation or mirror.
Outside socket zones the ground is byte-for-byte the standard hexgrid.build_ground layout.
"""
import math

import bpy
from mathutils import Vector

from . import builder as mesh_builder
from . import hexgrid, materials, palette

SOCKET_WIDTH = 3.0
SOCKET_HALF_WIDTH = SOCKET_WIDTH * 0.5
BED_EDGE_HALF_WIDTH = 0.9
BED_EDGE_DEPTH = -0.5
CHANNEL_CENTER_DEPTH = -0.6
WATER_LEVEL = -0.25
FOAM_LEVEL = -0.23
WATER_HALF_WIDTH = 1.4
FOAM_INNER_HALF_WIDTH = 1.0
FOAM_OUTER_HALF_WIDTH = 1.4
CHANNEL_PROFILE = ((0.0, CHANNEL_CENTER_DEPTH), (BED_EDGE_HALF_WIDTH, BED_EDGE_DEPTH), (SOCKET_HALF_WIDTH, 0.0))

RIVER_EDGE_KIND = "River"
EDGE_EMPTY_PREFIX = "EDGE_"
RIVER_MASK_PROPERTY = "edge_river_mask"
EMPTY_DISPLAY_SIZE = 0.5

# Band vertices inside a socket are slid along the side so the rim and the next ring carry the exact profile
# breakpoints (|t| before -> |t| after). Rim verts sit at multiples of the lattice spacing, ring-7 verts halfway.
BAND_LATERAL_REMAP = (
    (1.0 * hexgrid.LATTICE_SPACING, BED_EDGE_HALF_WIDTH),
    (2.0 * hexgrid.LATTICE_SPACING, SOCKET_HALF_WIDTH),
    (0.5 * hexgrid.LATTICE_SPACING, BED_EDGE_HALF_WIDTH),
    (1.5 * hexgrid.LATTICE_SPACING, SOCKET_HALF_WIDTH),
)
SOCKET_ZONE_HALF_WIDTH = 2.6
SOCKET_ZONE_INSET = 1.2
BAND_RING_INSET = hexgrid.APOTHEM / hexgrid.SUBDIVISIONS
MATCH_EPSILON = 1e-3
POSITION_EPSILON = 1e-4
SKIRT_TOP_THRESHOLD = -1.0

CANONICAL_RIM = ((-1.5, 0.0), (-0.9, -0.5), (0.0, -0.6), (0.9, -0.5), (1.5, 0.0))
CANONICAL_BAND = ((-1.5, 0.0), (-0.9, -0.5), (0.9, -0.5), (1.5, 0.0))
CANONICAL_RIM_DECOR = sorted([(-WATER_HALF_WIDTH, WATER_LEVEL), (WATER_HALF_WIDTH, WATER_LEVEL),
                              (-FOAM_INNER_HALF_WIDTH, FOAM_LEVEL), (FOAM_INNER_HALF_WIDTH, FOAM_LEVEL),
                              (-FOAM_OUTER_HALF_WIDTH, FOAM_LEVEL), (FOAM_OUTER_HALF_WIDTH, FOAM_LEVEL)])


def profile_depth(lateral):
    """Channel ground height at a lateral offset from the channel centerline (0 at and beyond the bank top)."""
    lateral = abs(lateral)
    if lateral >= SOCKET_HALF_WIDTH:
        return 0.0
    for (t0, z0), (t1, z1) in zip(CHANNEL_PROFILE, CHANNEL_PROFILE[1:]):
        if lateral <= t1:
            return z0 + (z1 - z0) * (lateral - t0) / (t1 - t0)
    return 0.0


def bed_style():
    """Material and UV of underwater channel/lake bed faces."""
    return materials.PALETTE_MATERIAL, palette.flat_uv("DeepWater", palette.SHADE_DARK)


def side_frame(side):
    """Returns (outward normal, CCW tangent) of a side in Blender space."""
    angle = hexgrid.side_angle(side)
    normal = Vector((math.cos(angle), math.sin(angle), 0.0))
    return normal, Vector((-normal.y, normal.x, 0.0))


def side_local(position, side):
    """Returns (t, inset) of a planar position relative to a side."""
    normal, tangent = side_frame(side)
    return (position.x * tangent.x + position.y * tangent.y,
            hexgrid.APOTHEM - (position.x * normal.x + position.y * normal.y))


def side_point(side, t, inset, z=0.0):
    """Returns the Blender-space point at side-local (t, inset) and height z."""
    normal, tangent = side_frame(side)
    point = normal * (hexgrid.APOTHEM - inset) + tangent * t
    return Vector((point.x, point.y, z))


def socket_zone(position, socket_sides, half_width=SOCKET_ZONE_HALF_WIDTH):
    """Returns (side, t, inset) if position lies in the edge band of a socket side, else None."""
    for side in socket_sides:
        t, inset = side_local(position, side)
        if inset < SOCKET_ZONE_INSET and abs(t) < half_width:
            return side, t, inset
    return None


def remap_band_lateral(t):
    """Slides a band/rim lattice position onto the socket profile breakpoints (keeps sign)."""
    magnitude = abs(t)
    for before, after in BAND_LATERAL_REMAP:
        if abs(magnitude - before) < MATCH_EPSILON:
            return math.copysign(after, t)
    return t


def mask_from_sides(sides):
    """Bit k set for every socket side k."""
    mask = 0
    for side in sides:
        mask |= 1 << side
    return mask


def sides_from_mask(mask):
    """Socket side indices of a mask."""
    return [side for side in range(hexgrid.SIDE_COUNT) if mask & (1 << side)]


def rotate_mask(mask, steps):
    """Mask after rotating the tile so local side k lands on side (k + steps) % 6 (Unity +60 deg yaw = +1)."""
    steps %= hexgrid.SIDE_COUNT
    full = (1 << hexgrid.SIDE_COUNT) - 1
    return ((mask << steps) | (mask >> (hexgrid.SIDE_COUNT - steps))) & full


def build_socket_ground(builder, rng, face_style, height_function, socket_sides, snap_function=None,
                        jitter_fraction=hexgrid.DEFAULT_JITTER_FRACTION):
    """hexgrid.build_ground with river sockets: socket band verts follow the canonical cross-section.

    Identical to the standard builder (same lattice, jitter sequence, triangulation, rim style and skirt)
    except inside socket zones, where rim and band verts are slid onto the profile breakpoints, lowered to the
    profile and band faces over the channel bed use bed_style.
    """
    n = hexgrid.SUBDIVISIONS
    interior_max_ring = n - 1 - hexgrid.EDGE_BAND_RINGS
    index = {}
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            ring = hexgrid.lattice_ring(i, j)
            if ring > n:
                continue
            position = hexgrid.lattice_position(i, j)
            if ring <= interior_max_ring:
                position.x += rng.uniform(-1.0, 1.0) * jitter_fraction * hexgrid.LATTICE_SPACING
                position.y += rng.uniform(-1.0, 1.0) * jitter_fraction * hexgrid.LATTICE_SPACING
                if snap_function is not None:
                    position = snap_function(position)
                position.z = height_function(position.x, position.y)
            else:
                zone = socket_zone(position, socket_sides)
                if zone is not None:
                    side, t, inset = zone
                    t = remap_band_lateral(t)
                    position = side_point(side, t, inset, profile_depth(t))
            index[(i, j)] = builder.add_vertex(position, ring=ring)

    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            for triangle in (((i, j), (i + 1, j), (i, j + 1)), ((i + 1, j), (i + 1, j + 1), (i, j + 1))):
                if not all(key in index for key in triangle):
                    continue
                ids = [index[key] for key in triangle]
                touches_rim = any(hexgrid.lattice_ring(*key) == n for key in triangle)
                centroid = sum((builder.vertices[k] for k in ids), Vector((0.0, 0.0, 0.0))) / 3.0
                if touches_rim:
                    zone = socket_zone(centroid, socket_sides, SOCKET_HALF_WIDTH)
                    in_bed = zone is not None and abs(zone[1]) < FOAM_INNER_HALF_WIDTH
                    material, uv = bed_style() if in_bed else hexgrid.rim_style()
                else:
                    material, uv = face_style(centroid, rng)
                if callable(uv):
                    uv = [uv(builder.vertices[k]) for k in ids]
                builder.add_face(ids, material, uv)

    rim = [vertex for key, vertex in index.items() if hexgrid.lattice_ring(*key) == n]
    rim.sort(key=lambda v: math.atan2(builder.vertices[v].y, builder.vertices[v].x))
    bottoms = {}
    for vertex in rim:
        top = builder.vertices[vertex]
        bottoms[vertex] = builder.add_vertex((top.x, top.y, -hexgrid.SKIRT_DEPTH), ring=n)
    skirt_top, skirt_bottom = palette.strip_uv("SoilSkirt", 0.0), palette.strip_uv("SoilSkirt", 1.0)
    for k, a in enumerate(rim):
        b = rim[(k + 1) % len(rim)]
        builder.add_face([a, bottoms[a], bottoms[b], b], materials.PALETTE_MATERIAL,
                         [skirt_top, skirt_bottom, skirt_bottom, skirt_top])


def add_socket_empty(obj, name, location, properties=None):
    """Adds an empty parented to obj (in obj's collections) at a local location, with optional custom props."""
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = "PLAIN_AXES"
    empty.empty_display_size = EMPTY_DISPLAY_SIZE
    for collection in obj.users_collection:
        collection.objects.link(empty)
    empty.parent = obj
    empty.location = location
    for key, value in (properties or {}).items():
        empty[key] = value
    return empty


def add_river_edge_markers(obj, socket_sides):
    """Adds EDGE_River_<side> empties at socket midpoints (water level) and the edge_river_mask property."""
    obj[RIVER_MASK_PROPERTY] = mask_from_sides(socket_sides)
    for side in socket_sides:
        location = hexgrid.side_midpoint(side)
        add_socket_empty(obj, f"{EDGE_EMPTY_PREFIX}{RIVER_EDGE_KIND}_{side}", (location.x, location.y, WATER_LEVEL),
                         {"edge_kind": RIVER_EDGE_KIND.lower(), "edge_side": side})


def _rounded_profile(points):
    return sorted((round(t, 3), round(z, 3)) for t, z in points)


def _matches(actual, expected):
    if len(actual) != len(expected):
        return False
    return all(abs(a[0] - b[0]) < MATCH_EPSILON and abs(a[1] - b[1]) < MATCH_EPSILON
               for a, b in zip(sorted(actual), sorted(expected)))


def socket_checks(obj, socket_sides):
    """Socket-aware replacement for the edge_band_flat check plus exact per-socket cross-section checks.

    Returns a list of {"check", "ok", "detail"} dicts.
    """
    mesh = obj.data
    rings = [0] * len(mesh.vertices)
    mesh.attributes[mesh_builder.RING_ATTRIBUTE].data.foreach_get("value", rings)
    band_ring = hexgrid.SUBDIVISIONS - hexgrid.EDGE_BAND_RINGS
    results = []

    band_off = 0
    rim_points = {side: [] for side in socket_sides}
    band_points = {side: [] for side in socket_sides}
    decor_points = {side: [] for side in socket_sides}
    for vertex, ring in zip(mesh.vertices, rings):
        co = vertex.co
        if co.z <= SKIRT_TOP_THRESHOLD:
            continue
        zone = socket_zone(co, socket_sides)
        if ring >= band_ring:
            if zone is None:
                if abs(co.z) > POSITION_EPSILON:
                    band_off += 1
                continue
            side, t, inset = zone
            if abs(co.z - profile_depth(t)) > POSITION_EPSILON:
                band_off += 1
            (rim_points if ring == hexgrid.SUBDIVISIONS else band_points)[side].append((t, co.z))
        elif ring == mesh_builder.NOT_GROUND_RING and zone is not None and abs(zone[2]) < POSITION_EPSILON:
            decor_points[zone[0]].append((zone[1], co.z))
    results.append({"check": "edge_band_flat", "ok": band_off == 0,
                    "detail": f"{band_off} edge-band verts off z=0 / off the socket profile (sockets {socket_sides})"})

    bad_rim = [side for side in socket_sides if not _matches(rim_points[side], CANONICAL_RIM)]
    bad_band = [side for side in socket_sides if not _matches(band_points[side], CANONICAL_BAND)]
    results.append({"check": "socket_cross_section", "ok": not bad_rim and not bad_band,
                    "detail": f"rim mismatch on sides {bad_rim}, band mismatch on sides {bad_band}"})

    bad_water = [side for side in socket_sides
                 if not _matches(sorted(set(_rounded_profile(decor_points[side]))), CANONICAL_RIM_DECOR)]
    results.append({"check": "socket_water_foam_edge", "ok": not bad_water,
                    "detail": f"water/foam rim edge mismatch on sides {bad_water}"})

    expected_mask = mask_from_sides(socket_sides)
    edge_names = sorted(child.name for child in obj.children if child.name.startswith(EDGE_EMPTY_PREFIX))
    expected_names = sorted(f"{EDGE_EMPTY_PREFIX}{RIVER_EDGE_KIND}_{side}" for side in socket_sides)
    mask_ok = obj.get(RIVER_MASK_PROPERTY) == expected_mask and edge_names == expected_names
    results.append({"check": "edge_mask_markers", "ok": mask_ok,
                    "detail": f"{RIVER_MASK_PROPERTY}={obj.get(RIVER_MASK_PROPERTY)} (expected {expected_mask}), "
                              f"empties {edge_names}"})
    return results
