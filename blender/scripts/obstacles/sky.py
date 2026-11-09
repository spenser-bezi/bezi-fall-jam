"""Sky obstacles (GDD 5.8): hot-air balloons (Mid), storm cloud + lightning bolt (Mid-High), fog puff (All bands).

Balloons pivot at the envelope center (the basket hangs below); the clouds and fog pivot at their bounds center;
the lightning bolt pivots at its top so code can hang it under a storm cloud.
"""
import math
import random

from mathutils import Matrix

from lib import palette, shapes
from obstacles import checks, common, preview_sheets
from obstacles.common import BASE, DARK, EXTRA_DARK, LIGHT

# ---------------------------------------------------------------- balloons
ENVELOPE_SIDES = 16
ENVELOPE_PROFILE = ((0.9, -5.0), (1.7, -4.0), (3.1, -2.4), (4.25, -0.6), (4.6, 0.9), (4.35, 2.4), (3.55, 3.75),
                    (2.15, 4.7), (0.0, 5.0))
ENVELOPE_RING_COUNT = len(ENVELOPE_PROFILE)
ENVELOPE_BOTTOM = ENVELOPE_PROFILE[0][1]
ENVELOPE_TOP = ENVELOPE_PROFILE[-1][1]
CROWN_BANDS = 2          # top bands painted with the crown color
SKIRT_BANDS = 1          # bottom band painted with the skirt color
BELLY_BAND = 3           # optional horizontal accent band index
BASKET_SIZE = 1.6
BASKET_HEIGHT = 1.15
BASKET_GAP = 1.45        # mouth to basket rim
BASKET_RIM = 0.16
ROPE_WIDTH = 0.09
ROPE_TOP_INSET = 0.64
BURNER_SIZE = 0.5
BASKET_TOP = ENVELOPE_BOTTOM - BASKET_GAP
BASKET_BOTTOM = BASKET_TOP - BASKET_HEIGHT
BALLOON_CENTER_Z = (ENVELOPE_TOP + BASKET_BOTTOM) * 0.5

BALLOON_SCHEMES = {
    # stripe colors (alternating per gore), crown, skirt, optional belly band color
    "SM_Balloon_A": {"stripes": ("Pumpkin", "WallCream"), "crown": "MapleRed", "skirt": "MapleRed", "belly": None},
    "SM_Balloon_B": {"stripes": ("MapleRed", "HarvestGold"), "crown": "NavyRoof", "skirt": "NavyRoof",
                     "belly": None},
    "SM_Balloon_C": {"stripes": ("NavyRoof", "HarvestGold"), "crown": "HarvestGold", "skirt": "Pumpkin",
                     "belly": "Pumpkin"},
}

# ---------------------------------------------------------------- storm cloud
CLOUD_PUFFS = (  # x, y, z, radius
    (0.0, 0.0, 1.2, 6.2), (-7.0, 1.0, 0.4, 5.0), (7.2, -0.6, 0.2, 5.2), (-12.0, -0.8, -0.8, 3.6),
    (12.4, 0.6, -0.9, 3.5), (-3.2, -3.6, -0.2, 4.4), (3.8, 3.4, 0.0, 4.6), (-2.5, 3.8, 2.4, 3.6),
    (3.0, -3.2, 2.8, 3.8),
)
CLOUD_SEGMENTS = (8, 5)
CLOUD_SQUASH = 0.62
CLOUD_JITTER = 0.14
CLOUD_FLOOR_Z = -2.6
CLOUD_TOP_SHADE_Z = 2.5

# ---------------------------------------------------------------- lightning
BOLT_POINTS = ((0.0, 0.0, 0.0), (0.0, 0.0, -1.6), (1.7, 0.0, -4.2), (-0.5, 0.0, -6.6), (1.4, 0.0, -9.6),
               (-0.7, 0.0, -12.4), (0.5, 0.0, -15.0))
BOLT_BRANCH = ((-0.5, 0.0, -6.6), (-2.4, 0.0, -8.8), (-2.0, 0.0, -9.6), (-3.1, 0.0, -11.6))
BOLT_WIDTH_TOP = 1.0
BOLT_WIDTH_BOTTOM = 0.3
BOLT_BRANCH_WIDTH = (0.55, 0.2)
BOLT_COLOR = ("HarvestGold", LIGHT)  # M_Glow tints it in Unity; the swatch is the palette's brightest yellow

