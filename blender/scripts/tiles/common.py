"""Shared tile assembly: ground + decoration baked into one mesh object."""
import bpy

from lib import hexgrid
from lib.builder import MeshBuilder
from lib.scatter import Noise2D

DEFAULT_HEIGHT_AMPLITUDE = 0.1
DEFAULT_HEIGHT_FREQUENCY = 0.22


def gentle_height(seed, amplitude=DEFAULT_HEIGHT_AMPLITUDE, frequency=DEFAULT_HEIGHT_FREQUENCY):
    """Returns a height function with subtle rolling noise for interior ground vertices."""
    height_noise = Noise2D(seed + 1)
    return lambda x, y: amplitude * height_noise.sample(x, y, frequency)


def assemble_tile(spec, rng, face_style, height_function, decorate=None, snap_function=None):
    """Builds ground and decoration into one object named spec.mesh_name in its own collection."""
    builder = MeshBuilder()
    hexgrid.build_ground(builder, rng, face_style, height_function, snap_function)
    if decorate is not None:
        decorate(builder)
    collection = bpy.data.collections.new(spec.mesh_name)
    bpy.context.scene.collection.children.link(collection)
    return builder.build_object(spec.mesh_name, collection)
