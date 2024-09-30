import uuid

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import (
    AssetMetaData,
    AssetRepresentation,
    Context,
    PropertyGroup,
    UILayout,
    UIList,
)

from .. import hive_mind


def _has_context_asset(C: Context = None) -> bool:
    C = C or bpy.context
    return hasattr(C, "asset") and C.asset is not None


class SH_UL_TagList(UIList):
    def draw_item(
        self,
        context,
        layout: UILayout,
        data,
        item: "SH_AssetTag",
        icon,
        active_data,
        active_propname,
        index,
        flt_flag,
    ):
        layout.label(text=item.name)


class SH_AssetTag(PropertyGroup):
    id: StringProperty(
        name="ID",
        description="UUID of the tag in the Superhive (formerly Blender Market) system",
    )
    name: StringProperty(
        name="Name",
        description="Name of the tag in the Superhive (formerly Blender Market) system",
    )
    desc: StringProperty(
        name="Description",
        description="Description of the tag in the Superhive (formerly Blender Market) system",
    )


class SH_AssetTags(PropertyGroup):
    tags: CollectionProperty(type=SH_AssetTag)
    active_index: IntProperty()
    """The active index in the tag list. Used for UILists"""

    def check_is_dirty(self, context: Context, context_check: bool = None) -> None:
        """Check and set if the asset tags are dirty."""
        if context_check is None and not _has_context_asset(C=context):
            return False  # No asset to check
        asset = context.asset
        return len(asset.metadata.tags) != len(self.tags) or any(
            orig_tag.name not in {new_tag.name for new_tag in self.tags}
            for orig_tag in asset.metadata.tags
        )

    def set_is_dirty(
        self, context: Context, value: bool, context_check: bool = None
    ) -> None:
        if context_check is None and not _has_context_asset(C=context):
            return False  # No asset to check
        asset = context.asset
        asset.metadata.sh_is_dirty_tags = value

    def update_is_dirty(self, context: Context) -> None:
        """Update the is_dirty property of the asset tags."""
        if not _has_context_asset(C=context):
            return  # No asset to check
        self.set_is_dirty(
            context,
            self.check_is_dirty(context, context_check=True),
            context_check=True,
        )

    def new_tag(
        self, name: str, context: Context, id: str = None, desc: str = None
    ) -> SH_AssetTag:
        """
        Create a new asset tag.

        Parameters
        ----------
        name : str
            The name of the tag.
        context : Context
            The context containing the asset. If set to None, the `is_dirty` property will not be updated.
        id : str, optional
            The ID of the tag. If not provided, a random UUID will be generated.
        desc : str, optional
            The description of the tag.

        Returns
        -------
        SH_AssetTag
            The newly created asset tag.
        """
        self.tags: bpy.types.CollectionProperty
        tag = self.tags.add()
        tag.name = name
        tag.id = id or str(uuid.uuid4())
        tag.desc = desc or ""

        if context:
            self.update_is_dirty(context)

        return tag

    def remove_tag(self, tag: SH_AssetTag | int, context: Context) -> None:
        """
        Remove a tag from the asset.

        Parameters
        ----------
        tag : SH_AssetTag or int
            The tag to be removed. It can be either an instance of SH_AssetTag or an integer.
        context : Context
            The context containing the asset. If set to None, the `is_dirty` property will not be updated.

        Returns
        -------
        None
        """
        if isinstance(tag, int):
            self.tags.remove(tag)
        else:
            i = self.tags.find(tag)
            self.tags.remove(i)

        if context:
            self.update_is_dirty(context)

    def load_from_asset(self, asset: AssetRepresentation) -> None:
        for tag in asset.metadata.tags:
            self.new_tag(tag.name)
        asset.metadata.sh_is_dirty_tags = False

    def load_from_active_asset(self, context: Context) -> None:
        """
        Load original tags from the active asset in the given context.
        Will clear the current tags list and set the `sh_is_dirty_tags` property to False.

        Parameters:
        - context (Context): The context containing the active asset.

        Returns:
        - None
        """
        asset = context.asset
        self.load_from_active_asset(asset)

    def clear(self, context: Context) -> None:
        """Clears the tags list.

        Parameters
        ----------
        context : Context
            The context containing the asset. If set to None, the `is_dirty` property will not be updated.
        """

        while self.tags:
            self.tags.remove(0)

        self.update_is_dirty(context)

    def validate(self, context: Context) -> None:
        """Ensure all tags are supported by Superhive (formerly Blender Market)."""
        pass


