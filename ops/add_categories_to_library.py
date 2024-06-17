from pathlib import Path

import bpy
from bpy.types import Operator, UserAssetLibrary
from bpy_extras import asset_utils

from .. import hive_mind, utils


class SH_OT_AddCategoriesToLibrary(Operator):
    bl_idname = "superhive.add_categories_to_library"
    bl_label = "Add Categories to Library"
    bl_description = "Add Superhive's categories to the asset library. Hold Alt to remove existing categories."
    bl_options = {"REGISTER", "UNDO"}

    load_from_superhive: bpy.props.BoolProperty(
        name="Load from Superhive",
        description="Load categories from Superhive API",
        default=False,
    )
    
    clear_existing: bpy.props.BoolProperty(
        name="Clear Existing",
        description="Clear existing categories",
        default=False,
    )

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        is_asset_browser = asset_utils.SpaceAssetInfo.is_asset_browser(context.space_data)
        if not is_asset_browser:
            cls.poll_message_set("`context.space_data` must be Asset Browser")

        return is_asset_browser

    def invoke(self, context, event):
        self.alt = event.alt
        return self.execute(context)

    def execute(self, context: bpy.types.Context) -> set[str]:
        lib_name: str = context.space_data.params.asset_library_reference
        lib: UserAssetLibrary = context.preferences.filepaths.asset_libraries.get(lib_name)

        if not lib:
            self.report({"ERROR"}, f"Asset library '{lib_name}' not found")
            return {"CANCELLED"}

        lib_path = Path(lib.path)
        if not lib_path.exists():
            lib_path.mkdir(parents=True)

        file_path = lib_path/"blender_assets.cats.txt"
        if self.clear_existing and file_path.exists():
            file_path.unlink()

        if self.load_from_superhive:
            hive_mind.load_categories()

        with utils.open_catalogs_file(lib.path, is_new=not file_path.exists()) as cat_file:
            cat_file: utils.CatalogsFile
            for category_uuid, sub_list in hive_mind.SUBCATEGORIES.items():
                cat_info = hive_mind.CATEGORIES.get(category_uuid)
                cat = cat_file.find_catalog(category_uuid)
                if not cat:
                    cat = cat_file.add_catalog(cat_info["name"], id=category_uuid)
                for sub_uuid, sub_info in sub_list.items():
                    sub = cat.find_catalog(sub_uuid)
                    if not sub:
                        sub = cat.add_child(sub_info["name"], id=sub_uuid)

        bpy.ops.asset.library_refresh()
        
        return {"FINISHED"}


classes = (
    SH_OT_AddCategoriesToLibrary,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
