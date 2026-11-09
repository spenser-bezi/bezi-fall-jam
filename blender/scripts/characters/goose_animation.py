"""SK_Goose actions: procedural pose functions baked into Blender actions at 24 fps.

Every action keys location, rotation (XYZ Euler) and scale for every bone on every frame, so each FBX take
is complete and Unity never falls back to stale values. Loops repeat their first frame as the last frame.
One-shots (Honk, Tumble) start and end on the first frame of A_Goose_Glide, so transitions blend cleanly.
The root bone is never animated (no root motion); the body bone carries bob, bank and tumble.
"""
import math
from collections import namedtuple

import bpy
from mathutils import Matrix, Vector

from characters import goose_rig as rig

FPS = 24
FIRST_FRAME = 1
EULER_ORDER = "XYZ"
CHANNELS = (("location", 3), ("rotation_euler", 3), ("scale", 3))

FLAP_FRAMES = 16
GLIDE_FRAMES = 48
BANK_FRAMES = 24
HONK_FRAMES = 20
TUMBLE_FRAMES = 36
SWIM_FRAMES = 48

LEG_TUCK_DEG = -80.0
TAIL_FLIGHT_PITCH_DEG = 4.0
BANK_ROLL_DEG = 24.0
BANK_GLIDE_MOTION = 0.6

ActionSpec = namedtuple("ActionSpec", "name frame_count loop pose_function")


class BonePose:
    """Local pose of one bone: ordered rotations (applied first to last about fixed local axes)."""

    __slots__ = ("rotations", "location", "scale")

    def __init__(self):
        self.rotations = []
        self.location = Vector((0.0, 0.0, 0.0))
        self.scale = Vector((1.0, 1.0, 1.0))

    def rotation_matrix(self):
        """Returns the composed 3x3 rotation."""
        matrix = Matrix.Identity(3)
        for axis, radians in self.rotations:
            matrix = Matrix.Rotation(radians, 3, axis) @ matrix
        return matrix


class Pose:
    """A full-rig pose built from semantic helpers."""

    def __init__(self):
        self.bones = {name: BonePose() for name in rig.bone_names()}

    def rotate(self, bone, axis, degrees):
        """Adds a rotation about a local bone axis ('X', 'Y' or 'Z')."""
        if degrees:
            self.bones[bone].rotations.append((axis, math.radians(degrees)))

    def move(self, bone, offset):
        """Adds a local-space translation."""
        self.bones[bone].location += Vector(offset)

    def scale(self, bone, factors):
        """Multiplies the local scale."""
        current = self.bones[bone].scale
        self.bones[bone].scale = Vector((current.x * factors[0], current.y * factors[1], current.z * factors[2]))


def spine(pose, bone, pitch=0.0, yaw=0.0, roll=0.0):
    """Rotates a forward-facing bone: pitch up, yaw left, roll right (positive = bank right)."""
    pose.rotate(bone, "Y", roll)
    pose.rotate(bone, "X", pitch)
    pose.rotate(bone, "Z", yaw)


def wing(pose, side, segment, lift=0.0, sweep=0.0, twist=0.0):
    """Rotates a wing segment: lift raises the tip, sweep folds it back, twist pitches the leading edge down."""
    sign = rig.SIDE_SIGN[side]
    bone = rig.wing_bone(side, segment)
    pose.rotate(bone, "Y", twist * sign)
    pose.rotate(bone, "X", lift)
    pose.rotate(bone, "Z", sweep * sign)


def leg(pose, side, swing):
    """Swings a leg: positive brings the foot forward, negative tucks it back."""
    pose.rotate(rig.leg_bone(side), "X", swing)


def tail(pose, pitch=0.0, yaw=0.0):
    """Rotates the tail: pitch lifts the tip, yaw swings it toward the goose's right."""
    pose.rotate(rig.TAIL, "X", pitch)
    pose.rotate(rig.TAIL, "Z", yaw)


def brow(pose, side, lift=0.0, angry=0.0):
    """Moves a brow: lift raises it (meters), angry tilts the inner end down (negative = worried)."""
    pose.move(rig.brow_bone(side), (0.0, 0.0, lift))
    pose.rotate(rig.brow_bone(side), "Y", angry * rig.SIDE_SIGN[side])


def jaw_open(pose, degrees):
    """Opens the lower beak."""
    spine(pose, rig.JAW, pitch=-degrees)


