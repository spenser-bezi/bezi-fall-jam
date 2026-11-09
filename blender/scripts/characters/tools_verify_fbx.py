"""Fresh-Blender re-import check for SK_Goose.fbx.

blender -b --factory-startup --python-exit-code 1 -P scripts/characters/tools_verify_fbx.py -- <fbx> <reference.json>

Checks the armature, bone names/count, both skinned meshes (triangles, vertex groups, armature modifier), that
every expected take came back, and that world-space bone positions of every take match the reference samples
written by goose.write_reference (which catches broken axis or bake_space_transform handling).
"""
import json
import math
import sys

import bpy

POSITION_TOLERANCE = 2e-3
REPORT_PREFIX = "[bezi-verify]"


def _arguments():
    argv = sys.argv[sys.argv.index("--") + 1:]
    return argv[0], argv[1]


def _take_name(action_name):
    parts = action_name.split("|")
    return parts[1] if len(parts) > 1 else action_name


def main():
    """Imports the FBX into an empty scene and compares it against the reference JSON."""
    fbx_path, reference_path = _arguments()
    with open(reference_path) as handle:
        reference = json.load(handle)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=fbx_path)
    scene = bpy.context.scene
    failures = []

    armatures = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    meshes = {o.name: o for o in bpy.data.objects if o.type == "MESH"}
    print(f"{REPORT_PREFIX} objects: {sorted(o.name + ':' + o.type for o in bpy.data.objects)}")
    if len(armatures) != 1:
        failures.append(f"expected 1 armature, found {len(armatures)}")
        print(f"{REPORT_PREFIX} FAIL " + "; ".join(failures))
        sys.exit(1)
    armature = armatures[0]
    for obj in [armature] + [o for o in bpy.data.objects if o.type == "MESH"]:
        rotation = tuple(round(math.degrees(a), 2) for a in obj.matrix_world.to_euler())
        print(f"{REPORT_PREFIX} node {obj.name}: world rotation {rotation} deg (importer axis conversion only "
              f"means +90 X here = identity node in the FBX), scale {tuple(round(s, 4) for s in obj.matrix_world.to_scale())}")
    bone_names = [b.name for b in armature.data.bones]
    print(f"{REPORT_PREFIX} armature {armature.name}: {len(bone_names)} bones {bone_names}")
    if sorted(bone_names) != sorted(reference["bones"]):
        failures.append(f"bones differ: {sorted(set(bone_names) ^ set(reference['bones']))}")

    for mesh_name, triangles in reference["meshes"].items():
        mesh = meshes.get(mesh_name)
        if mesh is None:
            failures.append(f"mesh {mesh_name} missing")
            continue
        imported_triangles = sum(len(p.vertices) - 2 for p in mesh.data.polygons)
        groups = sorted(g.name for g in mesh.vertex_groups)
        skinned = any(m.type == "ARMATURE" and m.object == armature for m in mesh.modifiers)
        print(f"{REPORT_PREFIX} mesh {mesh_name}: {imported_triangles} tris, parent "
              f"{mesh.parent.name if mesh.parent else None}, armature modifier {skinned}, groups {groups}")
        if imported_triangles != triangles:
            failures.append(f"{mesh_name} tris {imported_triangles} != {triangles}")
        if not skinned or not groups or not set(groups) <= set(bone_names):
            failures.append(f"{mesh_name} skinning broken")

    takes = {}
    for action in bpy.data.actions:
        if any(c.data_path.startswith("pose.bones") for c in action.fcurves):
            takes[_take_name(action.name)] = action
    print(f"{REPORT_PREFIX} fps {scene.render.fps}, takes {len(takes)}: "
          + ", ".join(f"{name} {tuple(int(f) for f in a.frame_range)}" for name, a in sorted(takes.items())))
    missing = sorted(set(reference["takes"]) - set(takes))
    extra = sorted(set(takes) - set(reference["takes"]))
    if missing or extra:
        failures.append(f"takes missing {missing}, extra {extra}")
    if scene.render.fps != reference["fps"]:
        failures.append(f"fps {scene.render.fps} != {reference['fps']}")

    if armature.animation_data is None:
        armature.animation_data_create()
    worst_overall = 0.0
    for take_name, take in reference["takes"].items():
        action = takes.get(take_name)
        if action is None:
            continue
        imported_first, imported_last = (int(round(f)) for f in action.frame_range)
        expected_length = take["last"] - take["first"]
        if imported_last - imported_first != expected_length:
            failures.append(f"{take_name} length {imported_last - imported_first} != {expected_length}")
        armature.animation_data.action = action
        worst = 0.0
        for frame_text, bones in take["samples"].items():
            scene.frame_set(imported_first + int(frame_text) - take["first"])
            for bone_name, (head, tail) in bones.items():
                pose_bone = armature.pose.bones[bone_name]
                world_head = armature.matrix_world @ pose_bone.head
                worst = max(worst, max(abs(a - b) for a, b in zip(world_head, head)))
        worst_overall = max(worst_overall, worst)
        print(f"{REPORT_PREFIX} take {take_name}: frames {imported_first}-{imported_last}, "
              f"max bone head error {worst * 1000.0:.3f} mm")
        if worst > POSITION_TOLERANCE:
            failures.append(f"{take_name} bone error {worst:.4f} m")

    status = "PASS" if not failures else "FAIL"
    print(f"{REPORT_PREFIX} {status}: {len(bone_names)} bones, {len(meshes)} meshes, {len(takes)} takes, "
          f"max bone error {worst_overall * 1000.0:.3f} mm" + ("" if not failures else " | " + "; ".join(failures)))
    if failures:
        sys.exit(1)


main()
