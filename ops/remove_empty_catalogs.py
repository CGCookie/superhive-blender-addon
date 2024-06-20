from pathlib import Path
import bpy
from bpy.types import Operator, UserAssetLibrary
from bpy_extras import asset_utils
from .. import utils


class SH_OT_RemoveEmptyCatalogs(Operator):
    bl_idname = "superhive.remove_empty_catalogs"
    bl_label = "Remove Empty Catalogs"
    bl_description = "Remove all empty catalogs from the active library"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        is_asset_browser = asset_utils.SpaceAssetInfo.is_asset_browser(context.space_data)
        if not is_asset_browser:
            cls.poll_message_set("`context.space_data` must be Asset Browser")

        lib_not_all = context.space_data.params.asset_library_reference != "ALL"
        if not lib_not_all:
            cls.poll_message_set("Active library must not be 'ALL'")

        return is_asset_browser and lib_not_all

    def execute(self, context):
        lib = utils.from_active(context, load_assets=True, load_catalogs=True)

        # Gather catalogs used by assets
        catalog_ids = {
            asset.metadata.catalog_id
            for asset in lib.get_possible_assets()
        }

        with lib.open_catalogs_file() as cat_file:
            cat_file: utils.CatalogsFile

            for cat in cat_file.get_catalogs():
                if cat.id not in catalog_ids:
                    cat.remove_self()

        bpy.ops.asset.library_refresh()

        return {'FINISHED'}
    
    def _execute(self, context):
        lib_name: str = context.space_data.params.asset_library_reference
        lib: UserAssetLibrary = context.preferences.filepaths.asset_libraries.get(lib_name)

        file = Path(lib.path)/"blender_assets.cats.txt"
        if not file.exists():
            self.report({'ERROR'}, f"No catalogs exist in library '{lib_name}'")
            return {'CANCELLED'}

        selected_assets_orig = context.selected_assets

        context.space_data.deselect_all()
        bpy.ops.file.select_all(action='SELECT')

        # Gather catalogs used by assets
        catalog_ids = {
            asset.metadata.catalog_id
            for asset in context.selected_assets
        }

        with utils.open_catalogs_file(lib.path) as cat_file:
            cat_file: utils.CatalogsFile

            for cat in cat_file.get_catalogs():
                if cat.id not in catalog_ids:
                    cat.remove_self()

        bpy.ops.asset.library_refresh()

        context.space_data.deselect_all()
        for asset in selected_assets_orig:
            context.space_data.activate_asset_by_id(asset)

        return {'FINISHED'}


classes = (
    SH_OT_RemoveEmptyCatalogs,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
