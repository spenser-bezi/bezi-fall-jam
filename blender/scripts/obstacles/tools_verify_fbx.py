"""Fresh-Blender re-import check for obstacle FBX files.

blender -b --factory-startup --python-exit-code 1 -P scripts/obstacles/tools_verify_fbx.py -- <fbx> <reference.json>

Checks the mesh came back with the same triangle count, every SOCKET_ empty is at its reference world position,
every expected take exists with the right length, and sampled world-space vertex positions match the reference at
rest and at every sampled frame of every take (catches broken axis, bake_space_transform or spin-axis handling).
"""
import json
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


def _max_error(obj, indices, expected):
    matrix = obj.matrix_world
    worst = 0.0
    for index, position in zip(indices, expected):
        world = matrix @ obj.data.vertices[index].co
        worst = max(worst, max(abs(a - b) for a, b in zip(world, position)))
    return worst


def main():
    """Imports the FBX into an empty scene and compares it against the reference JSON."""
    fbx_path, reference_path = _arguments()
    with open(reference_path) as handle:
        reference = json.load(handle)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=fbx_path)
    scene = bpy.context.scene
    failures = []
    print(f"{REPORT_PREFIX} file {fbx_path}")
    print(f"{REPORT_PREFIX} objects: {sorted(o.name + ':' + o.type for o in bpy.data.objects)}")

    obj = bpy.data.objects.get(reference["mesh"])
    if obj is None or obj.type != "MESH":
        print(f"{REPORT_PREFIX} FAIL mesh {reference['mesh']} missing")
        sys.exit(1)
    triangles = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{REPORT_PREFIX} mesh {obj.name}: {triangles} tris (reference {reference['triangles']}), "
          f"materials {[m.name for m in obj.data.materials if m]}")
    if triangles != reference["triangles"]:
        failures.append(f"tris {triangles} != {reference['triangles']}")

    for socket_name, position in reference["sockets"].items():
        socket = bpy.data.objects.get(socket_name)
        if socket is None:
            failures.append(f"socket {socket_name} missing")
            continue
        world = socket.matrix_world.translation
        error = max(abs(a - b) for a, b in zip(world, position))
        print(f"{REPORT_PREFIX} socket {socket_name}: parent {socket.parent.name if socket.parent else None}, "
              f"world {tuple(round(c, 3) for c in world)}, error {error * 1000.0:.3f} mm")
        if error > POSITION_TOLERANCE or socket.parent != obj:
            failures.append(f"socket {socket_name} error {error:.4f} m / parent")

    takes = {_take_name(a.name): a for a in bpy.data.actions}
    print(f"{REPORT_PREFIX} fps {scene.render.fps}, takes {len(takes)}: "
          + ", ".join(f"{name} {tuple(int(round(f)) for f in a.frame_range)}" for name, a in sorted(takes.items())))
    missing = sorted(set(reference["takes"]) - set(takes))
    extra = sorted(set(takes) - set(reference["takes"]))
    if missing or extra:
        failures.append(f"takes missing {missing}, extra {extra}")
    if reference["takes"] and scene.render.fps != reference["fps"]:
        failures.append(f"fps {scene.render.fps} != {reference['fps']}")

    indices = reference["sample_indices"]
    if not reference["takes"]:
        rest_error = _max_error(obj, indices, reference["rest"])
        print(f"{REPORT_PREFIX} rest pose max vertex error {rest_error * 1000.0:.3f} mm")
        if rest_error > POSITION_TOLERANCE:
            failures.append(f"rest vertex error {rest_error:.4f} m")

    worst_overall = 0.0
    for take_name, take in reference["takes"].items():
        action = takes.get(take_name)
        if action is None:
            continue
        first, last = (int(round(f)) for f in action.frame_range)
        if last - first != take["last"] - take["first"]:
            failures.append(f"{take_name} length {last - first} != {take['last'] - take['first']}")
        if obj.animation_data is None:
            obj.animation_data_create()
        obj.animation_data.action = action
        worst = 0.0
        for frame_text, expected in take["samples"].items():
            scene.frame_set(first + int(frame_text) - take["first"])
            worst = max(worst, _max_error(obj, indices, expected))
        worst_overall = max(worst_overall, worst)
        curves = sorted(f"{c.data_path}[{c.array_index}]" for c in action.fcurves)
        print(f"{REPORT_PREFIX} take {take_name}: frames {first}-{last}, curves {curves}, "
              f"max vertex error over {len(take['samples'])} sampled frames {worst * 1000.0:.3f} mm")
        if worst > POSITION_TOLERANCE:
            failures.append(f"{take_name} vertex error {worst:.4f} m")

    status = "PASS" if not failures else "FAIL"
    print(f"{REPORT_PREFIX} {status}: {obj.name}, {triangles} tris, {len(reference['sockets'])} sockets, "
          f"{len(takes)} takes, max take error {worst_overall * 1000.0:.3f} mm"
          + ("" if not failures else " | " + "; ".join(failures)))
    if failures:
        sys.exit(1)


main()
