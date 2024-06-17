import bpy
from bpy.types import Operator
from bpy_extras import asset_utils

from ..helpers import asset_helper


class SH_OT_ConvertAssetsToHive(Operator):
    bl_idname = "superhive.convert_assets_to_hive"
    bl_label = "Convert To Hive"
    bl_description = "Convert the selected assets to hive assets"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        is_asset_browser = asset_utils.SpaceAssetInfo.is_asset_browser(context.space_data)
        if is_asset_browser and context.selected_assets:
            return True
        
        if not is_asset_browser:
            cls.poll_message_set("Context must be in the asset browser")
        elif not context.selected_assets:
            cls.poll_message_set(
                "Please select an asset to convert to a hive asset")

        return False

    def execute(self, context):
        assets = context.selected_assets

        for asset in assets:
            if asset_helper.is_superhive_asset(asset):
                continue
            asset_helper.convert_to_superhive_asset(
                context, asset
            )

        return {'FINISHED'}


classes = (
    SH_OT_ConvertAssetsToHive,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
