"""Seeded noise and scatter helpers so every recipe is deterministic."""
import math
import random

from mathutils import Vector, noise

NOISE_OFFSET_RANGE = 1000.0
DEFAULT_SCATTER_ATTEMPTS = 4000


class Noise2D:
    """Seeded 2D Perlin noise (roughly -1..1)."""

    def __init__(self, seed):
        rng = random.Random(seed)
        self.offset = Vector([rng.uniform(-NOISE_OFFSET_RANGE, NOISE_OFFSET_RANGE) for _ in range(3)])

    def sample(self, x, y, frequency=1.0):
        """Samples the noise at (x, y) scaled by frequency."""
        return noise.noise(Vector((x * frequency, y * frequency, 0.0)) + self.offset)


def scatter_points(rng, count, extent, min_distance, accept, existing=(), attempts=DEFAULT_SCATTER_ATTEMPTS):
    """Dart-throwing Poisson scatter in a square of half-size extent. accept(x, y) filters candidates."""
    points = []
    blockers = list(existing)
    for _ in range(attempts):
        if len(points) >= count:
            break
        x, y = rng.uniform(-extent, extent), rng.uniform(-extent, extent)
        if not accept(x, y):
            continue
        if any(math.hypot(x - bx, y - by) < min_distance for bx, by in blockers):
            continue
        points.append((x, y))
        blockers.append((x, y))
    return points
