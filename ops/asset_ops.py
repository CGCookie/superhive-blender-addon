import os
from functools import partial
from threading import Thread

import bpy
from bpy.props import (
    BoolVectorProperty,
    CollectionProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import AssetRepresentation, Context, Event, Operator

from .. import hive_mind, utils
from ..settings import asset as asset_settings
from ..settings import scene
from . import polls


class SH_OT_UpdateAsset(Operator):
    bl_idname = "bkeeper.update_asset"
    bl_label = "Update Asset"
    bl_description = "Update the asset data of selected assets. Updates all assets if none are selected."
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return polls.is_asset_browser(context, cls=cls) and context.asset

    def execute(self, context):
        if not context.asset:
            self.report({"ERROR"}, "No active asset found")
            return {"CANCELLED"}

        prefs = utils.get_prefs()

        asset = utils.Asset(context.asset)

        if context.asset.metadata.sh_catalog == "CUSTOM":
            # Create catalog_id if it doesn't exist
            catalog_simple_name: str = context.asset.metadata.sh_catalog_custom
            if catalog_simple_name:
                lib = utils.from_active(context, load_catalogs=True)
                cat = lib.catalogs.get_catalog_by_path(catalog_simple_name)
                if cat:
                    asset.catalog_id = cat.id
                else:
                    with lib.open_catalogs_file() as cat_file:
                        if "/" in catalog_simple_name:
                            name = catalog_simple_name.split("/")[-1]
                            cat = cat_file.add_catalog(name, path=catalog_simple_name)
                        else:
                            cat = cat_file.add_catalog(catalog_simple_name)
                        asset.catalog_id = cat.id

        # Custom license handled when creating the custom Asset object

        asset.update_asset(prefs.ensure_default_blender_version().path)

        bpy.ops.asset.library_refresh()

        return {"FINISHED"}


class BatchUpdateAssets:
    update = False
    label = ""
    progress = 0.0

    metadata_progress = 0.0
    setup_progress = 0.0
    render_progress = 0.0
    apply_progress = 0.0

    start_metadata = False

    start_icon = False
    start_icon_setup = False
    start_icon_render = False
    start_icon_apply = False

    def _invoke(self, context: Context, event):
        self.scene_sets: scene.SH_Scene = context.scene.superhive

        self._thread = Thread(
            target=self.main,
            args=(
                self.scene_sets.metadata_update,
                context.selected_assets,
                context.space_data.params.asset_library_reference,
            ),
        )

        if not context.space_data.show_region_tool_props:
            context.space_data.show_region_tool_props = True

        self.prog = self.scene_sets.side_panel_batch_asset_update_progress_bar
        self.prog.metadata_label = "Metadata Update"
        self.prog.start()
        self.prog.draw_icon_rendering = (
            self.scene_sets.metadata_update.render_thumbnails
        )

        self.active_bar = self.prog.metadata_bar

        self.start_metadata = True
        self._thread.start()

        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        context.window_manager.modal_handler_add(self)

        return {"RUNNING_MODAL"}

    def modal(self, context: Context, event: Event):
        context.area.tag_redraw()
        self.active_bar.update_formated_time()

        if self.update:
            self.update = False

            if self.start_metadata:
                self.start_metadata = False
                self.prog.metadata_bar.start()
            elif self.start_icon or self.start_icon_setup:
                self.start_icon = False
                self.start_icon_setup = False
                self.prog.metadata_bar.end()
                self.prog.icon_rendering.setup_bar.start()
                self.active_bar = self.prog.icon_rendering.setup_bar
            elif self.start_icon_render:
                self.start_icon_render = False
                self.prog.icon_rendering.setup_bar.end()
                self.prog.icon_rendering.render_bar.start()
                self.active_bar = self.prog.icon_rendering.render_bar
            elif self.start_icon_apply:
                self.start_icon_apply = False
                self.prog.icon_rendering.render_bar.end()
                self.prog.icon_rendering.apply_bar.start()
                self.active_bar = self.prog.icon_rendering.apply_bar

            self.prog.metadata_bar.progress = self.metadata_progress
            self.prog.icon_rendering.setup_bar.progress = self.setup_progress
            self.prog.icon_rendering.render_bar.progress = self.render_progress
            self.prog.icon_rendering.apply_bar.progress = self.apply_progress

        if not self._thread.is_alive():
            self.report({"INFO"}, "Assets Updated!")
            bpy.ops.asset.library_refresh()
            context.window_manager.event_timer_remove(self._timer)
            bpy.app.timers.register(self.prog.end, first_interval=1)
            return {"FINISHED"}
        elif event.value == "ESC" and utils.mouse_in_window(
            context.window, event.mouse_x, event.mouse_y
        ):
            self.prog.cancel = True
        elif self.prog.cancel:
            self._thread.join()
            bpy.ops.asset.library_refresh()
            context.window_manager.event_timer_remove(self._timer)
            bpy.app.timers.register(self.prog.end, first_interval=1)
            return {"CANCELLED"}

        if "MOUSEWHEEL" in event.type:
            return {"PASS_THROUGH"}
        return {"RUNNING_MODAL"}

    def main(
        self,
        md_update: scene.BatchMetadataUpdate,
        selected_assets: list[AssetRepresentation],
        library_name: str,
    ):
        prefs = utils.get_prefs()

        lib = utils.from_name(library_name, load_catalogs=True)
        for i, bpy_asset in enumerate(selected_assets):
            if self.prog.cancel:
                break
            asset = utils.Asset(bpy_asset)
            md_update.process_asset_metadata(asset, bpy_asset, lib)
            asset.update_asset(
                prefs.ensure_default_blender_version().path, debug=md_update.debug_scene
            )
            self.metadata_progress = (i + 1) / len(selected_assets)
            self.update = True

        if md_update.render_thumbnails and not self.prog.cancel:
            self.start_icon = True
            self.update = True

            blends = {}
            for a in selected_assets:
                # if a.id_type=='OBJECT' or a.id_type=='COLLECTION' or a.id_type=='MATERIAL':
                if a.id_type in {"OBJECT", "COLLECTION", "MATERIAL"}:
                    blend_data = blends.get(a.full_library_path)
                    blends[a.full_library_path] = (
                        blend_data + [(a.name, a.id_type)]
                        if blend_data
                        else [(a.name, a.id_type)]
                    )

            lib_path = [
                a
                for a in bpy.context.preferences.filepaths.asset_libraries
                if a.name == library_name
            ]
            if lib_path:
                lib_path = lib_path[0].path

            prefs = utils.get_prefs()
            utils.rerender_thumbnail(
                paths=[b for b in blends.keys()],
                directory=lib_path,
                objects=[f for f in blends.values()],
                shading=md_update.shading,
                angle=utils.resolve_angle(
                    md_update.camera_angle,
                    md_update.flip_x,
                    md_update.flip_y,
                    md_update.flip_z,
                ),
                add_plane=prefs.add_ground_plane and not md_update.flip_z,
                world_name=md_update.scene_lighting,
                world_strength=md_update.world_strength,
                padding=1 - md_update.padding,
                rotate_world=md_update.rotate_world,
                debug_scene=md_update.debug_scene,
                op=self,
            )

        if md_update.reset_settings:
            md_update.reset()

    def cancel(self, context: Context):
        self.prog.cancel = True
        self._thread.join()
        bpy.ops.asset.library_refresh()
        context.window_manager.event_timer_remove(self._timer)
        bpy.app.timers.register(self.prog.end, first_interval=2)
        return {"CANCELLED"}


class SH_OT_BatchUpdateAssets(Operator, BatchUpdateAssets):
    bl_idname = "bkeeper.batch_update_assets"
    bl_label = "Batch Update Assets"
    bl_description = "Update the asset data of selected assets."
    bl_options = {"REGISTER", "UNDO"}

    metadata_update: PointerProperty(type=scene.BatchMetadataUpdate)

    @classmethod
    def poll(cls, context):
        cls.metadata_update: scene.BatchMetadataUpdate
        if not polls.is_asset_browser(context, cls=cls):
            return False

        if not context.selected_assets:
            cls.poll_message_set("Please select and asset first")
            return False

        return True

    def draw(self, context):
        layout = self.layout
        self.metadata_update.draw(context, layout)

    def invoke(self, context, event):
        self.metadata_update.reset()
        return context.window_manager.invoke_props_dialog(self, width=500)

    def check(self, context):
        return any(item.check() for item in self.metadata_update.metadata_items)

    def execute(self, context):
        return self._invoke(context, None)


class SH_OT_BatchUpdateAssetsFromScene(Operator, BatchUpdateAssets):
    bl_idname = "bkeeper.batch_update_assets_from_scene"
    bl_label = "Batch Update Assets"
    bl_description = "Update the asset data of selected assets."
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        cls.metadata_update: scene.BatchMetadataUpdate
        if not polls.is_asset_browser(context, cls=cls):
            return False

        if not context.selected_assets:
            cls.poll_message_set("Please select and asset first")
            return False

        return True

    def invoke(self, context, event):
        return self._invoke(context, event)


class SH_OT_AddUpdateAction(Operator):
    bl_idname = "bkeeper.add_update_action"
    bl_label = "Add Update Action"
    bl_description = "Add a new action to the batch update list."
    bl_options = {"REGISTER", "UNDO"}

    metadata_item: StringProperty()
    """The metadata item to add the action to."""

    action_index: IntProperty()
    """The index of the action that added the new action."""

    def execute(self, context):
        scene_sets: scene.SH_Scene = context.scene.superhive
        item = scene_sets.metadata_update.metadata_items.get(self.metadata_item)
        item.add_action(self.action_index)
        return {"FINISHED"}


class SH_OT_RemoveUpdateAction(Operator):
    bl_idname = "bkeeper.remove_update_action"
    bl_label = "Remove Update Action"
    bl_description = "Remove an action."
    bl_options = {"REGISTER", "UNDO"}

    metadata_item: StringProperty()
    """The metadata item to add the action to."""

    action_index: IntProperty()
    """The index of the action that added the new action."""

    def execute(self, context):
        scene_sets: scene.SH_Scene = context.scene.superhive
        item = scene_sets.metadata_update.metadata_items.get(self.metadata_item)
        item.remove_action(self.action_index)
        return {"FINISHED"}


class SH_OT_RerenderThumbnail(Operator, scene.RenderThumbnailProps):
    bl_idname = "bkeeper.rerender_thumbnail"
    bl_label = "Re-Render Thumbnail"
    bl_description = "Render the thumbnail of the selected assets."
    bl_options = {"REGISTER", "UNDO"}

    # Props from `scene.RenderThumbnailProps` #
    # --------------------------------------- #
    #  shading: EnumProperty
    #  camera_angle: EnumProperty
    #  flip_z: BoolProperty
    #  flip_x: BoolProperty
    #  flip_y: BoolProperty
    #  thumb_res: IntProperty
    #  camera_height: FloatProperty
    #  camera_zoom: FloatProperty
    #  scene_lighting: EnumProperty
    # --------------------------------------- #

    @classmethod
    def poll(cls, context):
        return (
            context.area.ui_type == "ASSETS"
            and context.selected_assets
            and context.selected_assets[:]
            and context.space_data.params.asset_library_reference != "LOCAL"
        )

    @classmethod
    def description(cls, context, operator_properties):
        return f"Rerender the thumbnail of the asset{'s' if len(context.selected_assets)>1 else ''}"

    def draw(self, context):
        self.draw_thumbnail_props(self.layout)

    def invoke(self, context, event):
        self.reset_thumbnail_settings()
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        blends = {}
        for a in context.selected_assets:
            # if a.id_type=='OBJECT' or a.id_type=='COLLECTION' or a.id_type=='MATERIAL':
            if a.id_type in {"OBJECT", "COLLECTION", "MATERIAL"}:
                blend_data = blends.get(a.full_library_path)
                blends[a.full_library_path] = (
                    blend_data + [(a.name, a.id_type)]
                    if blend_data
                    else [(a.name, a.id_type)]
                )

        self.threads = []
        lib_path = [
            a
            for a in bpy.context.preferences.filepaths.asset_libraries
            if a.name == context.space_data.params.asset_library_reference
        ]
        if lib_path:
            lib_path = lib_path[0].path

        prefs = utils.get_prefs()
        thumbnail_rendering_func = partial(
            utils.rerender_thumbnail,
            paths=[b for b in blends.keys()],
            directory=lib_path,
            objects=[f for f in blends.values()],
            shading=self.shading,
            angle=utils.resolve_angle(
                self.camera_angle, self.flip_x, self.flip_y, self.flip_z
            ),
            add_plane=prefs.add_ground_plane and not self.flip_z,
            world_name=self.scene_lighting,
            world_strength=self.world_strength,
            padding=1 - self.padding,
            rotate_world=self.rotate_world,
            debug_scene=self.debug_scene,
        )

        self.thread = Thread(target=thumbnail_rendering_func)
        if prefs.non_blocking:
            wm = context.window_manager
            self.timer = wm.event_timer_add(1, window=context.window)
            wm.modal_handler_add(self)
            self.thread.start()
            print("Starting Modal")
            return {"RUNNING_MODAL"}
        else:
            thumbnail_rendering_func()

            bpy.ops.asset.library_refresh()

            return {"FINISHED"}

    def modal(self, context, event):
        if event.type == "TIMER":
            context.scene.sh_progress_t = f"Regenerating Thumbnails..."
            if context.area:
                context.area.tag_redraw()
            if not self.thread.is_alive():
                self.report({"INFO"}, "Thumbnails Regenerated!")
                bpy.ops.asset.library_refresh()
                context.scene.sh_progress_t = ""
                if context.area:
                    context.area.tag_redraw()
                print("Finished Modal/Operator")
                return {"FINISHED"}
        else:
            return {"PASS_THROUGH"}
        return {"RUNNING_MODAL"}


class SH_OT_ChangeAssetIcon(Operator):
    bl_idname = "bkeeper.change_asset_icon"
    bl_label = "Change Icon"
    bl_description = "Change the icon of the active asset."
    bl_options = {"REGISTER", "UNDO"}

    filepath: StringProperty(subtype="FILE_PATH")
    filename: StringProperty()
    directory: StringProperty(subtype="DIR_PATH")
    files: CollectionProperty(type=bpy.types.OperatorFileListElement)

    @classmethod
    def poll(cls, context):
        return polls.is_asset_browser(context, cls=cls) and context.asset

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        if not self.filepath:
            self.report({"ERROR"}, "No file selected")
            return {"CANCELLED"}

        if not os.path.exists(self.filepath):
            self.report({"ERROR"}, "File does not exist")
            return {"CANCELLED"}

        asset = utils.Asset(context.asset)
        asset.icon_path = self.filepath

        prefs = utils.get_prefs()
        asset.update_asset(prefs.ensure_default_blender_version().path)

        return {"FINISHED"}


class SH_OT_ResetAssetMetadataProperty(Operator):
    bl_idname = "bkeeper.reset_asset_metadata_property"
    bl_label = "Reset"
    bl_description = "Reset the metadata property of the active asset."
    bl_options = {"REGISTER", "UNDO"}

    property: StringProperty()
    original_value: StringProperty()

    @classmethod
    def poll(cls, context):
        return polls.is_asset_browser(context, cls=cls) and context.asset

    def execute(self, context):
        if self.property == "tags":
            # self.original_value should be a list of tags separated by commas
            tags = self.original_value.split(",")
            sh_tags: "asset_settings.SH_AssetTags" = context.asset.metadata.sh_tags
            for tag in tags:
                sh_tags.new_tag(tag, context=context)
        else:
            setattr(context.asset.metadata, self.property, self.original_value)
        return {"FINISHED"}


class SH_OT_ResetAssetMetadata(Operator):
    bl_idname = "bkeeper.reset_asset_metadata"
    bl_label = "Reset Asset Metadata"
    bl_description = "Reset the asset metadata of selected assets. Resets all assets if none are selected."
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        asset = utils.Asset(context.asset)

        asset.reset_metadata(context)

        return {"FINISHED"}


class SH_OT_AddTags(Operator):
    bl_idname = "bkeeper.add_tags"
    bl_label = "Add"
    bl_description = "Add new tags to the active asset."
    bl_options = {"REGISTER", "UNDO"}

    # name: StringProperty(
    #     name="Tag Name",
    #     description="The name of the tag to add",
    # )
    # name: EnumProperty(
    #     name="Tag Name",
    #     description="The name of the tag to add as allowed by Superhive",
    #     items=hive_mind.get_tags,
    # )
    tags: BoolVectorProperty(
        name="Tags",
        description="The tags to add to the asset",
        size=len(hive_mind.get_tags()),
    )

    @classmethod
    def poll(cls, context):
        return polls.is_asset_browser(context, cls=cls) and context.asset

    def draw(self, context):
        layout = self.layout
        grid = layout.grid_flow(columns=3, even_columns=True)
        for i, tag in enumerate(hive_mind.get_tags()):
            grid.prop(self, "tags", index=i, text=tag[1], expand=True)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)

    def execute(self, context):
        for i, (tag_id, tag_name, tag_desc) in enumerate(hive_mind.get_tags()):
            if self.tags[i]:
                tags: "asset_settings.SH_AssetTags" = context.asset.metadata.sh_tags
                tags.new_tag(tag_name, context, id=tag_id, desc=tag_desc)
        return {"FINISHED"}


