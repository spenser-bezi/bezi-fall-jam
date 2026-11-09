"""SK_Goose geometry: the skinned low-poly Canada goose body and the leader's knitted scarf.

Every part is a closed shell with outward faces, palette UVs (one swatch per face) and per-vertex bone
weights. Wing segments are rigid (one bone each, overlapping at the joints) so they can fold for swimming.
"""
import math
import random

from mathutils import Vector

from characters import goose_rig as rig
from lib import materials, palette, shapes
from lib.builder import MeshBuilder

BODY_MESH_SUFFIX = "_Body"
SCARF_MESH_NAME = "SM_Scarf"
MAX_INFLUENCES = 4
MIN_WEIGHT = 0.01

BASE = palette.SHADE_BASE
LIGHT = palette.SHADE_LIGHT
DARK = palette.SHADE_DARK
CHARCOAL = ("GooseCharcoal", BASE)
WHITE = ("Chinstrap", BASE)
TAUPE = ("GooseTaupe", BASE)
TAUPE_LIGHT = ("GooseTaupe", LIGHT)
TAUPE_DARK = ("GooseTaupe", DARK)
BEAK = ("Soil", DARK)
LEGS = ("Soil", BASE)
TONGUE = ("MapleRed", LIGHT)
SCARF = ("Pumpkin", BASE)
SCARF_LIGHT = ("Pumpkin", LIGHT)
SCARF_DARK = ("Pumpkin", DARK)
SCARF_STRIPE = ("MapleRed", BASE)

# Body: an egg with a full chest and a raised, tapering rear.
BODY_RADII = Vector((0.38, 0.56, 0.36))
BODY_SEGMENTS = (14, 9)
BODY_REAR_TAPER = 0.32
BODY_CHEST_FULLNESS = 0.06
BODY_TOP_FLATTEN = 0.92
BODY_REAR_LIFT = 0.10
BODY_CHEST_DROP = 0.04
BODY_TAIL_BLEND_START = 0.38
BODY_TAIL_BLEND_RANGE = 0.2
BODY_TAIL_BLEND_MAX = 0.5
BODY_NECK_BLEND_RADIUS = 0.18
BODY_NECK_BLEND_MAX = 0.4

NECK_SIDES = 8
NECK_START = Vector((0.0, -0.30, 0.04))
NECK_RADII = (0.13, 0.125, 0.12, 0.115, 0.11, 0.105, 0.10, 0.10, 0.095)
NECK_HEAD_OVERLAP = 0.06

HEAD_RADII = Vector((0.165, 0.185, 0.17))
HEAD_SEGMENTS = (10, 8)
CHINSTRAP_BAND_NORMAL = Vector((0.0, 0.894, -0.447))
CHINSTRAP_BAND_HALF_WIDTH = 0.38
CHINSTRAP_TOP_LIMIT = 0.45

BEAK_SIDES = 6
UPPER_BEAK_RINGS = ((Vector((0.0, -0.99, 0.445)), 0.065, 0.035), (Vector((0.0, -1.08, 0.435)), 0.05, 0.025),
                    (Vector((0.0, -1.15, 0.425)), 0.02, 0.012))
LOWER_BEAK_RINGS = ((Vector((0.0, -0.985, 0.405)), 0.055, 0.02), (Vector((0.0, -1.13, 0.39)), 0.018, 0.01))
TONGUE_RINGS = ((Vector((0.0, -1.0, 0.42)), 0.03, 0.008), (Vector((0.0, -1.08, 0.415)), 0.018, 0.006))

EYE_SEGMENTS = (8, 5)
EYE_VERTICAL_STRETCH = 1.1
PUPIL_SIDES = 6
PUPIL_RADIUS = 0.03
PUPIL_DEPTH = 0.022
PUPIL_GAZE = Vector((0.3, -1.0, 0.1))  # left eye; mirrored for the right
PUPIL_SURFACE_FRACTION = 0.82

BROW_HALF_SPAN = 0.055
BROW_HALF_DEPTH = 0.018
BROW_HALF_HEIGHT = 0.013
BROW_ARCH = 0.008
BROW_INNER_DROP = 0.008