# ---------------------------------------------------------------- fog puff
FOG_PUFFS = ((0.0, 0.0, 0.3, 3.6), (-3.6, 0.6, -0.2, 2.8), (3.7, -0.4, -0.25, 2.9), (-1.2, -2.2, -0.1, 2.6),
             (1.6, 2.1, 0.0, 2.5))
FOG_SEGMENTS = (7, 4)
FOG_SQUASH = 0.55
FOG_JITTER = 0.08
FOG_FLOOR_Z = -1.4
FOG_COLORS = (("Cloud", LIGHT), ("Cloud", LIGHT), ("Chinstrap", BASE), ("Cloud", BASE))

MID_BAND = "Mid band 12-26 m (spawn ~19 m; 12.6 m tall fits inside the 14 m band)"
STORM_BAND = "Mid-High zone (spawn ~30 m, spans ~25-35 m)"
RULES = {
    **{name: common.AssetRules(common.PIVOT_CENTER, (10.0, 14.0), expected_center=(0.0, 0.0, BALLOON_CENTER_Z),
                               band_note=MID_BAND) for name in BALLOON_SCHEMES},
    "SM_StormCloud": common.AssetRules(common.PIVOT_CENTER, (6.0, 12.0), band_note=STORM_BAND),
    "SM_Lightning": common.AssetRules(common.PIVOT_TOP, (12.0, 18.0),
                                      band_note="hangs from the storm cloud base; strikes through Low-Mid"),
    "SM_FogPuff": common.AssetRules(common.PIVOT_CENTER, (2.5, 6.0), band_note="All bands (visual only)"),
}


def _envelope_uv(scheme, rng):
    stripe_a, stripe_b = scheme["stripes"]
    cap_index = ENVELOPE_SIDES * (ENVELOPE_RING_COUNT - 1)
    top_band = ENVELOPE_RING_COUNT - 1 - CROWN_BANDS

    def uv(face, centroid):
        if face >= cap_index:
            return palette.flat_uv("GooseCharcoal", BASE)
        band, gore = divmod(face, ENVELOPE_SIDES)
        shade = LIGHT if band >= top_band - 1 and rng.random() < 0.35 else BASE
        if band >= top_band:
            return palette.flat_uv(scheme["crown"], shade)
        if band < SKIRT_BANDS:
            return palette.flat_uv(scheme["skirt"], DARK)
        if scheme["belly"] and band == BELLY_BAND:
            return palette.flat_uv(scheme["belly"], shade)
        return palette.flat_uv(stripe_a if gore % 2 == 0 else stripe_b, shade)

    return uv


def _balloon(builder, spec, rng):
    scheme = BALLOON_SCHEMES[spec.mesh_name]
    envelope = common.lathe(ENVELOPE_PROFILE, ENVELOPE_SIDES, angle_offset=math.pi / ENVELOPE_SIDES)
    common.add(builder, envelope, "Pumpkin", uv_for_face=_envelope_uv(scheme, rng))

    half = BASKET_SIZE * 0.5
    common.add(builder, common.centered_box(BASKET_SIZE, BASKET_SIZE, BASKET_HEIGHT, BASKET_BOTTOM), "Wood",
               uv_for_face=common.shaded(rng, "Wood", (BASE, DARK)))
    common.add(builder, common.centered_box(BASKET_SIZE + 0.12, BASKET_SIZE + 0.12, BASKET_RIM,
                                            BASKET_TOP - BASKET_RIM), "Wood", DARK)
    common.add(builder, common.centered_box(BURNER_SIZE, BURNER_SIZE, BURNER_SIZE,
                                            ENVELOPE_BOTTOM - BASKET_GAP * 0.55), "Slate")
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        top = (sx * ROPE_TOP_INSET, sy * ROPE_TOP_INSET, ENVELOPE_BOTTOM + 0.1)
        bottom = (sx * (half - 0.05), sy * (half - 0.05), BASKET_TOP - 0.05)
        common.add(builder, common.beam(top, bottom, ROPE_WIDTH), "Wood", DARK)


