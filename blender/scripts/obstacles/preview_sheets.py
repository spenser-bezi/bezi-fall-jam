"""Obstacle preview renders: auto-framed contact sheets and the obstacle lineup.

The default contact sheet uses a fixed 23 m ortho frame, which crops 20 m towers and 30 m clouds. These sheets frame
every panel from the asset bounds, add a 2.5 m goose-size marker (cyan) and, for ground obstacles, the GDD 5.3
altitude band lines (4 / 12 / 26 / 40 m). Panels (3 x 2): game view (45 m, 50 deg pitch) | front ortho (from +Y,
the approaching flock) | side ortho (from +X) / top ortho (Unity +Z up) | hero 3/4 | clay wireframe.
"""
import math
import os

import bpy
from mathutils import Matrix, Vector

import registry
from lib import paths
from lib import preview as preview_lib
from obstacles import common

SHEET_COLUMNS = 3
FRAME_MARGIN = 1.18
ORTHO_DISTANCE = 80.0
HERO_DIRECTION = Vector((0.62, 0.68, 0.42)).normalized()
HERO_DISTANCE_FACTOR = 1.08
GOOSE_LOW_ALTITUDE = 8.0
GOOSE_GAP_FACTOR = 0.08
GOOSE_MIN_GAP = 0.8
GOOSE_BODY_HALF = 1.1
GOOSE_COLOR = (0.05, 0.85, 1.0, 1.0)
GOOSE_EMISSION = 1.5
BAND_COLORS = {
    common.BAND_LOW_FLOOR: (0.15, 0.75, 0.2, 1.0),
    common.BAND_LOW_TOP: (0.95, 0.85, 0.1, 1.0),
    common.BAND_MID_TOP: (1.0, 0.45, 0.05, 1.0),
    common.BAND_HIGH_TOP: (0.9, 0.1, 0.1, 1.0),
}
BAND_LABELS = {
    common.BAND_LOW_FLOOR: "4 m  Low floor",
    common.BAND_LOW_TOP: "12 m  Low / Mid",
    common.BAND_MID_TOP: "26 m  Mid / High",
    common.BAND_HIGH_TOP: "40 m  ceiling",
}
BAND_LINE_FACTOR = 0.0022
BAND_LINE_MIN = 0.03
BAND_HEADROOM = 1.3
LABEL_SIZE_FACTOR = 0.045
GROUND_LINE_COLOR = (0.15, 0.12, 0.1, 1.0)
TEXT_COLOR = (0.08, 0.07, 0.07, 1.0)
EMISSION_STRENGTH = 1.0

LINEUP_FILE = "lineup_obstacles.png"
LINEUP_SIZE = (3600, 1125)
LINEUP_GAP = 3.0
LINEUP_BLADE_HALF = 8.6
LINEUP_LABEL_MARGIN = 15.0
LINEUP_LABEL_Z = -2.6
LINEUP_LABEL_SIZE = 1.15
LINEUP_FLOOR = -4.5
LINEUP_CEILING = 44.0
LINEUP_WIRE_SPAN = 24.0
LINEUP_BALLOON_Z = 20.0
LINEUP_PLANE_Z = 34.0
LINEUP_CLOUD_Z = 32.5
LINEUP_FOG_Z = 6.0
LINEUP_SNACK_Z = 6.0


# ------------------------------------------------------------------------------------------------ scene pieces


def _emissive_material(name, color, strength=EMISSION_STRENGTH):
    """Flat emission-only material so overlay colors render exactly (no sun shading)."""
    material = bpy.data.materials.get(name)
    if material is not None:
        return material
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = color
    emission.inputs["Strength"].default_value = strength
    output = nodes.new("ShaderNodeOutputMaterial")
    material.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    material.diffuse_color = color
    return material


def append_root(blend_path, object_name):
    """Appends an asset (collection with sockets) and returns the newly created root object.

    lib.preview.append_asset looks the root up by name, which returns the first copy when an asset is appended
    twice; this compares the object set before and after instead.
    """
    before = set(bpy.data.objects)
    preview_lib.append_asset(blend_path, object_name)
    new_objects = [obj for obj in bpy.data.objects if obj not in before]
    roots = [obj for obj in new_objects if obj.parent is None and obj.name.startswith(object_name)]
    return roots[0]


def _mesh_object(name, parts, material, color):
    vertices, faces = [], []
    for part in parts:
        offset = len(vertices)
        vertices.extend(tuple(v) for v in part.vertices)
        faces.extend(tuple(offset + i for i in face) for face in part.faces)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    obj.color = color
    bpy.context.scene.collection.objects.link(obj)
    return obj


