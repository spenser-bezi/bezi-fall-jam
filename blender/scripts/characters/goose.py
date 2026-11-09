"""SK_Goose: skinned low-poly Canada goose (Chicken Run style) with the leader's SM_Scarf and 7 actions.

Collection "SK_Goose":
    SK_Goose        armature (root object, pivot = body center, faces Blender -Y = Unity +Z)
    SK_Goose_Body   skinned body mesh
    SM_Scarf        skinned knitted scarf (leader only; prefabs toggle it)
Brows are bones (brow_L/R, children of head), not shape keys, so they ride the same FBX takes as the rig.
Run hooks: build, validate, export, preview.
"""
import json
import math
import os
import re
import subprocess

import bpy
from mathutils import Vector

import registry
from characters import goose_animation as animation
from characters import goose_geometry as geometry
from characters import goose_rig as rig
from lib import hexgrid, materials, palette, paths
from lib import preview as preview_lib

BODY_TRIANGLE_LIMIT = 1300
SCARF_TRIANGLE_LIMIT = 200
EXPECTED_BONE_COUNT = 18
WINGSPAN_TARGET = 2.5
WINGSPAN_TOLERANCE = 0.12
BEAK_MIN_FORWARD = 1.0  # beak tip must reach at least this far along Blender -Y
POSITION_EPSILON = 1e-4
LOOP_EPSILON = 1e-4
WEIGHT_SUM_EPSILON = 1e-3
ZERO_AREA_EPSILON = 1e-7
MAX_INFLUENCES = 4
SCARF_ALLOWED_BONES = set(rig.NECK_BONES) | {rig.BODY}

VERIFY_TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools_verify_fbx.py")
REFERENCE_SUFFIX = "_reference.json"
REFERENCE_SAMPLES_PER_ACTION = 4

PRIMARY_BONE_AXIS = "Y"  # keep Blender's bone frames: curves in Unity match the recipe's local axes
SECONDARY_BONE_AXIS = "X"

HERO_CAMERA_OFFSET = Vector((2.7, -3.3, 1.8))
HERO_TARGET = Vector((0.0, -0.2, 0.1))
STRIP_CAMERA_OFFSET = Vector((2.9, -3.6, 2.0))
ORTHO_SCALE = 3.0
ORTHO_DISTANCE = 20.0
PANEL_SIZE = (640, 480)
STRIP_PANEL_SIZE = (400, 300)
SHEET_COLUMNS = 3
STRIP_COLUMNS = 4
FORMATION_SIZE = (1280, 960)
FORMATION_ALTITUDE = 8.0
FORMATION_LATERAL = 2.8
FORMATION_BACK = 2.4
FORMATION_RANKS = 3
ONE_SHOT_STRIP_FRAMES = {"A_Goose_Honk": (1, 5, 8, 13), "A_Goose_Tumble": (6, 12, 19, 27)}
FORMATION_POSES = {  # (rank, side) -> (action, frame)
    (0, 0): ("A_Goose_Flap", 5),
    (1, 1): ("A_Goose_Flap", 9), (1, -1): ("A_Goose_Flap", 13),
    (2, 1): ("A_Goose_Glide", 1), (2, -1): ("A_Goose_Flap", 3),
    (3, 1): ("A_Goose_Glide", 20), (3, -1): ("A_Goose_Flap", 7),
}
WIRE_THICKNESS = 0.006
DATA_PATH_PATTERN = re.compile(r'pose\.bones\["(.+)"\]\.(\w+)')


def body_mesh_name(spec):
    """Returns the body mesh object name for a spec."""
    return spec.mesh_name + geometry.BODY_MESH_SUFFIX


# ------------------------------------------------------------------------------------------------ build


