"""Preview renders (Art Workflow 3.3): 4-panel contact sheets and tile seam cluster sheets."""
import math
import os
import random

import bpy
from mathutils import Matrix, Vector

from . import hexgrid, materials, palette, paths

PANEL_WIDTH = 640
PANEL_HEIGHT = 480
SHEET_COLUMNS = 2
RENDER_SAMPLES = 16
SHADOW_CASCADE_SIZE = "2048"

GAME_FOV_DEG = 35.0
GAME_PITCH_DEG = 50.0
GAME_DISTANCE = 45.0
WIDE_DISTANCE = 100.0
MIXED_DISTANCE = 135.0
CLOSE_DISTANCE = 30.0
SEAM_FOV_DEG = 55.0
TOP_ORTHO_SCALE = 23.0
SIDE_ORTHO_SCALE = 23.0
CORNER_ORTHO_SCALE = 9.0
CAMERA_HEIGHT = 80.0
SIDE_CAMERA_DISTANCE = 60.0
SIDE_CAMERA_HEIGHT = 1.5
SEAM_CAMERA_HEIGHT = 1.6
SEAM_CAMERA_BACK = 12.0
SEAM_TARGET_AHEAD = 4.0
MIXED_RING_COUNT = 2

SUN_ELEVATION_DEG = 32.0
SUN_AZIMUTH_DEG = 35.0
SUN_STRENGTH = 3.2
SUN_COLOR = (1.0, 0.88, 0.72)
SUN_ANGLE_RAD = 0.06
WORLD_STRENGTH = 0.85
GUIDE_THICKNESS = 0.06
GUIDE_LENGTH = 26.0
WIRE_THICKNESS = 0.035
CLAY_COLOR = (0.82, 0.80, 0.76, 1.0)
WIRE_COLOR = (0.08, 0.08, 0.10, 1.0)
SEPARATOR_PIXELS = 2

ENGINE_EEVEE = "BLENDER_EEVEE"
ENGINE_WORKBENCH = "BLENDER_WORKBENCH"
GAME_VIEW_DIRECTION = Vector((0.0, 1.0, 0.0))  # camera trails behind the flock (flight = Blender -Y)