def add_goose_marker(location, name="GooseRef"):
    """Adds a cyan 2.5 m wingspan goose stand-in (wings, body, neck, head) facing Blender -Y (flight)."""
    half_span = common.GOOSE_WINGSPAN * 0.5
    parts = [
        common.box(-half_span, half_span, -0.15, 0.4, -0.04, 0.04),       # wings
        common.box(-0.22, 0.22, -0.45, 0.65, -0.22, 0.18),                # body
        common.box(-0.07, 0.07, -0.85, -0.45, 0.0, 0.14),                 # neck
        common.box(-0.1, 0.1, -1.1, -0.85, 0.05, 0.25),                   # head
    ]
    material = _emissive_material("PreviewGooseRef", GOOSE_COLOR, GOOSE_EMISSION)
    marker = _mesh_object(name, parts, material, GOOSE_COLOR)
    marker.location = location
    return marker


def add_text(body, location, size, color=TEXT_COLOR, facing="front"):
    """Adds a flat text label readable from the front ortho camera (+Y looking -Y)."""
    curve = bpy.data.curves.new(f"Label_{body}", type="FONT")
    curve.body = body
    curve.size = size
    text = bpy.data.objects.new(f"Label_{body}", curve)
    text.data.materials.append(_emissive_material(f"PreviewText_{color}", color, 0.4))
    text.color = color
    text.location = location
    text.rotation_euler = (math.radians(90.0), 0.0, math.radians(180.0)) if facing == "front" else (0.0, 0.0, 0.0)
    bpy.context.scene.collection.objects.link(text)
    return text


def add_band_lines(x_range, y_range, top_z, frame_height, with_labels=True, label_x=None):
    """Adds thin glowing slabs at every altitude band boundary up to top_z (lines in front/side views)."""
    thickness = max(BAND_LINE_MIN, frame_height * BAND_LINE_FACTOR)
    objects = []
    for height in common.BAND_LINES:
        if height > top_z:
            continue
        slab = common.box(x_range[0], x_range[1], y_range[0], y_range[1], height - thickness, height + thickness)
        color = BAND_COLORS[height]
        objects.append(_mesh_object(f"Band_{int(height)}", [slab], _emissive_material(f"PreviewBand_{int(height)}",
                                                                                        color), color))
        if with_labels:
            label_size = frame_height * LABEL_SIZE_FACTOR
            x = x_range[0] if label_x is None else label_x
            objects.append(add_text(BAND_LABELS[height], (x, y_range[1], height + thickness * 2.0), label_size,
                                    color=tuple(c * 0.7 for c in color[:3]) + (1.0,)))
    ground = common.box(x_range[0], x_range[1], y_range[0], y_range[1], -thickness * 2.0, 0.0)
    objects.append(_mesh_object("GroundLine", [ground], _emissive_material("PreviewGround", GROUND_LINE_COLOR, 0.2),
                                GROUND_LINE_COLOR))
    return objects


def world_bounds(objects):
    """Returns (min, max) world-space Vectors over every mesh object's vertices."""
    points = [obj.matrix_world @ v.co for obj in objects if obj.type == "MESH" for v in obj.data.vertices]
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    return low, high


def _cull_backfaces():
    for material in bpy.data.materials:
        material.use_backface_culling = True  # flipped faces vanish, the way Unity will show them


def _attach(parent, spec_id, socket_name):
    """Appends another asset and parents it at one of parent's sockets (windmill rotor, propeller)."""
    spec = registry.ASSETS.get(spec_id)
    if spec is None or not os.path.exists(spec.blend_path):
        return None
    child = append_root(spec.blend_path, spec.mesh_name)
    socket = next(c for c in parent.children if c.name.startswith(socket_name))
    child.matrix_world = socket.matrix_world.copy()
    return child


def _ortho_scale(horizontal, vertical, size):
    aspect = size[0] / size[1]
    return max(horizontal, vertical * aspect, 0.5) * FRAME_MARGIN


# ------------------------------------------------------------------------------------------------ contact sheet


