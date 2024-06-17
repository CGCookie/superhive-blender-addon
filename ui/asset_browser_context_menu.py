import bpy
from bpy.types import UILayout


def asset_browser_context_menu(self, context):
    layout: UILayout = self.layout
    layout.separator()
    layout.label(text="Superhive")
    layout.operator_context = 'INVOKE_DEFAULT'
    layout.operator("superhive.add_to_library", text="Add to Library")


def register():
    bpy.types.ASSETBROWSER_MT_context_menu.append(asset_browser_context_menu)


def unregister():
    bpy.types.ASSETBROWSER_MT_context_menu.remove(asset_browser_context_menu)