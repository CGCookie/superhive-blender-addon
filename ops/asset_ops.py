# from typing import TYPE_CHECKING
import re

import bpy
from bpy.app.translations import contexts as i18n_contexts
from bpy.props import (BoolProperty, BoolVectorProperty, CollectionProperty,
                       EnumProperty, StringProperty)
from bpy.types import Operator, PropertyGroup, UILayout, AssetRepresentation

from .. import hive_mind, utils
from ..settings import asset as asset_settings
from . import polls

# if TYPE_CHECKING:



class SH_OT_UpdateAsset(Operator):
    bl_idname = "superhive.update_asset"
    bl_label = "Update Asset"
    bl_description = "Update the asset data of selected assets. Updates all assets if none are selected."
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return polls.is_asset_browser(context, cls=cls) and context.asset

    def execute(self, context):
        # lib = utils.from_active(context, load_assets=True)
        # if not lib.assets:
        if not context.asset:
            self.report({"ERROR"}, "No active asset found")
            return {"CANCELLED"}

        prefs = utils.get_prefs()

        asset = utils.Asset(context.asset)
        asset.update_asset(prefs.ensure_default_blender_version().path)

        bpy.ops.asset.library_refresh()
        
        # self.context = context
        
        # bpy.app.timers.register(
        #     partial(self.in_1_second, context, asset),
        #     first_interval=2.0,
        #     persistent=False
        # )
        
        return {"FINISHED"}

    # def in_1_second(self, context: Context, asset):
        # TODO: Implement Timer to check if the asset has been updated
        #  https://docs.blender.org/api/current/bpy.app.timers.html#module-bpy.app.timers

        # context.scene.update_tag()

        # lib = utils.from_active(context, load_assets=True)

        # new_asset = lib.assets[asset.new_name]

        # context.space_data.activate_asset_by_id(new_asset.orig_asset.local_id)

        # sh_tags: 'asset_settings.SH_AssetTags' = new_asset.orig_asset.metadata.sh_tags
        # sh_tags.load_from_asset(new_asset.orig_asset)

        # return {"FINISHED"}


class BatchUpdateAction(PropertyGroup):
    # NAME #
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
    
    def draw(self, layout: UILayout):
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
                self.batch_items.add()
                if i + 2 != len(self.batch_items):
                    self.batch_items.move(len(self.batch_items) - 1, i + 1)
                changed = True
                break
            if action.action_remove:
                action.action_remove = False
                if len(self.batch_items) > 1:
                    self.batch_items.remove(i)
                changed = True
                break

        # if (
        #         (self._data_source_prev != self.data_source) or
        #         (self._data_type_prev != self.data_type)
        # ):
        #     self._data_update(context)
        #     changed = True

        return changed
    
    def draw(self, layout: UILayout):
        action: BatchUpdateAction
        for action in self.batch_items:
            action.draw(layout.box())

    def process_text(self, text:str) -> str:
        action: BatchUpdateAction
        for action in self.batch_items:
            text = action.process_text(text)
        return text


