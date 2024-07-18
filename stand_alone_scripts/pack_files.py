"""
CLI Script to update the asset data of the current blend file:

Argument Order:
     0. blender executable
     1. background arg
     2. run python script arg
     3. script to run
     4. blend file to open: str
"""

import bpy

if __name__ == "__main__":
    for object in bpy.data.objects:
        if not object.asset_data or object.name in bpy.context.view_layer.objects:
            continue
        bpy.context.scene.collection.objects.link(object)
    
    for collection in bpy.data.collections:
        if not collection.asset_data or collection.name in bpy.context.scene.collection.children_recursive:
            continue
        bpy.context.scene.collection.children.link(collection)
    
    bpy.context.view_layer.update()
    
    bpy.ops.file.pack_all()