def keyed(frame, keys):
    """Eases between (frame, value) keys with smoothstep, holding the ends."""
    if frame <= keys[0][0]:
        return keys[0][1]
    for (f0, v0), (f1, v1) in zip(keys, keys[1:]):
        if frame <= f1:
            t = (frame - f0) / (f1 - f0)
            return v0 + (v1 - v0) * t * t * (3.0 - 2.0 * t)
    return keys[-1][1]


def _flight_base(pose):
    for side in rig.SIDES:
        leg(pose, side, LEG_TUCK_DEG)
    tail(pose, pitch=TAIL_FLIGHT_PITCH_DEG)


def glide_pose(pose, phase, motion=1.0):
    """Wings spread with a slight dihedral, gentle bob, tip flex and a look around."""
    w = 2.0 * math.pi * phase
    _flight_base(pose)
    for side in rig.SIDES:
        wing(pose, side, 1, lift=7.0 + 2.5 * motion * math.sin(w), sweep=3.0)
        wing(pose, side, 2, lift=2.0 + 1.5 * motion * math.sin(w - 0.6))
        wing(pose, side, 3, lift=6.0 + 4.0 * motion * math.sin(w - 1.2), twist=2.0 * motion * math.sin(w - 1.2))
        brow(pose, side, lift=0.004)
    pose.move(rig.BODY, (0.0, 0.0, 0.025 * motion * math.sin(w)))
    spine(pose, rig.BODY, pitch=1.5 * motion * math.sin(2.0 * w), roll=2.0 * motion * math.sin(w))
    spine(pose, rig.NECK_BONES[2], yaw=3.0 * motion * math.sin(w))
    spine(pose, rig.HEAD, pitch=-1.0, yaw=6.0 * motion * math.sin(w))
    tail(pose, pitch=2.0 * motion * math.sin(w + 1.0))


def flap_pose(pose, frame, frame_count):
    """Full wingbeat: shoulder leads, forearm and hand follow with a delay; body bobs on the downstroke."""
    w = 2.0 * math.pi * frame / frame_count
    _flight_base(pose)
    for side in rig.SIDES:
        wing(pose, side, 1, lift=10.0 + 38.0 * math.sin(w), sweep=4.0 * math.cos(w), twist=-8.0 * math.cos(w))
        wing(pose, side, 2, lift=4.0 + 16.0 * math.sin(w - 0.5), twist=-6.0 * math.cos(w - 0.5))
        wing(pose, side, 3, lift=4.0 + 24.0 * math.sin(w - 1.0), sweep=8.0 * math.cos(w - 1.0),
             twist=-10.0 * math.cos(w - 1.0))
        brow(pose, side, lift=0.004 * math.sin(w - 2.0))
    pose.move(rig.BODY, (0.0, 0.0, -0.045 * math.cos(w - 0.4)))
    spine(pose, rig.BODY, pitch=2.0 * math.sin(w))
    spine(pose, rig.NECK_BONES[0], pitch=-3.0 * math.cos(w - 0.4))
    spine(pose, rig.HEAD, pitch=3.0 * math.cos(w - 0.4))
    tail(pose, pitch=5.0 * math.sin(w - 1.5))


def glide_action_pose(pose, frame, frame_count):
    """A_Goose_Glide frame."""
    glide_pose(pose, frame / frame_count)


def bank_pose(pose, frame, frame_count, direction):
    """Banked glide. direction +1 = bank right (BankR), -1 = bank left (BankL)."""
    glide_pose(pose, frame / frame_count, BANK_GLIDE_MOTION)
    spine(pose, rig.BODY, roll=BANK_ROLL_DEG * direction, yaw=-6.0 * direction)
    spine(pose, rig.NECK_BONES[0], roll=-8.0 * direction)
    spine(pose, rig.NECK_BONES[1], roll=-6.0 * direction, yaw=-5.0 * direction)
    spine(pose, rig.HEAD, roll=-6.0 * direction, yaw=-8.0 * direction)
    inner, outer = ("R", "L") if direction > 0 else ("L", "R")
    wing(pose, inner, 1, lift=-4.0, sweep=6.0)
    wing(pose, inner, 3, lift=10.0)
    wing(pose, outer, 1, lift=5.0, sweep=-3.0)
    wing(pose, outer, 2, lift=3.0)
    tail(pose, yaw=6.0 * direction)
    for side in rig.SIDES:
        brow(pose, side, lift=-0.006 if side == inner else 0.008, angry=6.0)


