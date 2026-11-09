"""Obstacle/snack validation and FBX export hooks layered on the generic pipeline checks.

validate_asset adds naming, socket, pivot, height/scale, sway, normal-winding and spin-clip checks to
lib.validate.validate_object and rewrites the JSON report. export_asset writes the FBX (one take per spin clip)
and, when the rules ask for it, re-imports it in a fresh Blender via obstacles/tools_verify_fbx.py.
"""
import json
import os
import subprocess

import bmesh
import bpy
from mathutils import Vector

from lib import export_fbx, paths
from lib import validate as base_validate
from obstacles import common

POSITION_TOLERANCE = 0.02
BASE_SINK_LIMIT = 0.3
BASE_CENTER_SLICE = 1.0
BASE_CENTER_TOLERANCE_FACTOR = 0.12
BASE_CENTER_TOLERANCE_MIN = 0.3
CENTER_TOLERANCE_FACTOR = 0.06
CENTER_TOLERANCE_MIN = 0.1
SPAN_LENGTH = 1.0
REFERENCE_SAMPLE_COUNT = 32
REFERENCE_SUFFIX = "_reference.json"
REPORT_PREFIX = "[bezi-art]"
VERIFY_TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools_verify_fbx.py")


def _check(results, name, ok, detail):
    results.append({"check": name, "ok": bool(ok), "detail": detail})


def bounds(obj):
    """Returns (min, max) Vectors of the mesh in object space."""
    xs, ys, zs = zip(*(tuple(v.co) for v in obj.data.vertices))
    return Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs)))


def _pivot_check(results, obj, rules, low, high):
    size = high - low
    center = (low + high) * 0.5
    if rules.pivot == common.PIVOT_BASE:
        base_vertices = [v.co for v in obj.data.vertices if v.co.z < low.z + BASE_CENTER_SLICE]
        base_low = Vector((min(v.x for v in base_vertices), min(v.y for v in base_vertices)))
        base_high = Vector((max(v.x for v in base_vertices), max(v.y for v in base_vertices)))
        base_center = (base_low + base_high) * 0.5
        tolerance = max(BASE_CENTER_TOLERANCE_MIN, BASE_CENTER_TOLERANCE_FACTOR * max(size.x, size.y))
        ok = -BASE_SINK_LIMIT <= low.z <= common_epsilon() and base_center.length <= tolerance
        detail = f"base center ({base_center.x:.2f}, {base_center.y:.2f}) tol {tolerance:.2f}, min z {low.z:.2f}"
    elif rules.pivot == common.PIVOT_CENTER:
        offset = center - Vector(rules.expected_center)
        tolerance = max(CENTER_TOLERANCE_MIN, CENTER_TOLERANCE_FACTOR * max(size))
        ok = offset.length <= tolerance
        detail = (f"bounds center ({center.x:.2f}, {center.y:.2f}, {center.z:.2f}) vs expected "
                  f"{tuple(rules.expected_center)} tol {tolerance:.2f}")
    elif rules.pivot == common.PIVOT_HUB:
        offset = Vector((center.x, center.z))
        tolerance = max(CENTER_TOLERANCE_MIN, CENTER_TOLERANCE_FACTOR * max(size))
        ok = offset.length <= tolerance and low.y <= 0.0 <= high.y
        detail = f"spin axis offset (x {center.x:.3f}, z {center.z:.3f}) tol {tolerance:.2f}, y {low.y:.2f}..{high.y:.2f}"
    elif rules.pivot == common.PIVOT_SPAN_START:
        ok = (abs(low.x) <= common_epsilon() and abs(high.x - SPAN_LENGTH) <= common_epsilon()
              and abs(center.y) <= common_epsilon())
        detail = f"x {low.x:.4f}..{high.x:.4f} (expect 0..{SPAN_LENGTH}), center y {center.y:.4f}"
    elif rules.pivot == common.PIVOT_TOP:
        top_vertices = [v.co for v in obj.data.vertices if v.co.z > high.z - BASE_CENTER_SLICE]
        top_low = Vector((min(v.x for v in top_vertices), min(v.y for v in top_vertices)))
        top_high = Vector((max(v.x for v in top_vertices), max(v.y for v in top_vertices)))
        offset = (top_low + top_high) * 0.5
        ok = abs(high.z) <= POSITION_TOLERANCE and offset.length <= BASE_CENTER_TOLERANCE_MIN
        detail = f"top z {high.z:.3f}, top attach xy offset {offset.length:.2f} tol {BASE_CENTER_TOLERANCE_MIN}"
    else:
        ok, detail = False, f"unknown pivot rule {rules.pivot}"
    _check(results, f"pivot_{rules.pivot}", ok, detail)


