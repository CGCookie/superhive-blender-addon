from importlib import metadata
import re
from time import time

import bpy
import bpy.utils
from bpy.app.translations import contexts as i18n_contexts
from bpy.props import (BoolProperty, BoolVectorProperty, CollectionProperty,
                       EnumProperty, FloatProperty, PointerProperty,
                       StringProperty)
from bpy.types import AssetRepresentation, Context, PropertyGroup, UILayout

from .. import hive_mind, utils


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
        name="Add", description="Add a new action",
        translation_context=i18n_contexts.operator_default
    )
    action_remove: BoolProperty(
        name="Remove", description="Remove a this action",
        translation_context=i18n_contexts.operator_default
    )
    
    def draw(self, layout: UILayout, index:int, use_ops:bool=False):
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
            op = row.operator("superhive.remove_update_action", text="", icon="REMOVE")
            op.metadata_item = self.metadata_item
            op.action_index = index
            op = row.operator("superhive.add_update_action", text="", icon="ADD")
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

    def process_text(self, text:str) -> str:
        if not self.value and self.update_type != "CASE":
            return text
        match self.update_type:
            case "OVERWRITE":
                return self.value
            case "ADD":
                return text + self.value if self.add_type == "SUFFIX" else self.value + text
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
                    flags=(
                        0 if self.match_case_find else
                        re.IGNORECASE
                    ),
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
    
    def add_action(self, index:int):
        item: BatchUpdateAction = self.batch_items.add()
        item.metadata_item = self.name
        if index + 2 != len(self.batch_items):
            self.batch_items.move(len(self.batch_items) - 1, index + 1)
    
    def remove_action(self, index:int):
        if len(self.batch_items) > 1:
            self.batch_items.remove(index)
    
    def draw(self, layout: UILayout, use_ops:bool=False):
        action: BatchUpdateAction
        for i, action in enumerate(self.batch_items):
            action.draw(layout.box(), i, use_ops)

    def process_text(self, text:str) -> str:
        action: BatchUpdateAction
        for action in self.batch_items:
            text = action.process_text(text)
        return text


