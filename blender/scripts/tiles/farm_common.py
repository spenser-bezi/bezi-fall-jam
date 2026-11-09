"""Helpers shared by the farmland tiles (cornfield, pumpkin patch, farm, wind farm).

Covers striped field patches with planar per-corner UVs (the approved seam-test technique), splitting a content
blob into several patches along snapped lines, row runs for crop strips, hedgerow dressing on the grass rim,
socket helpers, a validator that also counts child rotor objects, and a 6-rotation review render.
"""
import json
import math
import os
import random
from dataclasses import dataclass

import bpy
from mathutils import Vector

from lib import hexgrid, materials, palette, paths, preview, validate
from lib.builder import MeshBuilder
from props import farm_props, kit, woodland_props
from tiles import woodland_common as woodland

PATTERN_BANDS = 10
ROW_SAMPLE_STEP = 0.2
HEDGE_MIN_INSET = 0.95
HEDGE_OUTSIDE_OFFSET = 0.55
HEDGE_RADIUS_RANGE = (0.45, 0.65)
HEDGE_COLORS = ("Moss", "Moss", "Pine", "Mustard")
LOW_BUSH_TRIANGLES = 20
HEDGE_ATTEMPTS = 400
ROTATION_SHEET_DISTANCE = 78.0
ROTATION_TOP_SCALE = 58.0
ROTATION_SHEET_NAME = "rotation_sheet.png"
ROTOR_PREFIX = "Rotor_"
EDGE_INSET_RANGE = (1.45, 1.9)
EDGE_ATTEMPTS = 300
EDGE_ANGLE_JITTER = 0.25
EDGE_SCAN_STEP = 0.25
HAY_CLEARANCE = 0.75
LINE_SNAP_MARGIN = 0.6
FULL_SNAP_THRESHOLD = 0.68 * hexgrid.LATTICE_SPACING
FOLD_FIX_ITERATIONS = 30
SNAP_KEY_DIGITS = 5
MIN_SNAPPED_FACE_AREA = 0.02


@dataclass
class StripedPatch:
    """A field patch striped with a repeating pattern strip; rows sit at band centers (one row per band).

    angle: row direction in radians (use multiples of 60 degrees so rows line up with a hex side at any rotation).
    """
    strip: str
    angle: float
    spacing: float
    center: Vector

    @property
    def direction(self):
        """Unit vector along the rows."""
        return Vector((math.cos(self.angle), math.sin(self.angle), 0.0))

    @property
    def normal(self):
        """Unit vector across the rows."""
        return Vector((-math.sin(self.angle), math.cos(self.angle), 0.0))

    def uv(self, position):
        """Planar per-corner UV along the pattern strip (callable form accepted by hexgrid.build_ground)."""
        span = self.spacing * PATTERN_BANDS
        offset = (position.x - self.center.x) * self.normal.x + (position.y - self.center.y) * self.normal.y
        return palette.strip_uv(self.strip, (offset + span * 0.5) / span)

    def row_offsets(self, half_extent):
        """Signed offsets (across the rows, relative to center) of every row center within +/- half_extent."""
        count = int(half_extent / self.spacing) + 1
        return [(k + 0.5) * self.spacing for k in range(-count - 1, count + 1)
                if abs((k + 0.5) * self.spacing) <= half_extent]

    def align(self, x, y, on_row):
        """Moves (x, y) across the rows onto the nearest row center (on_row) or the nearest furrow between rows."""
        across = (x - self.center.x) * self.normal.x + (y - self.center.y) * self.normal.y
        phase = 0.5 if on_row else 0.0
        target = (round(across / self.spacing - phase) + phase) * self.spacing
        return x + self.normal.x * (target - across), y + self.normal.y * (target - across)


def circle_contour(center, radius):
    """Returns a contour snapper (position, threshold) -> position for a circular clearing outline."""
    return lambda position, threshold: hexgrid.snap_to_polar_contour(position, center, lambda angle: radius,
                                                                     threshold)


