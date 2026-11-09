"""Fresh-Blender re-import check for the wind farm tile FBX.

blender -b --factory-startup --python-exit-code 1 -P scripts/tiles/farm_windfarm_verify.py -- <fbx> <reference.json>

Checks that the tile mesh, every Rotor_* object (parented to the tile) and every SOCKET_* empty came back, that each
rotor carries the A_Windpump_Spin take with the expected length at the expected fps, and that the baked world-space
rotor vertex positions match the reference samples (catches broken axis / bake_space_transform handling).
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
    return parts[-1]


def _max_unordered_error(expected, actual):
    """Largest distance from an expected point to its nearest imported point (vertex order may change on import)."""
    worst = 0.0
    for point in expected:
        best = min(sum((a - b) ** 2 for a, b in zip(point, other)) for other in actual)
        worst = max(worst, best ** 0.5)
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

    objects = {o.name: o for o in bpy.data.objects}
    print(f"{REPORT_PREFIX} objects: {sorted(o.name + ':' + o.type for o in bpy.data.objects)}")
    tile = objects.get(reference["tile"])
    if tile is None:
        failures.append(f"tile {reference['tile']} missing")
    else:
        triangles = sum(len(p.vertices) - 2 for p in tile.data.polygons)
        print(f"{REPORT_PREFIX} tile {tile.name}: {triangles} tris (expected {reference['tile_triangles']})")
        if triangles != reference["tile_triangles"]:
            failures.append(f"tile tris {triangles} != {reference['tile_triangles']}")
    sockets = sorted(name for name, o in objects.items() if name.startswith("SOCKET_") and o.type == "EMPTY")
    print(f"{REPORT_PREFIX} sockets: {sockets}")
    if sockets != reference["sockets"]:
        failures.append(f"sockets {sockets} != {reference['sockets']}")

    actions = {action.name: action for action in bpy.data.actions}
    print(f"{REPORT_PREFIX} fps {scene.render.fps}, actions: "
          + ", ".join(f"{name} {tuple(int(round(f)) for f in a.frame_range)}" for name, a in sorted(actions.items())))
    if scene.render.fps != reference["fps"]:
        failures.append(f"fps {scene.render.fps} != {reference['fps']}")

    for rotor_name, rotor_reference in sorted(reference["rotors"].items()):
        rotor = objects.get(rotor_name)
        if rotor is None or rotor.type != "MESH":
            failures.append(f"{rotor_name} missing")
            continue
        parent = rotor.parent.name if rotor.parent else None
        triangles = sum(len(p.vertices) - 2 for p in rotor.data.polygons)
        action = rotor.animation_data.action if rotor.animation_data else None
        take = _take_name(action.name) if action else None
        hub = tuple(round(c, 3) for c in rotor.matrix_world.translation)
        print(f"{REPORT_PREFIX} rotor {rotor_name}: parent {parent}, {triangles} tris, pivot {hub} "
              f"(expected {tuple(round(c, 3) for c in rotor_reference['hub'])}), take {take} "
              f"(action {action.name if action else None})")
        if parent != reference["tile"]:
            failures.append(f"{rotor_name} parent {parent}")
        if triangles != rotor_reference["triangles"]:
            failures.append(f"{rotor_name} tris {triangles} != {rotor_reference['triangles']}")
        if take != reference["take"]:
            failures.append(f"{rotor_name} take {take} != {reference['take']}")
            continue
        first, last = (int(round(f)) for f in action.frame_range)
        if last - first != reference["frame_count"]:
            failures.append(f"{rotor_name} take length {last - first} != {reference['frame_count']}")
        worst = 0.0
        for frame_text, expected in rotor_reference["samples"].items():
            scene.frame_set(first + int(frame_text))
            depsgraph = bpy.context.evaluated_depsgraph_get()
            evaluated = rotor.evaluated_get(depsgraph)
            actual = [list(evaluated.matrix_world @ v.co) for v in rotor.data.vertices]
            worst = max(worst, _max_unordered_error(expected, actual))
        print(f"{REPORT_PREFIX} rotor {rotor_name}: frames {first}-{last}, max baked vertex error "
              f"{worst * 1000.0:.3f} mm over frames {sorted(int(f) for f in rotor_reference['samples'])}")
        if worst > POSITION_TOLERANCE:
            failures.append(f"{rotor_name} vertex error {worst:.4f} m")

    status = "PASS" if not failures else "FAIL"
    print(f"{REPORT_PREFIX} {status}: {len(reference['rotors'])} rotors, take {reference['take']}"
          + ("" if not failures else " | " + "; ".join(failures)))
    if failures:
        sys.exit(1)


main()
