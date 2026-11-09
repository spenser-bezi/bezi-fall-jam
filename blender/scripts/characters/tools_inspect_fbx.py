"""Prints the raw Model nodes of an FBX (type, Lcl Translation/Rotation/Scaling) and its AnimStack names.

blender -b --factory-startup -P scripts/characters/tools_inspect_fbx.py -- <fbx>
"""
import sys

from io_scene_fbx import parse_fbx

TRANSFORM_PROPERTIES = (b"Lcl Translation", b"Lcl Rotation", b"Lcl Scaling")
REPORT_PREFIX = "[bezi-fbx]"


def _name(element):
    return element.props[1].split(b"\x00\x01")[0].decode()


def main():
    """Parses the FBX and prints every Model node transform and every take."""
    fbx_path = sys.argv[sys.argv.index("--") + 1]
    root, version = parse_fbx.parse(fbx_path)
    print(f"{REPORT_PREFIX} FBX version {version}")
    objects = next(e for e in root.elems if e.id == b"Objects")
    for element in objects.elems:
        if element.id == b"Model":
            transforms = {}
            for child in element.elems:
                if child.id == b"Properties70":
                    for prop in child.elems:
                        if prop.props[0] in TRANSFORM_PROPERTIES:
                            transforms[prop.props[0].decode()] = tuple(round(v, 4) for v in prop.props[4:7])
            kind = element.props[2].decode()
            if kind != "LimbNode" or _name(element) in ("root", "body"):
                print(f"{REPORT_PREFIX} Model {_name(element)} ({kind}): {transforms}")
        elif element.id == b"AnimationStack":
            print(f"{REPORT_PREFIX} take {_name(element)}")


main()
