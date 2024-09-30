import bpy
from bpy.types import UILayout


def object_context_menu(self, context):
    layout: UILayout = self.layout
    layout.separator()
    layout.label(text="Bkeeper")
    layout.operator_context = "INVOKE_DEFAULT"
    layout.operator_menu_enum(
        "bkeeper.add_as_asset_to_library", "library", text="Add to Library"
    )


def register():
    bpy.types.VIEW3D_MT_object_context_menu.append(object_context_menu)


def unregister():
    bpy.types.VIEW3D_MT_object_context_menu.remove(object_context_menu)
