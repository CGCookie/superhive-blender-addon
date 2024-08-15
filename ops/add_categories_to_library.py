import bpy
from bpy.types import Operator

from .. import hive_mind, utils
from . import polls


class SH_OT_AddCategoriesToLibrary(Operator):
    bl_idname = "bkeeper.add_categories_to_library"
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
        return polls.is_asset_browser(context, cls=cls)

    def invoke(self, context, event):
        self.alt = event.alt
        return self.execute(context)

    def execute(self, context: bpy.types.Context) -> set[str]:
        lib = utils.from_active(context, load_catalogs=True)

        lib_path_exists: bool = lib.path.exists()
        if not lib_path_exists:
            lib.path.mkdir(parents=True)

        if self.clear_existing and lib.catalogs.exists():
            lib.catalogs.delete_file()
            lib.catalogs.write_empty_file()
            lib.catalogs.load_catalogs()

        if self.load_from_superhive:
            hive_mind.load_categories()

        with lib.open_catalogs_file() as cat_file:
            for category_uuid, sub_list in hive_mind.SUBCATEGORIES_DICT.items():
                cat_info = hive_mind.CATEGORIES_DICT.get(category_uuid)
                cat = cat_file.find_catalog(category_uuid)
                if not cat:
                    cat = cat_file.add_catalog(cat_info["name"], id=category_uuid)
                for sub_uuid, sub_info in sub_list.items():
                    sub = cat.find_catalog(sub_uuid)
                    if not sub:
                        sub = cat.add_child(sub_info["name"], id=sub_uuid)

        bpy.ops.asset.library_refresh()

        return {"FINISHED"}


classes = (SH_OT_AddCategoriesToLibrary,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