def honk_pose(pose, frame, frame_count):
    """Anticipation (head back, squash), honk (neck thrust, beak open, stretch, brows up), settle."""
    glide_pose(pose, 0.0)
    anticipation = keyed(frame, ((0, 0.0), (4, 1.0), (7, 0.0)))
    honk = keyed(frame, ((0, 0.0), (4, 0.0), (7, 1.0), (12, 0.9), (16, 0.2), (frame_count, 0.0)))
    beak = keyed(frame, ((0, 0.0), (5, 0.0), (7, 1.0), (12, 0.85), (15, 0.0)))
    squash = keyed(frame, ((0, 0.0), (4, 1.0), (7, -1.0), (11, 0.35), (15, -0.1), (frame_count, 0.0)))
    pose.scale(rig.BODY, (1.0 + 0.05 * squash, 1.0 - 0.08 * squash, 1.0 + 0.05 * squash))
    spine(pose, rig.NECK_BONES[0], pitch=14.0 * anticipation - 8.0 * honk)
    spine(pose, rig.NECK_BONES[1], pitch=6.0 * anticipation - 6.0 * honk)
    spine(pose, rig.NECK_BONES[2], pitch=-4.0 * anticipation + 10.0 * honk)
    spine(pose, rig.HEAD, pitch=-6.0 * anticipation + 18.0 * honk)
    head_scale = 1.0 + 0.12 * honk - 0.04 * anticipation
    pose.scale(rig.HEAD, (head_scale, head_scale, head_scale))
    jaw_open(pose, 38.0 * beak)
    for side in rig.SIDES:
        brow(pose, side, lift=0.025 * honk - 0.01 * anticipation, angry=6.0 * anticipation - 8.0 * honk)
        wing(pose, side, 1, lift=6.0 * honk)
    tail(pose, pitch=10.0 * honk)


def tumble_pose(pose, frame, frame_count):
    """Hit reaction: a full barrel roll with flailing wings, neck whip, open beak and alarmed brows."""
    glide_pose(pose, 0.0)
    roll_end = frame_count * 0.72
    roll_t = min(frame / roll_end, 1.0)
    roll = 360.0 * roll_t * roll_t * roll_t * (roll_t * (roll_t * 6.0 - 15.0) + 10.0)
    envelope = keyed(frame, ((0, 0.0), (5, 1.0), (24, 1.0), (34, 0.0)))
    w = 2.0 * math.pi * frame / frame_count
    drop = -0.15 * math.sin(math.pi * min(frame / (frame_count - 6), 1.0))
    pose.move(rig.BODY, (0.0, 0.0, drop))
    spine(pose, rig.BODY, roll=roll, pitch=15.0 * math.sin(2.0 * w) * envelope)
    for side, offset in (("L", 0.0), ("R", math.pi * 0.5)):
        wing(pose, side, 1, lift=35.0 * math.sin(3.0 * w + offset) * envelope,
             sweep=15.0 * math.sin(2.0 * w + offset) * envelope)
        wing(pose, side, 3, lift=25.0 * math.sin(3.0 * w - 1.0 + offset) * envelope)
        leg(pose, side, 50.0 * math.sin(3.0 * w + 2.0 * offset) * envelope)
        brow(pose, side, lift=0.03 * envelope, angry=-12.0 * envelope)
    spine(pose, rig.NECK_BONES[0], yaw=20.0 * math.sin(2.0 * w) * envelope)
    spine(pose, rig.NECK_BONES[1], pitch=15.0 * math.sin(2.0 * w + 1.0) * envelope)
    spine(pose, rig.HEAD, roll=25.0 * math.sin(3.0 * w) * envelope)
    jaw_open(pose, 25.0 * envelope)
    tail(pose, yaw=15.0 * math.sin(3.0 * w) * envelope)


def swim_pose(pose, frame, frame_count):
    """Floating: wings folded along the flanks, neck upright in an S, legs paddling, gentle bob."""
    w = 2.0 * math.pi * frame / frame_count
    pose.move(rig.BODY, (0.0, 0.0, 0.02 * math.sin(w)))
    spine(pose, rig.BODY, pitch=3.0, roll=2.5 * math.sin(w + 1.0))
    spine(pose, rig.NECK_BONES[0], pitch=35.0)
    spine(pose, rig.NECK_BONES[1], pitch=5.0)
    spine(pose, rig.NECK_BONES[2], pitch=-20.0 + 3.0 * math.sin(w), yaw=5.0 * math.sin(w))
    spine(pose, rig.HEAD, pitch=-27.0 - 3.0 * math.sin(w), yaw=10.0 * math.sin(w))
    for side, offset in (("L", 0.0), ("R", math.pi)):
        wing(pose, side, 1, lift=-5.0, sweep=78.0, twist=-85.0)
        wing(pose, side, 2, lift=5.0, sweep=8.0)
        wing(pose, side, 3, lift=12.0, sweep=10.0)
        leg(pose, side, -15.0 + 30.0 * math.sin(2.0 * w + offset))
        brow(pose, side, lift=0.008, angry=-3.0)
    tail(pose, pitch=18.0, yaw=5.0 * math.sin(2.0 * w))


