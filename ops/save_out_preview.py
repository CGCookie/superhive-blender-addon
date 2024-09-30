import bpy
from bpy.types import Operator

from . import polls
from .. import utils


class SH_OT_SaveOutPreview(Operator):
    bl_idname = "bkeeper.save_out_preview"
    bl_label = "Save Preview"
    bl_description = "Save the preview of the active asset"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return polls.is_asset_browser(context, cls=cls) and context.selected_assets

    def execute(self, context):
        bpy_lib = utils.get_active_bpy_library_from_context(context, area=context.area)
        asset = utils.Asset(context.asset)

        print("STARTING SAVE OUT PREVIEW")
        asset.save_out_preview(bpy_lib.path)
        print("FINISHED SAVE OUT PREVIEW")

        return {"FINISHED"}


classes = (SH_OT_SaveOutPreview,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
