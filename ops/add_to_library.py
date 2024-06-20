import bpy
from bpy.types import Operator, AssetRepresentation, UserAssetLibrary
from bpy.props import BoolProperty, EnumProperty
from pathlib import Path
# from fuzzywuzzy import process, fuzz

from .. import utils


class SH_OT_AddToLibrary(Operator):
    bl_idname = "superhive.add_to_library"
    bl_label = "Add to Library"
    bl_description = "Add the selected asset(s) to a library"
    bl_options = {"REGISTER", "UNDO"}

    # TODO: Remove fuzzywuzzy if not used in other places

    def _get_library_items(self, context):
        asset_libs = context.preferences.filepaths.asset_libraries
        return [(lib.name, lib.name, f"Add the asset(s) to the '{lib.name}' library") for lib in asset_libs]
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

    asset_types_to_id_types = {
        "ACTION": "actions",
        "ARMATURE": "armatures",
        "BRUSH": "brushes",
        "CACHEFILE": "cache_files",
        "CAMERA": "cameras",
        "COLLECTION": "collections",
        "CURVE": "curves",
        "CURVES": "curves",
        "FONT": "fonts",
        "GREASEPENCIL": "grease_pencils",
        "GREASEPENCIL_V3": "grease_pencils",
        "IMAGE": "images",
        "KEY": "shape_keys",
        "LATTICE": "lattices",
        "LIBRARY": "libraries",
        "LIGHT": "lights",
        "LIGHT_PROBE": "lightprobes",
        "LINESTYLE": "linestyles",
        "MASK": "masks",
        "MATERIAL": "materials",
        "MESH": "meshes",
        "META": "metaballs",
        "MOVIECLIP": "movieclips",
        "NODETREE": "node_groups",
        "OBJECT": "objects",
        "PAINTCURVE": "paint_curves",
        "PALETTE": "palettes",
        "PARTICLE": "particles",
        "POINTCLOUD": "",
        "SCENE": "scenes",
        "SCREEN": "screens",
        "SOUND": "sounds",
        "SPEAKER": "speakers",
        "TEXT": "texts",
        "TEXTURE": "textures",
        "VOLUME": "volumes",
        "WINDOWMANAGER": "window_managers",
        "WORKSPACE": "workspaces",
        "WORLD": "worlds",
    }

    def execute(self, context):
        lib = utils.from_name(
            self.library, context=context,
            load_catalogs=True
        )

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

    def _execute(self, context):
        lib: UserAssetLibrary = context.preferences.filepaths.asset_libraries.get(
            self.library
        )

        if not lib:
            self.report({"ERROR"}, f"Library `{self.library}` not found")
            return {"CANCELLED"}

        dir = Path(lib.path)

        dir.mkdir(parents=True, exist_ok=True)

        assets = context.selected_assets

        if self.keep_blend_files_as_is:
            self.add_to_library_keep(assets, dir)
        else:
            self.add_to_library_split(assets, dir)

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
                data_type = self.asset_types_to_id_types[asset.id_type]
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
                    if self.copy_catalogs:
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
                                Path(asset.full_library_path).parent.parent
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


classes = (SH_OT_AddToLibrary,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