def is_dirty(self: AssetRepresentation) -> bool:
    return any(
        [
            self.sh_is_dirty_name,
            self.sh_is_dirty_description,
            self.sh_is_dirty_catalog,
            self.sh_is_dirty_author,
            self.sh_is_dirty_license,
            self.sh_is_dirty_copyright,
            self.sh_is_dirty_tags,
            self.sh_is_dirty_created_blender_version,
            # self.sh_is_dirty_icon,
        ]
    )


classes = (
    SH_UL_TagList,
    SH_AssetTag,
    SH_AssetTags,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    def _get_asset_data(prop: str) -> dict:
        def get(self):
            item = self.get(f"_{prop}", None)
            if item is not None:
                return item
            return getattr(self, prop)

        return get

    def _set_asset_data(prop: str) -> dict:
        def set(self, value):
            self[f"_{prop}"] = value
            setattr(self, f"sh_is_dirty_{prop}", value != getattr(self, prop))

        return set

    # TODO: add in stuff to revert to original (current) values

    AssetMetaData.sh_is_dirty = is_dirty

    AssetMetaData.sh_uuid = StringProperty(
        name="UUID",
        description="UUID of the asset in the Superhive (formerly Blender Market) system",
        default="",
    )

    def _get_active_asset_name(self: "AssetMetaData"):
        item = self.get("_name", None)
        if item is not None:
            return item
        if bpy.context.asset:
            return bpy.context.asset.name
        return "Error: no active asset"

    def _set_active_asset_name(self, value: str):
        self["_name"] = value
        if _has_context_asset(C=bpy.context):
            self.sh_is_dirty_name = value != bpy.context.asset.name

    AssetMetaData.sh_is_dirty_name = BoolProperty()
    AssetMetaData.sh_name = StringProperty(
        name="Name",
        description="Name of the asset in the Superhive (formerly Blender Market) system",
        default="",
        get=_get_active_asset_name,
        set=_set_active_asset_name,
    )
    AssetMetaData.sh_is_dirty_description = BoolProperty()
    AssetMetaData.sh_description = StringProperty(
        name="Description",
        description="Description of the asset in the Superhive (formerly Blender Market) system",
        default="",
        get=_get_asset_data("description"),
        set=_set_asset_data("description"),
    )

    def _get_asset_catalog(self: AssetMetaData) -> dict:
        item = self.get("_catalog", None)
        if item is not None:
            return item

        item = hive_mind.CATALOG_DICT.get(self.catalog_id, {})
        if item:
            return item.get("id_int", 444)

        item = hive_mind.get_catalog_by_name(
            self.catalog_simple_name, is_catalog_simple_name=True
        )

        return item.get("id_int", 444) if item else 444

    def _set_asset_catalog(self: AssetMetaData, value) -> dict:
        self["_catalog"] = value
        item = next(
            (val for val in hive_mind.CATALOG_DICT.values() if val["id_int"] == value),
            None,
        )

        if "-" in self.catalog_simple_name:
            set_cat_name = self.catalog_simple_name.split("-")[-1]
        else:
            set_cat_name = self.catalog_simple_name

        self.sh_is_dirty_catalog = not any(
            (item["id"] == self.catalog_id, item["name"] == set_cat_name)
        )

    AssetMetaData.sh_is_dirty_catalog = BoolProperty()
    AssetMetaData.sh_catalog = EnumProperty(
        name="Catalog",
        description="Catalog for the asset in the Superhive (formerly Blender Market) system",
        items=hive_mind.get_categories(),
        get=_get_asset_catalog,
        set=_set_asset_catalog,
    )

    def _get_sh_catalog_custom(self) -> dict:
        item = self.get("_sh_catalog_custom", None)
        if item is not None:
            return item
        return ""

    def _set_sh_catalog_custom(self, value: str) -> dict:
        self.sh_is_dirty_catalog_custom = value != ""
        self["_sh_catalog_custom"] = value

    AssetMetaData.sh_is_dirty_catalog_custom = BoolProperty()
    AssetMetaData.sh_catalog_custom = StringProperty(
        name="Custom Catalog",
        description="Catalog for the asset",
        get=_get_sh_catalog_custom,
        set=_set_sh_catalog_custom,
    )
    AssetMetaData.sh_is_dirty_author = BoolProperty()
    AssetMetaData.sh_author = StringProperty(
        name="Author",
        description="Author of the asset in the Superhive (formerly Blender Market) system",
        default="",
        get=_get_asset_data("author"),
        set=_set_asset_data("author"),
    )

    def _get_asset_license(self: AssetMetaData) -> dict:
        item = self.get("_license", None)
        if item is not None:
            return item

        item = hive_mind.LICENSES_DICT.get(self.license, {})
        if item:
            return item.get("id_int", 444)

        item = hive_mind.get_license_by_name(self.license)
        return item.get("id_int", 444) if item else 444

    def _set_asset_license(self: AssetMetaData, value) -> dict:
        self["_license"] = value
        item = next(
            (val for val in hive_mind.LICENSES_DICT.values() if val["id_int"] == value),
            None,
        )

        self.sh_is_dirty_license = not any(
            (item["id"] == self.license, item["name"] == self.license)
        )

    AssetMetaData.sh_is_dirty_license = BoolProperty()
    AssetMetaData.sh_license = EnumProperty(
        name="License",
        description="Superhive (formerly Blender Market) compatible license for the asset",
        items=hive_mind.get_licenses(),
        get=_get_asset_license,
        set=_set_asset_license,
    )
    AssetMetaData.sh_license_custom = StringProperty(
        name="Custom License",
        description="License for the asset",
        get=_get_asset_data("license"),
        set=_set_asset_data("license"),
    )
    AssetMetaData.sh_is_dirty_copyright = BoolProperty()
    AssetMetaData.sh_copyright = StringProperty(
        name="Copyright",
        description="Copyright for the asset in the Superhive (formerly Blender Market) system",
        get=_get_asset_data("copyright"),
        set=_set_asset_data("copyright"),
    )
    AssetMetaData.sh_is_dirty_created_blender_version = BoolProperty()
    AssetMetaData.sh_created_blender_version = StringProperty(
        name="Created Blender Version",
        description="Blender version the asset was created in",
        default=bpy.app.version_string,
    )
    AssetMetaData.sh_is_dirty_tags = BoolProperty()
    AssetMetaData.sh_tags = PointerProperty(
        name="Tags",
        description="Tags for the asset in the Superhive (formerly Blender Market) system",
        type=SH_AssetTags,
    )


def unregister():
    del AssetMetaData.sh_uuid
    del AssetMetaData.sh_name
    del AssetMetaData.sh_is_dirty_name
    del AssetMetaData.sh_description
    del AssetMetaData.sh_is_dirty_description
    del AssetMetaData.sh_tags
    del AssetMetaData.sh_is_dirty_tags
    del AssetMetaData.sh_catalog
    del AssetMetaData.sh_is_dirty_catalog
    del AssetMetaData.sh_author
    del AssetMetaData.sh_is_dirty_author
    del AssetMetaData.sh_license
    del AssetMetaData.sh_is_dirty_license
    del AssetMetaData.sh_copyright
    del AssetMetaData.sh_is_dirty_copyright
    del AssetMetaData.sh_created_blender_version
    del AssetMetaData.sh_is_dirty_created_blender_version

    for cls in classes:
        bpy.utils.unregister_class(cls)
