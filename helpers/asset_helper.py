import bpy
from bpy.types import Context, AssetRepresentation
from typing import Any, TYPE_CHECKING
import uuid
from .. import __package__ as base_package


if TYPE_CHECKING:
    from ..ui import prefs as sh_prefs


# def is_superhive_asset(asset: AssetRepresentation) -> bool:
#     return bool(asset.metadata.sh_uuid)


# def convert_to_superhive_asset(context: Context, asset: AssetRepresentation, name: str = "", description: str = "", tags: list[str] = None) -> None:
#     if is_superhive_asset(asset):
#         return
#     asset.metadata.sh_uuid = str(uuid.uuid4())
#     # asset.metadata.sh_name = name or asset.name
#     asset.metadata.sh_description = description or asset.name
#     # asset.metadata.sh_tags.from_dict(tags or [])
#     prefs: 'sh_prefs.SH_AddonPreferences' = context.preferences.addons[base_package].preferences
#     asset.metadata.sh_author = prefs.default_author_name or asset.metadata.author
#     try:
#         asset.metadata.sh_license = prefs.default_license or asset.metadata.license
#     except Exception:
#         pass
#     asset.metadata.sh_created_blender_version = bpy.app.version_string


# def to_dict(asset: AssetRepresentation) -> dict[str, Any]:
#     return {
#         "uuid": asset.metadata.sh_uuid,
#         "name": asset.metadata.sh_name,
#         "description": asset.metadata.sh_description,
#         "tags": asset.metadata.sh_tags.to_dict(),
#         "category": asset.metadata.sh_category,
#         "author": asset.metadata.sh_author,
#         "license": asset.metadata.sh_license,
#         "created_blender_version": asset.metadata.sh_created_blender_version,
#     }


# def from_dict(asset: AssetRepresentation, data: dict[str, Any]):
#     if not data:
#         return

#     asset.metadata.sh_uuid = data.get(
#         "uuid",
#         asset.metadata.sh_uuid
#     )
#     asset.metadata.sh_name = data.get(
#         "name",
#         asset.metadata.sh_name
#     )
#     asset.metadata.sh_description = data.get(
#         "description",
#         asset.metadata.sh_description
#     )
#     asset.metadata.sh_tags.from_dict(
#         data.get("tags", {})
#     )
#     asset.metadata.sh_category = data.get(
#         "category",
#         asset.metadata.sh_category
#     )
#     asset.metadata.sh_author = data.get(
#         "author",
#         asset.metadata.sh_author
#     )
#     asset.metadata.sh_license = data.get(
#         "license",
#         asset.metadata.sh_license
#     )
#     asset.metadata.sh_created_blender_version = data.get(
#         "created_blender_version",
#         asset.metadata.sh_created_blender_version
#     )
