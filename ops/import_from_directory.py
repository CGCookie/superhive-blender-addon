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
from bpy.types import (
    Context,
    Event,
    Operator,
    OperatorFileListElement,
    PropertyGroup,
)

import functools
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
            # self.items.remove(item)
            self.items.remove(0)

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

        layout.prop(self, "mark_worlds", text="Worlds", icon="WORLD", toggle=True)

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

        utils.ensure_sidepanel_right_is_open(context.space_data)

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

        if event.type in {"MIDDLEMOUSE", "WHEELUPMOUSE", "WHEELDOWNMOUSE"}:
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
        if hasattr(self, "_thread"):  # Ensure `execute` has run
            self.prog.cancel = True
            self._thread.join()
            bpy.ops.asset.library_refresh()
            context.window_manager.event_timer_remove(self._timer)
            bpy.app.timers.register(self.prog.end, first_interval=2)


def get_all_files_with_extension(path: Path, ext: str) -> list[Path]:
    return [
        subdir
        for subdir in path.rglob("*")
        if subdir.is_file() and subdir.suffix.lower() == f".{ext.lower()}"
    ]


class SH_OT_USD_Assets_From_Directory(
    bpy.types.Operator, utils.Create_Assets_From_USD_Props_Base
):
    bl_idname = "bkeeper.create_assets_from_directory_usd"
    bl_label = "Create Assets From USD Files"
    bl_description = "Create Assets from Directory"
    bl_options = {"REGISTER", "UNDO"}

    updated = False
    cancelled = False

    progress = 0.0
    pre_label = ""
    label = ""
    post_label = ""

    total_files = 1
    total_imported = 0
    total_skipped = 0

    def draw(self, context):
        super().draw(self.layout)

    def invoke(self, context, event):
        self.thread = None

        self.progress = 0.0
        self.label = "Importing:"

        scene_sets: "scene.SH_Scene" = context.scene.superhive
        self.prog = scene_sets.import_from_directory

        self.lib = utils.from_active(context, area=context.area)

        self.load_settings(utils.get_prefs().usd_import_settings)

        self.active_library_name = utils.get_active_library_name(
            context, area=context.area
        )

        context.window_manager.fileselect_add(self)

        return {"RUNNING_MODAL"}

    def execute(self, context):
        prefs = utils.get_prefs()
        dir_path = self.filepath
        filters = []
        filters.append("OBJECTS")
        filters.append("MESH")

        catalog = self.catalog if self.catalog != "NEW" else self.new_catalog_name
        lib = utils.from_active(context, area=context.area)

        files = []
        if self.files:
            dir_path = Path(self.filepath).parent
        else:
            dir_path = Path(self.filepath)

        if len(self.files) > 0 and all(
            a.name and Path(dir_path, a.name).exists() for a in self.files
        ):
            files = [Path(dir_path, a.name) for a in self.files]
        else:
            files = get_all_files_with_extension(dir_path, "usd")
            files.extend(get_all_files_with_extension(dir_path, "usdc"))
            files.extend(get_all_files_with_extension(dir_path, "usda"))
            files.extend(get_all_files_with_extension(dir_path, "usdz"))

        args_dict = {
            "scale": self.scale,
            "set_frame_range": self.set_frame_range,
            "import_cameras": self.import_cameras,
            "import_curves": self.import_curves,
            "import_lights": self.import_lights,
            "import_materials": self.import_materials,
            "import_meshes": self.import_meshes,
            "import_volumes": self.import_volumes,
            "import_shapes": self.import_shapes,
            "import_skeletons": self.import_skeletons,
            "import_blendshapes": self.import_blendshapes,
            "import_points": self.import_points,
            "import_subdiv": self.import_subdiv,
            # "import_instance_proxies": self.import_instance_proxies,
            "support_scene_instancing": self.support_scene_instancing,
            "import_visible_only": self.import_visible_only,
            "create_collection": self.create_collection,
            "read_mesh_uvs": self.read_mesh_uvs,
            "read_mesh_colors": self.read_mesh_colors,
            "read_mesh_attributes": self.read_mesh_attributes,
            "prim_path_mask": self.prim_path_mask,
            "import_guide": self.import_guide,
            "import_proxy": self.import_proxy,
            "import_render": self.import_render,
            "import_usd_preview": self.import_usd_preview,
            "set_material_blend": self.set_material_blend,
            "light_intensity_scale": self.light_intensity_scale,
            "mtl_name_collision_mode": self.mtl_name_collision_mode,
            "import_all_materials": self.import_all_materials,
            "import_textures_dir": self.import_textures_dir,
            "import_textures_mode": self.import_textures_mode,
            "tex_name_collision_mode": self.tex_name_collision_mode,
            "attr_import_mode": self.attr_import_mode,
            "create_world_material": self.create_world_material,
            "import_defined_only": self.import_defined_only,
        }

        if filters and dir_path.is_dir() and lib:
            self.thread = Thread(
                target=utils.create_usd_assets_from_path,
                args=(
                    files,
                    lib.path,
                    self.override,
                ),
                kwargs=dict(
                    shading=self.shading,
                    engine=self.engine,
                    max_time=self.max_time,
                    force_previews=self.force_previews,
                    angle=utils.resolve_angle(
                        self.camera_angle, self.flip_x, self.flip_y, self.flip_z
                    ),
                    catalog=catalog,
                    add_plane=prefs.add_ground_plane and not self.flip_z,
                    pack=self.pack,
                    make_collection=self.make_collection == "Collection",
                    op=self,
                    **args_dict,
                ),
            )
            self.total_files = len(files)
            self.total_imported = 0
            self.total_skipped = 0
            self.prog.pre_label = self.pre_label = (
                f"Importing (1/{self.total_files}): {files[0].name}"
            )
            self.prog.label = self.label = ""
            self.prog.post_label = self.post_label = (
                "Report| Imported: -- | Success: -- | Errors: 0"
            )
            self.cancelled = False
            self.thread.start()

        wm = context.window_manager
        self.timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        self.prog.start()
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if context.area:
            context.area.tag_redraw()
            self.prog.update_formated_time()

        if self.updated:
            self.updated = False
            self.prog.progress = self.progress
            self.prog.pre_label = self.pre_label
            self.prog.label = self.label
            self.prog.post_label = self.post_label
            # bpy.ops.asset.library_refresh()

        if event.type == "ESC":
            self.cancelled = True

        if self.cancelled and not self.prog.cancel:
            self.prog.label = "Cancelling..."
            self.prog.cancel = True

        if self.thread and not self.thread.is_alive():
            self.thread.join()
            bpy.app.timers.register(self.follow_up, first_interval=1)
            utils.update_asset_browser_areas()
            if self.cancelled:
                self.report(
                    {"WARNING"},
                    f"USD Assets Creation User Cancelled. {self.total_imported} of {self.total_files} Imported, {self.total_skipped} Errors",
                )
                return {"CANCELLED"}
            else:
                self.report(
                    {"INFO"},
                    f"USD Assets Creation Finished! {self.total_files} Chosen, {self.total_imported} Imported, {self.total_skipped} Not Imported due to Errors",
                )
                return {"FINISHED"}

        return {"RUNNING_MODAL"}

    def cancel(self, context):
        if hasattr(self, "_thread"):  # Ensure `execute` has run
            self.thread.join()
        self.prog.end()

    def follow_up(self):
        scene_sets: "scene.SH_Scene" = bpy.context.scene.superhive
        scene_sets.import_from_directory.end()


