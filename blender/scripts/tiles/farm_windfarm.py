"""SM_Tile_WindFarm_A/_B: a patchwork field (three striped bands with different strips and row directions) with
short windpumps standing on the grass near the hex corners, plus SOCKET_Prop_Windmill_* empties on clear spots of
the field where WS2 may spawn the big windmill obstacle.

A: two windpumps, one windmill socket.  B: one windpump, two windmill sockets.
Each windpump rotor is a separate child object Rotor_01, Rotor_02 (pivot at the hub, spin axis local X) sharing the
looping action A_Windpump_Spin. The export hook bakes that animation into one FBX take and re-imports the FBX in a
fresh Blender to verify the rotor objects, the take and the baked rotor motion.
"""
import json
import math
import os
import random
import subprocess

import bpy

from lib import hexgrid, paths
from props import windpump
from tiles import common
from tiles import farm_common as farm
from tiles import woodland_common as woodland

HEIGHT_AMPLITUDE = 0.08
FIELD_HEIGHT_FACTOR = 0.3
BLOB_CENTER_JITTER = 0.3
BLOB_RADIUS = 5.6
BLOB_WOBBLE = 0.08
ROW_SPACING = 1.3
PATCH_STRIPS = ("FieldRows", "PlowedRows", "CornRows")
BAND_WIDTH = (3.2, 4.0)
PUMP_FIELD_CLEARANCE = 1.0
PUMP_PART_MIN_INSET = 1.0
PUMP_SCAN_STEP = 0.2
PUMP_SPACING = 4.0
PUMP_CLEARANCE = 1.4
PUMP_ANGLE_JITTER = 0.35
SOCKET_FIELD_MARGIN = 1.6
SOCKET_SPACING = 4.0
SOCKET_PUMP_SPACING = 3.5
SOCKET_CLEAR_RADIUS = 2.0
PLACEMENT_ATTEMPTS = 2000
SOCKET_NAME = "SOCKET_Prop_Windmill_{:02d}"
SOCKET_HOVER = 0.0
VERIFY_TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "farm_windfarm_verify.py")
REFERENCE_SUFFIX = "_rotor_reference.json"
REFERENCE_FRAMES = (0, 6, 12, 24, 36, 47, 48)
VERIFY_PREFIX = "[bezi-verify]"

VARIANTS = {
    woodland.VARIANT_A: {"pumps": 2, "sockets": 1, "round_bales": 2, "square_stacks": 0, "hedge_bushes": 4},
    woodland.VARIANT_B: {"pumps": 1, "sockets": 2, "round_bales": 1, "square_stacks": 1, "hedge_bushes": 5},
}


def _pump_extremes(x, y):
    """Planar points bounding a windpump at (x, y): tower legs, tail vane and rotor tips (rotor faces +X)."""
    half = windpump.TOWER_BASE_HALF
    vane_x = x - windpump.TAIL_LENGTH - windpump.VANE_SIZE[1] * 0.5
    rotor_x = x + windpump.HUB_FORWARD
    tip = windpump.rotor_tip_radius()
    return [(x + half, y + half), (x - half, y + half), (x - half, y - half), (x + half, y - half),
            (vane_x, y), (rotor_x, y + tip), (rotor_x, y - tip)]