# Wing planform, left side, keyed by span x: leading edge y, trailing edge y, thickness.
WING_LEADING_EDGE = ((0.2, -0.20), (0.6, -0.22), (0.92, -0.18), (1.12, -0.10))
WING_TRAILING_EDGE = ((0.2, 0.30), (0.6, 0.24), (0.92, 0.20), (1.12, 0.10))
WING_THICKNESS = ((0.2, 0.09), (0.6, 0.06), (0.92, 0.045), (1.12, 0.03))
WING_ROOT_Z = 0.12
WING_DIHEDRAL_SLOPE = 0.025
WING_TOP_FRACTION = 0.3
WING_BOTTOM_FRACTION = 0.35
WING_SEGMENT_STATIONS = ((0.20, 0.40, 0.61), (0.56, 0.75, 0.95), (0.90, 1.02, 1.12))
WING_JOINT_INSET = 0.93
WING_SEGMENT_TOP_COLORS = (TAUPE_LIGHT, TAUPE_LIGHT, TAUPE)
WING_SEGMENT_REAR_COLORS = (TAUPE, TAUPE, TAUPE_DARK)
FINGER_ANGLES_DEG = (-5.0, 15.0, 35.0, 55.0)
FINGER_BASE_X = 1.07
FINGER_LENGTH = 0.17
FINGER_HALF_WIDTH = 0.034
FINGER_HALF_THICKNESS = 0.011
FINGER_MID_FRACTION = 0.55
FINGER_MID_WIDTH = 0.85
FINGER_TIP_WIDTH = 0.25

TAIL_RINGS = ((Vector((0.0, 0.40, 0.05)), 0.12, 0.05), (Vector((0.0, 0.62, 0.10)), 0.17, 0.035),
              (Vector((0.0, 0.78, 0.13)), 0.15, 0.015))
TAIL_SIDES = 6

LEG_SIDES = 4
LEG_HALF_WIDTH = 0.028
FOOT_OUTLINE = ((0.0, 0.03), (-0.07, -0.12), (0.0, -0.16), (0.07, -0.12))  # (u, v) in the leg plane, CCW
FOOT_THICKNESS = 0.02
FOOT_DROP = 0.015

SCARF_SIDES = 8
SCARF_WRAP_CENTER_T = 0.9  # along neck_1, from its head
SCARF_WRAP_PROFILE = ((0.112, -0.075), (0.172, -0.06), (0.185, 0.0), (0.172, 0.06), (0.112, 0.075))
SCARF_KNIT_RADIUS_THRESHOLD = 0.12
SCARF_KNIT_JITTER = 0.06
SCARF_KNOT_OFFSET = Vector((0.13, 0.08, 0.05))
SCARF_KNOT_RADIUS = 0.07
SCARF_RIBBON_HALF_WIDTH = 0.085
SCARF_RIBBON_HALF_THICKNESS = 0.014
SCARF_RIBBON_CLEARANCE = 0.05
SCARF_RIBBON_WAVE = 0.03
# Ribbon tails streaming back over the back: knot-relative start, then (x, y) stations; z follows the body top.
SCARF_TAIL_STATIONS = (
    ((0.12, -0.36), (0.15, -0.16), (0.17, 0.04), (0.18, 0.24), (0.17, 0.44)),
    ((0.0, -0.34), (-0.03, -0.14), (-0.05, 0.06), (-0.06, 0.26)),
)
SCARF_TAIL_FLUTTER_DEG = 14.0
SCARF_TAIL_BODY_BLEND = 0.8


class SkinnedMeshBuilder(MeshBuilder):
    """MeshBuilder that also records per-vertex bone weights and writes vertex groups."""

    def __init__(self):
        super().__init__()
        self.vertex_weights = []

    def add_shell(self, vertices, faces, weights, color):
        """Adds a closed shell.

        weights: {bone: weight}, a per-vertex list of those, or callable(vertex) -> {bone: weight}.
        color: (swatch, shade) or callable(face_index, centroid, normal) -> (swatch, shade).
        """
        base = len(self.vertices)
        for vertex_index, vertex in enumerate(vertices):
            vertex = Vector(vertex)
            self.add_vertex(vertex)
            if callable(weights):
                vertex_weights = weights(vertex)
            elif isinstance(weights, list):
                vertex_weights = weights[vertex_index]
            else:
                vertex_weights = weights
            self.vertex_weights.append(_normalized_weights(vertex_weights))
        for face_index, face in enumerate(faces):
            points = [Vector(vertices[index]) for index in face]
            centroid = sum(points, Vector()) / len(points)
            swatch = color(face_index, centroid, _newell_normal(points)) if callable(color) else color
            self.add_face([base + index for index in face], materials.PALETTE_MATERIAL, palette.flat_uv(*swatch))

    def build_skinned_object(self, name, collection, armature):
        """Writes the mesh, its vertex groups and an Armature modifier, parented to armature."""
        obj = self.build_object(name, collection)
        groups = {}
        for index, weights in enumerate(self.vertex_weights):
            for bone, weight in weights.items():
                if bone not in groups:
                    groups[bone] = obj.vertex_groups.new(name=bone)
                groups[bone].add([index], weight, "REPLACE")
        obj.parent = armature
        modifier = obj.modifiers.new("Armature", "ARMATURE")
        modifier.object = armature
        return obj


