"""Connected-river tiles (Art Workflow 4.3): channel along a centerline carved into the socket-aware ground,
M_Water ribbon + ShoreFoam strips, and the validate / export / preview hooks shared by the river recipes.

Every socket end of a centerline runs straight along the side's inward normal for LEAD_LENGTH, so the ground,
water and foam reach the rim with exactly the canonical edge_sockets cross-section.
"""
import contextlib
import io
import json
import math
import os
import random

import bpy
from mathutils import Matrix, Vector

from lib import edge_sockets, hexgrid, materials, palette, paths, preview, shapes, validate
from lib.scatter import scatter_points
from props import kit
from tiles import water_common

LEAD_LENGTH = 2.6
BEZIER_SAMPLES = 18
RIBBON_STEP = 1.0
TANGENT_PROBE = 0.5
DEFAULT_BULGE = 0.18
BULGE_RAMP_START = 2.8
BULGE_RAMP_END = 5.5
BANK_SNAP_THRESHOLD = 0.45
REED_LATERAL = 1.25
TREE_BANK_CLEARANCE = 1.2
TREE_SPACING = 2.5
TREE_MIN_RADIUS = 0.85
TREE_MAX_RADIUS = 1.1
TREE_COLORS = ("MapleRed", "Mustard", "Pumpkin")
BUSH_MIN_RADIUS = 0.4
BUSH_MAX_RADIUS = 0.6
BUSH_MIN_INSET = 0.9
ROCK_MIN_RADIUS = 0.28
ROCK_MAX_RADIUS = 0.5
SCATTER_ATTEMPTS = 4000

STRAIGHT_ID = "tile.river_straight"
BEND_ID = "tile.river_bend"
SOURCE_ID = "tile.river_source"
BASE_ID = "tile.base"
RIVER_SOCKETS = {STRAIGHT_ID: (0, 3), BEND_ID: (0, 2), SOURCE_ID: (0,)}
PATCH_FILL_POOL = (BASE_ID, BASE_ID, BASE_ID, BASE_ID, BASE_ID, "tile.lake_a", "tile.lake_b", "tile.village_a",
                   "tile.village_b", "tile.churchtown_a", "tile.churchtown_b", "tile.marsh_a")
CHAIN_SEQUENCE = ((SOURCE_ID, 0), (STRAIGHT_ID, 0), (BEND_ID, 0), (STRAIGHT_ID, 1), (BEND_ID, 1), (SOURCE_ID, 0))
PATCH_CHAIN_SEQUENCE = ((SOURCE_ID, 0), (STRAIGHT_ID, 1), (BEND_ID, 0), (STRAIGHT_ID, 0), (SOURCE_ID, 0))
PATCH_RING_COUNT = 3
PATCH_DISTANCE = 160.0
CHAIN_WIDE_DISTANCE = 100.0
SEAM_BACK = 6.5
SEAM_AHEAD = 4.0
SEAM_HEIGHT = 1.0
SEAM_TARGET_DROP = 0.35
ALONG_RIVER_BACK = 9.0
ALONG_RIVER_AHEAD = 6.0
ALONG_RIVER_HEIGHT = 1.6
SOCKET_ORTHO_SCALE = 9.0
ORTHO_MARGIN = 1.15
SHEET_COLUMNS = 2


