import bpy
import bpy.utils
from bpy.types import PropertyGroup
from bpy.props import EnumProperty, PointerProperty


class SH_Scene(PropertyGroup):
    library_mode: EnumProperty(
        items=(
            ("BLENDER", "Blender",
             "Blender's default asset library settings and options"),
            ("SUPERHIVE", "SuperHive",
             "Settings and options for uploading to Superhive's asset system"),
        ),
        name="Library Mode",
        description="Choose which asset library settings to use",
    )


classes = (
    SH_Scene,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.superhive = PointerProperty(type=SH_Scene)


def unregister():
    del bpy.types.Scene.superhive
    for cls in classes:
        bpy.utils.unregister_class(cls)