def common_epsilon():
    """Tolerance for exact pivot placements."""
    return base_validate.POSITION_EPSILON * 10.0


def _winding_checks(results, obj):
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    inconsistent = sum(1 for e in mesh.edges if len(e.link_faces) == 2 and not e.is_contiguous)
    over_shared = sum(1 for e in mesh.edges if len(e.link_faces) > 2)
    _check(results, "normals_consistent", inconsistent == 0 and over_shared == 0,
           f"{inconsistent} edges with flipped neighbours, {over_shared} edges shared by >2 faces")

    parent = list(range(len(mesh.verts)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for face in mesh.faces:
        first = find(face.verts[0].index)
        for vertex in face.verts[1:]:
            parent[find(vertex.index)] = first
    islands = {}
    for face in mesh.faces:
        islands.setdefault(find(face.verts[0].index), []).append(face)
    inward = 0
    for faces in islands.values():
        island_vertices = {v for f in faces for v in f.verts}
        center = sum((v.co for v in island_vertices), Vector()) / len(island_vertices)
        outwardness = sum((f.calc_center_median() - center).dot(f.normal) * f.calc_area() for f in faces)
        if outwardness < 0.0:
            inward += 1
    mesh.free()
    _check(results, "normals_outward", inward == 0, f"{inward} of {len(islands)} parts face inward")


def _spin_checks(results, obj, clip):
    track = obj.animation_data.nla_tracks.get(clip.name) if obj.animation_data else None
    action = bpy.data.actions.get(clip.name)
    if action is None or track is None or len(track.strips) != 1 or track.strips[0].action != action:
        _check(results, f"clip_{clip.name}", False, "missing action or NLA strip")
        return
    curves = list(action.fcurves)
    keyed = [(c.data_path, c.array_index) for c in curves]
    linear = all(p.interpolation == "LINEAR" for c in curves for p in c.keyframe_points)
    start, end = action.frame_range
    turn = curves[0].evaluate(end) - curves[0].evaluate(start) if curves else 0.0
    ok = (keyed == [("rotation_euler", common.SPIN_AXIS_INDEX)] and linear and action.use_fake_user
          and (start, end) == (float(common.FIRST_FRAME), float(clip.last_frame))
          and abs(abs(turn) - common.FULL_TURN) < 1e-5)
    _check(results, f"clip_{clip.name}", ok,
           f"curves {keyed}, linear {linear}, frames {int(start)}-{int(end)} ({clip.frame_count}), "
           f"turn {turn:.4f} rad, fake user {action.use_fake_user}")


def validate_asset(obj, spec, rules):
    """Runs the generic checks plus the obstacle rules; rewrites validation.json and returns the report."""
    report = base_validate.validate_object(obj, spec)
    results = report["checks"]
    low, high = bounds(obj)
    size = high - low

    children = sorted(child.name for child in obj.children)
    actions = sorted(a.name for a in bpy.data.actions)
    names_ok = (obj.name.startswith("SM_") and all(n.startswith("SOCKET_") for n in children)
                and all(a.startswith("A_") for a in actions))
    _check(results, "naming", names_ok, f"mesh {obj.name}, children {children}, actions {actions}")
    missing = sorted(set(rules.sockets) - set(children))
    _check(results, "sockets", not missing, f"expected {list(rules.sockets)}, missing {missing}")

    _pivot_check(results, obj, rules, low, high)
    low_h, high_h = rules.height_range
    _check(results, "height_range", low_h <= size.z <= high_h,
           f"height {size.z:.2f} m (allowed {low_h}-{high_h}); {rules.band_note}")
    low_d, high_d = rules.max_dimension_range
    _check(results, "max_dimension", low_d <= max(size) <= high_d,
           f"largest dimension {max(size):.2f} m (allowed {low_d}-{high_d})")

    sway_values = [0.0, 0.0, 0.0, 0.0] * len(obj.data.vertices)
    obj.data.color_attributes["Col"].data.foreach_get("color", sway_values)
    max_sway = max(sway_values[0::4]) if sway_values else 0.0
    _check(results, "sway_usage", (max_sway > 0.0) == rules.sway,
           f"max sway R {max_sway:.2f} (expected {'>0' if rules.sway else '0'})")

    _winding_checks(results, obj)
    if rules.spin is not None:
        _spin_checks(results, obj, rules.spin)
    elif actions:
        _check(results, "no_actions", False, f"unexpected actions {actions}")

    report["size"] = [round(size.x, 2), round(size.y, 2), round(size.z, 2)]
    report["bounds"] = {"min": [round(c, 3) for c in low], "max": [round(c, 3) for c in high]}
    report["pivot"] = rules.pivot
    report["band"] = rules.band_note
    report["sockets"] = {child.name: [round(c, 3) for c in child.matrix_world.translation]
                         for child in obj.children}
    report["passed"] = all(r["ok"] for r in results)
    out_path = os.path.join(paths.asset_render_dir(spec.asset_id), "validation.json")
    with open(out_path, "w") as handle:
        json.dump(report, handle, indent=2)
    status = "PASS" if report["passed"] else "FAIL"
    print(f"{REPORT_PREFIX} obstacle checks {spec.asset_id}: {status} {report['triangles']} tris, "
          f"size {report['size']} m, pivot {rules.pivot}")
    for result in results:
        if not result["ok"]:
            print(f"{REPORT_PREFIX}   FAIL {result['check']}: {result['detail']}")
    return report


# ------------------------------------------------------------------------------------------------ export


def _sample_indices(obj):
    count = len(obj.data.vertices)
    step = max(1, count // REFERENCE_SAMPLE_COUNT)
    return list(range(0, count, step))[:REFERENCE_SAMPLE_COUNT]


def _world_samples(obj, indices):
    matrix = obj.matrix_world
    return [[round(c, 5) for c in matrix @ obj.data.vertices[i].co] for i in indices]


def write_reference(obj, spec, rules, filepath):
    """Records triangles, socket positions and sampled world vertex positions per take for the re-import check."""
    scene = bpy.context.scene
    scene.frame_set(common.FIRST_FRAME)
    indices = _sample_indices(obj)
    reference = {
        "mesh": obj.name,
        "triangles": sum(len(p.vertices) - 2 for p in obj.data.polygons),
        "sockets": {child.name: [round(c, 5) for c in child.matrix_world.translation] for child in obj.children},
        "sample_indices": indices,
        "rest": _world_samples(obj, indices),
        "fps": scene.render.fps,
        "takes": {},
    }
    if rules.spin is not None:
        clip = rules.spin
        quarter = clip.frame_count // 4
        samples = {}
        for frame in range(common.FIRST_FRAME, clip.last_frame + 1, max(1, quarter)):
            scene.frame_set(frame)
            samples[str(frame)] = _world_samples(obj, indices)
        reference["takes"][clip.name] = {"first": common.FIRST_FRAME, "last": clip.last_frame, "samples": samples}
        scene.frame_set(common.FIRST_FRAME)
    with open(filepath, "w") as handle:
        json.dump(reference, handle)
    return filepath


def _export_animated(obj, filepath):
    paths.ensure_dir(os.path.dirname(filepath))
    for other in bpy.context.view_layer.objects:
        other.select_set(False)
    obj.select_set(True)
    for child in obj.children_recursive:
        child.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.context.scene.frame_set(common.FIRST_FRAME)
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
        bake_anim_use_nla_strips=True,
        bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True,
        bake_anim_step=1.0,
        bake_anim_simplify_factor=0.0,
    )
    print(f"{REPORT_PREFIX} exported {filepath} (animated)")


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


def export_asset(obj, spec, rules, filepath):
    """Exports the asset FBX (spin clips as named takes) and verifies the re-import when the rules ask for it."""
    reference_path = None
    if rules.verify_fbx or rules.spin is not None:
        reference_path = os.path.join(paths.asset_render_dir(spec.asset_id), spec.mesh_name + REFERENCE_SUFFIX)
        write_reference(obj, spec, rules, reference_path)
    if rules.spin is not None:
        _export_animated(obj, filepath)
    else:
        export_fbx.export_object(obj, filepath, animated=False)
    if reference_path:
        verify_fbx(filepath, reference_path)
    return filepath