class Centerline:
    """Polyline river centerline with closest-point queries and arc-length sampling."""

    def __init__(self, points):
        self.points = [Vector((p[0], p[1], 0.0)) for p in points]
        self.cumulative = [0.0]
        for a, b in zip(self.points, self.points[1:]):
            self.cumulative.append(self.cumulative[-1] + (b - a).length)
        self.length = self.cumulative[-1]

    def closest(self, x, y):
        """Returns (distance, arc length, closest point) of (x, y) to the polyline."""
        point = Vector((x, y, 0.0))
        best = (float("inf"), 0.0, self.points[0])
        for index, (a, b) in enumerate(zip(self.points, self.points[1:])):
            segment = b - a
            length_squared = segment.length_squared
            u = 0.0 if length_squared == 0.0 else max(0.0, min(1.0, (point - a).dot(segment) / length_squared))
            foot = a + segment * u
            distance = (point - foot).length
            if distance < best[0]:
                best = (distance, self.cumulative[index] + u * math.sqrt(length_squared), foot)
        return best

    def sample(self, arc):
        """Returns the point at an arc length (clamped)."""
        arc = max(0.0, min(self.length, arc))
        for index in range(len(self.points) - 1):
            if arc <= self.cumulative[index + 1] or index == len(self.points) - 2:
                span = self.cumulative[index + 1] - self.cumulative[index]
                u = 0.0 if span == 0.0 else (arc - self.cumulative[index]) / span
                return self.points[index].lerp(self.points[index + 1], u)
        return self.points[-1].copy()

    def direction(self, arc):
        """Returns the unit flow direction at an arc length (exact segment direction at the ends)."""
        if arc <= 0.0:
            return (self.points[1] - self.points[0]).normalized()
        if arc >= self.length:
            return (self.points[-1] - self.points[-2]).normalized()
        before = self.sample(max(0.0, arc - TANGENT_PROBE))
        after = self.sample(min(self.length, arc + TANGENT_PROBE))
        return (after - before).normalized()


def socket_lead(side, length=LEAD_LENGTH):
    """Returns (rim midpoint, lead end) of the straight socket lead-in along a side's inward normal."""
    mid = hexgrid.side_midpoint(side)
    normal, _ = edge_sockets.side_frame(side)
    return mid, mid - normal * length


def cubic_bezier(p0, p1, p2, p3, count):
    """Samples a cubic Bezier into count points (both ends included)."""
    points = []
    for k in range(count):
        u = k / (count - 1)
        v = 1.0 - u
        points.append(p0 * v ** 3 + p1 * 3.0 * v * v * u + p2 * 3.0 * v * u * u + p3 * u ** 3)
    return points


def socket_to_socket_points(side_a, side_b, control_length, meander=0.0):
    """Centerline points from socket side_a to socket side_b, with an optional S-shaped meander."""
    mid_a, lead_a = socket_lead(side_a)
    mid_b, lead_b = socket_lead(side_b)
    inward_a, inward_b = (lead_a - mid_a).normalized(), (lead_b - mid_b).normalized()
    curve = cubic_bezier(lead_a, lead_a + inward_a * control_length, lead_b + inward_b * control_length, lead_b,
                         BEZIER_SAMPLES)
    if meander:
        chord = (lead_b - lead_a).normalized()
        lateral = Vector((-chord.y, chord.x, 0.0))
        for k, point in enumerate(curve):
            u = k / (len(curve) - 1)
            point += lateral * (meander * math.sin(2.0 * math.pi * u) * math.sin(math.pi * u))
    return [mid_a] + curve + [mid_b]


