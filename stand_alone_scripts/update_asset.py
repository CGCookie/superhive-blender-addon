"""
CLI Script to update the asset data of the current blend file:

Argument Order:
     0. blender executable
     1. factory startup arg
     2. blend file to run script on
     3. run python script arg
     4. script to run
     5. orig asset name: str
     5. new asset name: str
     6. bpy_data_type: str (id_type run through ASSET_TYPES_TO_ID_TYPES dict)
     7. author: str
     8. description: str
     9. license: str
    10. copyright: str
    11. catalog_id: str
    12. list of tags: str (list[str] , items separated by commas)
    13. icon path

"""

# import json
import sys
# from pathlib import Path

import bpy

# from settings import asset
# from bpy.types import Object

blend_file = bpy.data.filepath
orig_asset_name, new_asset_name, bpy_data_type, author, description, license, copyright, catalog_id, tags, icon_path = sys.argv[6:]

tags = tags.split(",") if tags else []

print(f"|     - asset_name: {orig_asset_name}, type: {type(orig_asset_name)}")
print(f"|     - asset_name: {new_asset_name}, type: {type(new_asset_name)}")
print(f"|     - bpy_data_type: {bpy_data_type}, type: {type(bpy_data_type)}")
print(f"|     - author: {author}, type: {type(author)}")
print(f"|     - description: {description}, type: {type(description)}")
print(f"|     - license: {license}, type: {type(license)}")
print(f"|     - copyright: {copyright}, type: {type(copyright)}")
print(f"|     - catalog_id: {catalog_id}, type: {type(catalog_id)}")
print(f"|     - tags: {tags}, type: {type(tags)}")
print(f"|     - icon_path: {icon_path}, type: {type(icon_path)}")
# print(f"|     - other: {_}, type: {type(_)}")


def update_asset():
    # Get id data
    id_data = getattr(bpy.data, bpy_data_type)

    # Check if there are any of data type
    if not id_data:
        print(f"|     - No '{bpy_data_type}' items in '{blend_file}'")
        return

    # Get asset item
    asset_item: bpy.types.ID = id_data.get(orig_asset_name)

    # Check if asset item exists
    if not asset_item:
        print(f"|     - Asset '{orig_asset_name}' not found as type '{bpy_data_type}' in file '{blend_file}'")
        return

    asset_item.asset_clear()

    if new_asset_name and new_asset_name != orig_asset_name:
        asset_item.name = new_asset_name

    asset_item.asset_mark()

    asset_item.asset_data.author = author
    asset_item.asset_data.description = description
    asset_item.asset_data.license = license
    asset_item.asset_data.copyright = copyright
    asset_item.asset_data.catalog_id = catalog_id

    for tag in tags:
        asset_item.asset_data.tags.new(tag, skip_if_exists=True)

    # TODO: Handle Icon

    bpy.ops.wm.save_mainfile(compress=True)


if __name__ == "__main__":
    print("| Starting")
    update_asset()
    print("| Complete")
    bpy.ops.wm.quit_blender()
