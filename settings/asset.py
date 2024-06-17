from typing import Any
import bpy

from bpy.types import PropertyGroup, AssetMetaData
from bpy.props import PointerProperty, StringProperty, EnumProperty

from .. import hive_mind


class SH_AssetTags(PropertyGroup):
    def to_dict(self) -> dict:
        return {}

    def from_dict(self, data: dict[str, Any]):
        if not data:
            return


classes = (
    SH_AssetTags,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    AssetMetaData.sh_uuid = StringProperty(
        name="UUID",
        description="UUID of the asset in the Superhive system",
        default="",
    )
    AssetMetaData.sh_name = StringProperty(
        name="Name",
        description="Name of the asset in the Superhive system",
        default="",
    )
    AssetMetaData.sh_description = StringProperty(
        name="Description",
        description="Description of the asset in the Superhive system",
        default="",
    )
    AssetMetaData.sh_tags = PointerProperty(
        name="Tags",
        description="Tags for the asset in the Superhive system",
        type=SH_AssetTags,
    )
    AssetMetaData.sh_category = EnumProperty(
        name="Category",
        description="Category for the asset in the Superhive system",
        items=hive_mind.get_categories(),
    )
    AssetMetaData.sh_author = StringProperty(
        name="Author",
        description="Author of the asset in the Superhive system",
        default="",
    )
    AssetMetaData.sh_license = EnumProperty(
        name="License",
        description="License for the asset in the Superhive system",
        items=hive_mind.get_licenses(),
    )
    AssetMetaData.sh_created_blender_version = StringProperty(
        name="Created Blender Version",
        description="Blender version the asset was created in",
        default=bpy.app.version_string
    )


def unregister():
    del AssetMetaData.sh_uuid
    del AssetMetaData.sh_name
    del AssetMetaData.sh_description
    del AssetMetaData.sh_tags
    del AssetMetaData.sh_category
    del AssetMetaData.sh_author
    del AssetMetaData.sh_license
    del AssetMetaData.sh_created_blender_version

    for cls in classes:
        bpy.utils.unregister_class(cls)