@dataclass
class SplitLine:
    """A straight line through point with unit normal; splits a blob into two patches."""
    point: Vector
    normal: Vector

    def side(self, x, y):
        """Signed distance of (x, y) from the line."""
        return (x - self.point.x) * self.normal.x + (y - self.point.y) * self.normal.y

    def snap(self, position, threshold):
        """Moves a lattice vertex onto the line when within threshold."""
        distance = self.side(position.x, position.y)
        if abs(distance) < threshold:
            position.x -= self.normal.x * distance
            position.y -= self.normal.y * distance
        return position


def unit(angle):
    """Planar unit vector at angle (radians)."""
    return Vector((math.cos(angle), math.sin(angle), 0.0))


def combined_snap(blob, lines=(), extra=()):
    """Returns snap_with_threshold(position, threshold) snapping to the blob outline, split lines and extra contours.

    extra: callables (position, threshold) -> position.
    """
    def snap_with_threshold(position, threshold):
        position = blob.snap(position, threshold)
        for line in lines:
            dx, dy = position.x - blob.center.x, position.y - blob.center.y
            if math.hypot(dx, dy) < blob.boundary(math.atan2(dy, dx)) + LINE_SNAP_MARGIN:
                position = line.snap(position, threshold)
        for contour in extra:
            position = contour(position, threshold)
        return position
    return snap_with_threshold


def row_runs(accept, origin, direction, normal, offset, half_length, end_margin, min_length):
    """Finds contiguous runs along a row line where accept(x, y) holds, shrunk by end_margin at both ends.

    The row line is origin + normal * offset + direction * s for s in [-half_length, half_length].
    Returns a list of (start, end) planar Vectors.
    """
    base = origin + normal * offset
    runs, start = [], None
    steps = int(2.0 * half_length / ROW_SAMPLE_STEP)
    for k in range(steps + 1):
        s = -half_length + k * ROW_SAMPLE_STEP
        point = base + direction * s
        inside = accept(point.x, point.y)
        if inside and start is None:
            start = s
        if (not inside or k == steps) and start is not None:
            end = s - (0.0 if inside else ROW_SAMPLE_STEP)
            if end - start - 2.0 * end_margin >= min_length:
                runs.append((base + direction * (start + end_margin), base + direction * (end - end_margin)))
            start = None
    return runs


def pick_spread(points, count):
    """Greedy farthest-point pick (starting nearest the center) so sockets spread across the tile."""
    if not points:
        return []
    chosen = [min(points, key=lambda p: p[0] ** 2 + p[1] ** 2)]
    while len(chosen) < min(count, len(points)):
        chosen.append(max((p for p in points if p not in chosen),
                          key=lambda p: min(math.hypot(p[0] - c[0], p[1] - c[1]) for c in chosen)))
    return chosen


def add_sockets(tile, name_format, points, hover):
    """Adds SOCKET_* empties at (x, y, z + hover) for each point, numbered from 01."""
    return [woodland.add_socket(tile, name_format.format(index), (x, y, z + hover))
            for index, (x, y, z) in enumerate(points, start=1)]


class Obstacles:
    """Planar keep-out circles so decor never overlaps (buildings, bales, pumps, sockets)."""

    def __init__(self):
        self.circles = []

    def add(self, x, y, radius):
        """Registers a keep-out circle."""
        self.circles.append((x, y, radius))

    def clear(self, x, y, radius):
        """True if a circle at (x, y) with radius overlaps no registered circle."""
        return all(math.hypot(x - cx, y - cy) >= radius + cr for cx, cy, cr in self.circles)