class SH_OT_FBX_Assets_From_Directory(
    bpy.types.Operator, utils.Create_Assets_From_FBX_Props_Base
):
    bl_idname = "bkeeper.create_assets_from_directory_fbx"
    bl_label = "Create Assets From FBX Files"
    bl_description = "Create Assets from Directory"
    bl_options = {"REGISTER", "UNDO"}

    updated = False
    cancelled = False

    progress = 0.0
    pre_label = ""
    label = ""
    post_label = ""

    total_files = 1
    total_imported = 0
    total_skipped = 0

    def draw(self, context):
        super().draw(self.layout)

    def invoke(self, context, event):
        self.thread = None

        self.progress = 0.0
        self.label = "Importing:"

        scene_sets: "scene.SH_Scene" = context.scene.superhive
        self.prog = scene_sets.import_from_directory

        self.load_settings(utils.get_prefs().fbx_import_settings)

        self.active_library_name = utils.get_active_library_name(
            context, area=context.area
        )

        context.window_manager.fileselect_add(self)

        return {"RUNNING_MODAL"}

    def execute(self, context):
        prefs = utils.get_prefs()
        dir_path = self.filepath
        filters = []
        filters.append("OBJECTS")
        filters.append("MESH")

        catalog = self.catalog if self.catalog != "NEW" else self.new_catalog_name
        lib = utils.from_active(context, area=context.area)

        files = []
        if self.files:
            dir_path = Path(self.filepath).parent
        else:
            dir_path = Path(self.filepath)

        if len(self.files) > 0 and all(
            a.name and Path(dir_path, a.name).exists() for a in self.files
        ):
            files = [Path(dir_path, a.name) for a in self.files]
        else:
            files = get_all_files_with_extension(dir_path, "fbx")

        if filters and dir_path.is_dir():
            self.thread = Thread(
                target=utils.create_fbx_assets_from_path,
                args=(
                    files,
                    lib.path,
                    self.override,
                ),
                kwargs=dict(
                    shading=self.shading,
                    engine=self.engine,
                    max_time=self.max_time,
                    force_previews=self.force_previews,
                    angle=utils.resolve_angle(
                        self.camera_angle, self.flip_x, self.flip_y, self.flip_z
                    ),
                    catalog=catalog,
                    add_plane=prefs.add_ground_plane and not self.flip_z,
                    use_auto_bone_orientation=self.use_auto_bone_orientation,
                    my_calculate_roll=self.my_calculate_roll,
                    my_bone_length=self.my_bone_length,
                    my_leaf_bone=self.my_leaf_bone,
                    use_fix_bone_poses=self.use_fix_bone_poses,
                    use_fix_attributes=self.use_fix_attributes,
                    use_only_deform_bones=self.use_only_deform_bones,
                    use_vertex_animation=self.use_vertex_animation,
                    use_animation=self.use_animation,
                    my_animation_offset=self.my_animation_offset,
                    use_animation_prefix=self.use_animation_prefix,
                    use_triangulate=self.use_triangulate,
                    my_import_normal=self.my_import_normal,
                    use_auto_smooth=self.use_auto_smooth,
                    my_angle=self.my_angle,
                    my_shade_mode=self.my_shade_mode,
                    my_scale=self.my_scale,
                    use_optimize_for_blender=self.use_optimize_for_blender,
                    use_reset_mesh_origin=self.use_reset_mesh_origin,
                    use_edge_crease=self.use_edge_crease,
                    my_edge_crease_scale=self.my_edge_crease_scale,
                    my_edge_smoothing=self.my_edge_smoothing,
                    use_import_materials=self.use_import_materials,
                    use_rename_by_filename=self.use_rename_by_filename,
                    my_rotation_mode=self.my_rotation_mode,
                    use_manual_orientation=self.use_manual_orientation,
                    global_scale=self.global_scale,
                    bake_space_transform=self.bake_space_transform,
                    use_custom_normals=self.use_custom_normals,
                    colors_type=self.colors_type,
                    use_image_search=self.use_image_search,
                    use_alpha_decals=self.use_alpha_decals,
                    decal_offset=self.decal_offset,
                    use_anim=self.use_anim,
                    anim_offset=self.anim_offset,
                    use_subsurf=self.use_subsurf,
                    use_custom_props=self.use_custom_props,
                    use_custom_props_enum_as_string=self.use_custom_props_enum_as_string,
                    ignore_leaf_bones=self.ignore_leaf_bones,
                    force_connect_children=self.force_connect_children,
                    automatic_bone_orientation=self.automatic_bone_orientation,
                    primary_bone_axis=self.primary_bone_axis,
                    secondary_bone_axis=self.secondary_bone_axis,
                    use_prepost_rot=self.use_prepost_rot,
                    axis_forward=self.axis_forward,
                    axis_up=self.axis_up,
                    # importer=prefs.fbx_importer,
                    importer="Blender",
                    pack=self.pack,
                    single_file=self.single_file,
                    make_collection=self.make_collection == "Collection",
                    op=self,
                ),
            )
            self.total_files = len(files)
            self.total_imported = 0
            self.total_skipped = 0
            self.prog.pre_label = self.pre_label = (
                f"Importing (1/{self.total_files}): {files[0].name}"
            )
            self.prog.label = self.label = ""
            self.prog.post_label = self.post_label = (
                "Report| Imported: -- | Success: -- | Errors: 0"
            )
            self.cancelled = False
            self.thread.start()

        wm = context.window_manager
        self.timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        self.prog.start()
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if context.area:
            context.area.tag_redraw()
            self.prog.update_formated_time()

        if self.updated:
            self.updated = False
            self.prog.progress = self.progress
            self.prog.pre_label = self.pre_label
            self.prog.label = self.label
            self.prog.post_label = self.post_label
            # bpy.ops.asset.library_refresh()

        if event.type == "ESC":
            self.cancelled = True

        if self.cancelled and not self.prog.cancel:
            self.prog.label = "Cancelling..."
            self.prog.cancel = True

        if self.thread and not self.thread.is_alive():
            self.thread.join()
            bpy.app.timers.register(self.follow_up, first_interval=1)
            utils.update_asset_browser_areas()
            if self.cancelled:
                self.report(
                    {"WARNING"},
                    f"FBX Assets Creation User Cancelled. {self.total_imported} of {self.total_files} Imported, {self.total_skipped} Errors",
                )
                return {"CANCELLED"}
            else:
                self.report(
                    {"INFO"},
                    f"FBX Assets Creation Finished! {self.total_files} Chosen, {self.total_imported} Imported, {self.total_skipped} Not Imported due to Errors",
                )
                return {"FINISHED"}

        return {"RUNNING_MODAL"}

    def cancel(self, context):
        if hasattr(self, "_thread"):  # Ensure `execute` has run
            self.thread.join()
        self.prog.end()

    def follow_up(self):
        scene_sets: "scene.SH_Scene" = bpy.context.scene.superhive
        scene_sets.import_from_directory.end()