def _smoothstep(edge0, edge1, value):
    t = max(0.0, min(1.0, (value - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


class RiverChannel:
    """A river channel: socket-profile cross-section swept along a centerline, widening between sockets."""

    def __init__(self, centerline, bulge=DEFAULT_BULGE, socket_at_start=True, socket_at_end=True):
        self.centerline = centerline
        self.bulge = bulge
        self.socket_at_start = socket_at_start
        self.socket_at_end = socket_at_end

    def scale(self, arc):
        """Width multiplier at an arc length (exactly 1 near every socket end)."""
        distance = float("inf")
        if self.socket_at_start:
            distance = min(distance, arc)
        if self.socket_at_end:
            distance = min(distance, self.centerline.length - arc)
        return 1.0 + self.bulge * _smoothstep(BULGE_RAMP_START, BULGE_RAMP_END, distance)

    def lateral(self, x, y):
        """Normalized lateral offset (1.5 = bank top) and the raw query result."""
        distance, arc, foot = self.centerline.closest(x, y)
        return distance / self.scale(arc), (distance, arc, foot)

    def ground_depth(self, x, y):
        """Channel ground height (< 0) or None outside the bank top."""
        lateral, _ = self.lateral(x, y)
        if lateral >= edge_sockets.SOCKET_HALF_WIDTH:
            return None
        return edge_sockets.profile_depth(lateral)

    def bank_offset(self, x, y):
        """Distance from the bank-top contour (negative inside the channel)."""
        lateral, (distance, arc, _) = self.lateral(x, y)
        return distance - edge_sockets.SOCKET_HALF_WIDTH * self.scale(arc)

    def snap(self, position):
        """Snaps lattice verts near the bank top onto it."""
        distance, arc, foot = self.centerline.closest(position.x, position.y)
        target = edge_sockets.SOCKET_HALF_WIDTH * self.scale(arc)
        if distance > 1e-6 and abs(distance - target) < BANK_SNAP_THRESHOLD:
            offset = Vector((position.x - foot.x, position.y - foot.y, 0.0)) * (target / distance)
            position.x, position.y = foot.x + offset.x, foot.y + offset.y
        return position

    def cross_section(self, arc):
        """Returns (center point, left unit vector, width scale) at an arc length."""
        forward = self.centerline.direction(arc)
        return self.centerline.sample(arc), Vector((-forward.y, forward.x, 0.0)), self.scale(arc)

    def ribbon_arcs(self, arc_start=0.0, arc_end=None):
        """Evenly spaced arc lengths covering [arc_start, arc_end]."""
        arc_end = self.centerline.length if arc_end is None else arc_end
        count = max(1, math.ceil((arc_end - arc_start) / RIBBON_STEP))
        return [arc_start + (arc_end - arc_start) * k / count for k in range(count + 1)]

    def add_water(self, builder, arc_start=0.0, arc_end=None):
        """Adds the M_Water ribbon and the two ShoreFoam strips between two arc lengths."""
        arcs = self.ribbon_arcs(arc_start, arc_end)
        water, foam_left, foam_right = [], [], []
        for arc in arcs:
            center, left, scale = self.cross_section(arc)
            level_water = Vector((0.0, 0.0, edge_sockets.WATER_LEVEL))
            level_foam = Vector((0.0, 0.0, edge_sockets.FOAM_LEVEL))
            water.append((center - left * (edge_sockets.WATER_HALF_WIDTH * scale) + level_water,
                          center + left * (edge_sockets.WATER_HALF_WIDTH * scale) + level_water))
            foam_left.append((center + left * (edge_sockets.FOAM_INNER_HALF_WIDTH * scale) + level_foam,
                              center + left * (edge_sockets.FOAM_OUTER_HALF_WIDTH * scale) + level_foam))
            foam_right.append((center - left * (edge_sockets.FOAM_OUTER_HALF_WIDTH * scale) + level_foam,
                               center - left * (edge_sockets.FOAM_INNER_HALF_WIDTH * scale) + level_foam))
        _add_strip(builder, water, materials.WATER_MATERIAL, palette.flat_uv("LakeTeal"))
        for strip in (foam_left, foam_right):
            _add_strip(builder, strip, materials.PALETTE_MATERIAL, palette.flat_uv("ShoreFoam"))


def _add_strip(builder, rows, material, uv):
    """Adds quads between consecutive (right, left) vertex pairs (right -> left is +90 deg of the flow)."""
    vertices = [v for row in rows for v in row]
    faces = [(2 * k, 2 * k + 2, 2 * k + 3, 2 * k + 1) for k in range(len(rows) - 1)]
    builder.add_part(shapes.Part(vertices, faces), Matrix.Identity(4), material, lambda face, centroid: uv)


def scatter_land_decor(builder, rng, height, land_ok, tree_count, bush_count, rock_count, blockers=()):
    """Scatters autumn trees, bushes and rocks on land accepted by land_ok(x, y, clearance)."""
    trees = []
    for _ in range(SCATTER_ATTEMPTS):
        if len(trees) >= tree_count:
            break
        radius = rng.uniform(TREE_MIN_RADIUS, TREE_MAX_RADIUS)
        x, y = rng.uniform(-hexgrid.TILE_RADIUS, hexgrid.TILE_RADIUS), rng.uniform(-hexgrid.TILE_RADIUS,
                                                                                   hexgrid.TILE_RADIUS)
        if not water_common.tree_clear_of_rim(x, y, kit.tree_max_canopy_radius(radius)):
            continue
        if not land_ok(x, y, TREE_BANK_CLEARANCE):
            continue
        if any(math.hypot(x - bx, y - by) < TREE_SPACING for bx, by in list(blockers) + [(t[0], t[1]) for t in trees]):
            continue
        trees.append((x, y, radius))
    for index, (x, y, radius) in enumerate(trees):
        kit.add_deciduous_tree(builder, rng, x, y, height(x, y), radius, TREE_COLORS[index % len(TREE_COLORS)])
    occupied = list(blockers) + [(x, y) for x, y, _ in trees]
    bushes = scatter_points(rng, bush_count, hexgrid.TILE_RADIUS, 1.5,
                            lambda x, y: hexgrid.inset_distance(x, y) >= BUSH_MIN_INSET and land_ok(x, y, 0.6),
                            existing=occupied)
    for x, y in bushes:
        kit.add_bush(builder, rng, x, y, height(x, y), rng.uniform(BUSH_MIN_RADIUS, BUSH_MAX_RADIUS))
    rocks = scatter_points(rng, rock_count, hexgrid.TILE_RADIUS, 1.3,
                           lambda x, y: hexgrid.inset_distance(x, y) >= 1.5 and land_ok(x, y, 0.1)
                           and not land_ok(x, y, 0.9),
                           existing=occupied + bushes)
    for x, y in rocks:
        kit.add_rock(builder, rng, x, y, height(x, y), rng.uniform(ROCK_MIN_RADIUS, ROCK_MAX_RADIUS))
    return occupied + bushes + rocks


def add_bank_reeds(builder, rng, channel, height, arcs):
    """Adds reed clumps on alternating banks at the given arc lengths."""
    for index, arc in enumerate(arcs):
        center, left, scale = channel.cross_section(arc)
        side = 1.0 if index % 2 == 0 else -1.0
        point = center + left * (side * REED_LATERAL * scale)
        kit.add_reed_clump(builder, rng, point.x, point.y, height(point.x, point.y))


def finish_river_tile(obj, socket_sides, snack_points):
    """Adds the EDGE_River_* markers, edge_river_mask and the water snack sockets to a built tile."""
    edge_sockets.add_river_edge_markers(obj, socket_sides)
    water_common.add_water_snack_sockets(obj, snack_points)
    return obj


def validate_river_tile(obj, spec, socket_sides):
    """Standard tile checks with edge_band_flat replaced by the socket-aware checks. Writes validation.json."""
    with contextlib.redirect_stdout(io.StringIO()):
        report = validate.validate_object(obj, spec)
    socket_results = edge_sockets.socket_checks(obj, socket_sides)
    replaced = {result["check"] for result in socket_results}
    report["checks"] = [r for r in report["checks"] if r["check"] not in replaced] + socket_results
    report["passed"] = all(r["ok"] for r in report["checks"])
    report[edge_sockets.RIVER_MASK_PROPERTY] = obj.get(edge_sockets.RIVER_MASK_PROPERTY)
    out_path = os.path.join(paths.asset_render_dir(spec.asset_id), "validation.json")
    with open(out_path, "w") as handle:
        json.dump(report, handle, indent=2)
    status = "PASS" if report["passed"] else "FAIL"
    print(f"[bezi-art] validate {spec.asset_id}: {status} ({report['triangles']} tris, socket-aware, "
          f"{edge_sockets.RIVER_MASK_PROPERTY}={report[edge_sockets.RIVER_MASK_PROPERTY]})")
    for result in report["checks"]:
        if not result["ok"]:
            print(f"[bezi-art]   FAIL {result['check']}: {result['detail']}")
    return report


def export_with_custom_props(obj, filepath):
    """FBX export with the pipeline's Unity settings plus custom properties (edge_river_mask), then re-imports
    the file to confirm the property and EDGE_/SOCKET_ empties survived."""
    paths.ensure_dir(os.path.dirname(filepath))
    for other in bpy.context.view_layer.objects:
        other.select_set(False)
    obj.select_set(True)
    for child in obj.children_recursive:
        child.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(
        filepath=filepath, use_selection=True, object_types={"MESH", "ARMATURE", "EMPTY"},
        apply_unit_scale=True, apply_scale_options="FBX_SCALE_ALL", axis_forward="-Z", axis_up="Y",
        bake_space_transform=True, mesh_smooth_type="FACE", use_mesh_modifiers=True, use_triangles=True,
        add_leaf_bones=False, path_mode="STRIP", bake_anim=False, use_custom_props=True,
    )
    print(f"[bezi-art] exported {filepath} (custom props)")
    _verify_fbx(filepath, obj.name)
    return filepath


def _verify_fbx(filepath, mesh_name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=filepath, use_custom_props=True)
    imported = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in imported if o.type == "MESH"]
    mask = meshes[0].get(edge_sockets.RIVER_MASK_PROPERTY) if meshes else None
    empties = sorted(o.name.split(".")[0] for o in imported if o.type == "EMPTY")
    print(f"[bezi-art] fbx check {mesh_name}: {edge_sockets.RIVER_MASK_PROPERTY}={mask}, empties={empties}")
    for item in imported:
        bpy.data.objects.remove(item, do_unlink=True)


# ---------------------------------------------------------------------------------------------- previews

def _registry():
    import registry  # deferred: registry imports the catalog, which must not import recipes at load time
    return registry


def _load_sources(asset_ids):
    sources = {}
    for asset_id in dict.fromkeys(asset_ids):
        spec = _registry().ASSETS[asset_id]
        obj = preview.append_asset(spec.blend_path, spec.mesh_name)
        obj.hide_render = True
        sources[asset_id] = obj
    return sources


def world_side(local_side, rotation_steps):
    """World side of a local side after a Blender CCW rotation of rotation_steps x 60 deg."""
    return (local_side - rotation_steps) % hexgrid.SIDE_COUNT


def rotation_for(local_side, target_world_side):
    """Rotation steps (Blender CCW) that put local_side on target_world_side."""
    return (local_side - target_world_side) % hexgrid.SIDE_COUNT


def _key(position):
    return (round(position.x, 2), round(position.y, 2))


def lay_chain(sequence, start_position, start_exit):
    """Places a socket-matched river chain. sequence items: (asset_id, entry socket choice index).

    Returns placements [(asset_id, position, rotation_steps, exit_world_side or None)].
    """
    placements = []
    position, exit_side = Vector(start_position), start_exit
    for index, (asset_id, choice) in enumerate(sequence):
        sockets = RIVER_SOCKETS[asset_id]
        if index == 0:
            rotation = rotation_for(sockets[0], exit_side)
            next_exit = exit_side
        else:
            entry = (exit_side + 3) % hexgrid.SIDE_COUNT
            entry_local = sockets[choice % len(sockets)]
            rotation = rotation_for(entry_local, entry)
            others = [s for s in sockets if s != entry_local]
            next_exit = world_side(others[0], rotation) if others else None
        placements.append((asset_id, position.copy(), rotation, next_exit))
        if next_exit is None:
            break
        position = position + hexgrid.neighbor_center(next_exit)
        exit_side = next_exit
    return placements


def _socket_frame(placement):
    """World (midpoint, outward normal, tangent) of a placement's exit socket."""
    _, position, _, exit_side = placement
    normal, tangent = edge_sockets.side_frame(exit_side)
    return position + hexgrid.side_midpoint(exit_side), normal, tangent


def _seam_camera(name, midpoint, tangent):
    return preview.make_camera(name, midpoint - tangent * SEAM_BACK + Vector((0.0, 0.0, SEAM_HEIGHT)),
                               midpoint + tangent * SEAM_AHEAD - Vector((0.0, 0.0, SEAM_TARGET_DROP)),
                               fov_deg=preview.SEAM_FOV_DEG)


def _along_river_camera(name, midpoint, normal):
    return preview.make_camera(name, midpoint - normal * ALONG_RIVER_BACK + Vector((0.0, 0.0, ALONG_RIVER_HEIGHT)),
                               midpoint + normal * ALONG_RIVER_AHEAD, fov_deg=preview.SEAM_FOV_DEG)


def _render_panels(cameras, out_dir, out_name, prefix):
    panels = []
    for index, camera in enumerate(cameras):
        panels.append(preview.render(camera, os.path.join(out_dir, f"_{prefix}{index}.png")))
    return preview.stitch(panels, os.path.join(out_dir, out_name), columns=SHEET_COLUMNS)


def river_cluster_sheet(spec, seed):
    """Flower around a river tile: matching Straight tiles on its sockets, base tiles elsewhere; seam close-ups."""
    preview.reset_scene()
    rng = random.Random(seed)
    sources = _load_sources([spec.asset_id, STRAIGHT_ID, BASE_ID])
    rotation = rng.randrange(hexgrid.SIDE_COUNT)
    preview.add_instance(sources[spec.asset_id], Vector((0.0, 0.0, 0.0)), rotation)
    sockets = [world_side(side, rotation) for side in RIVER_SOCKETS[spec.asset_id]]
    for side in range(hexgrid.SIDE_COUNT):
        center = hexgrid.neighbor_center(side)
        if side in sockets:
            preview.add_instance(sources[STRAIGHT_ID], center, rotation_for(0, (side + 3) % hexgrid.SIDE_COUNT))
        else:
            preview.add_instance(sources[BASE_ID], center, rng.randrange(hexgrid.SIDE_COUNT))
    socket = sockets[0]
    normal, tangent = edge_sockets.side_frame(socket)
    midpoint = hexgrid.side_midpoint(socket)
    origin = Vector((0.0, 0.0, 0.0))
    cameras = [
        preview.game_camera("CamGame", origin, preview.GAME_DISTANCE),
        preview.game_camera("CamWide", origin, preview.WIDE_DISTANCE),
        _seam_camera("CamSeam", midpoint, tangent),
        _along_river_camera("CamRiver", midpoint, normal),
        preview.top_camera("CamSocket", midpoint, SOCKET_ORTHO_SCALE),
        preview.top_camera("CamTop", origin, hexgrid.TILE_RADIUS * 3.2),
    ]
    return _render_panels(cameras, paths.asset_render_dir(spec.asset_id), "cluster_sheet.png", "c")


def _fill_neighbors(sources, occupied, fill_ids, rng, extra_keys=()):
    keys = set(occupied) | set(extra_keys)
    for position in list(occupied.values()):
        for side in range(hexgrid.SIDE_COUNT):
            neighbor = position + hexgrid.neighbor_center(side)
            if _key(neighbor) in keys:
                continue
            keys.add(_key(neighbor))
            preview.add_instance(sources[rng.choice(fill_ids)], neighbor, rng.randrange(hexgrid.SIDE_COUNT))


def chain_sheet(seed):
    """River chain Source -> Straight -> Bend -> Straight -> Bend -> Source(mouth) on base tiles, 6 panels."""
    preview.reset_scene()
    rng = random.Random(seed)
    sources = _load_sources(list(RIVER_SOCKETS) + [BASE_ID])
    placements = lay_chain(CHAIN_SEQUENCE, Vector((0.0, 0.0, 0.0)), 4)
    occupied = {}
    for asset_id, position, rotation, _ in placements:
        preview.add_instance(sources[asset_id], position, rotation)
        occupied[_key(position)] = position
    _fill_neighbors(sources, occupied, [BASE_ID], rng)
    centroid = sum((p for _, p, _, _ in placements), Vector((0.0, 0.0, 0.0))) / len(placements)
    extent = max((p - centroid).length for _, p, _, _ in placements) + hexgrid.TILE_RADIUS
    rotations = [f"{asset_id.split('_')[-1]}@{rotation * 60}deg" for asset_id, _, rotation, _ in placements]
    print(f"[bezi-art] river chain: {rotations}")
    seam_a, normal_a, tangent_a = _socket_frame(placements[1])
    seam_b, normal_b, tangent_b = _socket_frame(placements[2])
    seam_c, normal_c, _ = _socket_frame(placements[3])
    cameras = [
        preview.game_camera("CamChainWide", centroid, CHAIN_WIDE_DISTANCE),
        preview.top_camera("CamChainTop", centroid, 2.0 * extent * ORTHO_MARGIN),
        preview.game_camera("CamChainGame", seam_a, preview.GAME_DISTANCE),
        _seam_camera("CamChainSeam", seam_b, tangent_b),
        _along_river_camera("CamChainRiver", seam_c, normal_c),
        preview.top_camera("CamChainSocket", seam_a, SOCKET_ORTHO_SCALE),
    ]
    out_dir = paths.ensure_dir(os.path.join(paths.RENDERS_DIR, "river_chain"))
    return _render_panels(cameras, out_dir, "river_chain_sheet.png", "r")


def _hex_ring_positions(rings):
    positions = []
    for q in range(-rings, rings + 1):
        for r in range(-rings, rings + 1):
            if max(abs(q), abs(r), abs(q + r)) <= rings:
                positions.append(hexgrid.axial_center(q, r))
    return positions


def mixed_patch_sheet(seed):
    """37-tile patch mixing tile.base and the water/settlement tiles, with a socket-matched river threaded through."""
    preview.reset_scene()
    rng = random.Random(seed)
    patch = _hex_ring_positions(PATCH_RING_COUNT)
    patch_keys = {_key(p) for p in patch}
    best = None
    for start in patch:
        for exit_side in range(hexgrid.SIDE_COUNT):
            placements = lay_chain(PATCH_CHAIN_SEQUENCE, start, exit_side)
            keys = [_key(p) for _, p, _, _ in placements]
            if len(set(keys)) != len(keys) or not all(k in patch_keys for k in keys):
                continue
            spread = max(p.length for _, p, _, _ in placements)
            if best is None or spread < best[0]:
                best = (spread, placements)
    placements = best[1]
    sources = _load_sources(list(RIVER_SOCKETS) + list(PATCH_FILL_POOL) + ["tile.goosebay_lodge"])
    used = set()
    for asset_id, position, rotation, _ in placements:
        preview.add_instance(sources[asset_id], position, rotation)
        used.add(_key(position))
    free = [p for p in patch if _key(p) not in used]
    lodge_index = rng.randrange(len(free))
    for index, position in enumerate(free):
        asset_id = "tile.goosebay_lodge" if index == lodge_index else rng.choice(PATCH_FILL_POOL)
        preview.add_instance(sources[asset_id], position, rng.randrange(hexgrid.SIDE_COUNT))
    camera = preview.game_camera("CamPatch", (0.0, 0.0, 0.0), PATCH_DISTANCE)
    out_dir = paths.ensure_dir(os.path.join(paths.RENDERS_DIR, "river_chain"))
    out_path = os.path.join(out_dir, "mixed_patch_with_base.png")
    preview.render(camera, out_path, size=(preview.PANEL_WIDTH * 2, preview.PANEL_HEIGHT * 2))
    print(f"[bezi-art] preview written: {out_path}")
    return out_path


def river_preview(spec, seed, include_chain=False):
    """Preview hook body: standard contact sheet, socket-matched cluster sheet and optionally chain + patch."""
    written = [preview.contact_sheet(spec, spec.blend_path), river_cluster_sheet(spec, seed)]
    if include_chain:
        written.append(chain_sheet(seed))
        written.append(mixed_patch_sheet(seed))
    return written