def add_hedgerow(builder, rng, blob, height_at, count, obstacles, budget):
    """Dresses the grass rim just outside the field blob with a few low bushes (Dorfromantik hedgerow).

    Bushes stay >= HEDGE_MIN_INSET inside the rim and respect the obstacle circles and triangle budget.
    """
    placed, phase = 0, rng.uniform(0.0, 2.0 * math.pi)
    for attempt in range(HEDGE_ATTEMPTS):
        if placed >= count:
            break
        angle = phase + 2.0 * math.pi * (placed + rng.uniform(-0.3, 0.3)) / count + attempt * 0.07
        radius = blob.boundary(angle - 0.0) + HEDGE_OUTSIDE_OFFSET + rng.uniform(-0.1, 0.4)
        x = blob.center.x + radius * math.cos(angle)
        y = blob.center.y + radius * math.sin(angle)
        size = rng.uniform(*HEDGE_RADIUS_RANGE)
        if hexgrid.inset_distance(x, y) < HEDGE_MIN_INSET + size * 0.5 or not obstacles.clear(x, y, size):
            continue
        if not woodland.fits_budget(builder, LOW_BUSH_TRIANGLES, budget):
            break
        woodland_props.add_low_bush(builder, rng, x, y, height_at(x, y), size, rng.choice(HEDGE_COLORS))
        obstacles.add(x, y, size)
        placed += 1
    return placed


def fold_free_snap(rng, height_function, snap_with_threshold, threshold=FULL_SNAP_THRESHOLD):
    """Returns a snap function that snaps every interior vertex within threshold of an outline, except the few
    vertices whose snapping would fold a ground triangle.

    Like woodland_common.safe_snap it probes hexgrid.build_ground on a copy of rng's state (so the real build sees
    the identical jitter), but instead of shrinking the threshold for the whole tile it freezes only the vertices of
    folded triangles and re-probes. A threshold of about half the lattice spacing means nearly every lattice edge
    that crosses an outline gets an endpoint on it, so region outlines come out smooth instead of saw-toothed.
    Falls back to safe_snap if the folds do not clear.
    """
    frozen = set()

    def make_snap(frozen_keys):
        def snap(position):
            if (round(position.x, SNAP_KEY_DIGITS), round(position.y, SNAP_KEY_DIGITS)) in frozen_keys:
                return position
            return snap_with_threshold(position, threshold)
        return snap

    for _ in range(FOLD_FIX_ITERATIONS):
        probe_rng = random.Random()
        probe_rng.setstate(rng.getstate())
        probe = MeshBuilder()
        keys_by_vertex = {}
        moves = {}
        candidate = make_snap(frozen)

        def recording(position):
            key = (round(position.x, SNAP_KEY_DIGITS), round(position.y, SNAP_KEY_DIGITS))
            keys_by_vertex[len(probe.vertices)] = key
            before = position.copy()
            result = candidate(position)
            moves[key] = (result - before).length
            return result

        hexgrid.build_ground(probe, probe_rng, lambda centroid, face_rng: hexgrid.rim_style(), height_function,
                             recording)
        newly_frozen = set()
        folded = 0
        for indices, _, _ in probe.faces:
            if len(indices) != 3:
                continue
            a, b, c = (probe.vertices[k] for k in indices)
            normal = (b - a).cross(c - a)
            if normal.z <= MIN_SNAPPED_FACE_AREA * 2.0:
                folded += 1
                movable = [keys_by_vertex[k] for k in indices
                           if k in keys_by_vertex and moves.get(keys_by_vertex[k], 0.0) > 0.0]
                if movable:
                    newly_frozen.add(max(movable, key=lambda key: moves[key]))
        if folded == 0:
            print(f"[bezi-art]   fold-free snap {threshold:.2f} m, {len(frozen)} vertices left unsnapped")
            return make_snap(frozen)
        if not newly_frozen - frozen:
            break
        frozen |= newly_frozen
    print("[bezi-art]   fold-free snap did not converge, falling back to safe_snap")
    return woodland.safe_snap(rng, height_function, snap_with_threshold)