class BatchMetadataUpdate(PropertyGroup):
    metadata_type: EnumProperty(
        name="Metadata Type",
        description="Choose metadata settings to display",
        items=[
            ("name", "Name", "Display the settings for updating the name of the asset(s)"),
            ("description", "Description", "Display the settings for updating the description of the asset(s)"),
            ("author", "Author", "Display the settings for updating the author of the asset(s)"),
            ("license", "License", "Display the settings for updating the license of the asset(s)"),
            ("catalog", "Catalog", "Display the settings for updating the catalog of the asset(s)"),
            ("copyright", "Copyright", "Display the settings for updating the copyright of the asset(s)"),
            ("tags", "Tags", "Display the settings for updating the tags of the asset(s)"),
        ]
    )

    metadata_items: CollectionProperty(
        name="Metadata Items",
        type=BatchItemWithActions,
    )

    def _get_ignore_licenses(self, context):
        self.metadata_items: bpy.types.CollectionProperty | list[BatchItemWithActions] | dict[str, BatchItemWithActions]
        return [
            ("IGNORE", "Ignore", "Ignore the license"),
        ] + hive_mind.get_licenses()
    license: EnumProperty(
        name="License",
        description="The license to apply to the asset",
        items=_get_ignore_licenses,
        default=1,
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

    # TAGS #
    tags_update_type: EnumProperty(
        name="Update Type",
        items=[
            ("ADD", "Add", "Add tags to the existing tags"),
            ("OVERWRITE", "Overwrite", "Overwrite the existing tags"),
            ("REMOVE", "Remove", "Match and remove existing tags"),
        ]
    )
    # Don't set overwrite as default otherwise all tags
    # will be removed by default behavior
    tags: BoolVectorProperty(
        name="Tags",
        description="The tags to add to the asset",
        size=len(hive_mind.get_tags()),
    )
    
    reset_settings: BoolProperty(
        name="Reset Settings",
        description="Reset the settings after updating the assets",
        default=True
    )

    def process_text(self, metadata_item:str, text:str) -> str:
        item = self.metadata_items.get(metadata_item)
        return item.process_text(text)

    def draw(self, context: Context, layout: UILayout, use_ops:bool=False):
        row = layout.row()
        row.scale_y = 1.5
        row.prop(self, "metadata_type", expand=True)
        
        if self.metadata_type == "license":
            layout.prop(self, "license")
        elif self.metadata_type == "catalog":
            layout.prop(self, "catalog")
        elif self.metadata_type == "tags":
            layout.prop(self, "tags_update_type")
            grid = layout.grid_flow(columns=3, even_columns=True)
            for i, tag in enumerate(hive_mind.get_tags()):
                grid.prop(self, "tags", index=i, text=tag[1], expand=True)
        else:
            meta_data_item: BatchItemWithActions = self.metadata_items.get(self.metadata_type)
            meta_data_item.draw(layout, use_ops=use_ops)
            
            box = layout.box()
            row = box.row()
            row.alignment = "CENTER"
            row.label(text="Preview")
            col = box.column(align=True)
            asset: AssetRepresentation
            for asset in context.selected_assets[:5]:
                col.label(
                    text=asset.name+": "+meta_data_item.process_text(
                        getattr(
                            asset if self.metadata_type == "name" else asset.metadata,
                            self.metadata_type
                        )
                    )
                )
            if len(context.selected_assets) > 5:
                col.label(text="...")
    
    def process_tags(self, asset:utils.Asset):
        selected_tags = [
            tag_id
            for i, (tag_id, _tag_name, _tag_desc) in enumerate(hive_mind.get_tags())
            if self.tags[i]
        ]
        if self.tags_update_type == "OVERWRITE":
            return sorted(selected_tags)
        elif self.tags_update_type == "ADD":
            return sorted(list(set(asset.bpy_tags + selected_tags)))
        elif self.tags_update_type == "REMOVE": # REMOVE
            return sorted(list(set(asset.bpy_tags) - set(selected_tags)))
        return asset.bpy_tags
    
    def process_asset_metadata(self, asset: utils.Asset) -> None:
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
        if self.license != "IGNORE":
            asset.license = self.license
        if self.license != "IGNORE":
            asset.catalog_id = self.catalog
        asset.tags = self.process_tags(asset)
    
    def reset(self):
        self.metadata_items.clear()
        for name in ("name","description","author","copyright"):
            item: BatchItemWithActions = self.metadata_items.add()
            item.name = name
            item.add_action(0)
        
        for i in range(len(hive_mind.get_tags())):
            self.tags[i] = False
        
        self.license = "IGNORE"
        self.catalog = "IGNORE"
        
        self.metadata_type = "name"
        self.tags_update_type = "ADD"


class ProgressBar(PropertyGroup):
    progress: FloatProperty(subtype="PERCENTAGE", min=0, max=100)
    show: BoolProperty()
    label: StringProperty()
    """Label for the progress bar. This is the text that will be displayed on the progress bar."""

    formated_time: StringProperty()
    start_time = 0

    cancel: BoolProperty(
        name="Cancel",
        description="Cancel the current process",
        default=False,
    )
    is_complete: BoolProperty()

    def start(self):
        self.progress = 0
        self.show = True
        self.cancel = False
        self.start_time = time()

        self.is_complete = False

    def end(self):
        self.is_complete = True
        self.show = False

    def update_formated_time(self) -> None:
        """Converts the time taken to import the pack to a string and returns it. The string will be formatted to two decimal places."""
        hrs = 0
        mins = 0
        secs = 0
        timer = time() - self.start_time
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

    def draw(self, layout: UILayout) -> None:
        row = layout.row(align=True)
        row.prop(self, "progress", text=self.label)
        row.label(text=self.formated_time)


class SH_Scene(PropertyGroup):
    header_progress_bar: PointerProperty(type=ProgressBar)

    library_mode: EnumProperty(
        items=(
            ("BLENDER", "Blender",
             "Blender's default asset library settings and options"),
            ("SUPERHIVE", "SuperHive", "Settings and options for uploading to Superhive's asset system"),
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


classes = (
    BatchUpdateAction,
    BatchItemWithActions,
    BatchMetadataUpdate,
    ProgressBar,
    SH_Scene,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.superhive = PointerProperty(type=SH_Scene)


def unregister():
    del bpy.types.Scene.superhive
    for cls in classes:
        bpy.utils.unregister_class(cls)
