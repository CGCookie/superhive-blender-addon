"""
CLI Script to update the asset data of the current blend file:

Argument Order:
     0. blender executable
     1. background arg
     2. run python script arg
     3. script to run
     4. library name: str
     5. library path: str
"""

import sys

import bpy

LIB_NAME, LIB_PATH = sys.argv[4:]

print(f"{LIB_NAME=}, {LIB_PATH=}")

if __name__ == "__main__":
    bpy.context.preferences.filepaths.asset_libraries.new(
        name=LIB_NAME, directory=LIB_PATH
    )
    bpy.ops.wm.save_userpref()
