"""SK_Goose armature layout and construction.

Blender space: Z up, the goose faces -Y (= Unity +Z, see lib/hexgrid.py) and its left wing points to +X
(= Unity -X). Every bone is rolled so its local Z points up (or forward for vertical bones). That gives
these local-axis meanings, which goose_animation.py relies on:
    spine bones (body, neck_*, head, jaw, brows): +X pitch up, +Z yaw left, +Y roll right (bank right)
    wing bones: +X raise, +Y twist (sign mirrored per side), +Z sweep (sign mirrored per side)
    leg bones:  +X swing the foot forward
    tail:       +X tip up, +Z tip toward the goose's right
"""
import bpy
from mathutils import Vector

ROOT = "root"
BODY = "body"
NECK_BONES = ("neck_1", "neck_2", "neck_3")
HEAD = "head"
JAW = "jaw"
TAIL = "tail"
SIDES = ("L", "R")
SIDE_SIGN = {"L": 1.0, "R": -1.0}  # +X is the goose's left side
WING_SEGMENTS = (1, 2, 3)

WORLD_UP = Vector((0.0, 0.0, 1.0))
WORLD_FORWARD = Vector((0.0, -1.0, 0.0))

ROOT_LENGTH = 0.3
BODY_TIP = Vector((0.0, -0.38, 0.04))
NECK_POINTS = (Vector((0.0, -0.40, 0.10)), Vector((0.0, -0.55, 0.22)), Vector((0.0, -0.67, 0.33)),
               Vector((0.0, -0.77, 0.41)))
HEAD_TIP = Vector((0.0, -0.97, 0.47))
JAW_HEAD = Vector((0.0, -0.965, 0.415))
JAW_TIP = Vector((0.0, -1.13, 0.385))
TAIL_HEAD = Vector((0.0, 0.46, 0.06))
TAIL_TIP = Vector((0.0, 0.74, 0.12))
WING_JOINTS = (Vector((0.26, -0.08, 0.12)), Vector((0.58, -0.06, 0.13)), Vector((0.92, -0.03, 0.14)),
               Vector((1.25, 0.02, 0.15)))  # left side: shoulder, elbow, wrist, tip
HIP = Vector((0.13, 0.08, -0.18))
ANKLE = Vector((0.13, 0.10, -0.56))

HEAD_CENTER = Vector((0.0, -0.86, 0.48))
EYE_OFFSET = Vector((0.075, -0.11, 0.075))  # left eye, from the head center
EYE_RADIUS = 0.068
BROW_OFFSET = Vector((0.0, -0.04, 0.056))  # from the eye center
BROW_LENGTH = 0.06


def wing_bone(side, segment):
    """Returns the wing bone name for a side ('L'/'R') and segment (1 shoulder .. 3 hand)."""
    return f"wing_{side}_{segment}"


def leg_bone(side):
    """Returns the leg bone name for a side."""
    return f"leg_{side}"


def brow_bone(side):
    """Returns the brow bone name for a side."""
    return f"brow_{side}"


def mirrored(point, side):
    """Mirrors a left-side point to the given side."""
    return Vector((point.x * SIDE_SIGN[side], point.y, point.z))


def eye_center(side):
    """Returns the center of one eyeball."""
    return HEAD_CENTER + mirrored(EYE_OFFSET, side)


def brow_center(side):
    """Returns the rest position of one brow (also its bone head)."""
    return eye_center(side) + BROW_OFFSET


def bone_layout():
    """Returns the bones in hierarchy order as (name, head, tail, parent, connected, roll_axis)."""
    up, forward = WORLD_UP, WORLD_FORWARD
    origin = Vector((0.0, 0.0, 0.0))
    layout = [
        (ROOT, origin, Vector((0.0, 0.0, ROOT_LENGTH)), None, False, forward),
        (BODY, origin, BODY_TIP, ROOT, False, up),
    ]
    parent = BODY
    for index, name in enumerate(NECK_BONES):
        layout.append((name, NECK_POINTS[index], NECK_POINTS[index + 1], parent, index > 0, up))
        parent = name
    layout.append((HEAD, NECK_POINTS[-1], HEAD_TIP, parent, True, up))
    layout.append((JAW, JAW_HEAD, JAW_TIP, HEAD, False, up))
    for side in SIDES:
        center = brow_center(side)
        layout.append((brow_bone(side), center, center + Vector((0.0, -BROW_LENGTH, 0.0)), HEAD, False, up))
    for side in SIDES:
        parent = BODY
        for segment in WING_SEGMENTS:
            name = wing_bone(side, segment)
            layout.append((name, mirrored(WING_JOINTS[segment - 1], side), mirrored(WING_JOINTS[segment], side),
                           parent, segment > 1, up))
            parent = name
    for side in SIDES:
        layout.append((leg_bone(side), mirrored(HIP, side), mirrored(ANKLE, side), BODY, False, forward))
    layout.append((TAIL, TAIL_HEAD, TAIL_TIP, BODY, False, up))
    return layout


def bone_names():
    """Returns every bone name in hierarchy order."""
    return [entry[0] for entry in bone_layout()]


def build_armature(name, collection):
    """Creates the goose armature object (at the origin) linked to collection."""
    data = bpy.data.armatures.new(name)
    data.display_type = "STICK"
    armature = bpy.data.objects.new(name, data)
    collection.objects.link(armature)
    view_layer = bpy.context.view_layer
    view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for bone_name, head, tail, parent, connected, roll_axis in bone_layout():
        bone = data.edit_bones.new(bone_name)
        bone.head, bone.tail = head, tail
        bone.align_roll(roll_axis)
        bone.use_deform = True
        if parent:
            bone.parent = data.edit_bones[parent]
            bone.use_connect = connected
    bpy.ops.object.mode_set(mode="OBJECT")
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "XYZ"
    return armature