ACTIONS = (
    ActionSpec("A_Goose_Flap", FLAP_FRAMES, True, flap_pose),
    ActionSpec("A_Goose_Glide", GLIDE_FRAMES, True, glide_action_pose),
    ActionSpec("A_Goose_BankL", BANK_FRAMES, True, lambda pose, f, n: bank_pose(pose, f, n, -1.0)),
    ActionSpec("A_Goose_BankR", BANK_FRAMES, True, lambda pose, f, n: bank_pose(pose, f, n, 1.0)),
    ActionSpec("A_Goose_Honk", HONK_FRAMES, False, honk_pose),
    ActionSpec("A_Goose_Tumble", TUMBLE_FRAMES, False, tumble_pose),
    ActionSpec("A_Goose_Swim", SWIM_FRAMES, True, swim_pose),
)
ACTION_NAMES = tuple(spec.name for spec in ACTIONS)


def frame_range(spec):
    """Returns the (first, last) frame of an action; loops repeat their first pose on the last frame."""
    return FIRST_FRAME, FIRST_FRAME + spec.frame_count


def sample_pose(spec, frame_offset):
    """Evaluates an action's pose function at a frame offset from its first frame."""
    pose = Pose()
    spec.pose_function(pose, frame_offset, spec.frame_count)
    return pose


def bake_action(spec):
    """Bakes one ActionSpec into a Blender action with linear keys on every frame for every bone."""
    action = bpy.data.actions.new(spec.name)
    action.use_fake_user = True
    names = rig.bone_names()
    first, last = frame_range(spec)
    frames = list(range(first, last + 1))
    samples = {name: {"location": [], "rotation_euler": [], "scale": []} for name in names}
    previous = {}
    for frame in frames:
        pose = sample_pose(spec, frame - first)
        for name in names:
            bone_pose = pose.bones[name]
            matrix = bone_pose.rotation_matrix()
            euler = matrix.to_euler(EULER_ORDER, previous[name]) if name in previous else matrix.to_euler(EULER_ORDER)
            previous[name] = euler
            samples[name]["location"].append(tuple(bone_pose.location))
            samples[name]["rotation_euler"].append(tuple(euler))
            samples[name]["scale"].append(tuple(bone_pose.scale))
    if spec.loop:
        for name in names:
            for channel in samples[name].values():
                channel[-1] = channel[0]

    for name in names:
        for path, size in CHANNELS:
            values = samples[name][path]
            for index in range(size):
                curve = action.fcurves.new(f'pose.bones["{name}"].{path}', index=index, action_group=name)
                curve.keyframe_points.add(len(frames))
                coordinates = []
                for frame, value in zip(frames, values):
                    coordinates.extend((float(frame), value[index]))
                curve.keyframe_points.foreach_set("co", coordinates)
                for point in curve.keyframe_points:
                    point.interpolation = "LINEAR"
                curve.update()
    action.use_frame_range = True
    action.frame_start, action.frame_end = first, last
    action.use_cyclic = spec.loop
    action["bz_loop"] = spec.loop
    return action


def bake_all(armature):
    """Bakes every goose action and stacks each on its own NLA track (one FBX take per strip)."""
    animation_data = armature.animation_data_create()
    actions = []
    for spec in ACTIONS:
        action = bake_action(spec)
        track = animation_data.nla_tracks.new()
        track.name = spec.name
        strip = track.strips.new(spec.name, FIRST_FRAME, action)
        strip.name = spec.name
        actions.append(action)
    animation_data.action = None
    return actions


def show_action(armature, action_name, frame):
    """Evaluates a single action on an armature (NLA disabled) at a frame, for previews and references."""
    animation_data = armature.animation_data
    animation_data.use_nla = False
    animation_data.action = bpy.data.actions[action_name]
    bpy.context.scene.frame_set(int(frame))


def restore_export_state(armature):
    """Puts the armature back into NLA mode with no active action and every track/strip unmuted."""
    animation_data = armature.animation_data
    animation_data.action = None
    animation_data.use_nla = True
    for track in animation_data.nla_tracks:
        track.mute = False
        for strip in track.strips:
            strip.mute = False
