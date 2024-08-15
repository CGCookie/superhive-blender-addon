import re
from time import time

import bpy
import bpy.utils
from bpy.app.translations import contexts as i18n_contexts
from bpy.props import (
    BoolProperty,
    BoolVectorProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import AssetRepresentation, Context, PropertyGroup, UILayout

from .. import hive_mind, utils
from ..icons import sh_icons


class RenderThumbnailProps:
    shading: EnumProperty(
        name="Thumbnail Shading",
        items=(
            ("Material", "Material", "Material"),
            ("Eevee", "Eevee", "Eevee"),
            ("Cycles", "Cycles", "Cycles"),
        ),
        default="Cycles",
    )

    camera_angle: EnumProperty(
        items=(
            ("XZ", "X-Axis", "X-Axis"),
            ("YZ", "Y-Axis", "Y-Axis"),
            ("XYZ", "Isometric", "Equal distance on all axis"),
        )
    )

    flip_z: BoolProperty(name="Flip Z", default=False)

    flip_x: BoolProperty(name="Flip X", default=False)

    flip_y: BoolProperty(name="Flip Y", default=False)

    thumb_res: IntProperty(
        default=256, min=128, max=1024, subtype="PIXEL", name="Resolution"
    )

    camera_height: FloatProperty(
        default=1.0,
        min=0,
        max=2,
        soft_max=1,
        subtype="PERCENTAGE",
        name="Camera Height",
    )

    camera_zoom: FloatProperty(default=1, min=0.5, max=5, soft_max=2, name="Zoom")

    world_strength: FloatProperty(
        name="World Lighting Strength",
        default=1,
    )

    add_ground_plane: BoolProperty(
        name="Add Ground Plane",
        description="Add ground plane for thumbnails",
        default=False,
    )

    def _get_scene_lighting_items(self, context):
        return (
            ("Studio Soft", "Studio Soft", "", sh_icons.studio_soft_icon.icon_id, 0),
            ("Studio Harsh", "Studio Harsh", "", sh_icons.studio_harsh_icon.icon_id, 1),
            ("Outdoor Soft", "Outdoor Soft", "", sh_icons.outdoor_soft_icon.icon_id, 2),
            (
                "Outdoor Harsh",
                "Outdoor Harsh",
                "",
                sh_icons.outdoor_harsh_icon.icon_id,
                3,
            ),
        )

    scene_lighting: EnumProperty(
        name="Lighting Setup",
        description="The lighting setup to use for the thumbnail",
        items=_get_scene_lighting_items,
    )

    padding: FloatProperty(
        name="Padding",
        description="Padding around the object in the thumbnail.",
        default=0.0,
        min=0.0,
        max=1,
    )

    rotate_world: BoolProperty(
        name="Rotate World",
        description="Rotate the world to match the camera angle so the lighting aligns with the camera view",
        default=True,
    )

    debug_scene: BoolProperty(
        name="Debug Scene",
        description="Setup the blend file like normal but don't render the thumbnail and keep the scene open for debugging",
        default=False,
    )

    def draw_thumbnail_props(self, layout: UILayout) -> None:
        layout.row().prop(self, "shading", expand=True)
        layout.prop(self, "world_strength")
        layout.row().prop(self, "camera_angle", expand=True)
        row = layout.row(align=True)
        # layout.prop(self,'camera_height')
        # layout.prop(self,'camera_zoom')
        row.prop(self, "flip_x", toggle=True)
        row.prop(self, "flip_y", toggle=True)
        row.prop(self, "flip_z", toggle=True)

        if not self.flip_z:
            row = layout.row(align=True)
            row.prop(
                self,
                "add_ground_plane",
                toggle=True,
                icon="CHECKBOX_HLT" if self.add_ground_plane else "CHECKBOX_DEHLT",
            )

        layout.prop(self, "padding", text="Extra Padding", slider=True)
        layout.prop(
            self,
            "rotate_world",
            icon="CHECKBOX_HLT" if self.rotate_world else "CHECKBOX_DEHLT",
        )

        # layout.prop(self,'thumb_res')
        if self.shading != "Material":
            layout.template_icon_view(self, "scene_lighting", show_labels=True)
            row = layout.row()
            row.alignment = "CENTER"
            row.label(text=self.scene_lighting)

        if utils.get_prefs().display_extras:
            layout.prop(self, "debug_scene")

    def reset_thumbnail_settings(self) -> None:
        prefs = utils.get_prefs()
        self.shading = prefs.shading
        self.camera_angle = prefs.camera_angle
        self.flip_x = prefs.flip_x
        self.flip_y = prefs.flip_y
        self.flip_z = prefs.flip_z
        self.thumb_res = prefs.thumb_res
        self.camera_height = prefs.camera_height
        self.camera_zoom = prefs.camera_zoom
        self.world_strength = prefs.world_strength
        self.scene_lighting = prefs.scene_lighting
        self.padding = prefs.padding
        self.rotate_world = prefs.rotate_world
        self.add_ground_plane = prefs.add_ground_plane
        self.debug_scene = prefs.debug_scene


class BatchUpdateAction(PropertyGroup):
    metadata_item: StringProperty()

    update_type: EnumProperty(
        name="Update Type",
        items=[
            ("OVERWRITE", "Overwrite", "Overwrite the existing metadata"),
            ("ADD", "Add", "Add to the existing asset metadata"),
            ("REPLACE", "Replace", "Match and replace the existing metadata"),
            ("CASE", "Case", "Change the case of the metadata"),
        ],
    )
    value: StringProperty(
        name="Value",
    )
    replace_with: StringProperty(
        name="Replace With",
        description="Replace with this text",
    )
    add_type: EnumProperty(
        name="Prefix/Suffix",
        description="Choose whether to add text to the beginning or end",
        items=[
            ("PREFIX", "Prefix", "Add text to the beginning"),
            ("SUFFIX", "Suffix", "Add text to the end"),
        ],
    )
    case_type: EnumProperty(
        name="Case Type",
        items=[
            ("UPPER", "Upper", "Convert to uppercase"),
            ("LOWER", "Lower", "Convert to lowercase"),
            ("TITLE", "Title", "Convert to title case"),
            ("CAPITALIZE", "Capitalize", "Capitalize the first letter"),
            ("SWAP", "Swap", "Swap the case"),
        ],
    )

    match_case_find: BoolProperty(
        name="Match Case",
        description="Match the case of the original text when finding",
    )
    use_regex_find: BoolProperty(
        name="Use Regex",
        description="Use regular expressions when finding",
    )
    # match_case_replace: BoolProperty(
    #     name="Match Case",
    #     description="Match the case of the original text when replacing",
    # )
    use_regex_replace: BoolProperty(
        name="Use Regex",
        description="Use regular expressions when replacing",
    )

    # use () to capture groups and \1, \2, etc. to reference them

    action_add: BoolProperty(
        name="Add",
        description="Add a new action",
        translation_context=i18n_contexts.operator_default,
    )
    action_remove: BoolProperty(
        name="Remove",
        description="Remove a this action",
        translation_context=i18n_contexts.operator_default,
    )

    def draw(self, layout: UILayout, index: int, use_ops: bool = False):
        row = layout.row()
        col_l = row.column()
        col_l.prop(self, "update_type")

        match self.update_type:
            case "OVERWRITE":
                self.draw_overwrite(col_l)
            case "ADD":
                self.draw_add(col_l)
            case "REPLACE":
                self.draw_replace(col_l)
            case "CASE":
                self.draw_case(col_l)
            case _:
                raise ValueError(f"Invalid update type: {self.update_type}")

        col_r = row.column()
        row = col_r.row(align=True)
        row.scale_x = 1.2
        if use_ops:
            op = row.operator("bkeeper.remove_update_action", text="", icon="REMOVE")
            op.metadata_item = self.metadata_item
            op.action_index = index
            op = row.operator("bkeeper.add_update_action", text="", icon="ADD")
            op.metadata_item = self.metadata_item
            op.action_index = index
        else:
            row.prop(self, "action_remove", text="", icon="REMOVE", toggle=1)
            row.prop(self, "action_add", text="", icon="ADD", toggle=1)

    def draw_overwrite(self, layout: UILayout):
        layout.prop(self, "value")

    def draw_add(self, layout: UILayout):
        layout.prop(self, "add_type")
        layout.prop(self, "value")

    def draw_replace(self, layout: UILayout):
        row = layout.row(align=True)
        re_error_src = None
        try:
            re.compile(self.value)
        except BaseException as ex:
            re_error_src = str(ex)
            row.alert = True
        row.alert = False
        row.prop(self, "value")
        row.prop(self, "match_case_find", icon="SYNTAX_OFF", text="")
        row.prop(self, "use_regex_find", icon="SORTBYEXT", text="")

        if re_error_src is not None:
            row = layout.split(factor=0.25)
            row.label(text="")
            row.alert = True
            row.label(text=re_error_src)

        row = layout.row(align=True)
        re_error_dst = None
        if self.use_regex_find and self.use_regex_replace and re_error_src is None:
            try:
                re.sub(self.value, self.replace_with, "")
            except BaseException as ex:
                re_error_dst = str(ex)
                row.alert = True
        row.prop(self, "replace_with")
        r = row.row(align=True)
        r.active = self.use_regex_find
        r.prop(self, "use_regex_replace", icon="SORTBYEXT", text="")

        if re_error_dst is not None:
            row = layout.split(factor=0.25)
            row.label(text="")
            row.alert = True
            row.label(text=re_error_dst)

    def draw_case(self, layout: UILayout):
        layout.prop(self, "case_type")

    def process_text(self, text: str) -> str:
        if not self.value and self.update_type != "CASE":
            return text
        match self.update_type:
            case "OVERWRITE":
                return self.value
            case "ADD":
                return (
                    text + self.value
                    if self.add_type == "SUFFIX"
                    else self.value + text
                )
            case "REPLACE":
                if self.use_regex_find:
                    replace_src = self.value
                    if self.use_regex_replace:
                        replace_dst = self.replace_with
                    else:
                        replace_dst = self.replace_with.replace("\\", "\\\\")
                else:
                    replace_src = re.escape(self.value)
                    replace_dst = self.replace_with.replace("\\", "\\\\")
                return re.sub(
                    replace_src,
                    replace_dst,
                    text,
                    flags=(0 if self.match_case_find else re.IGNORECASE),
                )
            case "CASE":
                match self.case_type:
                    case "UPPER":
                        return text.upper()
                    case "LOWER":
                        return text.lower()
                    case "TITLE":
                        return text.title()
                    case "CAPITALIZE":
                        return text.capitalize()
                    case "SWAP":
                        return text.swapcase()
                    case _:
                        raise ValueError(f"Invalid case type: {self.case_type}")


class BatchItemWithActions(PropertyGroup):
    batch_items: CollectionProperty(
        name="Batch Items",
        type=BatchUpdateAction,
    )

    def check(self):
        changed = False
        action: BatchUpdateAction
        for i, action in enumerate(self.batch_items):
            if action.action_add:
                action.action_add = False
                self.add_action(i)
                changed = True
                break
            if action.action_remove:
                action.action_remove = False
                self.remove_action(i)
                changed = True
                break

        # if (
        #         (self._data_source_prev != self.data_source) or
        #         (self._data_type_prev != self.data_type)
        # ):
        #     self._data_update(context)
        #     changed = True

        return changed

    def add_action(self, index: int):
        item: BatchUpdateAction = self.batch_items.add()
        item.metadata_item = self.name
        if index + 2 != len(self.batch_items):
            self.batch_items.move(len(self.batch_items) - 1, index + 1)

    def remove_action(self, index: int):
        if len(self.batch_items) > 1:
            self.batch_items.remove(index)

    def draw(self, layout: UILayout, use_ops: bool = False):
        action: BatchUpdateAction
        for i, action in enumerate(self.batch_items):
            action.draw(layout.box(), i, use_ops)

    def process_text(self, text: str) -> str:
        action: BatchUpdateAction
        for action in self.batch_items:
            text = action.process_text(text)
        return text


class BatchMetadataUpdate(PropertyGroup, RenderThumbnailProps):
    metadata_type: EnumProperty(
        name="Metadata Type",
        description="Choose metadata settings to display",
        items=[
            (
                "name",
                "Name",
                "Display the settings for updating the name of the asset(s)",
            ),
            (
                "description",
                "Description",
                "Display the settings for updating the description of the asset(s)",
            ),
            (
                "author",
                "Author",
                "Display the settings for updating the author of the asset(s)",
            ),
            (
                "license",
                "License",
                "Display the settings for updating the license of the asset(s)",
            ),
            (
                "catalog",
                "Catalog",
                "Display the settings for updating the catalog of the asset(s)",
            ),
            (
                "copyright",
                "Copyright",
                "Display the settings for updating the copyright of the asset(s)",
            ),
            (
                "tags",
                "Tags",
                "Display the settings for updating the tags of the asset(s)",
            ),
        ],
    )

    metadata_items: CollectionProperty(
        name="Metadata Items",
        type=BatchItemWithActions,
    )

    def _get_ignore_licenses(self, context):
        self.metadata_items: (
            bpy.types.CollectionProperty
            | list[BatchItemWithActions]
            | dict[str, BatchItemWithActions]
        )
        return [
            ("IGNORE", "Ignore", "Ignore the license"),
        ] + hive_mind.get_licenses()

    license: EnumProperty(
        name="License",
        description="The license to apply to the asset",
        items=_get_ignore_licenses,
        default=1,
    )

    license_custom: StringProperty(
        name="Custom License",
        description="The custom license to apply to the asset",
    )

    def _get_ignore_licenses(self, context):
        return [
            ("IGNORE", "Ignore", "Ignore the license"),
        ] + hive_mind.get_categories()

    catalog: EnumProperty(
        name="Catalog",
        description="The catalog to apply to the asset",
        items=_get_ignore_licenses,
    )

    catalog_custom: StringProperty(
        name="Custom Catalog",
        description="The custom catalog to apply to the asset",
    )

    # TAGS #
    tags_update_type: EnumProperty(
        name="Update Type",
        items=[
            ("ADD", "Add", "Add tags to the existing tags"),
            ("OVERWRITE", "Overwrite", "Overwrite the existing tags"),
            ("REMOVE", "Remove", "Match and remove existing tags"),
        ],
    )
    # Don't set overwrite as default otherwise all tags
    # will be removed by default behavior
    tags: BoolVectorProperty(
        name="Tags",
        description="The tags to add to the asset",
        size=len(hive_mind.get_tags()),
    )

    render_thumbnails: BoolProperty(
        name="Render Thumbnails",
        description="Render thumbnails for the assets when updating",
    )

    reset_settings: BoolProperty(
        name="Reset Settings",
        description="Reset the settings after updating the assets",
        default=True,
    )

    def process_text(self, metadata_item: str, text: str) -> str:
        item = self.metadata_items.get(metadata_item)
        return item.process_text(text)

    def draw(self, context: Context, layout: UILayout, use_ops: bool = False):
        box = layout.box()
        header, body = box.panel("asset_update_render_thumbnail")
        header.scale_y = 1.25
        r = header.row()
        r.alignment = "CENTER"
        r.label(text="Render Thumbnails", icon="FILE_IMAGE")

        if body:
            col = body.column()
            col.enabled = self.render_thumbnails
            self.draw_thumbnail_props(col)

        layout.separator()

        box = layout.box()
        header, body = box.panel("asset_update_metadata")
        header.scale_y = 1.25
        r = header.row()
        r.alignment = "CENTER"
        r.label(text="Metadata", icon="TEXT")

        if body:
            self.draw_metadata_settings(context, box, use_ops)

    def draw_metadata_settings(self, context: Context, layout: UILayout, use_ops: bool):
        row = layout.row()
        row.scale_y = 1.5
        row.prop(self, "metadata_type", expand=True)

        match self.metadata_type:
            case "license":
                col = layout.column(align=True)
                col.prop(self, "license")
                if self.license == "CUSTOM":
                    col.prop(self, "license_custom")
            case "catalog":
                col = layout.column(align=True)
                col.prop(self, "catalog")
                if self.catalog == "CUSTOM":
                    col.prop(self, "catalog_custom")
            case "tags":
                layout.prop(self, "tags_update_type")
                grid = layout.grid_flow(columns=3, even_columns=True)
                for i, tag in enumerate(hive_mind.get_tags()):
                    grid.prop(self, "tags", index=i, text=tag[1], expand=True)
            case _:
                meta_data_item: BatchItemWithActions = self.metadata_items.get(
                    self.metadata_type
                )
                meta_data_item.draw(layout, use_ops=use_ops)

                box = layout.box()
                row = box.row()
                row.alignment = "CENTER"
                row.label(text="Preview")
                col = box.column(align=True)
                asset: AssetRepresentation
                for asset in context.selected_assets[:5]:
                    col.label(
                        text=asset.name
                        + ": "
                        + meta_data_item.process_text(
                            getattr(
                                (
                                    asset
                                    if self.metadata_type == "name"
                                    else asset.metadata
                                ),
                                self.metadata_type,
                            )
                        )
                    )
                if len(context.selected_assets) > 5:
                    col.label(text="...")

    def process_tags(self, asset: utils.Asset):
        selected_tags = [
            tag_id
            for i, (tag_id, _tag_name, _tag_desc) in enumerate(hive_mind.get_tags())
            if self.tags[i]
        ]
        if self.tags_update_type == "OVERWRITE":
            return sorted(selected_tags)
        elif self.tags_update_type == "ADD":
            return sorted(list(set(asset.bpy_tags + selected_tags)))
        elif self.tags_update_type == "REMOVE":  # REMOVE
            return sorted(list(set(asset.bpy_tags) - set(selected_tags)))
        return asset.bpy_tags

    def process_asset_metadata(
        self,
        asset: utils.Asset,
        bpy_asset: AssetRepresentation,
        lib: utils.AssetLibrary,
    ) -> None:
        """
        Process the metadata according to the set actions.

        Parameters:
            asset (utils.Asset): The asset to process.

        Returns:
            None
        """
        asset.new_name = self.process_text("name", asset.name)
        asset.description = self.process_text("description", asset.description)
        asset.author = self.process_text("author", asset.author)
        asset.copyright = self.process_text("copyright", asset.copyright)
        if self.license == "CUSTOM":
            asset.license = self.license_custom
        elif self.license != "IGNORE":
            asset.license = self.license
        if self.catalog == "CUSTOM":
            # Create catalog_id if it doesn't exist
            catalog_simple_name: str = self.catalog_custom
            if catalog_simple_name:
                cat = lib.catalogs.get_catalog_by_path(catalog_simple_name)
                if cat:
                    asset.catalog_id = cat.id
                else:
                    if "/" not in catalog_simple_name:
                        cat = lib.catalogs.get_catalog_by_name(catalog_simple_name)
                        if cat:
                            asset.catalog_id = cat.id
                    if not cat:
                        with lib.open_catalogs_file() as cat_file:
                            cat_file: "utils.CatalogsFile"
                            if "/" in catalog_simple_name:
                                name = catalog_simple_name.split("/")[-1]
                                cat = cat_file.add_catalog(
                                    name, path=catalog_simple_name
                                )
                            else:
                                cat = cat_file.add_catalog(catalog_simple_name)
                            asset.catalog_id = cat.id
        elif self.catalog != "IGNORE":
            asset.catalog_id = self.catalog
        asset.tags = self.process_tags(asset)

    def reset(self):
        self.metadata_items.clear()
        for name in ("name", "description", "author", "copyright"):
            item: BatchItemWithActions = self.metadata_items.add()
            item.name = name
            item.add_action(0)

        for i in range(len(hive_mind.get_tags())):
            self.tags[i] = False

        self.license = "IGNORE"
        self.catalog = "IGNORE"

        self.metadata_type = "name"
        self.tags_update_type = "ADD"

        self.render_thumbnails = False

        self.reset_thumbnail_settings()


class ProgressBarBase:
    progress: FloatProperty(subtype="PERCENTAGE", min=0, max=100)
    show: BoolProperty()
    label: StringProperty()
    """Label for the progress bar. This is the text that will be displayed on the progress bar."""

    formated_time: StringProperty()
    start_time: StringProperty()

    cancel: BoolProperty(
        name="Cancel",
        description="Cancel the current process",
        default=False,
    )
    is_complete: BoolProperty()

    def start(self) -> None:
        self.reset()
        self.show = True
        self.update_start_time()

    def reset(self) -> None:
        self.progress = 0
        self.cancel = False
        self.is_complete = False

    def end(self) -> None:
        self.is_complete = True
        self.show = False

    def update_start_time(self) -> None:
        self.start_time = str(time())

    def update_formated_time(self) -> None:
        """Converts the time taken to import the pack to a string and returns it. The string will be formatted to two decimal places."""
        if not self.start_time:
            return "0s"
        hrs = 0
        mins = 0
        secs = 0
        timer = time() - float(self.start_time)
        # Hours
        if timer > 3600:
            hrs = timer // 3600
        # Minutes
        elif timer > 60:
            mins = (timer - hrs * 3600) // 60
        # Seconds
        secs = timer - hrs * 3600 - mins * 60

        if hrs:
            self.formated_time = f"{hrs:.0f}h, {mins:.0f}m, {secs:.2f}s"
        elif mins:
            self.formated_time = f"{mins:.0f}m, {secs:.2f}s"
        else:
            self.formated_time = f"{secs:.2f}s"

    def draw(self, layout: UILayout, draw_time: bool = False) -> None:
        row = layout.row(align=True)
        row.progress(
            text=self.label or f"{round(self.progress*100, 2)}%", factor=self.progress
        )

        if draw_time:
            row.label(text=self.formated_time)


class ProgressBar(PropertyGroup, ProgressBarBase): ...


class ProgressBarForMulti(PropertyGroup, ProgressBarBase):
    is_complete: BoolProperty(default=False)


class MultiProgressBarBase:
    show: BoolProperty()
    progress_bars: CollectionProperty(type=ProgressBarForMulti)

    total_progress: PointerProperty(type=ProgressBar)

    active_bar_index: IntProperty(default=0)

    @property
    def active_bar(self) -> ProgressBarForMulti:
        if self.active_bar_index < len(self.progress_bars):
            return self.progress_bars[self.active_bar_index]

    def new_progress_bar(self, name: str) -> ProgressBarForMulti:
        self.progress_bars: (
            bpy.types.CollectionProperty
            | list[ProgressBarForMulti]
            | dict[str, ProgressBarForMulti]
        )
        self.total_progress: ProgressBar
        pb: ProgressBarForMulti = self.progress_bars.add()
        pb.name = name
        return pb

    def clear(self) -> None:
        self.progress_bars.clear()

    def start(self) -> None:
        self.show = True
        self.active_bar_index = 0
        for pb in self.progress_bars:
            pb.is_complete = False

    def start_next_active(self) -> ProgressBarForMulti:
        self.active_bar.is_complete = True

        self.active_bar_index += 1
        if not self.active_bar:
            return

        self.active_bar.start()

        return self.active_bar

    def end(self) -> None:
        self.show = False


class ProgressUpdate_Asset(PropertyGroup, MultiProgressBarBase):
    @property
    def metadata_bar(self) -> ProgressBar:
        return self.progress_bars.get("Metadata Update")

    @property
    def icon_bar(self) -> ProgressBar:
        return self.progress_bars.get("Icon Rendering")

    def setup(self):
        self.progress_bars.clear()

        self.new_progress_bar("Metadata Update")
        self.new_progress_bar("Icon Rendering")

    def draw(self, layout: UILayout) -> None:
        self.total_progress.draw(layout)
        for pb in self.progress_bars:
            pb.draw(layout)


class IconRenderingProgressBars(PropertyGroup):
    setup_bar: PointerProperty(type=ProgressBar)
    render_bar: PointerProperty(type=ProgressBar)
    apply_bar: PointerProperty(type=ProgressBar)

    def reset(self) -> None:
        self.setup_bar.reset()
        self.render_bar.reset()
        self.apply_bar.reset()

    def draw(self, layout: UILayout) -> None:
        self.setup_bar: ProgressBar
        self.render_bar: ProgressBar
        self.apply_bar: ProgressBar

        col = layout.column()
        col.active = self.setup_bar.progress == 1
        row = col.row()
        r = row.row()
        r.alignment = "LEFT"
        r.label(text="Setup Scenes:")
        self.setup_bar.draw(row, draw_time=True)

        col = layout.column()
        col.active = self.setup_bar.progress == 1
        row = col.row()
        r = row.row()
        r.alignment = "LEFT"
        r.label(text="Rendering:")
        self.render_bar.draw(row, draw_time=True)

        col = layout.column()
        col.active = self.setup_bar.progress == 1
        row = col.row()
        r = row.row()
        r.alignment = "LEFT"
        r.label(text="Applying Thumbnails:")
        self.apply_bar.draw(row, draw_time=True)


class MultiProgressBarUpdate_Assets(PropertyGroup):
    show: BoolProperty()
    metadata_bar: PointerProperty(type=ProgressBar)
    metadata_label: StringProperty(default="Metadata Update")
    icon_rendering: PointerProperty(type=IconRenderingProgressBars)

    draw_icon_rendering: BoolProperty()

    cancel: BoolProperty()

    def start(self) -> None:
        self.reset()
        self.show = True

    def end(self) -> None:
        self.show = False
        self.reset()

    def reset(self) -> None:
        self.metadata_bar.reset()
        self.icon_rendering.reset()

    def draw(self, layout: UILayout) -> None:
        self.metadata_bar: ProgressBar
        self.icon_rendering: IconRenderingProgressBars

        row = layout.row()
        r = row.row()
        r.alignment = "LEFT"
        r.label(text=f"{self.metadata_label}:")
        self.metadata_bar.draw(row, draw_time=True)

        if self.draw_icon_rendering:
            row = layout.row()
            row.label(text="Icon Rendering:")

            split = layout.split(factor=0.25)
            split.separator()
            self.icon_rendering.draw(split.column())


class MovingFilesProgressBar(PropertyGroup):
    main: PointerProperty(type=ProgressBar)
    file: PointerProperty(type=ProgressBar)
    sub: PointerProperty(type=ProgressBar)

    sub_label: StringProperty()
    file_label: StringProperty()

    show_sub: BoolProperty()

    def reset(self) -> None:
        self.main: ProgressBar
        self.file: ProgressBar
        self.sub: ProgressBar
        self.main.reset()
        self.file.reset()
        self.sub.reset()

    def update_formated_time(self) -> None:
        self.main.update_formated_time()
        self.file.update_formated_time()
        if self.show_sub:
            self.sub.update_formated_time()

    def draw(self, layout: UILayout, draw_time=False) -> None:
        split = layout.split(factor=0.05)
        split.separator()
        self.main.draw(split, draw_time=True)

        split = layout.split(factor=0.1)
        split.separator()
        r = split.row()
        r.label(text=self.file_label)
        split = layout.split(factor=0.15)
        split.separator()
        self.file.draw(split, draw_time=True)

        if self.show_sub:
            row = layout.row()
            row.label(text=self.sub_label)
            self.sub.draw(row, draw_time=True)


class MultiProgressBarExportLibrary(PropertyGroup):
    show: BoolProperty()
    movingfiles_bar: PointerProperty(type=MovingFilesProgressBar)
    zipping_bar: PointerProperty(type=ProgressBar)
    upload_bar: PointerProperty(type=ProgressBar)

    cancel: BoolProperty()

    def start(self) -> None:
        self.reset()
        self.show = True

    def end(self) -> None:
        self.show = False
        self.reset()

    def reset(self) -> None:
        self.movingfiles_bar.reset()
        self.zipping_bar.reset()
        self.upload_bar.reset()

    def draw(self, layout: UILayout) -> None:
        self.movingfiles_bar: MovingFilesProgressBar
        self.zipping_bar: ProgressBar
        self.upload_bar: ProgressBar

        layout.label(text="Exporting Library:")
        split = layout.split(factor=0.05)
        split.separator()
        col = split.column()

        r = col.row()
        r.alignment = "LEFT"
        r.label(text="Gathering Files:")

        self.movingfiles_bar.draw(col, draw_time=True)

        row = col.row()
        row.label(text="Zipping Files:")

        self.zipping_bar.draw(col.column(), draw_time=True)

        # row = layout.row()
        # row.label(text="Uploading:")
        # split = layout.split(factor=0.25)
        # split.separator()
        # self.upload_bar.draw(split.column())


class SH_Scene(PropertyGroup):
    header_progress_bar: PointerProperty(type=ProgressBar)
    side_panel_batch_asset_update_progress_bar: PointerProperty(
        type=MultiProgressBarUpdate_Assets
    )

    export_library: PointerProperty(type=MultiProgressBarExportLibrary)

    library_mode: EnumProperty(
        items=(
            (
                "BLENDER",
                "Blender",
                "Blender's default asset library settings and options",
            ),
            (
                "SUPERHIVE",
                "SuperHive",
                "Settings and options for uploading to Superhive's asset system",
            ),
        ),
        name="Library Mode",
        description="Choose which asset library settings to use",
    )

    utils = utils
    hivemind = hive_mind

    metadata_update: PointerProperty(type=BatchMetadataUpdate)

    def __ignore__(self):
        self.metadata_update: BatchMetadataUpdate
        self.header_progress_bar: ProgressBar
        self.side_panel_batch_asset_update_progress_bar: MultiProgressBarUpdate_Assets
        self.export_library: MultiProgressBarExportLibrary


classes = (
    BatchUpdateAction,
    BatchItemWithActions,
    BatchMetadataUpdate,
    # Progress Bars
    ProgressBar,
    ProgressBarForMulti,
    ProgressUpdate_Asset,
    IconRenderingProgressBars,
    MultiProgressBarUpdate_Assets,
    MovingFilesProgressBar,
    MultiProgressBarExportLibrary,
    SH_Scene,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.superhive = PointerProperty(type=SH_Scene)
    bpy.types.Scene.sh_progress_t = bpy.props.StringProperty(default="")


def unregister():
    del bpy.types.Scene.superhive
    del bpy.types.Scene.sh_progress_t
    for cls in classes:
        bpy.utils.unregister_class(cls)
