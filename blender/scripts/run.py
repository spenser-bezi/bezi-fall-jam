"""Art pipeline entry point.

blender -b --factory-startup --python-exit-code 1 -P scripts/run.py -- <command> <asset-id|group:name> [options]
  palette   regenerate textures/T_Palette_Fall.png
  build     build recipe(s) and save .blend
  validate  validate saved .blend(s)
  export    export saved .blend(s) to FBX (staging in renders/, or --unity)
  all       build + validate + export
  preview   contact sheets (+ tile cluster sheets, + mixed patch for groups)
"""
import argparse
import importlib
import json
import os
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import bpy  # noqa: E402

import registry  # noqa: E402
from lib import export_fbx, palette, paths, preview, validate  # noqa: E402

COMMANDS = ("palette", "build", "validate", "export", "all", "preview")


def parse_arguments():
    """Parses the arguments after Blender's '--' separator."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="run.py")
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("target", nargs="?", default="group:seam_test")
    parser.add_argument("--seed", type=int, default=None, help="override the registry seed")
    parser.add_argument("--unity", action="store_true", help="export into the Unity project art folder")
    parser.add_argument("--no-cluster", action="store_true", help="skip tile cluster renders")
    return parser.parse_args(argv)


def build_asset(spec, seed):
    """Builds one asset in a fresh scene and saves its .blend."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    module = importlib.import_module(spec.module)
    obj = module.build(spec, seed)
    paths.ensure_dir(os.path.dirname(spec.blend_path))
    bpy.context.preferences.filepaths.save_version = 0  # no .blend1 backups; recipes are the source of truth
    bpy.ops.wm.save_as_mainfile(filepath=spec.blend_path)
    print(f"[bezi-art] built {spec.asset_id} -> {spec.blend_path}")
    return obj


def load_asset(spec):
    """Opens an asset's saved .blend and returns its object."""
    bpy.ops.wm.open_mainfile(filepath=spec.blend_path)
    return bpy.data.objects[spec.mesh_name]


def recipe_module(spec):
    """Imports the recipe module for a spec.

    Optional hooks a recipe module may define to override the defaults:
        validate(obj, spec) -> report dict with a "passed" key
        export(obj, spec, filepath)
        preview(spec, seed) -> list of written image paths
    """
    return importlib.import_module(spec.module)


def main():
    """Runs the requested pipeline command."""
    args = parse_arguments()
    if args.command == "palette":
        palette.generate_atlas()
        return
    specs = registry.resolve(args.target)
    failures = []

    if args.command in ("build", "validate", "export", "all"):
        palette.load_atlas()
        for spec in specs:
            seed = spec.seed if args.seed is None else args.seed
            module = recipe_module(spec)
            obj = build_asset(spec, seed) if args.command in ("build", "all") else load_asset(spec)
            if args.command in ("validate", "all"):
                validator = getattr(module, "validate", validate.validate_object)
                report = validator(obj, spec)
                if not report["passed"]:
                    failures.append(spec.asset_id)
            if args.command in ("export", "all"):
                target_path = spec.unity_fbx_path if args.unity else spec.staging_fbx_path
                if hasattr(module, "export"):
                    module.export(obj, spec, target_path)
                else:
                    export_fbx.export_object(obj, target_path, animated=spec.animated)

    if args.command == "preview":
        tiles = []
        for spec in specs:
            seed = spec.seed if args.seed is None else args.seed
            module = recipe_module(spec)
            if hasattr(module, "preview"):
                module.preview(spec, seed)
                continue
            preview.contact_sheet(spec, spec.blend_path)
            if spec.kind == "tile":
                tiles.append((spec, spec.blend_path))
                if not args.no_cluster:
                    preview.cluster_sheet(spec, spec.blend_path, seed)
        if len(tiles) > 1 and args.target.startswith("group:"):
            group_name = args.target.split(":", 1)[1]
            preview.mixed_patch(tiles, tiles[0][0].seed, os.path.join(paths.ensure_dir(paths.RENDERS_DIR),
                                                                       f"mixed_{group_name}.png"))

    summary = {"command": args.command, "target": args.target, "failures": failures}
    print("[bezi-art] SUMMARY " + json.dumps(summary))
    if failures:
        sys.exit(1)


main()