class SH_OT_OBJ_Assets_From_Directory(
    utils.Create_Assets_From_OBJ_Props_Base, bpy.types.Operator
):
    bl_idname = "bkeeper.create_assets_from_directory_obj"
    bl_label = "Create Assets From OBJ Files"
    bl_description = "Create Assets from Directory"
    bl_options = {"REGISTER", "UNDO"}

    updated = False
    cancelled = False

    progress = 0.0
    pre_label = ""
    label = ""
    post_label = ""

    total_files = 1
    total_imported = 0
    total_skipped = 0

    def draw(self, context):
        super().draw(self.layout)

    def invoke(self, context, event):
        self.thread = None

        self.progress = 0.0
        self.label = "Importing:"

        scene_sets: "scene.SH_Scene" = context.scene.superhive
        self.prog = scene_sets.import_from_directory

        self.load_settings(utils.get_prefs().obj_import_settings)

        self.active_library_name = utils.get_active_library_name(
            context, area=context.area
        )

        context.window_manager.fileselect_add(self)

        return {"RUNNING_MODAL"}

    def execute(self, context):
        prefs = utils.get_prefs()
        dir_path = self.filepath
        filters = []
        filters.append("OBJECTS")
        filters.append("MESH")

        catalog = self.catalog if self.catalog != "NEW" else self.new_catalog_name
        lib = utils.from_active(context, area=context.area)

        files = []
        dir_path = self.filepath
        if self.files:
            dir_path = Path(self.filepath).parent
        else:
            dir_path = Path(self.filepath)

        if len(self.files) > 0 and all(
            a.name and Path(dir_path, a.name).exists() for a in self.files
        ):
            files = [Path(dir_path, a.name) for a in self.files]
        else:
            files = get_all_files_with_extension(dir_path, "obj")

        if filters and dir_path.is_dir() and lib:
            self.thread = Thread(
                target=utils.create_obj_assets_from_path,
                args=(
                    files,
                    lib.path,
                    self.override,
                ),
                kwargs=dict(
                    shading=self.shading,
                    engine=self.engine,
                    max_time=self.max_time,
                    force_previews=self.force_previews,
                    angle=utils.resolve_angle(
                        self.camera_angle, self.flip_x, self.flip_y, self.flip_z
                    ),
                    catalog=catalog,
                    add_plane=prefs.add_ground_plane and not self.flip_z,
                    use_auto_bone_orientation=self.use_auto_bone_orientation,
                    my_calculate_roll=self.my_calculate_roll,
                    my_bone_length=self.my_bone_length,
                    my_leaf_bone=self.my_leaf_bone,
                    use_fix_bone_poses=self.use_fix_bone_poses,
                    use_fix_attributes=self.use_fix_attributes,
                    use_only_deform_bones=self.use_only_deform_bones,
                    use_vertex_animation=self.use_vertex_animation,
                    use_animation=self.use_animation,
                    my_animation_offset=self.my_animation_offset,
                    use_animation_prefix=self.use_animation_prefix,
                    use_triangulate=self.use_triangulate,
                    my_import_normal=self.my_import_normal,
                    use_auto_smooth=self.use_auto_smooth,
                    my_angle=self.my_angle,
                    my_shade_mode=self.my_shade_mode,
                    my_scale=self.my_scale,
                    use_optimize_for_blender=self.use_optimize_for_blender,
                    use_reset_mesh_origin=self.use_reset_mesh_origin,
                    use_edge_crease=self.use_edge_crease,
                    my_edge_crease_scale=self.my_edge_crease_scale,
                    my_edge_smoothing=self.my_edge_smoothing,
                    use_import_materials=self.use_import_materials,
                    use_rename_by_filename=self.use_rename_by_filename,
                    my_rotation_mode=self.my_rotation_mode,
                    use_edges=self.use_edges,
                    use_smooth_groups=self.use_smooth_groups,
                    use_split_objects=self.use_split_objects,
                    use_split_groups=self.use_split_groups,
                    use_groups_as_vgroups=self.use_groups_as_vgroups,
                    use_image_search=self.use_image_search,
                    split_mode=self.split_mode,
                    global_clamp_size=self.global_clamp_size,
                    clamp_size=self.clamp_size,
                    global_scale=self.global_scale,
                    import_vertex_groups=self.import_vertex_groups,
                    validate_meshes=self.validate_meshes,
                    collection_separator=self.collection_separator,
                    axis_forward=self.axis_forward,
                    axis_up=self.axis_up,
                    # importer=prefs.fbx_importer,
                    pack=self.pack,
                    single_file=self.single_file,
                    make_collection=self.make_collection == "Collection",
                    op=self,
                ),
            )
            self.total_files = len(files)
            self.total_imported = 0
            self.total_skipped = 0
            self.prog.pre_label = self.pre_label = (
                f"Importing (1/{self.total_files}): {files[0].name}"
            )
            self.prog.label = self.label = ""
            self.prog.post_label = self.post_label = (
                "Report| Imported: -- | Success: -- | Errors: 0"
            )
            self.cancelled = False
            self.thread.start()

        wm = context.window_manager
        self.timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        self.prog.start()
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if context.area:
            context.area.tag_redraw()
            self.prog.update_formated_time()

        if self.updated:
            self.updated = False
            self.prog.progress = self.progress
            self.prog.pre_label = self.pre_label
            self.prog.label = self.label
            self.prog.post_label = self.post_label
            # bpy.ops.asset.library_refresh()

        if event.type == "ESC":
            self.cancelled = True

        if self.cancelled and not self.prog.cancel:
            self.prog.label = "Cancelling..."
            self.prog.cancel = True

        if self.thread and not self.thread.is_alive():
            self.thread.join()
            bpy.app.timers.register(self.follow_up, first_interval=1)
            utils.update_asset_browser_areas()
            if self.cancelled:
                self.report(
                    {"WARNING"},
                    f"OBJ Assets Creation User Cancelled. {self.total_imported} of {self.total_files} Imported, {self.total_skipped} Errors",
                )
                return {"CANCELLED"}
            else:
                self.report(
                    {"INFO"},
                    f"OBJ Assets Creation Finished! {self.total_files} Chosen, {self.total_imported} Imported, {self.total_skipped} Not Imported due to Errors",
                )
                return {"FINISHED"}

        return {"RUNNING_MODAL"}

    def cancel(self, context):
        if hasattr(self, "_thread"):  # Ensure `execute` has run
            self.thread.join()
        self.prog.end()

    def follow_up(self):
        scene_sets: "scene.SH_Scene" = bpy.context.scene.superhive
        scene_sets.import_from_directory.end()


classes = (
    Catalog,
    Catalogs,
    SH_OT_ImportFromDirectory,
    SH_OT_OBJ_Assets_From_Directory,
    SH_OT_FBX_Assets_From_Directory,
    SH_OT_USD_Assets_From_Directory,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
