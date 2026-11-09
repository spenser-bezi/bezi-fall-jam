"""Shared helpers for obstacle and snack recipes: low-poly geometry, painting, sockets, spin clips and rules.

Axis conventions (Art Workflow 3.5): Blender -Y exports as Unity +Z (flight direction), Blender Z is up.
Flocks approach from Blender +Y, so faces that the geese see first point toward +Y.
"""
import math
from dataclasses import dataclass, field

import bpy
from mathutils import Matrix, Vector

from lib import edge_sockets, materials, palette, shapes
from lib.builder import MeshBuilder

MATERIAL = materials.PALETTE_MATERIAL
GLOW = materials.GLOW_MATERIAL

BASE = palette.SHADE_BASE
LIGHT = palette.SHADE_LIGHT
DARK = palette.SHADE_DARK
EXTRA_DARK = palette.SHADE_EXTRA_DARK

PIVOT_BASE = "base"            # base center on z = 0
PIVOT_CENTER = "center"        # bounds center (or expected_center) at the origin
PIVOT_HUB = "hub"              # spin axis (Blender Y) passes through the origin
PIVOT_SPAN_START = "span_start"  # 1 m span along +X starting at the origin
PIVOT_TOP = "top"              # attach point at the top center

ANIMATION_FPS = 24
FIRST_FRAME = 1
FULL_TURN = 2.0 * math.pi
SPIN_AXIS_INDEX = 1  # Blender Y = Unity Z (flight direction)

# GDD 5.3 altitude bands (meters above ground)
BAND_LOW_FLOOR = 4.0
BAND_LOW_TOP = 12.0
BAND_MID_TOP = 26.0
BAND_HIGH_TOP = 40.0
BAND_LINES = (BAND_LOW_FLOOR, BAND_LOW_TOP, BAND_MID_TOP, BAND_HIGH_TOP)
GOOSE_WINGSPAN = 2.5


@dataclass(frozen=True)
class SpinClip:
    """A looping linear rotation about the spin axis, exported as one FBX take."""
    name: str
    frame_count: int
    direction: float = 1.0

    @property
    def last_frame(self):
        """Last keyed frame (the full-turn pose, identical to the first pose)."""
        return FIRST_FRAME + self.frame_count


@dataclass(frozen=True)
class AssetRules:
    """Per-asset checks layered on top of the generic validation.

    height_range: allowed bounds height (z extent) in meters.
    max_dimension_range: allowed largest bounds dimension (snack icon scale).
    expected_center: bounds center that PIVOT_CENTER compares against (balloons: envelope center at origin).
    band_note: GDD 5.3 band this obstacle blocks, shown in reports.
    """
    pivot: str
    height_range: tuple = (0.0, 1000.0)
    max_dimension_range: tuple = (0.0, 1000.0)
    expected_center: tuple = (0.0, 0.0, 0.0)
    sockets: tuple = ()
    sway: bool = False
    spin: SpinClip = None
    band_note: str = ""
    verify_fbx: bool = False
    extra: dict = field(default_factory=dict)


# ------------------------------------------------------------------------------------------------ geometry


def box(x0, x1, y0, y1, z0, z1):
    """Axis-aligned closed box between two corners (12 tris, outward faces)."""
    vertices = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return shapes.Part(vertices, faces)


def centered_box(size_x, size_y, size_z, z0=0.0, x=0.0, y=0.0):
    """Closed box centered on (x, y) standing on z0."""
    hx, hy = size_x * 0.5, size_y * 0.5
    return box(x - hx, x + hx, y - hy, y + hy, z0, z0 + size_z)


def lathe(profile, sides, angle_offset=0.0, radius_scale=None):
    """Revolves a (radius, z) profile (bottom to top) around Z into a closed faceted solid.

    A radius of 0 at either end becomes a pole; otherwise that end is capped flat.
    radius_scale(k, ring) optionally multiplies the radius per vertex (pumpkin ribs, jitter).
    """
    vertices, rings = [], []
    for ring_index, (radius, z) in enumerate(profile):
        if radius <= 0.0:
            vertices.append((0.0, 0.0, z))
            rings.append([len(vertices) - 1])
            continue
        ring = []
        for k in range(sides):
            angle = angle_offset + 2.0 * math.pi * k / sides
            scaled = radius * (radius_scale(k, ring_index) if radius_scale else 1.0)
            vertices.append((scaled * math.cos(angle), scaled * math.sin(angle), z))
            ring.append(len(vertices) - 1)
        rings.append(ring)

    faces = []
    for lower, upper in zip(rings, rings[1:]):
        for k in range(sides):
            n = (k + 1) % sides
            if len(lower) == 1:
                faces.append((lower[0], upper[n], upper[k]))
            elif len(upper) == 1:
                faces.append((lower[k], lower[n], upper[0]))
            else:
                faces.append((lower[k], lower[n], upper[n], upper[k]))
    if len(rings[0]) > 1:
        faces.append(tuple(reversed(rings[0])))
    if len(rings[-1]) > 1:
        faces.append(tuple(rings[-1]))
    return shapes.Part(vertices, faces)


