"""
CLI Script to update the asset data of the current blend file:

Argument Order:
     0. blender executable
     1. background arg
     2. factory startup arg
     3. blend file to open: str
     4. run python script arg
     5. script to run
     6. IDs to keep (if None, look at IDs to remove)
     7. IDs to remove
     8. types (this is a list of strings that represent the types of the IDs to keep or remove)
"""

import bpy
import sys

print(f"{sys.argv=}")

IDS_TO_KEEP = sys.argv[6].split(":--separator--:") if sys.argv[6] != "None" else []
IDS_TO_REMOVE = sys.argv[7].split(":--separator--:") if sys.argv[7] != "None" else []
TYPES = sys.argv[8].split(":--separator--:")

print(f"{IDS_TO_KEEP=}")
print(f"{IDS_TO_REMOVE=}")
print(f"{TYPES=}")


def remove_other_assets():
    """Remove the assets that are not in the IDS_TO_KEEP list."""
    for data_type in dir(bpy.data):
        ids_data = getattr(bpy.data, data_type)
        if not isinstance(ids_data, bpy.types.bpy_prop_collection):
            continue
        for id in ids_data:
            if hasattr(id, "asset_data") and id.asset_data and id.name not in IDS_TO_KEEP:
                id.asset_clear()


if __name__ == "__main__":
    if IDS_TO_KEEP:
        remove_other_assets()
        for id_type in set(TYPES):
            if id_type == "NODETREE":
                data_type = bpy.data.node_groups
            else:
                data_type = getattr(bpy.data, id_type.lower() + "s")
            for id in data_type:
                if id.name not in IDS_TO_KEEP:
                    data_type.remove(id)
    elif IDS_TO_REMOVE:
        for id,id_type in zip(IDS_TO_REMOVE, TYPES):
            if id_type == "NODETREE":
                data_type = bpy.data.node_groups
            else:
                data_type = getattr(bpy.data, id_type.lower() + "s")
            data_type.remove(data_type[id])
    
    bpy.ops.wm.save_mainfile()
