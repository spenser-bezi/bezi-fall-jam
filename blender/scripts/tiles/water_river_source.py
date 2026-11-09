"""SM_Tile_River_Source: spring pond at the center with a single river exit on socket side 0.

Also serves as the river mouth (a river ending in the pond) when a chain enters it.
"""
import math
import random

from mathutils import Vector

from lib import edge_sockets, hexgrid
from props import kit, water_props
from tiles import common, water_common
from tiles import water_river_common as river

SOCKET_SIDES = (0,)
POND_CENTER = (0.0, 1.3)
POND_RADIUS = 3.5
POND_WOBBLE = 0.14
POND_DEPTH = 0.7
LEAD_CONTROL = 2.4
POND_APPROACH = 2.6
MEANDER_RANGE = 1.6
END_SEARCH_STEP = 0.05
MOUTH_INSET = 0.15
REED_ARC_FRACTIONS = (0.25, 0.5)
POND_PLANTS = 5
POND_PLANT_INSET = 0.3
SPRING_ROCKS = 3
SPRING_ROCK_INSET = -0.2
LILY_PADS = 4
TREE_COUNT = 5
BUSH_COUNT = 4
ROCK_COUNT = 2
SNACK_ARC_FRACTION = 0.32


def build(spec, seed):
    """Builds the river source tile."""
    rng = random.Random(seed)
    grass = hexgrid.GrassPainter(seed)
    base_height = common.gentle_height(seed)
    pond = water_common.PondShape(POND_CENTER, POND_RADIUS, seed + 11, wobble=POND_WOBBLE, depth=POND_DEPTH)

    mid, lead = river.socket_lead(SOCKET_SIDES[0])
    inward = (lead - mid).normalized()
    side_offset = Vector((-inward.y, inward.x, 0.0)) * rng.uniform(-MEANDER_RANGE, MEANDER_RANGE)
    curve = river.cubic_bezier(lead, lead + inward * LEAD_CONTROL,
                               pond.center - inward * POND_APPROACH + side_offset, pond.center, river.BEZIER_SAMPLES)
    centerline = river.Centerline([mid] + curve)
    channel = river.RiverChannel(centerline, socket_at_end=False)

    arc_end = centerline.length
    while arc_end > 0.0:
        center, left, scale = channel.cross_section(arc_end)
        half = edge_sockets.WATER_HALF_WIDTH * scale
        edge_left, edge_right = center + left * half, center - left * half
        if max(pond.inset(p.x, p.y) for p in (edge_left, edge_right)) <= MOUTH_INSET:
            break
        arc_end -= END_SEARCH_STEP
    level = Vector((0.0, 0.0, edge_sockets.WATER_LEVEL))
    mouth_left, mouth_right = edge_left + level, edge_right + level

    def angle_of(point):
        return math.atan2(point.y - pond.center.y, point.x - pond.center.x)

    mouth_wedge = (angle_of(mouth_left), angle_of(mouth_right))

    def height(x, y):
        depths = [d for d in (pond.ground_depth(x, y), channel.ground_depth(x, y)) if d is not None]
        return base_height(x, y) if not depths else min(depths)

    def snap(position):
        pond_delta = abs(pond.inset(position.x, position.y))
        channel_delta = abs(channel.bank_offset(position.x, position.y))
        if pond_delta <= channel_delta:
            return pond.snap(position)
        if pond.inset(position.x, position.y) > 0.0:
            return position
        return channel.snap(position)

    def decorate(builder):
        channel.add_water(builder, 0.0, arc_end)
        pond.add_water(builder, (mouth_wedge[0], mouth_wedge[1], [mouth_left, mouth_right]))
        pond.add_foam(builder, mouth_wedge)
        river.add_bank_reeds(builder, rng, channel, height,
                             [centerline.length * fraction for fraction in REED_ARC_FRACTIONS])
        exit_angle = angle_of(mid)
        for k in range(POND_PLANTS):
            angle = exit_angle + math.radians(55.0) + k * math.radians(250.0) / (POND_PLANTS - 1)
            point = pond.point(angle, -POND_PLANT_INSET)
            if k % 2 == 0:
                water_props.add_cattail_clump(builder, rng, point.x, point.y, height(point.x, point.y))
            else:
                kit.add_reed_clump(builder, rng, point.x, point.y, height(point.x, point.y))
        spring_angle = exit_angle + math.pi
        for k in range(SPRING_ROCKS):
            angle = spring_angle + (k - 1) * 0.35
            point = pond.point(angle, SPRING_ROCK_INSET)
            kit.add_rock(builder, rng, point.x, point.y, height(point.x, point.y), rng.uniform(0.35, 0.6))
        lily = pond.point(spring_angle + 0.9, -pond.radius(spring_angle + 0.9) * 0.45, 0.0)
        water_props.add_lily_pads(builder, rng, lily.x, lily.y, edge_sockets.WATER_LEVEL, LILY_PADS)
        river.scatter_land_decor(builder, rng, height,
                                 lambda x, y, clearance: (channel.bank_offset(x, y) > clearance
                                                          and pond.inset(x, y) < -clearance),
                                 TREE_COUNT, BUSH_COUNT, ROCK_COUNT)

    obj = water_common.assemble_tile(spec, rng, grass.style, height, decorate, snap, SOCKET_SIDES)
    snack_points = [tuple(pond.center.xy), tuple(centerline.sample(centerline.length * SNACK_ARC_FRACTION).xy)]
    return river.finish_river_tile(obj, SOCKET_SIDES, snack_points)


def validate(obj, spec):
    """Socket-aware validation hook."""
    return river.validate_river_tile(obj, spec, SOCKET_SIDES)


def export(obj, spec, filepath):
    """FBX export hook (keeps edge_river_mask as an FBX user property)."""
    return river.export_with_custom_props(obj, filepath)


def preview(spec, seed):
    """Contact sheet + socket-matched cluster sheet + river chain and the mixed patch with tile.base."""
    return river.river_preview(spec, seed, include_chain=True)
