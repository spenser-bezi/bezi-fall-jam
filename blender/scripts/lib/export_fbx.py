"""Unity-ready FBX export (Art Workflow 3.5)."""
import os

import bpy

from . import paths


def export_object(obj, filepath, animated=False):
    """Exports one object (plus its children) to FBX with the pipeline's Unity settings."""
    paths.ensure_dir(os.path.dirname(filepath))
    for other in bpy.context.view_layer.objects:
        other.select_set(False)
    obj.select_set(True)
    for child in obj.children_recursive:
        child.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(
        filepath=filepath,
        use_selection=True,
        object_types={"MESH", "ARMATURE", "EMPTY"},
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
        bake_anim=animated,
    )
    print(f"[bezi-art] exported {filepath}")
    return filepath