def _puff_cluster(builder, rng, puffs, segments, squash, jitter, floor_z, uv_for_height):
    for x, y, z, radius in puffs:
        puff = shapes.blob(segments[0], segments[1], radius, squash, jitter, rng)
        common.clamp_below(puff, floor_z - z)
        rotation = Matrix.Rotation(rng.uniform(0.0, 2.0 * math.pi), 4, "Z")
        builder.add_part(puff, Matrix.Translation((x, y, z)) @ rotation, common.MATERIAL,
                         lambda face, centroid, base_z=z: uv_for_height(base_z + centroid.z))


def _storm_cloud(builder, rng):
    def uv_for_height(z):
        if z < CLOUD_FLOOR_Z + 0.4:
            return palette.flat_uv("Slate", EXTRA_DARK)
        if z < 0.0:
            return palette.flat_uv("StormGray", EXTRA_DARK)
        if z < CLOUD_TOP_SHADE_Z:
            return palette.flat_uv(rng.choice(("StormGray", "StormGray", "Slate")), DARK)
        return palette.flat_uv("StormGray", rng.choice((BASE, DARK, DARK)))

    _puff_cluster(builder, rng, CLOUD_PUFFS, CLOUD_SEGMENTS, CLOUD_SQUASH, CLOUD_JITTER, CLOUD_FLOOR_Z, uv_for_height)
    common.recenter(builder)


def _fog_puff(builder, rng):
    def uv_for_height(z):
        if z < FOG_FLOOR_Z + 0.3:
            return palette.flat_uv("Cloud", BASE)
        return palette.flat_uv(*rng.choice(FOG_COLORS))

    _puff_cluster(builder, rng, FOG_PUFFS, FOG_SEGMENTS, FOG_SQUASH, FOG_JITTER, FOG_FLOOR_Z, uv_for_height)
    common.recenter(builder)


def _lightning(builder):
    uv = common.solid(*BOLT_COLOR)
    segment_count = len(BOLT_POINTS) - 1
    for index, (start, end) in enumerate(zip(BOLT_POINTS, BOLT_POINTS[1:])):
        w0 = BOLT_WIDTH_TOP + (BOLT_WIDTH_BOTTOM - BOLT_WIDTH_TOP) * index / segment_count
        w1 = BOLT_WIDTH_TOP + (BOLT_WIDTH_BOTTOM - BOLT_WIDTH_TOP) * (index + 1) / segment_count
        common.add(builder, common.beam(start, end, w0, w1), None, material=common.GLOW, uv_for_face=uv)
    branch_count = len(BOLT_BRANCH) - 1
    w_start, w_end = BOLT_BRANCH_WIDTH
    for index, (start, end) in enumerate(zip(BOLT_BRANCH, BOLT_BRANCH[1:])):
        w0 = w_start + (w_end - w_start) * index / branch_count
        w1 = w_start + (w_end - w_start) * (index + 1) / branch_count
        common.add(builder, common.beam(start, end, w0, w1), None, material=common.GLOW, uv_for_face=uv)


def build(spec, seed):
    """Builds one sky obstacle (chosen by spec.mesh_name) and returns its mesh object."""
    rng = random.Random(seed)
    if spec.mesh_name == "SM_Lightning":
        builder = common.new_builder((common.GLOW,))
        _lightning(builder)
    else:
        builder = common.new_builder()
        if spec.mesh_name in BALLOON_SCHEMES:
            _balloon(builder, spec, rng)
        elif spec.mesh_name == "SM_StormCloud":
            _storm_cloud(builder, rng)
        else:
            _fog_puff(builder, rng)
    return common.finish(builder, spec)


def validate(obj, spec):
    """Generic + obstacle checks (pivot, size, winding)."""
    return checks.validate_asset(obj, spec, RULES[spec.mesh_name])


def export(obj, spec, filepath):
    """Static FBX export."""
    return checks.export_asset(obj, spec, RULES[spec.mesh_name], filepath)


def preview(spec, seed):
    """Auto-framed contact sheet with a goose-size marker."""
    return preview_sheets.contact_sheet(spec, RULES[spec.mesh_name])