def reset_scene():
    """Starts an empty scene with the preview render, world and sun settings."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.resolution_x = PANEL_WIDTH
    scene.render.resolution_y = PANEL_HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.eevee.taa_render_samples = RENDER_SAMPLES
    scene.eevee.use_gtao = True
    scene.eevee.use_soft_shadows = True
    scene.eevee.shadow_cascade_size = SHADOW_CASCADE_SIZE
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "OBJECT"

    world = bpy.data.worlds.new("PreviewWorld")
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (*palette.swatch_linear("CreamSky"), 1.0)
    background.inputs["Strength"].default_value = WORLD_STRENGTH
    scene.world = world

    sun_data = bpy.data.lights.new("PreviewSun", type="SUN")
    sun_data.energy = SUN_STRENGTH
    sun_data.color = SUN_COLOR
    sun_data.angle = SUN_ANGLE_RAD
    sun = bpy.data.objects.new("PreviewSun", sun_data)
    scene.collection.objects.link(sun)
    elevation, azimuth = math.radians(SUN_ELEVATION_DEG), math.radians(SUN_AZIMUTH_DEG)
    toward_sun = Vector((math.cos(elevation) * math.cos(azimuth), math.cos(elevation) * math.sin(azimuth),
                         math.sin(elevation)))
    sun.rotation_euler = (-toward_sun).to_track_quat("-Z", "Y").to_euler()
    return scene


def append_asset(blend_path, object_name):
    """Appends an asset into the current scene and returns its root object.

    If the .blend has a collection named object_name, the whole collection (root + children such as rotors)
    is appended; otherwise only the named object.
    """
    with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
        if object_name in data_from.collections:
            data_to.collections = [object_name]
        else:
            data_to.objects = [name for name in data_from.objects if name == object_name]
    if data_to.collections:
        collection = data_to.collections[0]
        bpy.context.scene.collection.children.link(collection)
        obj = collection.objects.get(object_name) or bpy.data.objects.get(object_name)
    elif data_to.objects:
        obj = data_to.objects[0]
        bpy.context.scene.collection.objects.link(obj)
    else:
        obj = None
    if obj is None:
        raise RuntimeError(f"{object_name} not found in {blend_path}")
    materials.relink_atlas_images()
    return obj


def add_instance(obj, location, rotation_steps):
    """Adds a linked duplicate rotated by rotation_steps x 60 degrees."""
    instance = bpy.data.objects.new(f"{obj.name}_inst", obj.data)
    bpy.context.scene.collection.objects.link(instance)
    instance.location = location
    instance.rotation_euler = (0.0, 0.0, math.radians(60.0 * rotation_steps))
    return instance


def look_at(obj, target, up=(0.0, 0.0, 1.0)):
    """Rotates a camera so it looks at target with the given world up."""
    forward = (Vector(target) - obj.location).normalized()
    right = forward.cross(Vector(up))
    if right.length < 1e-6:
        right = forward.cross(Vector((0.0, 1.0, 0.0)))
    right.normalize()
    true_up = right.cross(forward)
    obj.rotation_euler = Matrix((right, true_up, -forward)).transposed().to_euler()


def make_camera(name, location, target, up=(0.0, 0.0, 1.0), fov_deg=GAME_FOV_DEG, ortho_scale=None):
    """Creates a perspective (vertical FOV) or orthographic camera aimed at target."""
    data = bpy.data.cameras.new(name)
    data.clip_start = 0.1
    data.clip_end = 2000.0
    if ortho_scale:
        data.type = "ORTHO"
        data.ortho_scale = ortho_scale
    else:
        data.sensor_fit = "VERTICAL"
        data.angle_y = math.radians(fov_deg)
    camera = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = location
    look_at(camera, target, up)
    return camera


def game_camera(name, target, distance):
    """Camera at the GDD 5.1 gameplay angle (50 deg pitch, 35 deg FOV) trailing the flight direction."""
    pitch = math.radians(GAME_PITCH_DEG)
    offset = GAME_VIEW_DIRECTION * (distance * math.cos(pitch)) + Vector((0.0, 0.0, distance * math.sin(pitch)))
    return make_camera(name, Vector(target) + offset, target)


def top_camera(name, target, ortho_scale):
    """Orthographic top-down camera with Unity +Z (Blender -Y) pointing up in the image."""
    location = Vector(target) + Vector((0.0, 0.0, CAMERA_HEIGHT))
    return make_camera(name, location, target, up=(0.0, -1.0, 0.0), ortho_scale=ortho_scale)


def render(camera, filepath, engine=ENGINE_EEVEE, size=(PANEL_WIDTH, PANEL_HEIGHT)):
    """Renders the scene from camera into filepath."""
    scene = bpy.context.scene
    scene.camera = camera
    scene.render.engine = engine
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)
    return filepath


def stitch(panel_paths, out_path, columns=SHEET_COLUMNS):
    """Combines equally sized PNG panels into one grid image (row-major, top-left first)."""
    import numpy as np

    arrays = []
    for path in panel_paths:
        image = bpy.data.images.load(path, check_existing=False)
        width, height = image.size
        pixels = np.empty(width * height * 4, dtype=np.float32)
        image.pixels.foreach_get(pixels)
        arrays.append(pixels.reshape(height, width, 4))
        bpy.data.images.remove(image)
    height, width = arrays[0].shape[:2]
    rows = math.ceil(len(arrays) / columns)
    canvas = np.zeros((rows * height, columns * width, 4), dtype=np.float32)
    canvas[:, :, 3] = 1.0
    for index, array in enumerate(arrays):
        row, column = divmod(index, columns)
        y0 = (rows - 1 - row) * height  # Blender pixel rows start at the bottom
        canvas[y0:y0 + height, column * width:(column + 1) * width] = array
        canvas[y0:y0 + height, column * width:column * width + SEPARATOR_PIXELS, :3] = 0.0
        canvas[y0:y0 + SEPARATOR_PIXELS, column * width:(column + 1) * width, :3] = 0.0
    sheet = bpy.data.images.new("PreviewSheet", columns * width, rows * height, alpha=True)
    sheet.pixels.foreach_set(canvas.ravel())
    sheet.filepath_raw = out_path
    sheet.file_format = "PNG"
    sheet.save()
    bpy.data.images.remove(sheet)
    for path in panel_paths:
        os.remove(path)
    print(f"[bezi-art] preview written: {out_path}")
    return out_path


def _guide_bar(height):
    material = bpy.data.materials.new("PreviewGuide")
    material.use_nodes = True
    bsdf = material.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (1.0, 0.05, 0.05, 1.0)
    bsdf.inputs["Emission Color"].default_value = (1.0, 0.05, 0.05, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 2.0
    half_x, half_t = GUIDE_LENGTH * 0.5, GUIDE_THICKNESS * 0.5
    vertices = [(x, y, height + z) for x in (-half_x, half_x) for y in (-half_t, half_t) for z in (-half_t, half_t)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh = bpy.data.meshes.new("PreviewGuide")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    guide = bpy.data.objects.new("PreviewGuide", mesh)
    bpy.context.scene.collection.objects.link(guide)
    return guide


def contact_sheet(spec, blend_path):
    """Renders game view, top ortho, side ortho (with 3.5 m guide) and clay wireframe into one sheet."""
    reset_scene()
    obj = append_asset(blend_path, spec.mesh_name)
    obj.color = CLAY_COLOR
    out_dir = paths.asset_render_dir(spec.asset_id)

    guide = _guide_bar(hexgrid.MAX_DECOR_HEIGHT)
    guide.hide_render = True
    wire = bpy.data.objects.new(f"{obj.name}_wire", obj.data)
    bpy.context.scene.collection.objects.link(wire)
    modifier = wire.modifiers.new("Wire", "WIREFRAME")
    modifier.thickness = WIRE_THICKNESS
    wire.color = WIRE_COLOR
    wire.hide_render = True

    origin = Vector((0.0, 0.0, 0.0))
    panels = [render(game_camera("CamGame", origin, GAME_DISTANCE), os.path.join(out_dir, "_p0.png"))]
    panels.append(render(top_camera("CamTop", origin, TOP_ORTHO_SCALE), os.path.join(out_dir, "_p1.png")))

    guide.hide_render = False
    side = make_camera("CamSide", (0.0, SIDE_CAMERA_DISTANCE, SIDE_CAMERA_HEIGHT), (0.0, 0.0, SIDE_CAMERA_HEIGHT),
                       ortho_scale=SIDE_ORTHO_SCALE)
    panels.append(render(side, os.path.join(out_dir, "_p2.png")))
    guide.hide_render = True

    wire.hide_render = False
    close_direction = Vector((0.55, 0.7, 0.6)).normalized()
    close = make_camera("CamClose", close_direction * CLOSE_DISTANCE, origin)
    panels.append(render(close, os.path.join(out_dir, "_p3.png"), engine=ENGINE_WORKBENCH))
    return stitch(panels, os.path.join(out_dir, "contact_sheet.png"))


def cluster_sheet(spec, blend_path, seed):
    """Renders a 7-tile flower of one tile type (random 60 deg rotations) to check same-type seams."""
    reset_scene()
    rng = random.Random(seed)
    obj = append_asset(blend_path, spec.mesh_name)
    obj.rotation_euler = (0.0, 0.0, math.radians(60.0 * rng.randrange(hexgrid.SIDE_COUNT)))
    for side in range(hexgrid.SIDE_COUNT):
        add_instance(obj, hexgrid.neighbor_center(side), rng.randrange(hexgrid.SIDE_COUNT))
    out_dir = paths.asset_render_dir(spec.asset_id)
    origin = Vector((0.0, 0.0, 0.0))

    seam_mid = hexgrid.side_midpoint(0)
    seam_camera = make_camera("CamSeam", seam_mid + Vector((-SEAM_CAMERA_BACK, 0.0, SEAM_CAMERA_HEIGHT)),
                              seam_mid + Vector((SEAM_TARGET_AHEAD, 0.0, 0.0)), fov_deg=SEAM_FOV_DEG)
    corner_point = (hexgrid.side_midpoint(0) + hexgrid.side_midpoint(1)) * 0.5
    corner_point = corner_point.normalized() * hexgrid.TILE_RADIUS
    panels = [
        render(game_camera("CamGame", origin, GAME_DISTANCE), os.path.join(out_dir, "_c0.png")),
        render(game_camera("CamWide", origin, WIDE_DISTANCE), os.path.join(out_dir, "_c1.png")),
        render(seam_camera, os.path.join(out_dir, "_c2.png")),
        render(top_camera("CamCorner", corner_point, CORNER_ORTHO_SCALE), os.path.join(out_dir, "_c3.png")),
    ]
    return stitch(panels, os.path.join(out_dir, "cluster_sheet.png"))


def mixed_patch(specs_and_paths, seed, out_path):
    """Renders a 19-tile patch randomly mixing the given tiles and rotations from the game angle."""
    reset_scene()
    rng = random.Random(seed)
    sources = [append_asset(path, spec.mesh_name) for spec, path in specs_and_paths]
    for source in sources:
        source.hide_render = True
    for q in range(-MIXED_RING_COUNT, MIXED_RING_COUNT + 1):
        for r in range(-MIXED_RING_COUNT, MIXED_RING_COUNT + 1):
            if max(abs(q), abs(r), abs(q + r)) > MIXED_RING_COUNT:
                continue
            add_instance(rng.choice(sources), hexgrid.axial_center(q, r), rng.randrange(hexgrid.SIDE_COUNT))
    camera = game_camera("CamMixed", (0.0, 0.0, 0.0), MIXED_DISTANCE)
    render(camera, out_path, size=(PANEL_WIDTH * 2, PANEL_HEIGHT * 2))
    print(f"[bezi-art] preview written: {out_path}")
    return out_path