def beam(start, end, width_start, width_end=None, roll=0.0):
    """Closed square-section beam from start to end (tapered if width_end is given), in world space."""
    width_end = width_start if width_end is None else width_end
    start, end = Vector(start), Vector(end)
    axis = end - start
    length = axis.length
    hs, he = width_start * 0.5, width_end * 0.5
    vertices = [(-hs, -hs, 0.0), (hs, -hs, 0.0), (hs, hs, 0.0), (-hs, hs, 0.0),
                (-he, -he, length), (he, -he, length), (he, he, length), (-he, he, length)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    up_hint = "Y" if abs(axis.normalized().y) < 0.9 else "X"
    orientation = axis.to_track_quat("Z", up_hint).to_matrix().to_4x4()
    matrix = Matrix.Translation(start) @ orientation @ Matrix.Rotation(roll, 4, "Z")
    return shapes.Part([matrix @ Vector(v) for v in vertices], faces)


def pyramid(sides, radius, height, angle_offset=0.0):
    """Closed cone/pyramid standing on z = 0 (bottom capped)."""
    part = shapes.cone(sides, radius, height, angle_offset=angle_offset)
    part.faces.append(tuple(reversed(range(sides))))
    return part


def recenter(builder, keep_z=False):
    """Moves every vertex so the bounds center lands on the origin (optionally keeping z untouched)."""
    low = Vector(tuple(min(v[i] for v in builder.vertices) for i in range(3)))
    high = Vector(tuple(max(v[i] for v in builder.vertices) for i in range(3)))
    offset = (low + high) * 0.5
    if keep_z:
        offset.z = 0.0
    for vertex in builder.vertices:
        vertex -= offset
    return offset


def clamp_below(part, floor_z):
    """Flattens every vertex of a part below floor_z onto floor_z (flat cloud bottoms)."""
    for vertex in part.vertices:
        vertex.z = max(vertex.z, floor_z)
    return part


# ------------------------------------------------------------------------------------------------ painting


def solid(color, shade=BASE):
    """UV callback painting every face with one swatch."""
    uv = palette.flat_uv(color, shade)
    return lambda face, centroid: uv


def shaded(rng, color, choices=(BASE, BASE, LIGHT, DARK)):
    """UV callback painting each face with a random shade of one color (painterly facets)."""
    return lambda face, centroid: palette.flat_uv(color, rng.choice(choices))


def add(builder, part, color, shade=BASE, matrix=None, material=MATERIAL, uv_for_face=None, sway=None):
    """Adds a part to a builder with a flat swatch (or a custom uv_for_face callback)."""
    builder.add_part(part, matrix if matrix is not None else Matrix.Identity(4), material,
                     uv_for_face or solid(color, shade), sway)


def merge_scaled(target, source, matrix):
    """Copies every vertex (with sway) and face of source builder into target, transformed by matrix."""
    offset = len(target.vertices)
    for vertex, sway, ring in zip(source.vertices, source.vertex_sway, source.vertex_ring):
        target.add_vertex(matrix @ vertex, sway=sway, ring=ring)
    for indices, material_index, uvs in source.faces:
        target.add_face([offset + i for i in indices], source.material_names[material_index], uvs)


# ------------------------------------------------------------------------------------------------ scene objects


def new_asset_collection(spec):
    """Creates (and links) the collection named after the mesh so previews append mesh + sockets together."""
    collection = bpy.data.collections.new(spec.mesh_name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def finish(builder, spec):
    """Writes the builder into the asset object inside its own collection and returns the object."""
    collection = new_asset_collection(spec)
    scene = bpy.context.scene
    scene.render.fps = ANIMATION_FPS
    scene.frame_start = FIRST_FRAME
    scene.frame_end = FIRST_FRAME
    return builder.build_object(spec.mesh_name, collection)


def new_builder(material_names=(MATERIAL,)):
    """Returns a MeshBuilder whose only slots are the given materials."""
    return MeshBuilder(material_names=material_names)


def add_socket(obj, name, location):
    """Adds a SOCKET_ empty parented to obj at a local location."""
    return edge_sockets.add_socket_empty(obj, name, location)


def add_spin_clip(obj, clip):
    """Adds a looping linear 360 degree turn about Blender Y as an NLA strip named after the clip."""
    obj.rotation_mode = "XYZ"
    animation_data = obj.animation_data_create()
    action = bpy.data.actions.new(clip.name)
    action.use_fake_user = True
    curve = action.fcurves.new("rotation_euler", index=SPIN_AXIS_INDEX)
    curve.keyframe_points.add(2)
    keys = ((FIRST_FRAME, 0.0), (clip.last_frame, clip.direction * FULL_TURN))
    for point, (frame, value) in zip(curve.keyframe_points, keys):
        point.co = (frame, value)
        point.handle_left = point.handle_right = point.co
        point.interpolation = "LINEAR"
    curve.update()
    track = animation_data.nla_tracks.new()
    track.name = clip.name
    strip = track.strips.new(clip.name, FIRST_FRAME, action)
    strip.name = clip.name
    animation_data.action = None
    scene = bpy.context.scene
    scene.frame_start = FIRST_FRAME
    scene.frame_end = clip.last_frame
    scene.frame_set(FIRST_FRAME)
    return action
