from typing import TYPE_CHECKING

import bpy
from bpy.types import AssetRepresentation, Context, Panel, UILayout
from bpy_extras import asset_utils

from .. import utils
from ..ops import polls

if TYPE_CHECKING:
    from ..settings import scene


def draw_assetbrowser_header(self, context: Context):
    layout: UILayout = self.layout

    scene_sets: "scene.SH_Scene" = context.scene.superhive
    if scene_sets.header_progress_bar.show:
        scene_sets.header_progress_bar.draw(layout)

    if polls.is_asset_browser(context):
        layout.prop(context.scene.superhive, "library_mode", text="")
        layout.operator("bkeeper.create_new_library", text="", icon="ADD")

    layout.label(text=context.scene.sh_progress_t)


class SH_PT_AssetSettings(asset_utils.AssetMetaDataPanel, Panel):
    bl_label = ""
    bl_order = 1000
    bl_options = {"HEADER_LAYOUT_EXPAND"}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return polls.is_asset_browser(context) and context.scene.superhive.library_mode == "SUPERHIVE"

    def draw_header(self, context: Context) -> None:
        layout = self.layout
        layout.alignment = "LEFT"
        layout.label(text="Superhive")

        if not context.selected_assets:
            return

        asset = context.selected_assets[0]
        if asset and asset.metadata.sh_is_dirty():
            row = layout.split(factor=0.8)

            row.operator("bkeeper.update_asset", text="*Unsaved Changes", icon="FILE_TICK")

            r = row.row()
            r.alignment = "RIGHT"
            r.operator("bkeeper.reset_asset_metadata", icon="FILE_REFRESH", text="")

    def draw(self, context):
        layout: UILayout = self.layout
        layout.use_property_split = True

        scene_sets: "scene.SH_Scene" = context.scene.superhive

        if scene_sets.side_panel_batch_asset_update_progress_bar.show:
            scene_sets.side_panel_batch_asset_update_progress_bar.draw(layout)
        elif not context.selected_assets:
            row = layout.row()
            row.alignment = "CENTER"
            row.label(text="Please select asset(s)")
            return
        elif len(context.selected_assets) > 1:
            self.draw_multiple_assets(context, layout)
        else:
            self.draw_single_asset(context, layout)

    def draw_single_asset(self, context: Context, layout: UILayout):
        asset: AssetRepresentation = context.asset
        if asset.local_id:
            self.draw_single_local_id(context, layout)
            return

        prefs = utils.get_prefs()
        active_file = context.active_file

        row = layout.row()
        # row.alignment = "CENTER"
        row.label(text="Icon:", icon="IMAGE_DATA")
        row = layout.row(align=True)
        box = row.box()
        box.template_icon(icon_value=active_file.preview_icon_id, scale=5.0)
        row.separator()
        col = row.column(align=True)
        col.operator("bkeeper.change_asset_icon", icon="FILE_FOLDER", text="")
        col.operator("bkeeper.rerender_thumbnail", icon="RESTRICT_RENDER_OFF", text="")
        if prefs.display_extras:
            col.operator("bkeeper.save_out_preview", icon="FILE_TICK", text="")

        layout.separator()

        row = layout.row()
        # row.alignment = "CENTER"
        row.label(text="Metadata:", icon="TEXT")

        def set_is_dirty_text(prop: str, text: str = None):
            if getattr(asset.metadata, f"sh_is_dirty_{prop}"):
                return f"{text or prop.title()}*"
            return None

        def display_metadata(
            layout: UILayout,
            prop: str,
            orig_prop: str,
            orig_value: str,
            text=None,
        ):
            row = layout.row(align=True)
            row.prop(asset.metadata, prop, text=text or set_is_dirty_text(orig_prop))
            if getattr(asset.metadata, f"sh_is_dirty_{orig_prop}"):
                op = row.operator("bkeeper.reset_asset_metadata_property", icon="X", text="")
                op.property = prop
                op.original_value = orig_value

        display_metadata(layout, "sh_name", "name", asset.name)
        display_metadata(layout, "sh_description", "description", asset.metadata.description)
        display_metadata(layout, "sh_author", "author", asset.metadata.author)
        col = layout.column(align=True)
        display_metadata(col, "sh_license", "license", asset.metadata.license)
        if asset.metadata.sh_license == "CUSTOM":
            display_metadata(
                col,
                asset,
                "sh_license_custom",
                "license",
                asset.metadata.license,
                text="Custom License",
            )
        col = layout.column(align=True)
        display_metadata(col, "sh_catalog", "catalog", asset.metadata.catalog_id)
        if asset.metadata.sh_catalog == "CUSTOM":
            row = col.row(align=True)
            row.prop(
                asset.metadata,
                "sh_catalog_custom",
                text=f"Custom Catalog{'*' if asset.metadata.sh_is_dirty_catalog_custom else ''}",
            )
            if asset.metadata.sh_is_dirty_catalog_custom:
                op = row.operator("bkeeper.reset_asset_metadata_property", icon="X", text="")
                op.property = "sh_catalog_custom"
                op.original_value = ""
        display_metadata(layout, "sh_copyright", "copyright", asset.metadata.copyright)
        display_metadata(layout, "sh_blend_version_enum", "blend_version", asset.metadata.sh_blend_version_str)

        layout.label(text="Tags*:" if asset.metadata.sh_is_dirty_tags else "Tags:", icon="TAG")
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
        col.operator("bkeeper.add_tags", icon="ADD", text="")
        col.operator("bkeeper.remove_tag", icon="REMOVE", text="")
        col.operator("bkeeper.reset_tag", icon="FILE_REFRESH", text="")

        if prefs.display_extras:
            layout.label(text="Extra information is displayed")
            layout.label(text=f"UUID: {asset.metadata.sh_uuid}")
            layout.label(text=f"Type (id_type): {asset.id_type}")

        row = layout.row()
        row.active = asset.metadata.sh_is_dirty()
        row.operator("bkeeper.update_asset", text="Save Changes", icon="FILE_TICK")

    def draw_single_local_id(self, context: Context, layout: UILayout):
        col = layout.column(align=True)
        col.scale_y = 0.75
        row = col.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Please use the settings above to set the asset metadata")
        row = col.row(align=True)
        row.alignment = "CENTER"
        row.label(text="as this is the active asset's file.")

    def draw_multiple_assets(self, context: Context, layout: UILayout):
        # layout.operator("bkeeper.rerender_thumbnail", icon="RESTRICT_RENDER_OFF")
        scene_sets: "scene.SH_Scene" = context.scene.superhive

        col = layout.column()
        col.use_property_decorate = False
        col.use_property_split = False
        scene_sets.metadata_update.draw(context, col, use_ops=True)

        col.separator()

        row = col.row(align=True)
        row.operator("bkeeper.batch_update_assets_from_scene")
        row.prop(scene_sets.metadata_update, "reset_settings", text="", icon="FILE_REFRESH")


class SH_PT_LibrarySettings(Panel):
    bl_idname = "SH_PT_LibrarySettings"
    bl_label = "Superhive"
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOLS"
    # bl_category = "Superhive"
    bl_order = 1000
    bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(cls, context):
        return polls.is_asset_browser(context) and context.scene.superhive.library_mode == "SUPERHIVE"

    def draw(self, context):
        layout: UILayout = self.layout

        scene_sets: "scene.SH_Scene" = context.scene.superhive
        if scene_sets.export_library.show:
            scene_sets.export_library.draw(layout)
            return

        layout.operator("bkeeper.add_categories_to_library")
        layout.operator("bkeeper.remove_empty_catalogs")
        layout.operator("bkeeper.export_library", text="Export to Superhive")
        layout.operator("bkeeper.import_from_directory")


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