def build(spec, seed):
    """Builds the armature, body, scarf and actions. Returns the armature (named spec.mesh_name)."""
    scene = bpy.context.scene
    scene.render.fps = animation.FPS
    scene.render.fps_base = 1.0
    collection = bpy.data.collections.new(spec.mesh_name)
    scene.collection.children.link(collection)

    armature = rig.build_armature(spec.mesh_name, collection)
    geometry.build_body_builder().build_skinned_object(body_mesh_name(spec), collection, armature)
    geometry.build_scarf_builder(seed).build_skinned_object(geometry.SCARF_MESH_NAME, collection, armature)
    animation.bake_all(armature)
    scene.frame_start = animation.FIRST_FRAME
    scene.frame_end = max(animation.frame_range(s)[1] for s in animation.ACTIONS)
    return armature


# --------------------------------------------------------------------------------------------- validate


def _check(results, name, ok, detail):
    results.append({"check": name, "ok": bool(ok), "detail": detail})


def _is_identity(obj):
    return (obj.location.length < POSITION_EPSILON and max(abs(a) for a in obj.rotation_euler) < POSITION_EPSILON
            and max(abs(s - 1.0) for s in obj.scale) < POSITION_EPSILON)


def triangle_count(mesh):
    """Returns the triangle count of a mesh after triangulation."""
    return sum(len(polygon.vertices) - 2 for polygon in mesh.polygons)