class SH_OT_RemoveTag(Operator):
    bl_idname = "bkeeper.remove_tag"
    bl_label = "Remove"
    bl_description = "Remove the active tag from the active asset."
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return polls.is_asset_browser(context, cls=cls) and context.asset

    def execute(self, context):
        tags: "asset_settings.SH_AssetTags" = context.asset.metadata.sh_tags
        tags.remove_tag(tags.active_index, context)
        return {"FINISHED"}


class SH_OT_ResetTags(Operator):
    bl_idname = "bkeeper.reset_tag"
    bl_label = "Reset"
    bl_description = "Reset the tags to the original tags."
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return polls.is_asset_browser(context, cls=cls) and context.asset

    def execute(self, context):
        sh_tags: "asset_settings.SH_AssetTags" = context.asset.metadata.sh_tags

        sh_tags.clear(context)

        for tag in context.asset.metadata.tags:
            sh_tags.new_tag(tag.name, context)

        return {"FINISHED"}


classes = (
    SH_OT_AddTags,
    SH_OT_RemoveTag,
    SH_OT_ResetTags,
    SH_OT_UpdateAsset,
    SH_OT_ResetAssetMetadataProperty,
    SH_OT_ResetAssetMetadata,
    SH_OT_AddUpdateAction,
    SH_OT_RemoveUpdateAction,
    SH_OT_BatchUpdateAssetsFromScene,
    SH_OT_BatchUpdateAssets,
    SH_OT_ChangeAssetIcon,
    SH_OT_RerenderThumbnail,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
