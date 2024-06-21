from ctypes import util
from typing import TYPE_CHECKING

import bpy
from bpy.props import BoolVectorProperty, EnumProperty, StringProperty
from bpy.types import Operator

from .. import hive_mind, utils
from . import polls

if TYPE_CHECKING:
    from ..settings import asset as asset_settings


class SH_OT_UpdateAsset(Operator):
    bl_idname = "superhive.update_asset"
    bl_label = "Update Asset"
    bl_description = "Update the asset data of selected assets. Updates all assets if none are selected."
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return polls.is_asset_browser(context, cls=cls) and context.asset

    def execute(self, context):
        # lib = utils.from_active(context, load_assets=True)
        # if not lib.assets:
        if not context.asset:
            self.report({"ERROR"}, "No active asset found")
            return {"CANCELLED"}

        prefs = utils.get_prefs()

        asset = utils.Asset(context.asset)
        asset.update_asset(prefs.ensure_default_blender_version().path)

        bpy.ops.asset.library_refresh()

        # Waiting on: https://projects.blender.org/blender/blender/issues/123572

        # context.scene.update_tag()

        # lib = utils.from_active(bpy.context, load_assets=True)

        # new_asset = lib.assets[asset.new_name]

        # # if asset.name == asset.new_name:
        # bpy.context.space_data.activate_asset_by_id(new_asset.orig_asset.local_id)

        # sh_tags: 'asset_settings.SH_AssetTags' = new_asset.orig_asset.metadata.sh_tags
        # sh_tags.load_from_asset(new_asset.orig_asset)

        return {"FINISHED"}


class SH_OT_ResetAssetMetadataProperty(Operator):
    bl_idname = "superhive.reset_asset_metadata_property"
    bl_label = "Reset"
    bl_description = "Reset the metadata property of the active asset."
    bl_options = {"REGISTER", "UNDO"}

    property: StringProperty()
    original_value: StringProperty()

    @classmethod
    def poll(cls, context):
        return polls.is_asset_browser(context, cls=cls) and context.asset

    def execute(self, context):
        if self.property == "tags":
            # self.original_value should be a list of tags separated by commas
            tags = self.original_value.split(",")
            sh_tags: 'asset_settings.SH_AssetTags' = context.asset.metadata.sh_tags
            for tag in tags:
                sh_tags.new_tag(tag, context=context)
        else:
            setattr(context.asset.metadata, self.property, self.original_value)
        return {"FINISHED"}


class SH_OT_ResetAssetMetadata(Operator):
    bl_idname = "superhive.reset_asset_metadata"
    bl_label = "Reset Asset Metadata"
    bl_description = "Reset the asset metadata of selected assets. Resets all assets if none are selected."
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        asset = utils.Asset(context.asset)

        asset.reset_metadata(context)

        return {"FINISHED"}


class SH_OT_AddTags(Operator):
    bl_idname = "superhive.add_tags"
    bl_label = "Add"
    bl_description = "Add new tags to the active asset."
    bl_options = {"REGISTER", "UNDO"}

    # name: StringProperty(
    #     name="Tag Name",
    #     description="The name of the tag to add",
    # )
    # name: EnumProperty(
    #     name="Tag Name",
    #     description="The name of the tag to add as allowed by Superhive",
    #     items=hive_mind.get_tags,
    # )
    tags: BoolVectorProperty(
        name="Tags",
        description="The tags to add to the asset",
        size=len(hive_mind.get_tags()),
    )

    @classmethod
    def poll(cls, context):
        return polls.is_asset_browser(context, cls=cls) and context.asset

    def draw(self, context):
        layout = self.layout
        grid = layout.grid_flow(columns=3, even_columns=True)
        for i, tag in enumerate(hive_mind.get_tags()):
            grid.prop(self, "tags", index=i, text=tag[1], expand=True)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)

    def execute(self, context):
        for i, (tag_id, tag_name, tag_desc) in enumerate(hive_mind.get_tags()):
            if self.tags[i]:
                tags: 'asset_settings.SH_AssetTags' = context.asset.metadata.sh_tags
                tags.new_tag(tag_name, context, id=tag_id, desc=tag_desc)
        return {"FINISHED"}


class SH_OT_RemoveTag(Operator):
    bl_idname = "superhive.remove_tag"
    bl_label = "Remove"
    bl_description = "Remove the active tag from the active asset."
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return polls.is_asset_browser(context, cls=cls) and context.asset

    def execute(self, context):
        tags: 'asset_settings.SH_AssetTags' = context.asset.metadata.sh_tags
        tags.remove_tag(tags.active_index, context)
        return {"FINISHED"}


class SH_OT_ResetTags(Operator):
    bl_idname = "superhive.reset_tag"
    bl_label = "Reset"
    bl_description = "Reset the tags to the original tags."
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return polls.is_asset_browser(context, cls=cls) and context.asset

    def execute(self, context):
        sh_tags: 'asset_settings.SH_AssetTags' = context.asset.metadata.sh_tags

        sh_tags.clear(context)

        for tag in context.asset.metadata.tags:
            sh_tags.new_tag(tag.name, context)

        return {"FINISHED"}


classes = (
    SH_OT_AddTags,
    SH_OT_RemoveTag,
    SH_OT_ResetTags,
    SH_OT_UpdateAsset,
    SH_OT_ResetAssetMetadataProperty,
    SH_OT_ResetAssetMetadata,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
