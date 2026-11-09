"""Low-poly primitive builders. Every builder returns a Part with outward-facing faces."""
import math

from mathutils import Vector


class Part:
    """Local-space geometry: a vertex list and faces as vertex index tuples."""

    def __init__(self, vertices, faces):
        self.vertices = [Vector(v) for v in vertices]
        self.faces = [tuple(face) for face in faces]


def prism(sides, radius, height, top_radius=None, cap_top=True, cap_bottom=False, angle_offset=0.0):
    """Builds an n-sided prism/frustum standing on z = 0."""
    top_radius = radius if top_radius is None else top_radius
    vertices = []
    for ring_radius, z in ((radius, 0.0), (top_radius, height)):
        for k in range(sides):
            angle = angle_offset + 2.0 * math.pi * k / sides
            vertices.append((ring_radius * math.cos(angle), ring_radius * math.sin(angle), z))
    faces = []
    for k in range(sides):
        n = (k + 1) % sides
        faces.append((k, n, sides + n, sides + k))
    if cap_top:
        faces.append(tuple(sides + k for k in range(sides)))
    if cap_bottom:
        faces.append(tuple(reversed(range(sides))))
    return Part(vertices, faces)


def cone(sides, radius, height, angle_offset=0.0):
    """Builds an open-bottomed cone standing on z = 0."""
    vertices = [(radius * math.cos(angle_offset + 2.0 * math.pi * k / sides),
                 radius * math.sin(angle_offset + 2.0 * math.pi * k / sides), 0.0) for k in range(sides)]
    vertices.append((0.0, 0.0, height))
    apex = sides
    faces = [(k, (k + 1) % sides, apex) for k in range(sides)]
    return Part(vertices, faces)


def blob(u_segments, v_segments, radius, squash=1.0, jitter=0.0, rng=None):
    """Builds a faceted UV-sphere blob centered on the origin, with optional radial jitter."""
    vertices = [(0.0, 0.0, -radius * squash)]
    for ring in range(1, v_segments):
        phi = -math.pi * 0.5 + math.pi * ring / v_segments
        ring_radius = radius * math.cos(phi)
        z = radius * math.sin(phi) * squash
        for k in range(u_segments):
            angle = 2.0 * math.pi * k / u_segments
            vertices.append((ring_radius * math.cos(angle), ring_radius * math.sin(angle), z))
    vertices.append((0.0, 0.0, radius * squash))
    top = len(vertices) - 1

    def ring_vertex(ring, k):
        return 1 + (ring - 1) * u_segments + (k % u_segments)

    faces = []
    for k in range(u_segments):
        faces.append((0, ring_vertex(1, k + 1), ring_vertex(1, k)))
    for ring in range(1, v_segments - 1):
        for k in range(u_segments):
            faces.append((ring_vertex(ring, k), ring_vertex(ring, k + 1),
                          ring_vertex(ring + 1, k + 1), ring_vertex(ring + 1, k)))
    for k in range(u_segments):
        faces.append((ring_vertex(v_segments - 1, k), ring_vertex(v_segments - 1, k + 1), top))

    part = Part(vertices, faces)
    if jitter > 0.0 and rng is not None:
        for vertex in part.vertices:
            vertex *= 1.0 + rng.uniform(-jitter, jitter)
    return part


def disc(points):
    """Builds a flat fan polygon from CCW (x, y, z) outline points."""
    center = Vector((0.0, 0.0, 0.0))
    for point in points:
        center += Vector(point)
    center /= len(points)
    vertices = [center] + [Vector(p) for p in points]
    count = len(points)
    faces = [(0, 1 + k, 1 + (k + 1) % count) for k in range(count)]
    return Part(vertices, faces)
