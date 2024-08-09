from pathlib import Path
from threading import Thread

import bpy
from bpy.props import (
    BoolProperty,
    BoolVectorProperty,
    CollectionProperty,
    EnumProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Context, Event, Operator, OperatorFileListElement, PropertyGroup

from .. import hive_mind, utils
from ..settings import scene
from . import polls


class Catalog(PropertyGroup):
    id: StringProperty()
    name: StringProperty()
    description: StringProperty()

    def get_item(self):
        return (self.id, self.name, self.description)


class Catalogs(PropertyGroup):
    items: CollectionProperty(type=Catalog)

    def clear(self):
        for item in reversed([c for c in self.items]):
            self.items.remove(item)

    def get_items(self):
        self.items: list[Catalog] | dict[str, Catalog]
        return (c.get_item() for c in self.items)


class SH_OT_ImportFromDirectory(Operator, scene.RenderThumbnailProps):
    bl_idname = "bkeeper.import_from_directory"
    bl_label = "Import From Directory"
    bl_description = "Opens file selector, after executes"
    bl_options = {"REGISTER"}

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

    filepath: StringProperty(subtype="FILE_PATH")
    filename: StringProperty(subtype="FILE_NAME")
    directory: StringProperty(subtype="DIR_PATH")
    files: CollectionProperty(type=OperatorFileListElement)

    mark_actions: BoolProperty(name="Mark Actions", default=False)

    mark_collections: BoolProperty(name="Mark Collections", default=False)

    mark_materials: BoolProperty(name="Mark Materials", default=False)

    mark_node_trees: BoolProperty(name="Mark Node Trees", default=False)

    mark_objects: BoolProperty(name="Mark Objects", default=True)

    mark_obj_armatures: BoolProperty(name="Mark Armatures", default=False)

    mark_obj_cameras: BoolProperty(name="Mark Cameras", default=False)

    mark_obj_curves: BoolProperty(name="Mark Curves", default=False)

    mark_obj_empties: BoolProperty(name="Mark Empties", default=False)

    mark_obj_fonts: BoolProperty(name="Mark Font Objects", default=False)

    mark_obj_gpencils: BoolProperty(name="Mark Grease Pencil", default=False)

    mark_obj_lattices: BoolProperty(name="Mark Lattices", default=False)

    mark_obj_lights: BoolProperty(name="Mark Lights", default=False)

    mark_obj_light_probes: BoolProperty(name="Mark Light Probes", default=False)

    mark_obj_meshes: BoolProperty(name="Mark Meshes", default=True)

    mark_obj_metas: BoolProperty(name="Mark Metaballs", default=False)

    mark_obj_point_clouds: BoolProperty(name="Mark Point Cloud", default=False)

    mark_obj_speakers: BoolProperty(name="Mark Speakers", default=False)

    mark_obj_surfaces: BoolProperty(name="Mark Surfaces", default=False)

    mark_obj_volumes: BoolProperty(name="Mark Volumes", default=False)

    mark_worlds: BoolProperty(name="Mark Worlds", default=False)

    clear_other_assets: BoolProperty(
        name="Clear Other Assets",
        default=False,
        description="Clear existing marked assets of types that aren't checked",
    )

    filter_glob: StringProperty(default="*.blend", options={"HIDDEN"})

    author: StringProperty(name="Author")

    desc: StringProperty(name="Description")

    license: EnumProperty(
        name="License",
        description="License of the asset",
        items=hive_mind.LICENSES_ENUM,
    )

    copyright: StringProperty(name="Copyright")

    tags: BoolVectorProperty(
        name="Tags",
        description="Tags to add to the asset",
        size=len(hive_mind.TAGS_DICT),
    )

    override_existing_data: BoolProperty(
        name="Override Existing Data",
        default=False,
        description="Override existing data",
    )

    skip_hidden: BoolProperty(
        default=True,
        name="Skip Hidden",
        description="Skip hidden objects and collections",
    )

    catalog_source: EnumProperty(
        name="Catalog Source",
        description="Where to get the catalog from",
        items=(
            ("Filename", "Filename", "Filename"),
            ("Directory", "Directory Name", "Directory Name"),
            ("NONE", "None", "None"),
            ("NEW", "New/Search", "New/Search"),
        ),
        default=3,
    )

    catalog_items: PointerProperty(type=Catalogs)

    def _get_catalog_items(self, context):
        self.catalog_items: Catalogs
        return self.catalog_items.get_items() or (("NONE", "None", "None"),)

    catalog: EnumProperty(items=_get_catalog_items, name="Catalog", default=3)

    def get_catalog_search_results_from_all(self, context, edit_text):
        results = []
        for a in self.catalog_items.items:
            if edit_text.lower() in a.id.lower():
                results.append(a.id)
        if not results:
            results.append(("Will Creating New Catalog"))
        return results

    new_catalog_name: StringProperty(
        default="",
        name="Catalog Name",
        search=get_catalog_search_results_from_all,
    )

    recursive: BoolProperty(
        name="Recursive",
        description="Whether to search recursively in the directory",
        default=True,
    )

    move_to_library: BoolProperty(
        name="Move to Library",
        description="Move the imported assets to the library",
        default=True,
    )

    render_icons: BoolProperty(
        name="Render Icons",
        description="Render icons for the assets",
        default=False,
    )

    @classmethod
    def poll(cls, context):
        return polls.is_not_all_library(context, cls=cls)

    def draw(self, context):
        layout = self.layout

        dpath = Path(context.space_data.params.directory.decode("utf-8"))

        # if self.catalog_source == "Filename":
        #     blends = (
        #         list(dpath.rglob("**/*.blend"))
        #         if self.recursive
        #         else list(dpath.glob("*.blend"))
        #     )
        #     blends_count = len(blends)
        # else:
        #     blends_count = len(
        #         list(dpath.rglob("**/*.blend"))
        #         if self.recursive
        #         else list(dpath.glob("*.blend"))
        #     )

        # layout.label(text=f"Blend Files Found: {blends_count}")

        col = layout.column()
        col.use_property_split = True
        col.prop(self, "catalog_source")

        match self.catalog_source:
            case "NEW":
                col.prop(self, "new_catalog_name")
            case "Filename":
                row = col.row()
                row.alignment = "RIGHT"
                row.enabled = False
                row.label(text="Catalog: Will be derived from the blend file names")
                row.separator()
            case "Directory":
                row = col.row()
                row.alignment = "RIGHT"
                row.enabled = False
                row.label(text=f"Catalog: {dpath.name}")
                row.separator()
            case "NONE":
                row = col.row()
                row.alignment = "RIGHT"
                row.enabled = False
                row.label(text="Catalog: No catalog will be set")
                row.separator()

        layout.prop(self, "mark_actions", text="Actions", icon="ACTION", toggle=True)

        layout.prop(
            self,
            "mark_collections",
            text="Collections",
            icon="OUTLINER_COLLECTION",
            toggle=True,
        )

        layout.prop(
            self, "mark_materials", text="Materials", icon="MATERIAL", toggle=True
        )

        layout.prop(
            self, "mark_node_trees", text="Node Trees", icon="NODETREE", toggle=True
        )

        header, body = layout.panel("mark_object_types")
        header.prop(self, "mark_objects", text="Objects", icon="OBJECT_DATAMODE")

        if body:
            body.enabled = self.mark_objects
            grid = body.grid_flow(row_major=True, columns=3, align=True)
            grid.prop(
                self,
                "mark_obj_armatures",
                toggle=True,
                text="Armatures",
                icon="ARMATURE_DATA",
            )
            grid.prop(
                self,
                "mark_obj_cameras",
                toggle=True,
                text="Cameras",
                icon="CAMERA_DATA",
            )
            grid.prop(
                self, "mark_obj_curves", toggle=True, text="Curves", icon="CURVE_DATA"
            )
            grid.prop(
                self, "mark_obj_empties", toggle=True, text="Empties", icon="EMPTY_DATA"
            )
            grid.prop(
                self, "mark_obj_fonts", toggle=True, text="Fonts", icon="FONT_DATA"
            )
            grid.prop(
                self,
                "mark_obj_gpencils",
                toggle=True,
                text="Gpencils",
                icon="OUTLINER_OB_GREASEPENCIL",
            )
            grid.prop(
                self,
                "mark_obj_lattices",
                toggle=True,
                text="Lattices",
                icon="LATTICE_DATA",
            )
            grid.prop(
                self, "mark_obj_lights", toggle=True, text="Lights", icon="LIGHT_DATA"
            )
            grid.prop(
                self,
                "mark_obj_light_probes",
                toggle=True,
                text="Light Probes",
                icon="OUTLINER_OB_LIGHTPROBE",
            )
            grid.prop(
                self, "mark_obj_meshes", toggle=True, text="Meshes", icon="MESH_DATA"
            )
            grid.prop(
                self, "mark_obj_metas", toggle=True, text="Metas", icon="META_DATA"
            )
            grid.prop(
                self,
                "mark_obj_point_clouds",
                toggle=True,
                text="PointClouds",
                icon="POINTCLOUD_DATA",
            )
            grid.prop(
                self,
                "mark_obj_speakers",
                toggle=True,
                text="Speakers",
                icon="OUTLINER_DATA_SPEAKER",
            )
            grid.prop(
                self,
                "mark_obj_surfaces",
                toggle=True,
                text="Surfaces",
                icon="SURFACE_DATA",
            )
            grid.prop(
                self,
                "mark_obj_volumes",
                toggle=True,
                text="Volumes",
                icon="VOLUME_DATA",
            )

        layout.prop(self, "mark_worlds", icon="WORLD", toggle=True)

        layout.prop(self, "clear_other_assets", text="Clear Existing")
        layout.prop(self, "skip_hidden", text="Skip Hidden")
        layout.prop(self, "recursive")
        layout.prop(self, "move_to_library")

        header, body = layout.panel("metadata", default_closed=True)
        row = header.row()
        row.alignment = "CENTER"
        row.label(text="Metadata", icon="TEXT")

        if body:
            col = body.column()
            col.use_property_split = True
            col.use_property_decorate = False
            col.prop(self, "author")
            col.prop(self, "desc")
            col.prop(self, "license")
            col.prop(self, "copyright")

            body.label(text="Tags:", icon="TAG")
            col = body.column(align=True)
            grid = col.grid_flow(row_major=True, columns=3, align=True)
            tags_count = len(hive_mind.TAGS_DICT)
            tags_slice = tags_count - (tags_count % 3)
            tag_names = list(hive_mind.TAGS_DICT.keys())
            for i, tag_name in enumerate(tag_names[:tags_slice]):
                # grid.prop(self, bool_prop, text=tag_name)
                grid.prop(self, "tags", index=i, text=tag_name, toggle=True)
            row = col.row(align=True)
            for i in range(tags_count - tags_slice):
                row.prop(
                    self,
                    "tags",
                    index=i + tags_slice,
                    text=tag_names[i + tags_slice],
                    toggle=True,
                )

        header, body = layout.panel("render_icons", default_closed=True)
        row = header.row()
        row.alignment = "LEFT"
        row.prop(self, "render_icons", text="")
        row = header.row()
        row.alignment = "CENTER"
        row.label(text="Render Icons", icon="IMAGE_DATA")
        header.separator()

        if body:
            self.draw_thumbnail_props(body)

    def invoke(self, context, event):
        self.lib = utils.from_active(context, area=context.area, load_catalogs=True)
        catalogs = self.lib.catalogs.get_catalogs()
        catalogs = sorted(catalogs, key=lambda x: x.name.lower())

        items = [
            (b.name, b.name, f"Add assets to the '{b.name}' catalog") for b in catalogs
        ]

        self.catalog_items.clear()

        for item in items:
            c: Catalog = self.catalog_items.items.add()
            c.id = item[0]
            c.name = item[1]
            c.description = item[2]

        context.window_manager.fileselect_add(self)

        return {"RUNNING_MODAL"}

    def execute(self, context):
        self.scene_sets: scene.SH_Scene = context.scene.superhive

        self._thread = Thread(
            target=self.main,
        )

        if not context.space_data.show_region_tool_props:
            context.space_data.show_region_tool_props = True

        self.prog = self.scene_sets.side_panel_batch_asset_update_progress_bar
        self.prog.metadata_label = "Importing Blend Files"
        self.prog.start()
        self.prog.draw_icon_rendering = self.render_icons

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

    def main(self):
        assets_marked = utils.mark_assets_in_blend(
            self.lib,
            self.directory,
            self.mark_actions,
            self.mark_collections,
            self.mark_materials,
            self.mark_node_trees,
            self.mark_objects,
            self.mark_obj_armatures,
            self.mark_obj_cameras,
            self.mark_obj_curves,
            self.mark_obj_empties,
            self.mark_obj_fonts,
            self.mark_obj_gpencils,
            self.mark_obj_lattices,
            self.mark_obj_lights,
            self.mark_obj_light_probes,
            self.mark_obj_meshes,
            self.mark_obj_metas,
            self.mark_obj_point_clouds,
            self.mark_obj_speakers,
            self.mark_obj_surfaces,
            self.mark_obj_volumes,
            self.mark_worlds,
            self.clear_other_assets,
            self.skip_hidden,
            self.catalog_source,
            self.new_catalog_name,
            self.author,
            self.desc,
            self.license,
            self.copyright,
            self.tags,
            self.move_to_library,
            override_existing_data=self.override_existing_data,
            recursive=self.recursive,
            op=self,
        )

        if self.render_icons and not self.prog.cancel:
            self.start_icon = True
            self.update = True
            prefs = utils.get_prefs()

            utils.rerender_thumbnail(
                paths=[p for p in assets_marked.keys()],
                directory=str(self.lib.path),
                objects=[f for f in assets_marked.values()],
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
                op=self,
            )

        if bpy.ops.asset.library_refresh.poll():
            bpy.ops.asset.library_refresh()

        return {"FINISHED"}

    def cancel(self, context: Context):
        self.prog.cancel = True
        self._thread.join()
        bpy.ops.asset.library_refresh()
        context.window_manager.event_timer_remove(self._timer)
        bpy.app.timers.register(self.prog.end, first_interval=2)
        return {"CANCELLED"}


classes = (Catalog, Catalogs, SH_OT_ImportFromDirectory)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
