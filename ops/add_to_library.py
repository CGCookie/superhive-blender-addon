from pathlib import Path
from threading import Thread

import bpy
from bpy.props import (BoolProperty, BoolVectorProperty, CollectionProperty,
                       EnumProperty, PointerProperty, StringProperty)
from bpy.types import ID, AssetRepresentation, Context, Operator, PropertyGroup, UILayout

from . import polls

from .. import hive_mind, utils

from ..settings import scene


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


class IDToHandle(PropertyGroup):
    operation: EnumProperty(
        name="Operation",
        items=[
            ("REPLACE", "Replace", "Overwrite the existing asset with the new one"),
            ("SKIP", "Skip", "Do not add the asset to the library"),
            ("RENAME", "Rename", "Rename the new asset to avoid conflicts"),
        ]
    )
    
    new_name: StringProperty(
        name="New Name",
        description="The new name of the asset to avoid conflicts",
    )

    lib_path: StringProperty()

    tag_for_renaming: BoolProperty()

    def draw(self, layout: UILayout):
        split = layout.split(factor=0.25, align=True)
        row = split.row(align=True)
        row.alignment = "RIGHT"
        row.label(text=self.name)
        
        new_path = Path(self.lib_path) / f"{self.new_name}.blend"
        
        exists = new_path.exists()
            
        row = split.row(align=True)
        row.alert = exists
        is_rename = self.operation == "RENAME"
        if is_rename:
            row.prop(self, "new_name", text="")
        
        row.prop(self, "operation", text="", icon_only=is_rename)
        if exists:
            row = layout.row()
            row.alert = True
            row.alignment = "RIGHT"
            row.label(text="File already exists")
        

class IDsToHandle(PropertyGroup):
    ids: CollectionProperty(type=IDToHandle)
        
    def clear(self) -> None:
        self.ids: bpy.types.CollectionProperty | list[IDToHandle] | dict[str, IDToHandle]
        self.ids.clear()
    
    def new(self, id: ID, lib_path: Path) -> IDToHandle:
        ith: IDToHandle = self.ids.add()
        ith.name = id.name
        ith.new_name = f"{id.name}_{len(tuple(lib_path.glob(f'{id.name}_*.blend'))) + 1}"
        ith.lib_path = str(lib_path)
        
        return ith
    
    def draw(self, layout: UILayout, only_tagged=False):
        for ith in self.ids:
            if not only_tagged or ith.tag_for_renaming:
                ith.draw(layout)