def contact_sheet(spec, rules):
    """Renders the 6-panel auto-framed contact sheet for one obstacle/snack and returns its path."""
    preview_lib.reset_scene()
    scene = bpy.context.scene
    scene.frame_set(common.FIRST_FRAME)
    obj = append_root(spec.blend_path, spec.mesh_name)
    preview_scale = rules.extra.get("preview_scale")
    if preview_scale:
        obj.scale = preview_scale  # e.g. the 1 m power wire previewed at a typical tower-to-tower span
        bpy.context.view_layer.update()
    asset_objects = [obj]
    attach = rules.extra.get("attach")
    if attach:
        child = _attach(obj, *attach)
        if child is not None:
            asset_objects.append(child)
    for asset in asset_objects:
        asset.color = preview_lib.CLAY_COLOR
    low, high = world_bounds(asset_objects)
    size = high - low

    gap = max(GOOSE_MIN_GAP, GOOSE_GAP_FACTOR * size.x)
    is_ground = rules.pivot == common.PIVOT_BASE
    goose_z = GOOSE_LOW_ALTITUDE if is_ground and size.z > GOOSE_LOW_ALTITUDE else (low.z + high.z) * 0.5
    # beside the asset in X and behind it in Y, so neither the front/side orthos nor the hero camera are blocked
    goose = add_goose_marker((high.x + gap + common.GOOSE_WINGSPAN * 0.5, low.y - gap - GOOSE_BODY_HALF, goose_z))
    frame_low, frame_high = world_bounds(asset_objects + [goose])
    if is_ground:
        frame_low.z = min(frame_low.z, 0.0)
    frame_size = frame_high - frame_low
    center = (frame_low + frame_high) * 0.5

    panel_size = preview_lib_size()
    overlays = []
    if is_ground:
        top_z = frame_high.z * BAND_HEADROOM + 1.0
        frame_high.z = max(frame_high.z, max((b for b in common.BAND_LINES if b <= top_z), default=0.0))
        frame_size = frame_high - frame_low
        center = (frame_low + frame_high) * 0.5
        front_scale = _ortho_scale(frame_size.x, frame_size.z, panel_size)
        side_scale = _ortho_scale(frame_size.y, frame_size.z, panel_size)
        # the front camera looks down -Y, so screen-left is world +X
        overlays = add_band_lines((center.x - front_scale * 0.6, center.x + front_scale * 0.6),
                                  (center.y - side_scale * 0.6, center.y + side_scale * 0.6), top_z,
                                  frame_size.z, label_x=center.x + front_scale * 0.48)
    _cull_backfaces()

    wire_objects = []
    for asset in asset_objects:
        wire = bpy.data.objects.new(f"{asset.name}_wire", asset.data)
        wire.matrix_world = asset.matrix_world.copy()
        scene.collection.objects.link(wire)
        modifier = wire.modifiers.new("Wire", "WIREFRAME")
        modifier.thickness = preview_lib.WIRE_THICKNESS * max(1.0, max(frame_size) / 20.0)
        wire.color = preview_lib.WIRE_COLOR
        wire.hide_render = True
        wire_objects.append(wire)

    out_dir = paths.asset_render_dir(spec.asset_id)
    for overlay in overlays:
        overlay.hide_render = True  # horizontal band slabs would cover the perspective views
    panels = [preview_lib.render(preview_lib.game_camera("CamGame", center, preview_lib.GAME_DISTANCE),
                                 os.path.join(out_dir, "_o0.png"))]
    for overlay in overlays:
        overlay.hide_render = False
    front = preview_lib.make_camera("CamFront", (center.x, frame_high.y + ORTHO_DISTANCE, center.z), center,
                                    ortho_scale=_ortho_scale(frame_size.x, frame_size.z, panel_size))
    panels.append(preview_lib.render(front, os.path.join(out_dir, "_o1.png")))
    side = preview_lib.make_camera("CamSide", (frame_high.x + ORTHO_DISTANCE, center.y, center.z), center,
                                   ortho_scale=_ortho_scale(frame_size.y, frame_size.z, panel_size))
    for overlay in overlays:
        if overlay.type == "FONT":
            overlay.hide_render = True
    panels.append(preview_lib.render(side, os.path.join(out_dir, "_o2.png")))
    for overlay in overlays:
        overlay.hide_render = True
    top = preview_lib.top_camera("CamTop", Vector((center.x, center.y, frame_high.z)),
                                 _ortho_scale(frame_size.x, frame_size.y, panel_size))
    panels.append(preview_lib.render(top, os.path.join(out_dir, "_o3.png")))

    radius = max(frame_size.length * 0.5, 0.5)
    distance = radius / math.sin(math.radians(preview_lib.GAME_FOV_DEG) * 0.5) * HERO_DISTANCE_FACTOR
    hero = preview_lib.make_camera("CamHero", center + HERO_DIRECTION * distance, center)
    panels.append(preview_lib.render(hero, os.path.join(out_dir, "_o4.png")))
    for wire in wire_objects:
        wire.hide_render = False
    panels.append(preview_lib.render(hero, os.path.join(out_dir, "_o5.png"), engine=preview_lib.ENGINE_WORKBENCH))
    return preview_lib.stitch(panels, os.path.join(out_dir, "contact_sheet.png"), columns=SHEET_COLUMNS)