def _place_pumps(rng, blob, count):
    """Finds grass spots near the hex corners (where the rim ring is widest) for count windpumps."""
    for _ in range(PLACEMENT_ATTEMPTS // 50):
        corners = list(range(hexgrid.SIDE_COUNT))
        rng.shuffle(corners)
        spots = []
        for corner_index in corners:
            if len(spots) >= count:
                break
            corner = hexgrid.corner(corner_index)
            angle = math.atan2(corner.y, corner.x) + rng.uniform(-PUMP_ANGLE_JITTER, PUMP_ANGLE_JITTER)
            for step in range(int(hexgrid.TILE_RADIUS / PUMP_SCAN_STEP)):
                radius = hexgrid.TILE_RADIUS - step * PUMP_SCAN_STEP
                x, y = radius * math.cos(angle), radius * math.sin(angle)
                if min(hexgrid.inset_distance(px, py) for px, py in _pump_extremes(x, y)) < PUMP_PART_MIN_INSET:
                    continue
                blob_angle = math.atan2(y - blob.center.y, x - blob.center.x)
                field_gap = math.hypot(x - blob.center.x, y - blob.center.y) - blob.boundary(blob_angle)
                if field_gap >= PUMP_FIELD_CLEARANCE + windpump.TOWER_BASE_HALF and all(
                        math.hypot(x - sx, y - sy) >= PUMP_SPACING for sx, sy in spots):
                    spots.append((x, y))
                break
        if len(spots) == count:
            return spots
    raise RuntimeError("could not place windpumps")


def _place_sockets(rng, blob, count, pumps):
    """Picks clear field spots for the big windmill obstacle sockets, away from the pumps and each other."""
    spots = []
    for _ in range(PLACEMENT_ATTEMPTS):
        if len(spots) >= count:
            break
        angle, distance = rng.uniform(0.0, 2.0 * math.pi), rng.uniform(0.0, blob.radius)
        x, y = blob.center.x + distance * math.cos(angle), blob.center.y + distance * math.sin(angle)
        if distance > blob.boundary(angle) - SOCKET_FIELD_MARGIN:
            continue
        if any(math.hypot(x - sx, y - sy) < SOCKET_SPACING for sx, sy in spots):
            continue
        if any(math.hypot(x - px, y - py) < SOCKET_PUMP_SPACING for px, py in pumps):
            continue
        spots.append((x, y))
    if len(spots) < count:
        raise RuntimeError("could not place windmill sockets")
    return spots


def build(spec, seed):
    """Builds a wind farm tile (variant from the mesh name suffix) with animated windpump rotors and windmill sockets."""
    variant = VARIANTS[woodland.variant_of(spec)]
    rng = random.Random(seed)
    grass = hexgrid.GrassPainter(seed)
    base_height = common.gentle_height(seed, amplitude=HEIGHT_AMPLITUDE)
    center = (rng.uniform(-BLOB_CENTER_JITTER, BLOB_CENTER_JITTER), rng.uniform(-BLOB_CENTER_JITTER, BLOB_CENTER_JITTER))
    blob = woodland.ContentBlob(seed + 5, BLOB_RADIUS, BLOB_WOBBLE, center)

    # Three parallel bands across the blob, each with its own strip and row direction (patchwork quilt).
    band_normal = farm.unit(math.radians(60.0 * rng.randrange(3)) + math.pi * 0.5)
    half_band = rng.uniform(*BAND_WIDTH) * 0.5
    shift = rng.uniform(-0.5, 0.5)
    lines = [farm.SplitLine(blob.center + band_normal * (shift - half_band), band_normal),
             farm.SplitLine(blob.center + band_normal * (shift + half_band), band_normal)]
    strips = list(PATCH_STRIPS)
    rng.shuffle(strips)
    first_row_angle = rng.randrange(3)
    band_tests = [lambda x, y: lines[0].side(x, y) < 0.0,
                  lambda x, y: lines[0].side(x, y) >= 0.0 > lines[1].side(x, y),
                  lambda x, y: lines[1].side(x, y) >= 0.0]
    patches = [(farm.StripedPatch(strip, math.radians(60.0 * ((first_row_angle + index) % 3)), ROW_SPACING,
                                  blob.center.copy()), band_tests[index]) for index, strip in enumerate(strips)]

    pump_spots = _place_pumps(rng, blob, variant["pumps"])
    socket_spots = _place_sockets(rng, blob, variant["sockets"], pump_spots)

    def height(x, y):
        value = base_height(x, y)
        return value * FIELD_HEIGHT_FACTOR if blob.contains(x, y) else value

    face_style = farm.field_face_style(blob, patches, grass)
    snap = farm.fold_free_snap(rng, height, farm.combined_snap(blob, lines))
    obstacles = farm.Obstacles()
    hubs = []

    def decorate(builder):
        budget = spec.triangle_budget
        for x, y in pump_spots:
            if woodland.fits_budget(builder, windpump.tower_triangles() + windpump.rotor_triangles(), budget):
                hubs.append(windpump.add_windpump_tower(builder, rng, x, y, height(x, y)))
            obstacles.add(x, y, PUMP_CLEARANCE)
        for x, y in socket_spots:
            obstacles.add(x, y, SOCKET_CLEAR_RADIUS)
        reserve = windpump.rotor_triangles() * len(hubs)
        farm.add_edge_hay(builder, rng, blob, height, obstacles, variant["round_bales"], variant["square_stacks"],
                          budget - reserve)
        farm.add_hedgerow(builder, rng, blob, height, variant["hedge_bushes"], obstacles, budget - reserve)

    tile = common.assemble_tile(spec, rng, face_style, height, decorate, snap)
    rotors = [windpump.create_rotor(index, tile, hub) for index, hub in enumerate(hubs, start=1)]
    windpump.assign_spin(rotors)
    farm.add_sockets(tile, SOCKET_NAME, [(x, y, height(x, y)) for x, y in socket_spots], SOCKET_HOVER)
    return tile


def validate(obj, spec):
    """Standard tile validation plus rotor checks (budget incl. rotors, heights, pivots, spin action)."""
    return farm.validate_tile(obj, spec)


def write_rotor_reference(obj, spec, reference_path):
    """Samples world-space rotor vertex positions over the loop (Blender space) for the re-import check."""
    scene = bpy.context.scene
    rotors = farm.rotor_children(obj)
    reference = {
        "tile": obj.name,
        "tile_triangles": sum(len(p.vertices) - 2 for p in obj.data.polygons),
        "fps": scene.render.fps,
        "take": windpump.SPIN_ACTION_NAME,
        "frame_count": windpump.SPIN_FRAME_COUNT,
        "sockets": sorted(child.name for child in obj.children if child.name.startswith("SOCKET_")),
        "rotors": {},
    }
    for rotor in rotors:
        samples = {}
        for frame in REFERENCE_FRAMES:
            scene.frame_set(windpump.SPIN_FRAME_START + frame)
            samples[str(frame)] = [list(rotor.matrix_world @ v.co) for v in rotor.data.vertices]
        reference["rotors"][rotor.name] = {
            "triangles": sum(len(p.vertices) - 2 for p in rotor.data.polygons),
            "hub": list(rotor.matrix_world.translation),
            "samples": samples,
        }
    scene.frame_set(windpump.SPIN_FRAME_START)
    with open(reference_path, "w") as handle:
        json.dump(reference, handle)
    return reference_path


def export(obj, spec, filepath):
    """Exports tile + rotors + sockets with the rotor spin baked into one FBX take named A_Windpump_Spin,
    then re-imports it in a fresh Blender and raises if the rotors, take or baked motion do not match."""
    paths.ensure_dir(os.path.dirname(filepath))
    reference_path = os.path.join(paths.asset_render_dir(spec.asset_id), spec.mesh_name + REFERENCE_SUFFIX)
    write_rotor_reference(obj, spec, reference_path)

    scene = bpy.context.scene
    original_scene_name = scene.name
    scene.name = windpump.SPIN_ACTION_NAME  # the exporter names the global take after the scene
    for other in bpy.context.view_layer.objects:
        other.select_set(False)
    obj.select_set(True)
    for child in obj.children_recursive:
        child.select_set(True)
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.export_scene.fbx(
            filepath=filepath,
            use_selection=True,
            object_types={"MESH", "EMPTY"},
            apply_unit_scale=True,
            apply_scale_options="FBX_SCALE_ALL",
            axis_forward="-Z",
            axis_up="Y",
            bake_space_transform=True,
            mesh_smooth_type="FACE",
            use_mesh_modifiers=True,
            use_triangles=True,
            add_leaf_bones=False,
            path_mode="STRIP",
            bake_anim=True,
            bake_anim_use_all_bones=False,
            bake_anim_use_nla_strips=False,
            bake_anim_use_all_actions=False,
            bake_anim_force_startend_keying=True,
            bake_anim_step=1.0,
            bake_anim_simplify_factor=0.0,
        )
    finally:
        scene.name = original_scene_name
    print(f"[bezi-art] exported {filepath}")
    verify_fbx(filepath, reference_path)
    return filepath


def verify_fbx(filepath, reference_path):
    """Re-imports the FBX in a separate factory-startup Blender and raises if any check fails."""
    command = [bpy.app.binary_path, "-b", "--factory-startup", "--python-exit-code", "1", "-P", VERIFY_TOOL,
               "--", filepath, reference_path]
    completed = subprocess.run(command, capture_output=True, text=True)
    for line in completed.stdout.splitlines():
        if line.startswith(VERIFY_PREFIX):
            print(line)
    if completed.returncode != 0:
        print(completed.stderr[-2000:])
        raise RuntimeError(f"FBX verification failed for {filepath}")