class AddAsAsset(scene.RenderThumbnailProps):
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
        items = [
            (lib.name, lib.name, f"Add the asset(s) to the '{lib.name}' library")
            for lib in asset_libs
        ]
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
    
    display_ids_to_handle: BoolProperty()
    """Show the IDs to Handle UI instead of the regular UI"""
    
    display_ids_to_rename: BoolProperty()
    
    ids_to_handle: PointerProperty(type=IDsToHandle)
    
    icon_source: EnumProperty(
        name="Icon Source",
        items=[
            ("IGNORE", "Ignore", "Do not set an icon for the asset"),
            ("RENDER", "Render", "Render out a thumbnail for the icon"),
            ("FILE", "File", "Use a file as the icon"),
        ],
    )
    
    icon_file: StringProperty(
        name="Icon File",
        description="The file to use as the icon",
        subtype="FILE_PATH",
    )
    
    def draw(self, context: Context):
        layout: UILayout = self.layout
        layout.use_property_split = True
        
        if self.display_ids_to_handle:
            self.draw_ids_to_handle(layout)
        elif self.display_ids_to_rename:
            self.draw_ids_to_rename(layout)
        else:
            self.draw_regular(context, layout)
    
    def draw_regular(self, context: Context, layout:UILayout):
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
        
        layout.separator(type="LINE")
        
        row = layout.row()
        row.use_property_split = False
        row.prop(self, "icon_source", expand=True)
        
        if self.icon_source == "FILE":
            layout.prop(self, "icon_file")
        elif self.icon_source == "RENDER":
            self.draw_thumbnail_props(layout)

    def draw_ids_to_handle(self, layout:UILayout):
        layout.use_property_split = True
        layout.label(text="Duplicate Asset Names")
        
        layout.separator(type="LINE")
        
        layout.label(text="Some assets have the same name as other assets in the chosen library.")
        
        col = layout.column(align=True)
        col.label(text="Please choose what to do for each asset:")
        self.ids_to_handle.draw(col)

    def draw_ids_to_rename(self, layout:UILayout):
        layout.use_property_split = True
        layout.label(text="Duplicate Asset Names")
        
        layout.separator(type="LINE")
        
        layout.label(text="Some assets still have the same name as other assets in the chosen library.")
        
        col = layout.column(align=True)
        col.label(text="Please choose what to do for each asset:")
        self.ids_to_handle.draw(col, only_tagged=True)

    def invoke(self, context: Context, event):
        self.ids_to_handle: IDsToHandle
        
        prefs = utils.get_prefs()
        self.name = context.object.name
        self.author = prefs.default_author_name
        self.license = prefs.default_license
        self.copyright = prefs.default_copyright
        
        self.ids = context.selected_ids
        
        self.display_ids_to_handle = False
        
        self.lib = None

        return context.window_manager.invoke_props_dialog(self, width=500)
    
    def get_ids(self, context: Context) -> list[ID]:...
    
    def execute(self, context: Context):
        if self.lib == None:
            if self.library == "NEW":
                if not self.new_library_name:
                    self.report({"ERROR"}, "Name not entered for new library")
                    return {"CANCELLED"}
                if self.new_library_name in context.preferences.filepaths.asset_libraries:
                    self.report({"ERROR"}, f"Library `{self.new_library_name}` already exists")
                    return {"CANCELLED"}

                dir: Path = Path(utils.get_prefs().library_directory) / self.new_library_name.replace(" ", "_").casefold()
                dir.mkdir(parents=True, exist_ok=True)
                self.lib = utils.AssetLibrary.create_new_library(
                    self.new_library_name, str(dir),
                    context=context, load_catalogs=True
                )
                self.is_new_library = True
            else:
                self.lib = utils.from_name(
                    self.library, context=context,
                    load_catalogs=True
                )
                self.is_new_library = False

            self.lib.path.mkdir(parents=True, exist_ok=True)
        
            self.ids_to_handle.clear()
        
            for id in self.ids:
                if (self.lib.path / f"{id.name}.blend").exists():
                    self.ids_to_handle.new(id, self.lib.path)
            
            if self.ids_to_handle.ids:
                self.display_ids_to_handle = True
                return context.window_manager.invoke_props_dialog(self, width=500)
            return self.assets_to_library(context)

        # Not First time through execute. Ensure ids_to_handle aren't set to duplicates again
        check = False
        for ith in self.ids_to_handle.ids:
            ith.tag_for_renaming = False
            if ith.operation == "RENAME":
                if (self.lib.path / f"{ith.new_name}.blend").exists():
                    ith.tag_for_renaming = True
                    check = True
        
        if check:
            self.display_ids_to_handle = False
            self.display_ids_to_rename = True
            return context.window_manager.invoke_props_dialog(self, width=500)
        
        return self.assets_to_library(context)
    
    def modal(self, context, event):
        if not self._thread.is_alive():
            self.refresh_library(context)
            return {"FINISHED"}
        return {"RUNNING_MODAL"}
    
    def check_ids_to_handle(self, context: Context):
        if self.ids_to_handle.ids:
            self.display_ids_to_handle = True
            return context.window_manager.invoke_popup(self, width=500)
        return self.assets_to_library(context)
        
    def assets_to_library(self, context: Context):
        lib_path = str(self.lib.path)
        blend_files = {}
        for id in self.ids:
            id_name = id.name
            ith: IDToHandle = self.ids_to_handle.ids.get(id_name)
            if ith:
                if ith.operation == "SKIP":
                    continue
                elif ith.operation == "RENAME":
                    id_name = ith.new_name
            blend_path = str(self.lib.path / f"{id_name}.blend")
            
            if self.icon_source == "RENDER":
                blend_data = blend_files.get(blend_path)
                new_item = [(id_name, type(id).__name__.upper())]
                blend_files[blend_path] = blend_data + new_item if blend_data else new_item
                icon_path = None
            elif self.icon_source == "FILE":
                icon_path = self.icon_file
            self.id_to_asset(context, id, blend_path, icon_path=icon_path)

        if self.icon_source == "RENDER":
            self._thread = Thread(
                target=self.render_icon,
                args=(
                    list(blend_files.keys()),
                    lib_path,
                    list(blend_files.values())
                )
            )
            
            context.window_manager.modal_handler_add(self)
            self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
            self._thread.start()
            
            return {"RUNNING_MODAL"}

        self.refresh_library(context)

        return {"FINISHED"}
        
    def id_to_asset(self, context: Context, id: ID, path: str, icon_path: str = None) -> None:
        id.asset_mark()
        id.asset_data.description = self.description
        id.asset_data.author = self.author
        id.asset_data.license = self.license
        id.asset_data.catalog_id = self.catalog
        id.asset_data.copyright = self.copyright

        prefs = utils.get_prefs()
        id.asset_data.author = prefs.default_author_name
        id.asset_data.license = prefs.default_license
        
        if icon_path:
            if Path(icon_path).exists():
                with context.temp_override(id=id):
                    bpy.ops.ed.lib_id_load_custom_preview(filepath=icon_path)
            else:
                print(f"Icon file does not exist: {icon_path}")

        for tag, value in zip(hive_mind.TAGS_ENUM, self.tags):
            if value:
                id.asset_data.tags.new(tag[1], skip_if_exists=True)
        
        bpy.data.libraries.write(path, set([id]), compress=True)
        
    def render_icon(self, paths: list[str], lib_path: str, ids: list[tuple[str, str]]) -> None:
        prefs = utils.get_prefs()
        utils.rerender_thumbnail(
            paths = paths,
            directory = lib_path,
            objects = ids,
            shading = self.shading,
            angle = utils.resolve_angle(
                self.camera_angle,
                self.flip_x,
                self.flip_y,
                self.flip_z
            ),
            add_plane = prefs.add_ground_plane and not self.flip_z,
            world_name = self.scene_lighting,
            world_strength = self.world_strength,
            padding = 1 - self.padding,
            rotate_world = self.rotate_world,
            debug_scene = self.debug_scene,
            # op=self,
        )
        
        self.reset_thumbnail_settings()
    
    def refresh_library(self, context: Context):
        if polls.is_asset_browser(context):
            area = context.area
        else:
            area = next(
                area for area in context.screen.areas if polls.asset_utils.SpaceAssetInfo.is_asset_browser(area.spaces.active)
            )
            if not area:
                return
        try:
            with context.temp_override(area=area, space_data=area.spaces.active):
                bpy.ops.asset.library_refresh()
        except Exception as e:
            print(f"An error occurred while refreshing the asset library: {e}")
    

class SH_OT_AddAsAssetToLibrary(Operator, AddAsAsset):
    bl_idname = "superhive.add_as_asset_to_library"



class SH_OT_AddToLibraryFromOutliner(Operator, AddAsAsset):
    bl_idname = "superhive.add_to_library_from_outliner"

    @classmethod
    def poll(cls, context):
        if not context.selected_ids:
            cls.poll_message_set("No items selected")
            return False
        return True
    


classes = (
    IDToHandle,
    IDsToHandle,
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
