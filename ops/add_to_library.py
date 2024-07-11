from pathlib import Path
from typing import Any, Literal

import bpy
from bpy.props import (BoolProperty, BoolVectorProperty, EnumProperty,
                       StringProperty)
from bpy.types import AssetRepresentation, Operator

from .. import hive_mind, utils

# from fuzzywuzzy import process, fuzz


class SH_OT_AddToLibrary(Operator):
    bl_idname = "superhive.add_to_library"
    bl_label = "Add to Library"
    bl_description = "Add the selected asset(s) to a library"
    bl_options = {"REGISTER", "UNDO"}

    # TODO: Remove fuzzywuzzy if not used in other places

    new_library_name: StringProperty(
        name="New Library Name",
        description="The name of the new library to create",
        default="",
    )

    def _get_library_items(self, context):
        asset_libs = context.preferences.filepaths.asset_libraries
        items = [(lib.name, lib.name, f"Add the asset(s) to the '{lib.name}' library") for lib in asset_libs]
        items.append(
            ("NEW", "New", "Create a new library and add the asset(s) to it", "ADD", 333)
        )
        return items
    library: EnumProperty(
        items=_get_library_items,
    )

    delete_after: BoolProperty(
        name="Delete After",
        description="Delete the source asset after adding it to the library",
        default=False,
    )

    keep_blend_files_as_is: BoolProperty(
        name="Keep Blend Files As Is",
        description="Normally we need to split up the assets into separate blend files to add them to the library. This option will keep the blend files as is.",
        default=False,
    )

    copy_catalogs: BoolProperty(
        name="Copy Catalogs",
        description="Copy the catalogs of the asset(s) from the source library to the destination library",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        if self.library == "NEW":
            row = layout.row()
            row.alert = not self.new_library_name
            row.activate_init = True
            row.prop(self, "new_library_name")

            if self.new_library_name in context.preferences.filepaths.asset_libraries:
                row = layout.row()
                row.alert = True
                row.alignment = "CENTER"
                row.label(text=f"Library `{self.new_library_name}` already exists")

        layout.prop(self, "keep_blend_files_as_is")
        layout.prop(self, "copy_catalogs")
        if self.keep_blend_files_as_is:
            col = layout.column(align=True)
            text = (
                "Warning: This will keep the blend files as is.",
                "This may cause issues with the library",
                "if the blend files contain objects you",
                "do not want in this library.",
            )
            for line in text:
                row = col.row(align=True)
                row.alert = True
                row.alignment = "CENTER"
                row.label(text=line)
        layout.prop(self, "delete_after")
        if self.delete_after:
            col = layout.column(align=True)
            text = (
                "Warning: This will delete the source asset",
                "after adding it to the library",
                "Please backup source files before proceeding",
                "in case of corruption.",
            )
            for line in text:
                row = col.row(align=True)
                row.alert = True
                row.alignment = "CENTER"
                row.label(text=line)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        if self.library == "NEW":
            if not self.new_library_name:
                self.report({"ERROR"}, "Name not entered for new library")
                return {"CANCELLED"}
            if self.new_library_name in context.preferences.filepaths.asset_libraries:
                self.report({"ERROR"}, f"Library `{self.new_library_name}` already exists")
                return {"CANCELLED"}

            dir: Path = Path(utils.get_prefs().library_directory) / self.new_library_name.replace(" ", "_").casefold()
            dir.mkdir(parents=True, exist_ok=True)
            lib = utils.AssetLibrary.create_new_library(
                self.new_library_name, str(dir),
                context=context, load_catalogs=True
            )
            self.is_new_library = True
        else:
            lib = utils.from_name(
                self.library, context=context,
                load_catalogs=True
            )
            self.is_new_library = False

        lib.path.mkdir(parents=True, exist_ok=True)

        assets = context.selected_assets

        if self.keep_blend_files_as_is:
            self.add_to_library_keep(assets, lib.path)
        else:
            self.add_to_library_split(assets, lib)

        try:
            bpy.ops.asset.library_refresh()
        except Exception as e:
            print(f"An error occurred while refreshing the asset library: {e}")

        return {"FINISHED"}

    def add_to_library_split(self, assets: list[AssetRepresentation], lib: utils.AssetLibrary):
        """Add the selected assets to the library by splitting them into separate blend files.

        Parameters
        ----------
        assets : list[AssetRepresentation]
            The assets to add to the library
        dir : Path
            The directory of the library to add the assets to
        """
        catalogs: list[utils.Catalog] = []
        with bpy.types.BlendData.temp_data() as bpy_data:
            bpy_data: bpy.types.BlendData
            for asset in assets:
                data_type = utils.ASSET_TYPES_TO_ID_TYPES[asset.id_type]
                with bpy_data.libraries.load(asset.full_library_path) as (
                    data_from,
                    data_to,
                ):
                    asset_item = next(
                        (
                            item
                            for item in getattr(data_from, data_type)
                            if item == asset.name
                        ),
                        None,
                    )

                    if asset_item:
                        getattr(data_to, data_type).append(asset_item)

                if data := getattr(data_to, data_type):
                    if self.copy_catalogs: # TODO: This doesn't work as expected
                        asset_catfile = utils.CatalogsFile(
                            Path(asset.full_library_path).parent
                        )
                        if not asset_catfile.catalogs:
                            asset_catfile = utils.CatalogsFile(
                                Path(asset.full_library_path).parent.parent
                            )
                        cat = asset_catfile.find_catalog(asset.metadata.catalog_id)
                        if cat:
                            catalogs.append(cat)
                        else:
                            asset_catfile = utils.CatalogsFile(
                                Path(asset.full_library_path).parent.parent,
                                is_new=self.is_new_library
                            )
                            cat = asset_catfile.find_catalog(asset.metadata.catalog_id)
                            if cat:
                                catalogs.append(cat)
                    bpy_data.libraries.write(
                        str(lib.path / f"{asset.name}.blend"), set(data), compress=True
                    )

        with lib.open_catalogs_file() as catfile:
            catfile: utils.CatalogsFile
            for catalog in catalogs:
                catfile.add_catalog_from_other(catalog)

    def add_to_library_keep(self, assets: list[AssetRepresentation], dir: Path):
        """Add the selected assets to the library without
        splitting them into separate blend files.

        Parameters
        ----------
        assets : list[AssetRepresentation]
            The assets to add to the library
        dir : Path
            The directory of the library to add the assets to
        """
        # Get unique blend files
        blend_files = {asset.full_library_path for asset in assets}

        for blend_file in blend_files:
            src = Path(blend_file)
            dst = dir / src.name
            # print(f"  - Copying blend file | {src} -> {dst}")
            dst.write_bytes(src.read_bytes())

# TODO: Remove from library (needs to not just delete the blend file,
# TODO: but check if other assets are in the blend and decide between
# TODO: deleting (no other assets) or removing the asset from the blend
# TODO: (other assets) and just removing the asset tag)


class SH_OT_AddAsAssetToLibrary(Operator):
    bl_idname: Any | Literal['superhive.add_to_library'] = "superhive.add_as_asset_to_library"
    bl_label = "Add to Library"
    bl_description = "Mark as asset, set default data, and add to a library"
    bl_options = {"REGISTER", "UNDO"}

    new_library_name: StringProperty(
        name="New Library Name",
        description="The name of the new library to create",
        default="",
    )

    def _get_library_items(self, context):
        asset_libs = context.preferences.filepaths.asset_libraries
        items = [(lib.name, lib.name, f"Add the asset(s) to the '{lib.name}' library") for lib in asset_libs]
        items.append(
            ("NEW", "New", "Create a new library and add the asset(s) to it", "ADD", 333)
        )
        return items
    library: EnumProperty(
        items=_get_library_items,
    )

    name: StringProperty(
        name="Name",
        description="The name of the asset",
    )

    description: StringProperty(
        name="Description",
        description="The description of the asset",
    )

    author: StringProperty(
        name="Author",
        description="The author of the asset",
    )

    license: EnumProperty(
        name="License",
        description="The license of the asset",
        items=hive_mind.LICENSES_ENUM,
    )

    catalog: EnumProperty(
        name="Catalog",
        description="The Superhive supported catalog of the asset",
        items=hive_mind.CATALOG_ENUM,
    )

    copyright: StringProperty(
        name="Copyright",
        description="The copyright of the asset",
    )

    tags: BoolVectorProperty(
        name="Tags",
        description="The Superhive supported tags of the asset",
        size=len(hive_mind.TAGS_ENUM),
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        if self.library == "NEW":
            row = layout.row()
            row.alert = not self.new_library_name
            row.activate_init = True
            row.prop(self, "new_library_name")

            if self.new_library_name in context.preferences.filepaths.asset_libraries:
                row = layout.row()
                row.alert = True
                row.alignment = "CENTER"
                row.label(text=f"Library `{self.new_library_name}` already exists")

        layout.prop(self, "description")
        layout.prop(self, "author")
        layout.prop(self, "license")
        layout.prop(self, "catalog")
        layout.prop(self, "copyright")

        layout.label(text="Tags:")
        grid = layout.grid_flow(columns=3, even_columns=True)
        for i, tag in enumerate(hive_mind.TAGS_ENUM):
            grid.prop(self, "tags", index=i, text=tag[1]) 

    def invoke(self, context, event):
        prefs = utils.get_prefs()
        self.name = context.object.name
        self.author = prefs.default_author_name
        self.license = prefs.default_license
        self.copyright = prefs.default_copyright

        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        if self.library == "NEW":
            if not self.new_library_name:
                self.report({"ERROR"}, "Name not entered for new library")
                return {"CANCELLED"}
            if self.new_library_name in context.preferences.filepaths.asset_libraries:
                self.report({"ERROR"}, f"Library `{self.new_library_name}` already exists")
                return {"CANCELLED"}

            dir: Path = Path(utils.get_prefs().library_directory) / self.new_library_name.replace(" ", "_").casefold()
            dir.mkdir(parents=True, exist_ok=True)
            lib = utils.AssetLibrary.create_new_library(
                self.new_library_name, str(dir),
                context=context, load_catalogs=True
            )
            self.is_new_library = True
        else:
            lib = utils.from_name(
                self.library, context=context,
                load_catalogs=True
            )
            self.is_new_library = False

        lib.path.mkdir(parents=True, exist_ok=True)

        obj = context.object
        obj.asset_mark()
        obj.asset_data.description = self.description
        obj.asset_data.author = self.author
        obj.asset_data.license = self.license
        obj.asset_data.catalog_id = self.catalog
        obj.asset_data.copyright = self.copyright

        prefs = utils.get_prefs()
        obj.asset_data.author = prefs.default_author_name
        obj.asset_data.license = prefs.default_license

        for tag, value in zip(hive_mind.TAGS_ENUM, self.tags):
            if value:
                obj.asset_data.tags.new(tag[1], skip_if_exists=True)

        # TODO: Handle Icons

        bpy.data.libraries.write(str(lib.path / f"{obj.name}.blend"), set([obj]), compress=True)

        try:
            bpy.ops.asset.library_refresh()
        except Exception as e:
            print(f"An error occurred while refreshing the asset library: {e}")

        # context.space_data.activate_asset_by_id(obj)

        return {"FINISHED"}


class SH_OT_AddToLibraryFromOutliner(Operator):
    bl_idname = "superhive.add_to_library_from_outliner"
    bl_label = "Add to Library"
    bl_description = "Mark as asset, set default data, and add to a library"
    bl_options = {"REGISTER", "UNDO"}

    new_library_name: StringProperty(
        name="New Library Name",
        description="The name of the new library to create",
        default="",
    )

    def _get_library_items(self, context):
        asset_libs = context.preferences.filepaths.asset_libraries
        items = [(lib.name, lib.name, f"Add the asset(s) to the '{lib.name}' library") for lib in asset_libs]
        items.append(
            ("NEW", "New", "Create a new library and add the asset(s) to it", "ADD", 333)
        )
        return items
    library: EnumProperty(
        items=_get_library_items,
    )

    name: StringProperty(
        name="Name",
        description="The name of the asset",
    )

    description: StringProperty(
        name="Description",
        description="The description of the asset",
    )

    author: StringProperty(
        name="Author",
        description="The author of the asset",
    )

    license: EnumProperty(
        name="License",
        description="The license of the asset",
        items=hive_mind.LICENSES_ENUM,
    )

    catalog: EnumProperty(
        name="Catalog",
        description="The Superhive supported catalog of the asset",
        items=hive_mind.CATALOG_ENUM,
    )

    copyright: StringProperty(
        name="Copyright",
        description="The copyright of the asset",
    )

    tags: BoolVectorProperty(
        name="Tags",
        description="The Superhive supported tags of the asset",
        size=len(hive_mind.TAGS_ENUM),
    )

    @classmethod
    def poll(cls, context):
        if not context.selected_ids:
            cls.poll_message_set("No items selected")
            return False
        return True

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        
        is_multi = len(context.selected_ids) > 1
        
        lib_name = self.library if self.library != "NEW" else self.new_library_name
        layout.label(text=f"Adding {len(context.selected_ids)} item{'s' if is_multi else ''} to library '{lib_name}'")

        if self.library == "NEW":
            row = layout.row()
            row.alert = not self.new_library_name
            row.activate_init = True
            row.prop(self, "new_library_name")

            if self.new_library_name in context.preferences.filepaths.asset_libraries:
                row = layout.row()
                row.alert = True
                row.alignment = "CENTER"
                row.label(text=f"Library `{self.new_library_name}` already exists")

        layout.prop(self, "description")
        layout.prop(self, "author")
        layout.prop(self, "license")
        layout.prop(self, "catalog")
        layout.prop(self, "copyright")

        layout.label(text="Tags:")
        grid = layout.grid_flow(columns=3)
        for i, tag in enumerate(hive_mind.TAGS_ENUM):
            grid.prop(self, "tags", index=i, text=tag[1]) 

    def invoke(self, context, event):
        prefs = utils.get_prefs()
        self.name = context.object.name
        self.author = prefs.default_author_name
        self.license = prefs.default_license
        self.copyright = prefs.default_copyright

        return context.window_manager.invoke_props_dialog(self, width=500)

    def execute(self, context):
        if self.library == "NEW":
            if not self.new_library_name:
                self.report({"ERROR"}, "Name not entered for new library")
                return {"CANCELLED"}
            if self.new_library_name in context.preferences.filepaths.asset_libraries:
                self.report({"ERROR"}, f"Library `{self.new_library_name}` already exists")
                return {"CANCELLED"}

            dir: Path = Path(utils.get_prefs().library_directory) / self.new_library_name.replace(" ", "_").casefold()
            dir.mkdir(parents=True, exist_ok=True)
            lib = utils.AssetLibrary.create_new_library(
                self.new_library_name, str(dir),
                context=context, load_catalogs=True
            )
            self.is_new_library = True
        else:
            lib = utils.from_name(
                self.library, context=context,
                load_catalogs=True
            )
            self.is_new_library = False

        lib.path.mkdir(parents=True, exist_ok=True)

        for id in context.selected_ids:
            id.asset_mark()
            id.asset_data.description = self.description
            id.asset_data.author = self.author
            id.asset_data.license = self.license
            id.asset_data.catalog_id = self.catalog
            id.asset_data.copyright = self.copyright

            prefs = utils.get_prefs()
            id.asset_data.author = prefs.default_author_name
            id.asset_data.license = prefs.default_license

            for tag, value in zip(hive_mind.TAGS_ENUM, self.tags):
                if value:
                    id.asset_data.tags.new(tag[1], skip_if_exists=True)

            # TODO: Handle Icons

            bpy.data.libraries.write(str(lib.path / f"{id.name}.blend"), set([id]), compress=True)

        return {"FINISHED"}
    


classes = (
    SH_OT_AddToLibrary,
    SH_OT_AddAsAssetToLibrary,
    SH_OT_AddToLibraryFromOutliner,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
