# import bpy
from bpy.types import Context, Operator
from bpy_extras import asset_utils


def is_asset_browser(context: Context, cls: Operator = None):
    is_asset_browser = asset_utils.SpaceAssetInfo.is_asset_browser(context.space_data)
    if cls and not is_asset_browser:
        cls.poll_message_set("`context.space_data` must be Asset Browser")
    return is_asset_browser


def is_not_all_library(context: Context, cls: Operator = None):
    if not is_asset_browser(context, cls=cls):
        return False

    lib_name: str = context.space_data.params.asset_library_reference
    if lib_name == "ALL":
        if cls:
            cls.poll_message_set("Active library must not be 'All'")
        return False
    return True