def preview_lib_size():
    """Contact sheet panel size in pixels."""
    return preview_lib.PANEL_WIDTH, preview_lib.PANEL_HEIGHT

# ------------------------------------------------------------------------------------------------ lineup
# The lineup camera looks down -Y (like the flock), so screen-right is world -X. Layout runs in screen
# coordinates s = -x so the lineup reads left to right.


def _screen_span(obj_list):
    low, high = world_bounds(obj_list)
    return -high.x, -low.x, low, high


def _place(spec_id, screen_left, z=0.0, yaw=0.0):
    """Appends an asset with its screen-left edge at screen_left and its pivot at height z.

    Returns (obj, screen_left, screen_right, world_min, world_max).
    """
    spec = registry.ASSETS[spec_id]
    obj = append_root(spec.blend_path, spec.mesh_name)
    obj.rotation_euler = (0.0, 0.0, yaw)
    obj.location = (0.0, 0.0, z)
    bpy.context.view_layer.update()
    s_left, _, _, _ = _screen_span([obj])
    obj.location.x -= screen_left - s_left
    bpy.context.view_layer.update()
    s_left, s_right, low, high = _screen_span([obj])
    return obj, s_left, s_right, low, high


def _place_center(spec_id, screen_center, z):
    """Appends an asset centered on screen_center with its pivot at height z and returns the object."""
    spec = registry.ASSETS[spec_id]
    obj = append_root(spec.blend_path, spec.mesh_name)
    obj.location = (0.0, 0.0, z)
    bpy.context.view_layer.update()
    s_left, s_right, _, _ = _screen_span([obj])
    obj.location.x -= screen_center - (s_left + s_right) * 0.5
    bpy.context.view_layer.update()
    return obj


def _label(text, screen_center, z=LINEUP_LABEL_Z, size=LINEUP_LABEL_SIZE):
    label = add_text(text, (0.0, 0.0, z), size)
    bpy.context.view_layer.update()
    label.location.x = -screen_center + label.dimensions.x * 0.5  # rotated text grows toward -X (screen-right)
    return label


def _goose_at(screen_x, z):
    return add_goose_marker((-screen_x, 0.0, z))


