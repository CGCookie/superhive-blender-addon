from typing import TYPE_CHECKING
import bpy
from bpy.types import Context, Panel, UILayout, AssetRepresentation
from bpy_extras import asset_utils

# from ..helpers import asset_helper

from .. import __package__ as base_package

if TYPE_CHECKING:
    from . import prefs as sh_prefs


def draw_assetbrowser_header(self, context: Context):
    space_data = context.space_data

    if asset_utils.SpaceAssetInfo.is_asset_browser(space_data):
        layout: UILayout = self.layout
        layout.prop(context.scene.superhive, "library_mode", text="")
        layout.operator(
            "superhive.create_hive_asset_library",
            text="", icon="ADD"
        )


class SH_PT_AssetSettings(asset_utils.AssetMetaDataPanel, Panel):
    bl_label = "Superhive"
    bl_order = 1000

    @classmethod
    def poll(cls, context: Context) -> bool:
        return context.scene.superhive.library_mode == "SUPERHIVE"

    def draw(self, context):
        layout: UILayout = self.layout

        prefs: 'sh_prefs.SH_AddonPreferences' = context.preferences.addons[base_package].preferences

        if not context.selected_assets:
            row = layout.row()
            row.alignment = "CENTER"
            row.label(text="Please select an asset")
            return

        asset: AssetRepresentation = context.asset

        if asset.metadata.sh_uuid == "":
            layout.operator("superhive.convert_assets_to_hive")
            return
        
        layout.prop(asset, "name")
        layout.prop(asset.metadata, "sh_description")
        layout.prop(asset.metadata, "author")
        layout.prop(asset.metadata, "sh_license")
        layout.prop(asset.metadata, "sh_created_blender_version")
        

        if prefs.display_extras:
            layout.label(text="Extra information is displayed")
            layout.label(text=f"UUID: {asset.metadata.sh_uuid}")


classes = (
    SH_PT_AssetSettings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.FILEBROWSER_HT_header.append(draw_assetbrowser_header)
    # bpy.types.ASSETBROWSER_PT_metadata.append(draw_assetbrowser_metadata)


def unregister():
    bpy.types.FILEBROWSER_HT_header.remove(draw_assetbrowser_header)
    # bpy.types.ASSETBROWSER_PT_metadata.remove(draw_assetbrowser_metadata)
    for cls in classes:
        bpy.utils.unregister_class(cls)