def edge_spot(rng, blob, obstacles, clearance, inset_range=EDGE_INSET_RANGE):
    """Finds a grass spot between the field blob and the rim, preferring hex corners where the ring is widest.

    Returns (x, y, angle) or None. angle is the polar direction of the spot (useful to orient props).
    """
    for _ in range(EDGE_ATTEMPTS):
        corner = hexgrid.corner(rng.randrange(hexgrid.SIDE_COUNT))
        angle = math.atan2(corner.y, corner.x) + rng.uniform(-EDGE_ANGLE_JITTER, EDGE_ANGLE_JITTER)
        direction = unit(angle)
        wanted_inset = rng.uniform(*inset_range)
        for step in range(int(hexgrid.TILE_RADIUS / EDGE_SCAN_STEP)):
            radius = hexgrid.TILE_RADIUS - step * EDGE_SCAN_STEP
            x, y = direction.x * radius, direction.y * radius
            if hexgrid.inset_distance(x, y) < wanted_inset:
                continue
            blob_angle = math.atan2(y - blob.center.y, x - blob.center.x)
            if math.hypot(x - blob.center.x, y - blob.center.y) < blob.boundary(blob_angle) + clearance:
                break
            if obstacles.clear(x, y, clearance):
                return x, y, angle
            break
    return None


def add_square_stack(builder, rng, x, y, angle, height_at):
    """Adds two square bales side by side with a third on top (30 tris), oriented across angle."""
    rotation = angle + math.pi * 0.5
    side = unit(angle) * (farm_props.SQUARE_BALE_SIZE[1] * 0.55)
    base = height_at(x, y)
    farm_props.add_square_hay_bale(builder, rng, x - side.x, y - side.y, base, rotation)
    top = farm_props.add_square_hay_bale(builder, rng, x + side.x, y + side.y, base, rotation)
    farm_props.add_square_hay_bale(builder, rng, x, y, base, rotation + rng.uniform(-0.2, 0.2), top - base)


def add_edge_hay(builder, rng, blob, height_at, obstacles, round_bales, square_stacks, budget):
    """Places round bales and stacked square bales on the grass between the field and the rim."""
    for _ in range(round_bales):
        spot = edge_spot(rng, blob, obstacles, HAY_CLEARANCE)
        if spot and woodland.fits_budget(builder, farm_props.ROUND_BALE_TRIANGLES, budget):
            kit.add_round_hay_bale(builder, rng, spot[0], spot[1], height_at(spot[0], spot[1]))
            obstacles.add(spot[0], spot[1], HAY_CLEARANCE)
    for _ in range(square_stacks):
        spot = edge_spot(rng, blob, obstacles, HAY_CLEARANCE)
        if spot is None or not woodland.fits_budget(builder, 3 * farm_props.SQUARE_BALE_TRIANGLES, budget):
            continue
        add_square_stack(builder, rng, spot[0], spot[1], spot[2], height_at)
        obstacles.add(spot[0], spot[1], HAY_CLEARANCE)


def field_face_style(blob, patches, grass, extra=None):
    """Returns face_style(centroid, rng): extra(centroid) override first, then the first accepting patch, else grass.

    patches: list of (StripedPatch, accept(x, y)).
    """
    def face_style(centroid, face_rng):
        if extra is not None:
            style = extra(centroid)
            if style is not None:
                return style
        if blob.contains(centroid.x, centroid.y):
            for patch, accept in patches:
                if accept(centroid.x, centroid.y):
                    return materials.PALETTE_MATERIAL, patch.uv
        return grass.style(centroid, face_rng)
    return face_style


def rotor_children(obj):
    """Child rotor mesh objects of a tile, sorted by name."""
    return sorted((child for child in obj.children if child.name.startswith(ROTOR_PREFIX)), key=lambda c: c.name)


