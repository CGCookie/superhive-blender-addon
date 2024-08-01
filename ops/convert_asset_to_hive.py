import bpy
from bpy.types import Operator

from ..helpers import asset_helper
from . import polls


class SH_OT_ConvertAssetsToHive(Operator):
    bl_idname = "bkeeper.convert_assets_to_hive"
    bl_label = "Convert To Hive"
    bl_description = "Convert the selected assets to hive assets"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        is_asset_browser = polls.is_asset_browser(context, cls=cls)
        if is_asset_browser and context.selected_assets:
            return True

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
