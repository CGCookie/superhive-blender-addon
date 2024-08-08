import bpy
from bpy.types import UILayout


def asset_browser_context_menu(self, context):
    layout: UILayout = self.layout
    layout.separator()
    layout.label(text="Superhive")
    layout.operator_context = "INVOKE_DEFAULT"
    layout.operator_menu_enum(
        "bkeeper.add_to_library", "library", text="Add to Library"
    )
    layout.operator("bkeeper.remove_from_library", icon="X")
    layout.operator("bkeeper.batch_update_assets", text="Change Metadata")


def register():
    bpy.types.ASSETBROWSER_MT_context_menu.append(asset_browser_context_menu)


def unregister():
    bpy.types.ASSETBROWSER_MT_context_menu.remove(asset_browser_context_menu)