def _shell_orientation_errors(mesh):
    """Counts closed shells whose signed volume is negative (faces pointing inward)."""
    parent = list(range(len(mesh.vertices)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for polygon in mesh.polygons:
        root = find(polygon.vertices[0])
        for vertex in polygon.vertices[1:]:
            other = find(vertex)
            if other != root:
                parent[other] = root
    volumes, open_shells, edge_use = {}, set(), {}
    for polygon in mesh.polygons:
        shell = find(polygon.vertices[0])
        points = [mesh.vertices[i].co for i in polygon.vertices]
        for k in range(1, len(points) - 1):
            volumes[shell] = volumes.get(shell, 0.0) + points[0].dot(points[k].cross(points[k + 1])) / 6.0
        for k, vertex in enumerate(polygon.vertices):
            edge = tuple(sorted((vertex, polygon.vertices[(k + 1) % len(polygon.vertices)])))
            edge_use[edge] = edge_use.get(edge, 0) + 1
    for edge, uses in edge_use.items():
        if uses != 2:
            open_shells.add(find(edge[0]))
    closed = [shell for shell in volumes if shell not in open_shells]
    inverted = sum(1 for shell in closed if volumes[shell] <= 0.0)
    return inverted, len(closed), len(open_shells)


def _mesh_checks(results, obj, armature, triangle_limit, allowed_bones, label):
    mesh = obj.data
    _check(results, f"{label}_parent", obj.parent == armature, f"parent {obj.parent.name if obj.parent else None}")
    modifiers = [m for m in obj.modifiers if m.type == "ARMATURE" and m.object == armature]
    _check(results, f"{label}_armature_modifier", len(modifiers) == 1, f"{len(modifiers)} armature modifiers")
    _check(results, f"{label}_transforms_applied", _is_identity(obj), "location 0, rotation 0, scale 1")
    triangles = triangle_count(mesh)
    _check(results, f"{label}_triangle_budget", triangles <= triangle_limit, f"{triangles} / {triangle_limit}")

    material_names = [m.name for m in mesh.materials if m is not None]
    _check(results, f"{label}_material_slots", material_names == [materials.PALETTE_MATERIAL],
           f"slots {material_names}")
    uv_layer = mesh.uv_layers.active
    bad_uv_faces = 0
    for polygon in mesh.polygons:
        regions = {palette.classify_uv(*uv_layer.data[i].uv) for i in polygon.loop_indices}
        if len(regions) != 1 or None in regions:
            bad_uv_faces += 1
    _check(results, f"{label}_uv_single_swatch", bad_uv_faces == 0, f"{bad_uv_faces} faces span or miss swatches")

    used = set()
    for polygon in mesh.polygons:
        used.update(polygon.vertices)
    loose = len(mesh.vertices) - len(used)
    _check(results, f"{label}_no_loose_vertices", loose == 0, f"{loose} loose")
    zero_area = sum(1 for p in mesh.polygons if p.area < ZERO_AREA_EPSILON)
    _check(results, f"{label}_no_zero_area_faces", zero_area == 0, f"{zero_area} zero-area faces")
    inverted, closed, open_count = _shell_orientation_errors(mesh)
    _check(results, f"{label}_normals_outward", inverted == 0 and open_count == 0,
           f"{inverted} inverted of {closed} closed shells, {open_count} open shells")
    flat = sum(1 for p in mesh.polygons if p.use_smooth)
    _check(results, f"{label}_flat_shaded", flat == 0, f"{flat} smooth faces")

    group_names = {group.index: group.name for group in obj.vertex_groups}
    bone_names = set(armature.data.bones.keys())
    unknown_groups = sorted(set(group_names.values()) - bone_names)
    unweighted, too_many, bad_sum, disallowed = 0, 0, 0, set()
    for vertex in mesh.vertices:
        weights = [(group_names[g.group], g.weight) for g in vertex.groups if g.weight > 0.0]
        if not weights:
            unweighted += 1
            continue
        if len(weights) > MAX_INFLUENCES:
            too_many += 1
        if abs(sum(w for _, w in weights) - 1.0) > WEIGHT_SUM_EPSILON:
            bad_sum += 1
        disallowed.update(name for name, _ in weights if allowed_bones is not None and name not in allowed_bones)
    _check(results, f"{label}_skin_weights",
           not (unknown_groups or unweighted or too_many or bad_sum or disallowed),
           f"unknown groups {unknown_groups}, unweighted {unweighted}, >{MAX_INFLUENCES} influences {too_many}, "
           f"unnormalized {bad_sum}, disallowed bones {sorted(disallowed)}")
    return triangles


def _pose_values(action, frame):
    return [curve.evaluate(frame) for curve in action.fcurves]


def _action_checks(results, armature):
    animation_data = armature.animation_data
    names = rig.bone_names()
    expected_paths = {f'pose.bones["{b}"].{path}' for b in names for path, _ in animation.CHANNELS}
    tracks = {t.name: t for t in animation_data.nla_tracks} if animation_data else {}
    glide = bpy.data.actions.get("A_Goose_Glide")
    glide_start = _pose_values(glide, animation.FIRST_FRAME) if glide else None
    summaries = []
    for spec in animation.ACTIONS:
        action = bpy.data.actions.get(spec.name)
        if action is None:
            _check(results, f"action_{spec.name}", False, "missing")
            continue
        first, last = animation.frame_range(spec)
        paths_keyed = {c.data_path for c in action.fcurves}
        curves_per_bone = sum(size for _, size in animation.CHANNELS)
        complete = paths_keyed == expected_paths and len(action.fcurves) == len(names) * curves_per_bone
        range_ok = tuple(action.frame_range) == (float(first), float(last))
        track = tracks.get(spec.name)
        strip_ok = bool(track and len(track.strips) == 1 and track.strips[0].action == action
                        and track.strips[0].name == spec.name)
        start_values, end_values = _pose_values(action, first), _pose_values(action, last)
        if spec.loop:
            seam_error = max(abs(a - b) for a, b in zip(start_values, end_values))
            seam_ok = seam_error < LOOP_EPSILON
            seam_detail = f"loop seam error {seam_error:.2e}"
        else:
            start_error = max(abs(a - b) for a, b in zip(start_values, glide_start))
            end_error = max(_turn_wrapped_difference(a, b) for a, b in zip(end_values, glide_start))
            seam_ok = start_error < LOOP_EPSILON and end_error < LOOP_EPSILON
            seam_detail = f"start/end vs glide pose {start_error:.2e}/{end_error:.2e}"
        _check(results, f"action_{spec.name}", complete and range_ok and strip_ok and seam_ok and action.use_fake_user,
               f"frames {first}-{last}, loop {spec.loop}, all bones keyed {complete}, range {range_ok}, "
               f"nla strip {strip_ok}, fake user {action.use_fake_user}, {seam_detail}")
        summaries.append({"name": spec.name, "frames": [first, last], "loop": spec.loop})
    extra = sorted(a.name for a in bpy.data.actions if a.name not in animation.ACTION_NAMES)
    _check(results, "no_extra_actions", not extra, f"extra {extra}")
    return summaries


def _turn_wrapped_difference(value, target):
    """Absolute difference ignoring whole turns, so the tumble's final 360 degree roll matches its start."""
    difference = value - target
    return abs(difference - round(difference / (2.0 * math.pi)) * 2.0 * math.pi)


def validate(obj, spec):
    """Validates the goose rig, both meshes and all actions. Writes validation.json; returns the report."""
    results = []
    armature = obj
    collection = bpy.data.collections.get(spec.mesh_name)
    _check(results, "root_is_armature", armature.type == "ARMATURE" and armature.name == spec.mesh_name,
           f"{armature.name} ({armature.type})")
    _check(results, "collection", collection is not None and armature.name in collection.objects,
           f"collection {spec.mesh_name}")
    _check(results, "armature_transforms_applied", _is_identity(armature), "location 0, rotation 0, scale 1")
    _check(results, "fps", bpy.context.scene.render.fps == animation.FPS, f"{bpy.context.scene.render.fps} fps")

    bones = armature.data.bones
    expected = rig.bone_layout()
    hierarchy_ok = all(name in bones and ((bones[name].parent.name if bones[name].parent else None) == parent)
                       for name, _, _, parent, _, _ in expected)
    _check(results, "bone_hierarchy", hierarchy_ok and len(bones) == EXPECTED_BONE_COUNT,
           f"{len(bones)} bones (expected {EXPECTED_BONE_COUNT}), hierarchy {hierarchy_ok}")
    pivot_ok = bones[rig.ROOT].head_local.length < POSITION_EPSILON and \
        bones[rig.BODY].head_local.length < POSITION_EPSILON
    _check(results, "pivot_body_center", pivot_ok, "root and body bones at the origin")

    body = bpy.data.objects.get(body_mesh_name(spec))
    scarf = bpy.data.objects.get(geometry.SCARF_MESH_NAME)
    _check(results, "meshes_present", body is not None and scarf is not None,
           f"{body_mesh_name(spec)} {body is not None}, {geometry.SCARF_MESH_NAME} {scarf is not None}")
    body_triangles = _mesh_checks(results, body, armature, BODY_TRIANGLE_LIMIT, None, "body") if body else 0
    scarf_triangles = _mesh_checks(results, scarf, armature, SCARF_TRIANGLE_LIMIT, SCARF_ALLOWED_BONES,
                                   "scarf") if scarf else 0
    total = body_triangles + scarf_triangles
    _check(results, "total_triangle_budget", total <= spec.triangle_budget, f"{total} / {spec.triangle_budget}")

    if body:
        xs = [v.co.x for v in body.data.vertices]
        ys = [v.co.y for v in body.data.vertices]
        span = max(xs) - min(xs)
        _check(results, "wingspan", abs(span - WINGSPAN_TARGET) <= WINGSPAN_TOLERANCE,
               f"{span:.2f} m (target {WINGSPAN_TARGET} +/- {WINGSPAN_TOLERANCE})")
        _check(results, "faces_unity_forward", -min(ys) >= BEAK_MIN_FORWARD and -min(ys) > max(ys),
               f"beak tip y {min(ys):.2f}, tail y {max(ys):.2f} (forward = Blender -Y = Unity +Z)")
    names_ok = spec.mesh_name.startswith("SK_") and geometry.SCARF_MESH_NAME.startswith("SM_") and \
        all(name.startswith("A_") for name in animation.ACTION_NAMES)
    _check(results, "naming", names_ok, "SK_/SM_ meshes, A_ actions")
    action_summaries = _action_checks(results, armature)

    report = {
        "asset": spec.asset_id,
        "mesh": spec.mesh_name,
        "triangles": {"body": body_triangles, "scarf": scarf_triangles, "total": total},
        "bones": rig.bone_names(),
        "actions": action_summaries,
        "passed": all(r["ok"] for r in results),
        "checks": results,
    }
    out_path = os.path.join(paths.asset_render_dir(spec.asset_id), "validation.json")
    with open(out_path, "w") as handle:
        json.dump(report, handle, indent=2)
    status = "PASS" if report["passed"] else "FAIL"
    print(f"[bezi-art] validate {spec.asset_id}: {status} (body {body_triangles} + scarf {scarf_triangles} tris)")
    for result in results:
        if not result["ok"]:
            print(f"[bezi-art]   FAIL {result['check']}: {result['detail']}")
    return report


# ----------------------------------------------------------------------------------------------- export


def _reference_frames(spec):
    first, last = animation.frame_range(spec)
    step = (last - first) / (REFERENCE_SAMPLES_PER_ACTION - 1)
    return sorted({int(round(first + step * k)) for k in range(REFERENCE_SAMPLES_PER_ACTION)})


def write_reference(armature, spec, filepath):
    """Samples world-space bone heads/tails per action so the FBX re-import can be compared against them."""
    reference = {"armature": armature.name, "bones": rig.bone_names(), "fps": animation.FPS, "meshes": {},
                 "takes": {}}
    for child in armature.children:
        if child.type == "MESH":
            reference["meshes"][child.name] = triangle_count(child.data)
    for action_spec in animation.ACTIONS:
        first, last = animation.frame_range(action_spec)
        samples = {}
        for frame in _reference_frames(action_spec):
            animation.show_action(armature, action_spec.name, frame)
            samples[str(frame)] = {bone.name: [list(armature.matrix_world @ bone.head),
                                               list(armature.matrix_world @ bone.tail)]
                                   for bone in armature.pose.bones}
        reference["takes"][action_spec.name] = {"first": first, "last": last, "loop": action_spec.loop,
                                                "samples": samples}
    animation.restore_export_state(armature)
    bpy.context.scene.frame_set(animation.FIRST_FRAME)
    with open(filepath, "w") as handle:
        json.dump(reference, handle)
    return filepath


def export(obj, spec, filepath):
    """Exports armature + both meshes with one FBX take per action, then verifies it in a fresh Blender."""
    armature = obj
    paths.ensure_dir(os.path.dirname(filepath))
    reference_path = os.path.join(paths.asset_render_dir(spec.asset_id), spec.mesh_name + REFERENCE_SUFFIX)
    write_reference(armature, spec, reference_path)
    animation.restore_export_state(armature)

    for other in bpy.context.view_layer.objects:
        other.select_set(False)
    armature.select_set(True)
    for child in armature.children:
        child.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.fbx(
        filepath=filepath,
        use_selection=True,
        object_types={"MESH", "ARMATURE"},
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_ALL",
        axis_forward="-Z",
        axis_up="Y",
        bake_space_transform=True,
        mesh_smooth_type="FACE",
        use_mesh_modifiers=False,
        use_triangles=True,
        add_leaf_bones=False,
        primary_bone_axis=PRIMARY_BONE_AXIS,
        secondary_bone_axis=SECONDARY_BONE_AXIS,
        use_armature_deform_only=False,
        armature_nodetype="NULL",
        path_mode="STRIP",
        bake_anim=True,
        bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=True,
        bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True,
        bake_anim_step=1.0,
        bake_anim_simplify_factor=0.0,
    )
    print(f"[bezi-art] exported {filepath}")
    verify_fbx(filepath, reference_path)
    return filepath


def verify_fbx(filepath, reference_path):
    """Re-imports the FBX in a separate factory-startup Blender and raises if any check fails."""
    command = [bpy.app.binary_path, "-b", "--factory-startup", "--python-exit-code", "1", "-P", VERIFY_TOOL,
               "--", filepath, reference_path]
    completed = subprocess.run(command, capture_output=True, text=True)
    for line in completed.stdout.splitlines():
        if line.startswith("[bezi-verify]"):
            print(line)
    if completed.returncode != 0:
        print(completed.stdout[-4000:])
        print(completed.stderr[-4000:])
        raise RuntimeError(f"FBX re-import verification failed for {filepath}")


# ---------------------------------------------------------------------------------------------- preview


def _load_goose(spec):
    armature = preview_lib.append_asset(spec.blend_path, spec.mesh_name)
    for material in bpy.data.materials:
        material.use_backface_culling = True  # catches inverted faces the way Unity will
    meshes = [child for child in armature.children if child.type == "MESH"]
    return armature, meshes


def _hero_camera(name, offset=HERO_CAMERA_OFFSET):
    return preview_lib.make_camera(name, HERO_TARGET + offset, HERO_TARGET)


def _ortho_camera(name, direction):
    location = HERO_TARGET + Vector(direction) * ORTHO_DISTANCE
    return preview_lib.make_camera(name, location, HERO_TARGET, ortho_scale=ORTHO_SCALE)


def contact_sheet(spec):
    """Game view (45 m), hero 3/4, front, side, top and clay wireframe panels in one sheet."""
    preview_lib.reset_scene()
    armature, meshes = _load_goose(spec)
    animation.show_action(armature, "A_Goose_Glide", animation.FIRST_FRAME)
    out_dir = paths.asset_render_dir(spec.asset_id)
    wires = []
    for mesh in meshes:
        wire = mesh.copy()
        bpy.context.scene.collection.objects.link(wire)
        modifier = wire.modifiers.new("Wire", "WIREFRAME")
        modifier.thickness = WIRE_THICKNESS
        wire.color = preview_lib.WIRE_COLOR
        wire.hide_render = True
        wires.append(wire)
    origin = Vector((0.0, 0.0, 0.0))
    panels = [
        preview_lib.render(preview_lib.game_camera("CamGame", origin, preview_lib.GAME_DISTANCE),
                       os.path.join(out_dir, "_s0.png"), size=PANEL_SIZE),
        preview_lib.render(_hero_camera("CamHero"), os.path.join(out_dir, "_s1.png"), size=PANEL_SIZE),
        preview_lib.render(_ortho_camera("CamFront", (0.0, -1.0, 0.0)), os.path.join(out_dir, "_s2.png"),
                       size=PANEL_SIZE),
        preview_lib.render(_ortho_camera("CamSide", (1.0, 0.0, 0.0)), os.path.join(out_dir, "_s3.png"),
                       size=PANEL_SIZE),
        preview_lib.render(preview_lib.top_camera("CamTop", HERO_TARGET, ORTHO_SCALE), os.path.join(out_dir, "_s4.png"),
                       size=PANEL_SIZE),
    ]
    for mesh in meshes:
        mesh.color = preview_lib.CLAY_COLOR
    for wire in wires:
        wire.hide_render = False
    panels.append(preview_lib.render(_hero_camera("CamWire"), os.path.join(out_dir, "_s5.png"),
                                 engine=preview_lib.ENGINE_WORKBENCH, size=PANEL_SIZE))
    return preview_lib.stitch(panels, os.path.join(out_dir, "contact_sheet.png"), columns=SHEET_COLUMNS)


def strip_frames(action_spec):
    """Returns the 4 frames shown in an action's pose strip."""
    if action_spec.name in ONE_SHOT_STRIP_FRAMES:
        return ONE_SHOT_STRIP_FRAMES[action_spec.name]
    first, _ = animation.frame_range(action_spec)
    return tuple(first + action_spec.frame_count * k // STRIP_COLUMNS for k in range(STRIP_COLUMNS))


def pose_strips(spec):
    """One row of 4 key frames per action (rows in ACTIONS order) in a single sheet."""
    preview_lib.reset_scene()
    armature, _ = _load_goose(spec)
    out_dir = paths.asset_render_dir(spec.asset_id)
    camera = _hero_camera("CamStrip", STRIP_CAMERA_OFFSET)
    panels = []
    for action_spec in animation.ACTIONS:
        for frame in strip_frames(action_spec):
            animation.show_action(armature, action_spec.name, frame)
            name = f"_{action_spec.name}_{frame:02d}.png"
            panels.append(preview_lib.render(camera, os.path.join(out_dir, name), size=STRIP_PANEL_SIZE))
    return preview_lib.stitch(panels, os.path.join(out_dir, "pose_strips.png"), columns=STRIP_COLUMNS)


def apply_action_pose(armature, action_name, frame):
    """Writes an action's values at frame straight onto an armature's pose bones (no action assigned)."""
    action = bpy.data.actions[action_name]
    for curve in action.fcurves:
        match = DATA_PATH_PATTERN.match(curve.data_path)
        bone_name, prop = match.group(1), match.group(2)
        getattr(armature.pose.bones[bone_name], prop)[curve.array_index] = curve.evaluate(frame)


def _duplicate_goose(armature, meshes):
    copy = armature.copy()
    bpy.context.scene.collection.objects.link(copy)
    copies = []
    for mesh in meshes:
        mesh_copy = mesh.copy()
        mesh_copy.parent = copy
        mesh_copy.modifiers["Armature"].object = copy
        bpy.context.scene.collection.objects.link(mesh_copy)
        copies.append(mesh_copy)
    return copy, copies


def formation_render(spec, seed):
    """Game-camera render of a 7-goose V (leader with scarf) at 8 m over a tile.base flower."""
    preview_lib.reset_scene()
    tile_spec = registry.ASSETS["tile.base"]
    tile = preview_lib.append_asset(tile_spec.blend_path, tile_spec.mesh_name)
    for side in range(hexgrid.SIDE_COUNT):
        preview_lib.add_instance(tile, hexgrid.neighbor_center(side), side)
    armature, meshes = _load_goose(spec)
    armature.animation_data_clear()
    geese = []
    for rank in range(FORMATION_RANKS + 1):
        for side in ((0,) if rank == 0 else (1, -1)):
            if rank == 0:
                goose, goose_meshes = armature, meshes
            else:
                goose, goose_meshes = _duplicate_goose(armature, meshes)
            goose.location = (side * rank * FORMATION_LATERAL, rank * FORMATION_BACK, FORMATION_ALTITUDE)
            for mesh in goose_meshes:
                if mesh.name.startswith(geometry.SCARF_MESH_NAME) and rank > 0:
                    mesh.hide_render = True
            geese.append((goose, FORMATION_POSES[(rank, side)]))
    for goose, (action_name, frame) in geese:
        apply_action_pose(goose, action_name, frame)
    leader = Vector((0.0, 0.0, FORMATION_ALTITUDE))
    out_path = os.path.join(paths.asset_render_dir(spec.asset_id), "formation_game_view.png")
    preview_lib.render(preview_lib.game_camera("CamFormation", leader, preview_lib.GAME_DISTANCE), out_path,
                   size=FORMATION_SIZE)
    print(f"[bezi-art] preview written: {out_path}")
    return out_path


def preview(spec, seed):
    """Writes the contact sheet, pose strips and the V-formation game view."""
    return [contact_sheet(spec), pose_strips(spec), formation_render(spec, seed)]