def validate_tile(obj, spec):
    """Runs the standard validation, then adds rotor checks (tile + rotor tris within budget, rotor heights,
    rotor footprint, pivot at hub, spin action present) and rewrites the JSON report."""
    report = validate.validate_object(obj, spec)
    rotors = rotor_children(obj)
    if not rotors:
        return report
    checks = report["checks"]
    rotor_triangles = sum(sum(len(p.vertices) - 2 for p in rotor.data.polygons) for rotor in rotors)
    total = report["triangles"] + rotor_triangles
    checks.append({"check": "triangle_budget_with_rotors", "ok": total <= spec.triangle_budget,
                   "detail": f"{total} / {spec.triangle_budget} ({rotor_triangles} in {len(rotors)} rotors)"})
    top = max((rotor.matrix_world @ v.co).z for rotor in rotors for v in rotor.data.vertices)
    checks.append({"check": "rotor_height", "ok": top <= hexgrid.MAX_DECOR_HEIGHT + validate.POSITION_EPSILON,
                   "detail": f"max rotor z {top:.2f} (limit {hexgrid.MAX_DECOR_HEIGHT})"})
    inset = min(hexgrid.inset_distance(*(rotor.matrix_world @ v.co).xy) for rotor in rotors
                for v in rotor.data.vertices)
    checks.append({"check": "rotor_inside_tile", "ok": inset >= woodland.TRUNK_MIN_INSET,
                   "detail": f"min rotor inset {inset:.2f} m"})
    pivot_errors = []
    for rotor in rotors:
        count = len(rotor.data.vertices)
        center = sum((v.co for v in rotor.data.vertices), Vector((0.0, 0.0, 0.0))) / count
        if abs(center.y) > 0.05 or abs(center.z) > 0.05:
            pivot_errors.append(f"{rotor.name} off-axis {tuple(round(c, 3) for c in center)}")
        action = rotor.animation_data.action if rotor.animation_data else None
        if action is None or not action.name.startswith("A_"):
            pivot_errors.append(f"{rotor.name} missing A_ action")
    checks.append({"check": "rotor_pivot_and_action", "ok": not pivot_errors,
                   "detail": "; ".join(pivot_errors) or f"{[r.name for r in rotors]} pivots at hub, action "
                                                        f"{rotors[0].animation_data.action.name}"})
    report["triangles_with_rotors"] = total
    report["passed"] = all(check["ok"] for check in checks)
    with open(os.path.join(paths.asset_render_dir(spec.asset_id), "validation.json"), "w") as handle:
        json.dump(report, handle, indent=2)
    status = "PASS" if report["passed"] else "FAIL"
    print(f"[bezi-art] validate {spec.asset_id} with rotors: {status} ({total} tris incl. rotors)")
    for check in checks[-4:]:
        print(f"[bezi-art]   {'ok  ' if check['ok'] else 'FAIL'} {check['check']}: {check['detail']}")
    return report


def _instance_with_children(source, location, rotation_steps):
    instance = preview.add_instance(source, location, rotation_steps)
    for child in rotor_children(source):
        copy = bpy.data.objects.new(f"{child.name}_inst", child.data)
        bpy.context.scene.collection.objects.link(copy)
        copy.parent = instance
        copy.location = child.location
        copy.rotation_euler = (math.radians(37.0 * rotation_steps), 0.0, 0.0)
    return instance


def rotation_sheet(spec):
    """Review render: the tile at rotation 0 in the center and at rotations 0..5 on its six neighbors.

    Shows every 60 degree rotation next to a same-type neighbor (game camera + top ortho). Rotors are included.
    """
    preview.reset_scene()
    source = preview.append_asset(spec.blend_path, spec.mesh_name)
    source.hide_render = True
    for child in source.children:
        child.hide_render = True
    _instance_with_children(source, Vector((0.0, 0.0, 0.0)), 0)
    for side in range(hexgrid.SIDE_COUNT):
        _instance_with_children(source, hexgrid.neighbor_center(side), side)
    out_dir = paths.asset_render_dir(spec.asset_id)
    origin = Vector((0.0, 0.0, 0.0))
    panels = [preview.render(preview.game_camera("CamRotGame", origin, ROTATION_SHEET_DISTANCE),
                             os.path.join(out_dir, "_r0.png")),
              preview.render(preview.top_camera("CamRotTop", origin, ROTATION_TOP_SCALE),
                             os.path.join(out_dir, "_r1.png"))]
    return preview.stitch(panels, os.path.join(out_dir, ROTATION_SHEET_NAME))