class SH_OT_BatchUpdateAssets(Operator):
    bl_idname = "superhive.batch_update_assets"
    bl_label = "Batch Update Assets"
    bl_description = "Update the asset data of selected assets."
    bl_options = {"REGISTER", "UNDO"}

    update_type_items = [
        ("OVERWRITE", "Overwrite", "Overwrite the existing metadata"),
        ("ADD", "Add", "Add to the existing asset metadata"),
        ("REPLACE", "Replace", "Match and replace the existing metadata"),
    ]

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
        items=update_type_items,
        # items=[
        #     ("OVERWRITE", "Overwrite", "Overwrite the existing metadata"),
        #     ("ADD", "Add", "Add to the existing asset metadata"),
        # ],
    )
    tags: BoolVectorProperty(
        name="Tags",
        description="The tags to add to the asset",
        size=len(hive_mind.get_tags()),
    )

    @classmethod
    def poll(cls, context):
        cls.metadata_items: CollectionProperty | list[BatchItemWithActions] | dict[str, BatchItemWithActions]
        if not polls.is_asset_browser(context, cls=cls):
            return False
        
        if not context.selected_assets:
            cls.poll_message_set("Please select and asset first")
            return False
        
        return True

    def invoke(self, context, event):
        self.metadata_items.clear()
        for name in ("name","description","author","copyright"):
            item: BatchItemWithActions = self.metadata_items.add()
            item.name = name
            action: BatchUpdateAction = item.batch_items.add()
        
        for i in range(len(hive_mind.get_tags())):
            self.tags[i] = False
        
        self.license = "IGNORE"
        self.catalog = "IGNORE"
            
        return context.window_manager.invoke_props_dialog(self, width=500)

    def draw(self, context):
        layout = self.layout
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
            meta_data_item.draw(layout)
            
            asset: AssetRepresentation
            for asset in context.selected_assets[:5]:
                layout.label(
                    text=meta_data_item.process_text(
                        getattr(
                            asset if self.metadata_type == "name" else asset.metadata,
                            self.metadata_type
                        )
                    )
                )
    
    def check(self, context):
        return any(
            item.check()
            for item in self.metadata_items
        )

    def execute(self, context):
        prefs = utils.get_prefs()

        for asset in context.selected_assets:
            asset = utils.Asset(asset)
            asset.new_name = self.metadata_items.get("name").process_text(asset.name)
            asset.description = self.metadata_items.get("description").process_text(asset.description)
            asset.author = self.metadata_items.get("author").process_text(asset.author)
            if self.license == "IGNORE":
                asset.license = self.license
            if self.license == "IGNORE":
                asset.catalog_id = self.catalog
            asset.copyright = self.metadata_items.get("copyright").process_text(asset.copyright)
            asset.tags = self.process_tags(asset)
            asset.update_asset(prefs.ensure_default_blender_version().path)

        bpy.ops.asset.library_refresh()

        return {"FINISHED"}
    
    def process_tags(self, asset:utils.Asset):
        selected_tags = [
            tag_id
            for i, (tag_id, _tag_name, _tag_desc) in enumerate(hive_mind.get_tags())
            if self.tags[i]
        ]
        if self.tags_update_type == "OVERWRITE":
            return selected_tags
        elif self.tags_update_type == "ADD":
            return sorted(list(set(asset.tags + selected_tags)))
        else: # REMOVE
            return list(set(asset.tags) - set(selected_tags))


# TODO: Icon generation (copy from True-Assets)


class SH_OT_ResetAssetMetadataProperty(Operator):
    bl_idname = "superhive.reset_asset_metadata_property"
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
            sh_tags: 'asset_settings.SH_AssetTags' = context.asset.metadata.sh_tags
            for tag in tags:
                sh_tags.new_tag(tag, context=context)
        else:
            setattr(context.asset.metadata, self.property, self.original_value)
        return {"FINISHED"}


class SH_OT_ResetAssetMetadata(Operator):
    bl_idname = "superhive.reset_asset_metadata"
    bl_label = "Reset Asset Metadata"
    bl_description = "Reset the asset metadata of selected assets. Resets all assets if none are selected."
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        asset = utils.Asset(context.asset)

        asset.reset_metadata(context)

        return {"FINISHED"}


class SH_OT_AddTags(Operator):
    bl_idname = "superhive.add_tags"
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
                tags: 'asset_settings.SH_AssetTags' = context.asset.metadata.sh_tags
                tags.new_tag(tag_name, context, id=tag_id, desc=tag_desc)
        return {"FINISHED"}


class SH_OT_RemoveTag(Operator):
    bl_idname = "superhive.remove_tag"
    bl_label = "Remove"
    bl_description = "Remove the active tag from the active asset."
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return polls.is_asset_browser(context, cls=cls) and context.asset

    def execute(self, context):
        tags: 'asset_settings.SH_AssetTags' = context.asset.metadata.sh_tags
        tags.remove_tag(tags.active_index, context)
        return {"FINISHED"}


class SH_OT_ResetTags(Operator):
    bl_idname = "superhive.reset_tag"
    bl_label = "Reset"
    bl_description = "Reset the tags to the original tags."
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return polls.is_asset_browser(context, cls=cls) and context.asset

    def execute(self, context):
        sh_tags: 'asset_settings.SH_AssetTags' = context.asset.metadata.sh_tags

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
    BatchUpdateAction,
    BatchItemWithActions,
    SH_OT_BatchUpdateAssets,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
