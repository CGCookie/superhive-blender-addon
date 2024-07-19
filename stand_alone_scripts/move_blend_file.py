"""
CLI Script to save the current blend file to a new location with updated relative paths and compression:

Argument Order:
     0. blender executable
     1. background arg
     2. factory startup arg
     3. blend file to open: str
     4. run python script arg
     5. script to run
     6. destination file path: str
"""

import bpy
import sys
from pathlib import Path

print(f"{sys.argv=}")

DST = sys.argv[6]

print(f"{DST=}")


if __name__ == "__main__":
    p = Path(DST)
    p.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_mainfile(filepath=DST, compress=True, relative_remap=True)