def _normalized_weights(weights):
    strongest = sorted(((w, b) for b, w in weights.items() if w >= MIN_WEIGHT), reverse=True)[:MAX_INFLUENCES]
    total = sum(w for w, _ in strongest)
    return {bone: weight / total for weight, bone in strongest}


def _newell_normal(points):
    normal = Vector((0.0, 0.0, 0.0))
    for index, current in enumerate(points):
        following = points[(index + 1) % len(points)]
        normal.x += (current.y - following.y) * (current.z + following.z)
        normal.y += (current.z - following.z) * (current.x + following.x)
        normal.z += (current.x - following.x) * (current.y + following.y)
    return normal.normalized() if normal.length > 0.0 else normal


def _lerp_table(table, x):
    if x <= table[0][0]:
        return table[0][1]
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return table[-1][1]


def _smoothstep(edge0, edge1, x):
    t = min(1.0, max(0.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def ring_basis(axis, up_hint=rig.WORLD_UP):
    """Returns (e1, e2) spanning the plane normal to axis, with e1 x e2 = axis and e2 close to up_hint."""
    axis = Vector(axis).normalized()
    up = Vector(up_hint)
    if abs(up.normalized().dot(axis)) > 0.99:
        up = Vector((0.0, -1.0, 0.0)) if abs(axis.y) < 0.9 else Vector((0.0, 0.0, 1.0))
    e2 = (up - axis * up.dot(axis)).normalized()
    e1 = e2.cross(axis)
    return e1, e2


def ring(center, axis, half_width, half_height, sides, up_hint=rig.WORLD_UP, angle_offset=0.0):
    """Returns an elliptical ring of points around axis, CCW seen from ahead (+axis looking back)."""
    e1, e2 = ring_basis(axis, up_hint)
    points = []
    for k in range(sides):
        angle = angle_offset + 2.0 * math.pi * k / sides
        points.append(Vector(center) + e1 * (half_width * math.cos(angle)) + e2 * (half_height * math.sin(angle)))
    return points


def loft(rings, cap_start=True, cap_end=True, periodic=False):
    """Skins consecutive rings (same point count, CCW seen from ahead) into an outward-facing shell.

    periodic connects the last ring back to the first (a torus) and adds no caps.
    """
    count = len(rings[0])
    vertices = [point for points in rings for point in points]
    spans = len(rings) if periodic else len(rings) - 1
    faces = []
    for span in range(spans):
        current = span * count
        following = ((span + 1) % len(rings)) * count
        for k in range(count):
            nxt = (k + 1) % count
            faces.append((current + k, current + nxt, following + nxt, following + k))
    if not periodic:
        if cap_start:
            faces.append(tuple(reversed(range(count))))
        if cap_end:
            faces.append(tuple((len(rings) - 1) * count + k for k in range(count)))
    return vertices, faces


def mirror_shell(vertices, faces):
    """Mirrors a shell across X, keeping faces outward."""
    return [Vector((-v.x, v.y, v.z)) for v in vertices], [tuple(reversed(face)) for face in faces]


def side_shell(vertices, faces, side):
    """Returns a left-side shell as-is, or mirrored for the right side."""
    return (vertices, faces) if side == "L" else mirror_shell(vertices, faces)


def _polyline_rings(points, radii, sides, up_hint=rig.WORLD_UP):
    rings = []
    for index, point in enumerate(points):
        previous = points[max(index - 1, 0)]
        following = points[min(index + 1, len(points) - 1)]
        radius = radii[index] if isinstance(radii[index], tuple) else (radii[index], radii[index])
        rings.append(ring(point, following - previous, radius[0], radius[1], sides, up_hint))
    return rings


# ---------------------------------------------------------------------------------------------- body parts


def _body_shape(unit):
    rear = max(unit.y, 0.0)
    front = max(-unit.y, 0.0)
    girth = (1.0 - BODY_REAR_TAPER * rear ** 1.5) * (1.0 + BODY_CHEST_FULLNESS * front)
    z = unit.z * BODY_RADII.z * girth * (BODY_TOP_FLATTEN if unit.z > 0.0 else 1.0)
    z += BODY_REAR_LIFT * rear ** 2 - BODY_CHEST_DROP * front
    return Vector((unit.x * BODY_RADII.x * girth, unit.y * BODY_RADII.y, z))


def body_top_height(x, y):
    """Returns the height of the body's upper surface above (x, y), matching _body_shape."""
    unit_y = max(-1.0, min(1.0, y / BODY_RADII.y))
    rear, front = max(unit_y, 0.0), max(-unit_y, 0.0)
    girth = (1.0 - BODY_REAR_TAPER * rear ** 1.5) * (1.0 + BODY_CHEST_FULLNESS * front)
    unit_x = x / (BODY_RADII.x * girth)
    unit_z = math.sqrt(max(0.0, 1.0 - unit_y * unit_y - unit_x * unit_x))
    return unit_z * BODY_RADII.z * girth * BODY_TOP_FLATTEN + BODY_REAR_LIFT * rear ** 2 - BODY_CHEST_DROP * front


def _body_color(unit_centroid):
    x, y, z = unit_centroid
    if y > 0.6 and z < 0.2:
        return WHITE
    if z < -0.55 or (y < -0.55 and z < 0.35):
        return TAUPE_LIGHT
    return TAUPE


def _body_weights(vertex):
    weights = {rig.BODY: 1.0}
    tail_blend = _smoothstep(BODY_TAIL_BLEND_START, BODY_TAIL_BLEND_START + BODY_TAIL_BLEND_RANGE, vertex.y)
    if tail_blend > 0.0:
        weights[rig.TAIL] = BODY_TAIL_BLEND_MAX * tail_blend
    neck_distance = (vertex - rig.NECK_POINTS[0]).length
    if neck_distance < BODY_NECK_BLEND_RADIUS:
        weights[rig.NECK_BONES[0]] = BODY_NECK_BLEND_MAX * (1.0 - neck_distance / BODY_NECK_BLEND_RADIUS)
    return weights


def add_body(builder):
    """Adds the chunky egg body (taupe back, pale breast and belly, white undertail)."""
    blob = shapes.blob(BODY_SEGMENTS[0], BODY_SEGMENTS[1], 1.0)
    unit_vertices = [Vector((v.x, -v.z, v.y)) for v in blob.vertices]  # poles along Y, winding preserved
    face_colors = []
    for face in blob.faces:
        centroid = sum((unit_vertices[i] for i in face), Vector()) / len(face)
        face_colors.append(_body_color(centroid))
    vertices = [_body_shape(v) for v in unit_vertices]
    builder.add_shell(vertices, blob.faces, _body_weights, lambda index, centroid, normal: face_colors[index])


def _neck_path():
    points = [NECK_START]
    weights = [{rig.BODY: 1.0}]
    joints = list(rig.NECK_POINTS)
    bones = list(rig.NECK_BONES)
    for index, bone in enumerate(bones):
        lower = rig.BODY if index == 0 else bones[index - 1]
        points.append(joints[index])
        weights.append({lower: 0.5, bone: 0.5})
        points.append((joints[index] + joints[index + 1]) * 0.5)
        weights.append({bone: 1.0})
    points.append(joints[-1])
    weights.append({bones[-1]: 0.5, rig.HEAD: 0.5})
    head_direction = (rig.HEAD_TIP - joints[-1]).normalized()
    points.append(joints[-1] + head_direction * NECK_HEAD_OVERLAP)
    weights.append({rig.HEAD: 1.0})
    return points, weights


def add_neck(builder):
    """Adds the black neck tube, blended across body, neck_1..3 and head."""
    points, ring_weights = _neck_path()
    rings = _polyline_rings(points, NECK_RADII, NECK_SIDES)
    vertices, faces = loft(rings)
    weights_by_vertex = [ring_weights[index // NECK_SIDES] for index in range(len(vertices))]
    builder.add_shell(vertices, faces, weights_by_vertex, CHARCOAL)


def _head_color(index, centroid, normal):
    direction = (centroid - rig.HEAD_CENTER)
    direction = Vector((direction.x / HEAD_RADII.x, direction.y / HEAD_RADII.y, direction.z / HEAD_RADII.z))
    direction.normalize()
    in_band = abs(direction.dot(CHINSTRAP_BAND_NORMAL)) < CHINSTRAP_BAND_HALF_WIDTH
    return WHITE if in_band and direction.z < CHINSTRAP_TOP_LIMIT else CHARCOAL


def add_head(builder):
    """Adds the round black head with the white chinstrap, beak, jaw and tongue."""
    blob = shapes.blob(HEAD_SEGMENTS[0], HEAD_SEGMENTS[1], 1.0)
    vertices = [rig.HEAD_CENTER + Vector((v.x * HEAD_RADII.x, v.y * HEAD_RADII.y, v.z * HEAD_RADII.z))
                for v in blob.vertices]
    builder.add_shell(vertices, blob.faces, {rig.HEAD: 1.0}, _head_color)
    for rings_spec, bone, color in ((UPPER_BEAK_RINGS, rig.HEAD, BEAK), (LOWER_BEAK_RINGS, rig.JAW, BEAK),
                                    (TONGUE_RINGS, rig.JAW, TONGUE)):
        axis = rings_spec[-1][0] - rings_spec[0][0]
        rings = [ring(center, axis, half_width, half_height, BEAK_SIDES)
                 for center, half_width, half_height in rings_spec]
        vertices, faces = loft(rings)
        builder.add_shell(vertices, faces, {bone: 1.0}, color)


def add_eyes_and_brows(builder):
    """Adds the big bulging eyes, pupils and the brow bars (one bone per brow)."""
    for side in rig.SIDES:
        center = rig.eye_center(side)
        blob = shapes.blob(EYE_SEGMENTS[0], EYE_SEGMENTS[1], rig.EYE_RADIUS)
        vertices = [center + Vector((v.x, v.y, v.z * EYE_VERTICAL_STRETCH)) for v in blob.vertices]
        builder.add_shell(vertices, blob.faces, {rig.HEAD: 1.0}, WHITE)

        gaze = rig.mirrored(PUPIL_GAZE, side).normalized()
        base = center + gaze * (rig.EYE_RADIUS * PUPIL_SURFACE_FRACTION)
        rings = [ring(base, gaze, PUPIL_RADIUS, PUPIL_RADIUS, PUPIL_SIDES),
                 ring(base + gaze * PUPIL_DEPTH, gaze, PUPIL_RADIUS * 0.85, PUPIL_RADIUS * 0.85, PUPIL_SIDES)]
        vertices, faces = loft(rings)
        builder.add_shell(vertices, faces, {rig.HEAD: 1.0}, CHARCOAL)

        brow = rig.brow_center(rig.SIDES[0])
        offsets = ((-BROW_HALF_SPAN, -BROW_INNER_DROP), (0.0, BROW_ARCH), (BROW_HALF_SPAN, 0.0))
        rings = [ring(brow + Vector((dx, 0.0, dz)), Vector((1.0, 0.0, 0.0)), BROW_HALF_DEPTH, BROW_HALF_HEIGHT, 4,
                      angle_offset=math.pi * 0.25) for dx, dz in offsets]
        vertices, faces = side_shell(*loft(rings), side)
        builder.add_shell(vertices, faces, {rig.brow_bone(side): 1.0}, CHARCOAL)


def _wing_profile(x, inset=1.0):
    leading = _lerp_table(WING_LEADING_EDGE, x)
    trailing = _lerp_table(WING_TRAILING_EDGE, x)
    thickness = _lerp_table(WING_THICKNESS, x)
    z = WING_ROOT_Z + WING_DIHEDRAL_SLOPE * (x - WING_SEGMENT_STATIONS[0][0])
    middle_y = leading + WING_TOP_FRACTION * (trailing - leading)
    points = [Vector((x, trailing, z - 0.004)), Vector((x, middle_y, z + thickness)), Vector((x, leading, z)),
              Vector((x, middle_y, z - WING_BOTTOM_FRACTION * thickness))]  # CCW seen from +X
    if inset != 1.0:
        centroid = sum(points, Vector()) / len(points)
        points = [centroid + (p - centroid) * inset for p in points]
    return points


def _wing_face_color(segment):
    def color(index, centroid, normal):
        if index >= (len(WING_SEGMENT_STATIONS[0]) - 1) * 4:
            return TAUPE_LIGHT  # end caps
        edge = index % 4
        if edge == 0:
            return WING_SEGMENT_REAR_COLORS[segment - 1]
        if edge == 1:
            return WING_SEGMENT_TOP_COLORS[segment - 1]
        return TAUPE_LIGHT
    return color


def _finger_shell(index):
    angle = math.radians(FINGER_ANGLES_DEG[index])
    direction = Vector((math.cos(angle), math.sin(angle), 0.0))
    leading = _lerp_table(WING_LEADING_EDGE, FINGER_BASE_X)
    trailing = _lerp_table(WING_TRAILING_EDGE, FINGER_BASE_X)
    t = (index + 0.5) / len(FINGER_ANGLES_DEG)
    z = WING_ROOT_Z + WING_DIHEDRAL_SLOPE * (FINGER_BASE_X - WING_SEGMENT_STATIONS[0][0])
    base = Vector((FINGER_BASE_X, leading + t * (trailing - leading), z))
    rings = []
    for fraction, width in ((0.0, 1.0), (FINGER_MID_FRACTION, FINGER_MID_WIDTH), (1.0, FINGER_TIP_WIDTH)):
        center = base + direction * (FINGER_LENGTH * fraction)
        rings.append(ring(center, direction, FINGER_HALF_WIDTH * width, FINGER_HALF_THICKNESS * width, 4))
    return loft(rings)


def add_wings(builder):
    """Adds both wings: three rigid segments per side plus four primary feather fingers on the hand."""
    for side in rig.SIDES:
        for segment, stations in zip(rig.WING_SEGMENTS, WING_SEGMENT_STATIONS):
            rings = [_wing_profile(x, WING_JOINT_INSET if (i == 0 and segment > 1) else 1.0)
                     for i, x in enumerate(stations)]
            vertices, faces = side_shell(*loft(rings), side)
            builder.add_shell(vertices, faces, {rig.wing_bone(side, segment): 1.0}, _wing_face_color(segment))
        for finger in range(len(FINGER_ANGLES_DEG)):
            vertices, faces = side_shell(*_finger_shell(finger), side)
            builder.add_shell(vertices, faces, {rig.wing_bone(side, 3): 1.0}, CHARCOAL)


def add_tail(builder):
    """Adds the black tail fan with a white underside."""
    rings = [ring(center, Vector((0.0, 1.0, 0.0)), half_width, half_height, TAIL_SIDES)
             for center, half_width, half_height in TAIL_RINGS]
    vertices, faces = loft(rings)
    root_y = TAIL_RINGS[0][0].y

    def weights(vertex):
        return {rig.BODY: 0.5, rig.TAIL: 0.5} if abs(vertex.y - root_y) < 1e-4 else {rig.TAIL: 1.0}

    builder.add_shell(vertices, faces, weights, lambda i, c, n: WHITE if n.z < -0.3 else CHARCOAL)


def add_legs(builder):
    """Adds the thin legs and flat webbed feet."""
    for side in rig.SIDES:
        rings = [ring(rig.HIP, Vector((0.0, 0.0, -1.0)), LEG_HALF_WIDTH, LEG_HALF_WIDTH, LEG_SIDES,
                      angle_offset=math.pi * 0.25),
                 ring(rig.ANKLE, Vector((0.0, 0.0, -1.0)), LEG_HALF_WIDTH * 0.8, LEG_HALF_WIDTH * 0.8, LEG_SIDES,
                      angle_offset=math.pi * 0.25)]
        vertices, faces = side_shell(*loft(rings), side)
        builder.add_shell(vertices, faces, {rig.leg_bone(side): 1.0}, LEGS)

        # Webbed foot in line with the leg (toes point down at rest), so tucked legs trail the toes backward.
        e1, e2 = ring_basis(Vector((0.0, 1.0, 0.0)))
        ankle = rig.ANKLE - Vector((0.0, 0.0, FOOT_DROP))
        outline = [ankle + e1 * u + e2 * v for u, v in FOOT_OUTLINE]
        half = Vector((0.0, FOOT_THICKNESS * 0.5, 0.0))
        rings = [[p - half for p in outline], [p + half for p in outline]]
        vertices, faces = side_shell(*loft(rings), side)
        builder.add_shell(vertices, faces, {rig.leg_bone(side): 1.0}, LEGS)


def build_body_builder():
    """Returns a SkinnedMeshBuilder holding the whole goose body (without the scarf)."""
    builder = SkinnedMeshBuilder()
    add_body(builder)
    add_neck(builder)
    add_head(builder)
    add_eyes_and_brows(builder)
    add_wings(builder)
    add_tail(builder)
    add_legs(builder)
    return builder


# ----------------------------------------------------------------------------------------------- scarf


def _scarf_wrap_frame():
    lower, upper = rig.NECK_POINTS[0], rig.NECK_POINTS[1]
    center = lower + (upper - lower) * SCARF_WRAP_CENTER_T
    axis = (rig.NECK_POINTS[2] - lower).normalized()
    return center, axis


def build_scarf_builder(seed):
    """Returns a SkinnedMeshBuilder holding the knitted pumpkin scarf (wrap, knot and two trailing tails)."""
    rng = random.Random(seed)
    builder = SkinnedMeshBuilder()
    center, axis = _scarf_wrap_frame()
    neck_low, neck_high = rig.NECK_BONES[0], rig.NECK_BONES[1]

    rings = []
    ring_weights = []
    for radius, offset in SCARF_WRAP_PROFILE:
        points = ring(center + axis * offset, axis, radius, radius, SCARF_SIDES)
        rings.append([center + axis * offset + (p - center - axis * offset) *
                      (1.0 + rng.uniform(-SCARF_KNIT_JITTER, SCARF_KNIT_JITTER) *
                       (radius > SCARF_KNIT_RADIUS_THRESHOLD)) for p in points])
        upper_share = 0.5 * _smoothstep(-0.06, 0.06, offset)
        ring_weights.append({neck_low: 1.0 - upper_share, neck_high: upper_share})
    vertices, faces = loft(rings, periodic=True)
    weights_by_vertex = [ring_weights[index // SCARF_SIDES] for index in range(len(vertices))]
    span_colors = (SCARF_DARK, SCARF, SCARF_LIGHT, SCARF_DARK, SCARF_DARK)
    builder.add_shell(vertices, faces, weights_by_vertex, lambda index, c, n: span_colors[index // SCARF_SIDES])

    knot = center + SCARF_KNOT_OFFSET
    blob = shapes.blob(6, 3, SCARF_KNOT_RADIUS)
    builder.add_shell([knot + v for v in blob.vertices], blob.faces, {neck_low: 1.0}, SCARF_DARK)

    for path_index, stations in enumerate(SCARF_TAIL_STATIONS):
        path = [knot]
        for station_index, (x, y) in enumerate(stations):
            wave = SCARF_RIBBON_WAVE * math.sin(math.pi * station_index + path_index)
            path.append(Vector((x, y, body_top_height(x, y) + SCARF_RIBBON_CLEARANCE + wave)))
        rings = []
        ring_weights = []
        for index, point in enumerate(path):
            t = index / (len(path) - 1)
            following = path[min(index + 1, len(path) - 1)]
            previous = path[max(index - 1, 0)]
            flutter = math.radians(SCARF_TAIL_FLUTTER_DEG) * math.sin(math.pi * 1.5 * t + path_index)
            tangent = (following - previous).normalized()
            e1, e2 = ring_basis(tangent)
            up_hint = e2 * math.cos(flutter) + e1 * math.sin(flutter)
            rings.append(ring(point, tangent, SCARF_RIBBON_HALF_WIDTH, SCARF_RIBBON_HALF_THICKNESS, 4, up_hint,
                              angle_offset=math.pi * 0.25))
            ring_weights.append({neck_low: 1.0 - SCARF_TAIL_BODY_BLEND * t, rig.BODY: SCARF_TAIL_BODY_BLEND * t})
        vertices, faces = loft(rings)
        weights_by_vertex = [ring_weights[index // 4] for index in range(len(vertices))]
        spans = len(path) - 1

        def tail_color(index, c, n, spans=spans):
            span = index // 4
            if span >= spans or span == spans - 1:
                return SCARF_LIGHT
            if span == spans - 2:
                return SCARF_STRIPE
            return SCARF if span % 2 == 0 else SCARF_DARK

        builder.add_shell(vertices, faces, weights_by_vertex, tail_color)
    return builder
