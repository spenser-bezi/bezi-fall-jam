"""Renders renders/lineup_obstacles.png from the built obstacle and snack .blend files.

blender -b --factory-startup --python-exit-code 1 -P scripts/obstacles/tools_lineup.py
"""
import os
import sys

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from obstacles import preview_sheets  # noqa: E402

preview_sheets.lineup()
