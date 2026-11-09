"""Snack pickups (GDD 5.7, Low band): chunky icon-scale corn cob, apple and pumpkin, ~1 m, pivot at the center.

Kit-derived shapes blown up to icon scale so they read at the 45 m gameplay camera; bob/spin is gameplay code.
"""
import math
import random

from mathutils import Matrix

from lib import palette
from obstacles import checks, common, preview_sheets
from obstacles.common import BASE, DARK, LIGHT

SNACK_SIZE_RANGE = (0.8, 1.2)
SNACK_BAND = "Low band pickup (4-12 m); bob/spin in code"

CORN_SIDES = 8
CORN_PROFILE = ((0.0, -0.44), (0.2, -0.4), (0.27, -0.16), (0.285, 0.14), (0.23, 0.38), (0.12, 0.5), (0.0, 0.54))
CORN_KERNELS = (("Mustard", BASE), ("HarvestGold", BASE), ("HarvestGold", LIGHT))
CORN_HUSKS = 3
CORN_HUSK_LENGTH = (0.62, 0.42)    # long, short husk tip height above the cob base
CORN_HUSK_WIDTH = (0.24, 0.05)
CORN_HUSK_SPLAY = 0.36
CORN_STEM = (0.11, 0.16)
CORN_TILT_DEG = 18.0

APPLE_SIDES = 10
APPLE_PROFILE = ((0.0, -0.34), (0.22, -0.4), (0.41, -0.26), (0.47, -0.02), (0.43, 0.22), (0.27, 0.36),
                 (0.0, 0.29))
APPLE_HIGHLIGHT_Z = 0.12
APPLE_STEM = ((0.0, 0.0, 0.26), (0.05, 0.0, 0.5), 0.06)
APPLE_LEAF = ((0.05, 0.0, 0.46), (0.33, 0.04, 0.52), 0.17, 0.04)  # start, end, width start, width end

PUMPKIN_SIDES = 16
PUMPKIN_PROFILE = ((0.0, -0.3), (0.32, -0.36), (0.5, -0.2), (0.545, 0.02), (0.48, 0.22), (0.3, 0.33), (0.0, 0.26))
PUMPKIN_RIB_DEPTH = 0.88
PUMPKIN_STEM = (((0.0, 0.0, 0.22), (0.02, 0.0, 0.42)), ((0.02, 0.0, 0.42), (0.11, 0.0, 0.55)))
PUMPKIN_STEM_WIDTH = (0.13, 0.09, 0.07)
PUMPKIN_LEAF = ((0.06, 0.0, 0.3), (0.34, -0.16, 0.33), 0.2, 0.04)

RULES = {
    name: common.AssetRules(common.PIVOT_CENTER, (0.5, 1.2), max_dimension_range=SNACK_SIZE_RANGE,
                            band_note=SNACK_BAND)
    for name in ("SM_Snack_Corn", "SM_Snack_Apple", "SM_Snack_Pumpkin")
}


def _corn(builder, rng):
    tilt = Matrix.Rotation(math.radians(CORN_TILT_DEG), 4, "Y")
    cob = common.lathe(CORN_PROFILE, CORN_SIDES)
    common.add(builder, cob, "Mustard", matrix=tilt,
               uv_for_face=lambda face, centroid: palette.flat_uv(*CORN_KERNELS[(face + face // CORN_SIDES) % 3]))
    base_z = CORN_PROFILE[0][1] + 0.06
    for husk in range(CORN_HUSKS):
        angle = 2.0 * math.pi * husk / CORN_HUSKS + rng.uniform(-0.2, 0.2)
        length = CORN_HUSK_LENGTH[husk % 2]
        direction = (math.cos(angle), math.sin(angle))
        start = (direction[0] * 0.17, direction[1] * 0.17, base_z)
        end = (direction[0] * CORN_HUSK_SPLAY, direction[1] * CORN_HUSK_SPLAY, base_z + length)
        part = common.beam(start, end, *CORN_HUSK_WIDTH, roll=angle)
        common.add(builder, part, "Moss", matrix=tilt,
                   uv_for_face=common.shaded(rng, "LightMoss" if husk % 2 else "Moss", (BASE, LIGHT)))
    stem_radius, stem_length = CORN_STEM
    stem = common.lathe(((stem_radius, base_z - stem_length), (stem_radius * 0.8, base_z + 0.02)), 5)
    common.add(builder, stem, "Moss", DARK, tilt)


def _apple(builder, rng):
    def apple_uv(face, centroid):
        if centroid.z > APPLE_HIGHLIGHT_Z and rng.random() < 0.5:
            return palette.flat_uv("MapleRed", LIGHT)
        return palette.flat_uv("MapleRed", rng.choice((BASE, BASE, DARK)))

    common.add(builder, common.lathe(APPLE_PROFILE, APPLE_SIDES), "MapleRed", uv_for_face=apple_uv)
    stem_start, stem_end, stem_width = APPLE_STEM
    common.add(builder, common.beam(stem_start, stem_end, stem_width, stem_width * 0.7), "Wood", DARK)
    leaf_start, leaf_end, w0, w1 = APPLE_LEAF
    common.add(builder, common.beam(leaf_start, leaf_end, w0, w1), "Moss", LIGHT)


def _pumpkin(builder, rng):
    ribbed = common.lathe(PUMPKIN_PROFILE, PUMPKIN_SIDES,
                          radius_scale=lambda k, ring: 1.0 if k % 2 == 0 else PUMPKIN_RIB_DEPTH)
    common.add(builder, ribbed, "Pumpkin", uv_for_face=common.shaded(rng, "Pumpkin", (BASE, BASE, LIGHT, DARK)))
    widths = PUMPKIN_STEM_WIDTH
    for index, (start, end) in enumerate(PUMPKIN_STEM):
        common.add(builder, common.beam(start, end, widths[index], widths[index + 1]), "Wood", DARK)
    leaf_start, leaf_end, w0, w1 = PUMPKIN_LEAF
    common.add(builder, common.beam(leaf_start, leaf_end, w0, w1), "Moss", BASE)


BUILDERS = {"SM_Snack_Corn": _corn, "SM_Snack_Apple": _apple, "SM_Snack_Pumpkin": _pumpkin}


def build(spec, seed):
    """Builds one snack pickup centered on its pivot and returns its mesh object."""
    rng = random.Random(seed)
    builder = common.new_builder()
    BUILDERS[spec.mesh_name](builder, rng)
    common.recenter(builder)
    return common.finish(builder, spec)


def validate(obj, spec):
    """Generic + pickup checks (center pivot, 0.8-1.2 m icon size, winding)."""
    return checks.validate_asset(obj, spec, RULES[spec.mesh_name])


def export(obj, spec, filepath):
    """Static FBX export."""
    return checks.export_asset(obj, spec, RULES[spec.mesh_name], filepath)


def preview(spec, seed):
    """Auto-framed contact sheet with a goose-size marker."""
    return preview_sheets.contact_sheet(spec, RULES[spec.mesh_name])
