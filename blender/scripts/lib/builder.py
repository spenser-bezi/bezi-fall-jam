"""MeshBuilder: accumulates low-poly geometry with per-face material and UV, then writes one Blender mesh."""
import bpy
from mathutils import Vector

from . import materials

SWAY_ATTRIBUTE = "Col"
RING_ATTRIBUTE = "bz_ring"
NOT_GROUND_RING = -1


class MeshBuilder:
    """Collects vertices and faces from many parts so a whole tile bakes into a single mesh."""

    def __init__(self, material_names=(materials.PALETTE_MATERIAL,)):
        self.material_names = list(material_names)
        self.vertices = []
        self.vertex_sway = []
        self.vertex_ring = []
        self.faces = []

    def material_index(self, name):
        """Returns the slot index of a material, adding the slot if needed."""
        if name not in self.material_names:
            self.material_names.append(name)
        return self.material_names.index(name)

    def add_vertex(self, position, sway=0.0, ring=NOT_GROUND_RING):
        """Adds a vertex and returns its index. ring marks hex ground lattice verts for validation."""
        self.vertices.append(Vector(position))
        self.vertex_sway.append(sway)
        self.vertex_ring.append(ring)
        return len(self.vertices) - 1

    def add_face(self, indices, material, uvs):
        """Adds a face. uvs is one (u, v) applied to every corner, or one (u, v) per corner."""
        if not isinstance(uvs[0], (tuple, list)):
            uvs = [uvs] * len(indices)
        self.faces.append((tuple(indices), self.material_index(material), [tuple(uv) for uv in uvs]))

    def add_part(self, part, matrix, material, uv_for_face, sway_for_vertex=None):
        """Adds a shapes.Part transformed by matrix. uv_for_face(face_index, local_centroid) -> uv."""
        base = len(self.vertices)
        for local in part.vertices:
            sway = sway_for_vertex(local) if sway_for_vertex else 0.0
            self.add_vertex(matrix @ local, sway=max(0.0, min(1.0, sway)))
        for face_index, face in enumerate(part.faces):
            centroid = Vector((0.0, 0.0, 0.0))
            for index in face:
                centroid += part.vertices[index]
            centroid /= len(face)
            self.add_face([base + index for index in face], material, uv_for_face(face_index, centroid))

    def triangle_count(self):
        """Returns the triangle count after triangulation."""
        return sum(len(face[0]) - 2 for face in self.faces)

    def build_object(self, name, collection):
        """Writes the accumulated data into a new flat-shaded mesh object linked to collection."""
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([tuple(v) for v in self.vertices], [], [list(face[0]) for face in self.faces])

        uv_layer = mesh.uv_layers.new(name="UVMap")
        flat_uvs = [component for face in self.faces for uv in face[2] for component in uv]
        uv_layer.data.foreach_set("uv", flat_uvs)
        mesh.polygons.foreach_set("material_index", [face[1] for face in self.faces])
        mesh.polygons.foreach_set("use_smooth", [False] * len(self.faces))

        sway = mesh.color_attributes.new(name=SWAY_ATTRIBUTE, type="BYTE_COLOR", domain="POINT")
        colors = []
        for value in self.vertex_sway:
            colors.extend((value, 0.0, 0.0, 1.0))
        sway.data.foreach_set("color", colors)

        rings = mesh.attributes.new(name=RING_ATTRIBUTE, type="INT", domain="POINT")
        rings.data.foreach_set("value", self.vertex_ring)

        for material_name in self.material_names:
            mesh.materials.append(materials.get_material(material_name))
        mesh.update()

        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        return obj
