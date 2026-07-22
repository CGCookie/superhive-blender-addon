import bpy
from bpy.types import Operator

from .. import hive_mind, utils
from . import polls


class SH_OT_AddCategoriesToLibrary(Operator):
    bl_idname = "bkeeper.add_categories_to_library"
    bl_label = "Add Categories to Library"
    bl_description = "Add Superhive's (formerly Blender Market) categories to the asset library. Hold Alt to remove existing categories."
    bl_options = {"REGISTER", "UNDO"}

    seed_from_server: bpy.props.BoolProperty(
        name="Superhive Catalog Roots",
        description=(
            "Create one top-level catalog per curated Superhive root (fetched"
            " from the server when possible). Published catalog paths must"
            " start with one of these roots. Disable to add the legacy"
            " category tree instead"
        ),
        default=True,
    )

    load_from_superhive: bpy.props.BoolProperty(
        name="Load from Superhive",
        description="Load categories from Superhive (formerly Blender Market)",
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

        if self.seed_from_server:
            self.seed_curated_roots(lib)
        else:
            self.add_legacy_categories(lib)

        bpy.ops.asset.library_refresh()

        return {"FINISHED"}

    def seed_curated_roots(self, lib: "utils.AssetLibrary"):
        """One top-level catalog per curated root, fresh uuids — the server's
        declarative catalog sync adopts client uuids, so no fixed ids needed."""
        client = None
        if bpy.app.online_access:
            try:
                client = utils.get_prefs().get_api_client()
            except RuntimeError:
                client = None  # no token/wheel yet — cached or static roots
        roots = hive_mind.load_roots(client)

        with lib.open_catalogs_file() as cat_file:
            cat_file: utils.CatalogsFile
            existing_root_names = {
                catalog.name for catalog in cat_file.catalogs.values()
            }
            for root_name in roots:
                if root_name not in existing_root_names:
                    cat_file.add_catalog(root_name)

    def add_legacy_categories(self, lib: "utils.AssetLibrary"):
        if self.load_from_superhive:
            hive_mind.load_categories()

        with lib.open_catalogs_file() as cat_file:
            cat_file: utils.CatalogsFile
            for category_uuid, sub_list in hive_mind.SUBCATEGORIES_DICT.items():
                cat_info = hive_mind.CATEGORIES_DICT.get(category_uuid)
                cat = cat_file.find_catalog(category_uuid)
                if not cat:
                    cat = cat_file.add_catalog(cat_info["name"], id=category_uuid)
                for sub_uuid, sub_info in sub_list.items():
                    sub = cat.find_catalog(sub_uuid)
                    if not sub:
                        sub = cat.add_child(sub_info["name"], id=sub_uuid)


classes = (SH_OT_AddCategoriesToLibrary,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