def lineup(out_path=None):
    """Front-ortho lineup of every obstacle and snack at gameplay altitudes, with band lines and goose markers."""
    preview_lib.reset_scene()
    bpy.context.scene.frame_set(common.FIRST_FRAME)
    cursor = 0.0
    slots = {}

    def ground(spec_id, label, yaw=0.0):
        nonlocal cursor
        _, s_left, s_right, _, _ = _place(spec_id, cursor, 0.0, yaw)
        slots[spec_id] = (s_left, s_right)
        _label(label, (s_left + s_right) * 0.5)
        cursor = s_right + LINEUP_GAP

    ground("obstacle.tree_cluster_a", "TreeCluster_A")
    ground("obstacle.tree_cluster_b", "TreeCluster_B")
    ground("obstacle.steeple", "Steeple")
    ground("obstacle.clock_tower", "ClockTower")
    ground("obstacle.silo_tall", "SiloTall")

    base_spec = registry.ASSETS["obstacle.windmill_base"]
    base = append_root(base_spec.blend_path, base_spec.mesh_name)
    base.location = (-(cursor + LINEUP_BLADE_HALF), 0.0, 0.0)
    bpy.context.view_layer.update()
    _attach(base, "obstacle.windmill_blades", "SOCKET_Blades")
    _label("Windmill_Base + Blades", cursor + LINEUP_BLADE_HALF)
    cursor += 2.0 * LINEUP_BLADE_HALF + LINEUP_GAP

    tower_a, a_left, a_right, _, _ = _place("obstacle.power_tower", cursor, 0.0, math.pi * 0.5)
    tower_b, _, b_right, _, _ = _place("obstacle.power_tower", a_right + LINEUP_WIRE_SPAN, 0.0, math.pi * 0.5)
    wire_spec = registry.ASSETS["obstacle.power_wire"]
    wire_source = append_root(wire_spec.blend_path, wire_spec.mesh_name)
    wire_source.hide_render = True
    span_length = 0.0
    for side in ("SOCKET_Wire_L", "SOCKET_Wire_R"):
        start = next(c for c in tower_a.children if c.name.startswith(side)).matrix_world.translation
        end = next(c for c in tower_b.children if c.name.startswith(side)).matrix_world.translation
        span = end - start
        span_length = span.length
        wire = bpy.data.objects.new(f"Wire_{side}", wire_source.data)
        bpy.context.scene.collection.objects.link(wire)
        wire.matrix_world = (Matrix.Translation(start) @ Matrix.Rotation(math.atan2(span.y, span.x), 4, "Z")
                             @ Matrix.Diagonal((span.length, 1.0, 1.0, 1.0)))
    span_center = (a_left + b_right) * 0.5
    _label(f"PowerTower x2 + PowerWire (yaw to socket, scale X = {span_length:.1f})", span_center)
    cursor = b_right + LINEUP_GAP

    _, fog_left, fog_right, _, _ = _place("obstacle.fog_puff", cursor, LINEUP_FOG_Z)
    _label("FogPuff", (fog_left + fog_right) * 0.5)
    cursor = fog_right + LINEUP_GAP
    for snack_id, snack_label in (("prop.snack_corn", "Corn"), ("prop.snack_apple", "Apple"),
                                  ("prop.snack_pumpkin", "Pumpkin")):
        _, s_left, s_right, _, _ = _place(snack_id, cursor, LINEUP_SNACK_Z)
        _label(snack_label, (s_left + s_right) * 0.5, z=LINEUP_SNACK_Z - 1.4, size=0.5)
        cursor = s_right + 1.0
    _goose_at(cursor + common.GOOSE_WINGSPAN * 0.5, LINEUP_SNACK_Z)
    cursor += common.GOOSE_WINGSPAN + LINEUP_GAP

    def slot_center(spec_id):
        left, right = slots[spec_id]
        return (left + right) * 0.5

    _place_center("obstacle.balloon_a", slot_center("obstacle.tree_cluster_a"), LINEUP_BALLOON_Z)
    _place_center("obstacle.balloon_b", slot_center("obstacle.tree_cluster_b"), LINEUP_BALLOON_Z)
    _place_center("obstacle.balloon_c", (fog_left + fog_right) * 0.5, LINEUP_BALLOON_Z)
    _place_center("obstacle.plane", slot_center("obstacle.clock_tower"), LINEUP_PLANE_Z)
    cloud = _place_center("obstacle.storm_cloud", span_center, LINEUP_CLOUD_Z)
    cloud_low, _ = world_bounds([cloud])
    _place_center("obstacle.lightning", span_center + 2.0, cloud_low.z + 0.8)
    _goose_at(slots["obstacle.tree_cluster_b"][0] - 1.5, LINEUP_BALLOON_Z)
    _goose_at(slot_center("obstacle.clock_tower") + 9.0, LINEUP_PLANE_Z)
    _goose_at(slots["obstacle.tree_cluster_b"][1] + 1.5, GOOSE_LOW_ALTITUDE)
    for name, spec_id in (("Balloon_A", "obstacle.tree_cluster_a"), ("Balloon_B", "obstacle.tree_cluster_b")):
        _label(name, slot_center(spec_id), z=LINEUP_BALLOON_Z + 6.6, size=0.9)
    _label("Balloon_C", (fog_left + fog_right) * 0.5, z=LINEUP_BALLOON_Z + 6.6, size=0.9)
    _label("Plane", slot_center("obstacle.clock_tower"), z=LINEUP_PLANE_Z + 2.6, size=0.9)
    _label("StormCloud + Lightning", span_center, z=LINEUP_CLOUD_Z + 6.0, size=0.9)

    screen_left, screen_right = -LINEUP_LABEL_MARGIN, cursor
    frame_height = LINEUP_CEILING - LINEUP_FLOOR
    ortho_scale = max(screen_right - screen_left, frame_height * LINEUP_SIZE[0] / LINEUP_SIZE[1])
    center = Vector((-(screen_left + screen_right) * 0.5, 0.0, (LINEUP_FLOOR + LINEUP_CEILING) * 0.5))
    add_band_lines((center.x - ortho_scale * 0.6, center.x + ortho_scale * 0.6), (-30.0, 30.0),
                   common.BAND_HIGH_TOP, frame_height, label_x=center.x + ortho_scale * 0.495)
    _cull_backfaces()
    camera = preview_lib.make_camera("CamLineup", (center.x, ORTHO_DISTANCE, center.z), center,
                                     ortho_scale=ortho_scale)
    out_path = out_path or os.path.join(paths.ensure_dir(paths.RENDERS_DIR), LINEUP_FILE)
    preview_lib.render(camera, out_path, size=LINEUP_SIZE)
    print(f"[bezi-art] lineup written: {out_path}")
    return out_path


