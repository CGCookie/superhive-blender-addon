# import bpy
from bpy.types import Context, Operator
from bpy_extras import asset_utils


def is_asset_browser(context: Context, cls: Operator = None):
    is_asset_browser = asset_utils.SpaceAssetInfo.is_asset_browser(context.space_data)
    if cls and not is_asset_browser:
        cls.poll_message_set("`context.space_data` must be Asset Browser")
    return is_asset_browser