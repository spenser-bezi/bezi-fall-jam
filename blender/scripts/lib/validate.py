"""Automated asset checks (Art Workflow 3.4). Writes a JSON report next to the previews."""
import json
import os

from . import builder as mesh_builder
from . import hexgrid, materials, palette, paths

POSITION_EPSILON = 1e-4
ZERO_AREA_EPSILON = 1e-6
SKIRT_TOP_THRESHOLD = -1.0
GROUND_MIN_NORMAL_Z = 0.2


def _check(results, name, ok, detail):
    results.append({"check": name, "ok": bool(ok), "detail": detail})


def validate_object(obj, spec):
    """Validates a built asset object against its spec. Returns the report dict."""
    mesh = obj.data
    results = []

    identity = (obj.location.length < POSITION_EPSILON
                and max(abs(a) for a in obj.rotation_euler) < POSITION_EPSILON
                and max(abs(s - 1.0) for s in obj.scale) < POSITION_EPSILON)
    _check(results, "transforms_applied", identity, "location 0, rotation 0, scale 1")

    triangles = sum(len(p.vertices) - 2 for p in mesh.polygons)
    _check(results, "triangle_budget", triangles <= spec.triangle_budget, f"{triangles} / {spec.triangle_budget}")

    material_names = [m.name for m in mesh.materials if m is not None]
    unknown = sorted(set(material_names) - materials.ALLOWED_MATERIALS)
    _check(results, "material_slots", not unknown, f"slots {material_names}, unknown {unknown}")

    uv_layer = mesh.uv_layers.active
    bad_uv_faces = 0
    for polygon in mesh.polygons:
        regions = {palette.classify_uv(*uv_layer.data[i].uv) for i in polygon.loop_indices}
        if len(regions) != 1 or None in regions:
            bad_uv_faces += 1
    _check(results, "uv_single_swatch", bad_uv_faces == 0, f"{bad_uv_faces} faces span or miss swatches")

    used = set()
    for polygon in mesh.polygons:
        used.update(polygon.vertices)
    loose = len(mesh.vertices) - len(used)
    _check(results, "no_loose_vertices", loose == 0, f"{loose} loose")

    zero_area = sum(1 for p in mesh.polygons if p.area < ZERO_AREA_EPSILON)
    _check(results, "no_zero_area_faces", zero_area == 0, f"{zero_area} zero-area faces")

    if spec.kind == "tile":
        rings = [0] * len(mesh.vertices)
        mesh.attributes[mesh_builder.RING_ATTRIBUTE].data.foreach_get("value", rings)
        band_ring = hexgrid.SUBDIVISIONS - hexgrid.EDGE_BAND_RINGS
        band_off = 0
        rim_off = 0
        for vertex, ring in zip(mesh.vertices, rings):
            co = vertex.co
            if ring >= band_ring and co.z > SKIRT_TOP_THRESHOLD and abs(co.z) > POSITION_EPSILON:
                band_off += 1
            if ring == hexgrid.SUBDIVISIONS and abs(hexgrid.inset_distance(co.x, co.y)) > POSITION_EPSILON:
                rim_off += 1
        _check(results, "edge_band_flat", band_off == 0, f"{band_off} edge-band verts off z=0")
        _check(results, "rim_on_hex", rim_off == 0, f"{rim_off} rim verts off the hex outline")

        flipped = 0
        steep = 0
        for polygon in mesh.polygons:
            corner_rings = [rings[v] for v in polygon.vertices]
            if min(corner_rings) < 0:
                continue
            if min(mesh.vertices[v].co.z for v in polygon.vertices) <= SKIRT_TOP_THRESHOLD:
                continue
            if polygon.normal.z <= 0.0:
                flipped += 1
            elif polygon.normal.z < GROUND_MIN_NORMAL_Z:
                steep += 1
        _check(results, "ground_faces_up", flipped == 0, f"{flipped} ground faces flipped ({steep} steep, info)")

        min_inset = min(hexgrid.inset_distance(v.co.x, v.co.y) for v in mesh.vertices)
        _check(results, "footprint_overhang", min_inset >= -hexgrid.MAX_CANOPY_OVERHANG - POSITION_EPSILON,
               f"max overhang {max(0.0, -min_inset):.2f} m (limit {hexgrid.MAX_CANOPY_OVERHANG})")
        z_values = [v.co.z for v in mesh.vertices]
        _check(results, "skirt_depth", min(z_values) >= -hexgrid.SKIRT_DEPTH - POSITION_EPSILON,
               f"min z {min(z_values):.2f}")
        _check(results, "decor_height", max(z_values) <= hexgrid.MAX_DECOR_HEIGHT + POSITION_EPSILON,
               f"max z {max(z_values):.2f} (limit {hexgrid.MAX_DECOR_HEIGHT})")

    report = {
        "asset": spec.asset_id,
        "mesh": spec.mesh_name,
        "triangles": triangles,
        "vertices": len(mesh.vertices),
        "materials": material_names,
        "passed": all(r["ok"] for r in results),
        "checks": results,
    }
    out_path = os.path.join(paths.asset_render_dir(spec.asset_id), "validation.json")
    with open(out_path, "w") as handle:
        json.dump(report, handle, indent=2)
    status = "PASS" if report["passed"] else "FAIL"
    print(f"[bezi-art] validate {spec.asset_id}: {status} ({triangles} tris)")
    for result in results:
        if not result["ok"]:
            print(f"[bezi-art]   FAIL {result['check']}: {result['detail']}")
    return report
