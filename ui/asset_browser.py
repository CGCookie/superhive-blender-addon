from typing import TYPE_CHECKING
import bpy
from bpy.types import Context, Panel, UILayout, AssetRepresentation
from bpy_extras import asset_utils

# from ..helpers import asset_helper
from ..ops import polls

from .. import __package__ as base_package

if TYPE_CHECKING:
    from ..settings import scene
    from . import prefs as sh_prefs


def draw_assetbrowser_header(self, context: Context):
    layout: UILayout = self.layout

    scene_sets: 'scene.SH_Scene' = context.scene.superhive
    if scene_sets.header_progress_bar.show:
        scene_sets.header_progress_bar.draw(layout)

    if polls.is_asset_browser(context):
        layout.prop(context.scene.superhive, "library_mode", text="")
        layout.operator(
            "superhive.create_hive_asset_library",
            text="", icon="ADD"
        )


class SH_PT_AssetSettings(asset_utils.AssetMetaDataPanel, Panel):
    bl_label = ""
    bl_order = 1000
    bl_options = {"HEADER_LAYOUT_EXPAND"}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return context.scene.superhive.library_mode == "SUPERHIVE"

    def draw_header(self, context: Context) -> None:
        layout = self.layout
        layout.alignment = "LEFT"
        layout.label(text="Superhive")

        asset = context.asset
        if asset and asset.metadata.sh_is_dirty():
            row = layout.row()
            row.active = False
            row.label(text="*Unsaved Changes")

    def draw(self, context):
        layout: UILayout = self.layout
        layout.use_property_split = True

        prefs: 'sh_prefs.SH_AddonPreferences' = context.preferences.addons[base_package].preferences

        if not context.asset:
            row = layout.row()
            row.alignment = "CENTER"
            row.label(text="Please select an asset")
            return

        asset: AssetRepresentation = context.asset

        # if asset.metadata.sh_uuid == "":
        #     layout.operator("superhive.convert_assets_to_hive")
        #     return

        def set_is_dirty_text(prop: str, text: str = None):
            if getattr(asset.metadata, f"sh_is_dirty_{prop}"):
                return f"{text or prop.title()}*"
            return None

        layout.prop(asset.metadata, "sh_name", text=set_is_dirty_text("name"))
        layout.prop(asset.metadata, "sh_description", text=set_is_dirty_text("description"))
        layout.prop(asset.metadata, "sh_author", text=set_is_dirty_text("author"))
        layout.prop(asset.metadata, "sh_license", text=set_is_dirty_text("license"))
        layout.prop(asset.metadata, "sh_catalog", text=set_is_dirty_text("catalog"))
        layout.prop(asset.metadata, "sh_copyright", text=set_is_dirty_text("copyright"))
        # layout.prop(asset.metadata, "sh_created_blender_version")

        layout.label(text="Tags*:" if asset.metadata.sh_is_dirty_tags else "Tags:")
        row = layout.row()
        row.template_list(
            "SH_UL_TagList",
            "",
            asset.metadata.sh_tags,
            "tags",
            asset.metadata.sh_tags,
            "active_index",
            item_dyntip_propname="desc",
        )
        col = row.column(align=True)
        col.operator("superhive.add_tags", icon="ADD", text="")
        col.operator("superhive.remove_tag", icon="REMOVE", text="")
        col.operator("superhive.reset_tag", icon="FILE_REFRESH", text="")

        if prefs.display_extras:
            layout.label(text="Extra information is displayed")
            layout.label(text=f"UUID: {asset.metadata.sh_uuid}")

        row = layout.row()
        row.active = asset.metadata.sh_is_dirty()
        row.operator("superhive.update_asset", icon="FILE_REFRESH")


class SH_PT_LibrarySettings(Panel):
    bl_idname = "SH_PT_LibrarySettings"
    bl_label = "Superhive"
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOLS"
    # bl_category = "Superhive"
    bl_order = 1000
    bl_options = {'HIDE_HEADER'}

    @classmethod
    def poll(cls, context):
        return polls.is_asset_browser(context) and context.scene.superhive.library_mode == "SUPERHIVE"

    def draw(self, context):
        layout: UILayout = self.layout

        layout.operator("superhive.add_categories_to_library")
        layout.operator("superhive.remove_empty_catalogs")
        layout.operator("superhive.export_library", text="Export to Superhive")


classes = (
    SH_PT_AssetSettings,
    SH_PT_LibrarySettings,
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