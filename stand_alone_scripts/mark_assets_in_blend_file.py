"""
CLI Script to remove objects/assets from a blend file:

Argument Order:
    0.  blender executable
    1.  background arg
    2.  factory startup arg
    3.  blend file to open: str
    4.  run python script arg
    5.  script to run
    6.  mark actions
    7.  mark collections
    8.  mark materials
    9.  mark node trees
    10. mark objects
    11. mark object armatures
    12. mark object cameras
    13. mark object curves
    14. mark object empties
    15. mark object fonts
    16. mark object grease pencils
    17. mark object lattices
    18. mark object lights
    19. mark object light probes
    20. mark object meshes
    21. mark object metas
    22. mark object point clouds
    23. mark object speakers
    24. mark object surfaces
    25. mark object volumes
    26. mark worlds
    27. clear other assets
    28. skip hidden
    29. catalog source # Unused?
    30. new catalog id
    31. override existing data, don't replace information that is already set
    32. author
    33. description
    34. license
    35. copyright
    36. tags
"""

import sys
from pathlib import Path

import bpy
from bpy.types import ID

MARK_ACTIONS = sys.argv[6] == "True"
MARK_COLLECTIONS = sys.argv[7] == "True"
MARK_MATERIALS = sys.argv[8] == "True"
MARK_NODE_TREES = sys.argv[9] == "True"
MARK_OBJECTS = sys.argv[10] == "True"
MARK_OBJECT_ARMATURES = sys.argv[11] == "True"
MARK_OBJECT_CAMERAS = sys.argv[12] == "True"
MARK_OBJECT_CURVES = sys.argv[13] == "True"
MARK_OBJECT_EMPTIES = sys.argv[14] == "True"
MARK_OBJECT_FONTS = sys.argv[15] == "True"
MARK_OBJECT_GREASE_PENCILS = sys.argv[16] == "True"
MARK_OBJECT_LATTICES = sys.argv[17] == "True"
MARK_OBJECT_LIGHTS = sys.argv[18] == "True"
MARK_OBJECT_LIGHT_PROBES = sys.argv[19] == "True"
MARK_OBJECT_MESHES = sys.argv[20] == "True"
MARK_OBJECT_METAS = sys.argv[21] == "True"
MARK_OBJECT_POINT_CLOUDS = sys.argv[22] == "True"
MARK_OBJECT_SPEAKERS = sys.argv[23] == "True"
MARK_OBJECT_SURFACES = sys.argv[24] == "True"
MARK_OBJECT_VOLUMES = sys.argv[25] == "True"
MARK_WORLDS = sys.argv[26] == "True"

CLEAR_OTHER_ASSETS = sys.argv[27] == "True"
SKIP_HIDDEN = sys.argv[28] == "True"

CATALOG_SOURCE = sys.argv[29]
NEW_CATALOG_ID = sys.argv[30]
SET_CATALOG_ID = NEW_CATALOG_ID != "NONE"

OVERRIDE_EXISTING_DATA = sys.argv[31] == "True"
AUTHOR = sys.argv[32]
DESCRIPTION = sys.argv[33]
LICENSE = sys.argv[34]
COPYRIGHT = sys.argv[35]
TAGS = sys.argv[36].split(",") if sys.argv[36] else []
MOVE_TO_LIBRARY = sys.argv[37] == "True"
LIB_DIRECTORY = sys.argv[38] if MOVE_TO_LIBRARY else ""


print(f"|     - {MARK_ACTIONS=}")
print(f"|     - {MARK_COLLECTIONS=}")
print(f"|     - {MARK_MATERIALS=}")
print(f"|     - {MARK_NODE_TREES=}")
print(f"|     - {MARK_OBJECTS=}")
print(f"|     - {MARK_OBJECT_ARMATURES=}")
print(f"|     - {MARK_OBJECT_CAMERAS=}")
print(f"|     - {MARK_OBJECT_CURVES=}")
print(f"|     - {MARK_OBJECT_EMPTIES=}")
print(f"|     - {MARK_OBJECT_FONTS=}")
print(f"|     - {MARK_OBJECT_GREASE_PENCILS=}")
print(f"|     - {MARK_OBJECT_LATTICES=}")
print(f"|     - {MARK_OBJECT_LIGHTS=}")
print(f"|     - {MARK_OBJECT_LIGHT_PROBES=}")
print(f"|     - {MARK_OBJECT_MESHES=}")
print(f"|     - {MARK_OBJECT_METAS=}")
print(f"|     - {MARK_OBJECT_POINT_CLOUDS=}")
print(f"|     - {MARK_OBJECT_SPEAKERS=}")
print(f"|     - {MARK_OBJECT_SURFACES=}")
print(f"|     - {MARK_OBJECT_VOLUMES=}")
print(f"|     - {MARK_WORLDS=}")
print(f"|     - {CLEAR_OTHER_ASSETS=}")
print(f"|     - {SKIP_HIDDEN=}")
print(f"|     - {CATALOG_SOURCE=}")
print(f"|     - {NEW_CATALOG_ID=}")
print(f"|     - {SET_CATALOG_ID=}")
print(f"|     - {OVERRIDE_EXISTING_DATA=}")
print(f"|     - {AUTHOR=}")
print(f"|     - {DESCRIPTION=}")
print(f"|     - {LICENSE=}")
print(f"|     - {COPYRIGHT=}")
print(f"|     - {TAGS=}")
print(f"|     - {MOVE_TO_LIBRARY=}")
print(f"|     - {LIB_DIRECTORY=}")


assets_marked: list[ID] = []

obj_type_to_conditions = {
    "ARMATURE": MARK_OBJECT_ARMATURES,
    "CAMERA": MARK_OBJECT_CAMERAS,
    "CURVE": MARK_OBJECT_CURVES,
    "EMPTY": MARK_OBJECT_EMPTIES,
    "FONT": MARK_OBJECT_FONTS,
    "GPENCIL": MARK_OBJECT_GREASE_PENCILS,
    "LATTICE": MARK_OBJECT_LATTICES,
    "LIGHT": MARK_OBJECT_LIGHTS,
    "LIGHT_PROBE": MARK_OBJECT_LIGHT_PROBES,
    "MESH": MARK_OBJECT_MESHES,
    "META": MARK_OBJECT_METAS,
    "POINT_CLOUD": MARK_OBJECT_POINT_CLOUDS,
    "SPEAKER": MARK_OBJECT_SPEAKERS,
    "SURFACE": MARK_OBJECT_SURFACES,
    "VOLUME": MARK_OBJECT_VOLUMES,
}


data_type_to_condition = {
    "actions": MARK_ACTIONS,
    "collections": MARK_COLLECTIONS,
    "materials": MARK_MATERIALS,
    "node_groups": MARK_NODE_TREES,
    "objects": MARK_OBJECTS,
    "armatures": MARK_OBJECT_ARMATURES,
    "cameras": MARK_OBJECT_CAMERAS,
    "curves": MARK_OBJECT_CURVES,
    # "empties": MARK_OBJECT_EMPTIES,
    # "fonts": MARK_OBJECT_FONTS,
    "grease_pencils": MARK_OBJECT_GREASE_PENCILS,
    "lattices": MARK_OBJECT_LATTICES,
    "lights": MARK_OBJECT_LIGHTS,
    "lightprobes": MARK_OBJECT_LIGHT_PROBES,
    "meshes": MARK_OBJECT_MESHES,
    "metaballs": MARK_OBJECT_METAS,
    "pointclouds": MARK_OBJECT_POINT_CLOUDS,
    "speakers": MARK_OBJECT_SPEAKERS,
    # "surfaces": MARK_OBJECT_SURFACES,
    "volumes": MARK_OBJECT_VOLUMES,
    "worlds": MARK_WORLDS,
}


def clear_other_assets():
    """Remove asset data that is not set to be marked"""
    if not CLEAR_OTHER_ASSETS:
        return

    if not MARK_ACTIONS:
        for action in bpy.data.actions:
            action.asset_clear()

    if not MARK_COLLECTIONS:
        for collection in bpy.data.collections:
            collection.asset_clear()

    if not MARK_MATERIALS:
        for material in bpy.data.materials:
            material.asset_clear()

    if not MARK_NODE_TREES:
        for node_tree in bpy.data.node_groups:
            node_tree.asset_clear()

    obj_types_to_clear = {
        obj_type
        for obj_type, condition in obj_type_to_conditions.items()
        if not condition
    }
    if obj_types_to_clear:
        print(f"|     - {obj_types_to_clear=}")
        for obj in bpy.data.objects:
            if obj.type in obj_types_to_clear:
                obj.asset_clear()

    if not MARK_WORLDS:
        for world in bpy.data.worlds:
            world.asset_clear()


def make_asset(item: ID) -> None:
    global assets_marked

    assets_marked.append(item)

    item.asset_mark()

    if OVERRIDE_EXISTING_DATA:
        item.asset_data.author = AUTHOR
        item.asset_data.description = DESCRIPTION
        item.asset_data.license = LICENSE
        item.asset_data.copyright = COPYRIGHT

        for tag in item.asset_data.tags:
            item.asset_data.tags.remove(tag)
        for tag in TAGS:
            item.asset_data.tags.new(tag)

        if SET_CATALOG_ID:
            item.asset_data.catalog_id = NEW_CATALOG_ID
    else:
        if not item.asset_data.author:
            item.asset_data.author = AUTHOR
        if not item.asset_data.description:
            item.asset_data.description = DESCRIPTION
        if not item.asset_data.license:
            item.asset_data.license = LICENSE
        if not item.asset_data.copyright:
            item.asset_data.copyright = COPYRIGHT
        if SET_CATALOG_ID and not item.asset_data.catalog_id:
            item.asset_data.catalog_id = NEW_CATALOG_ID

        # Don't add tags that are already present
        for tag in TAGS:
            if tag not in item.asset_data.tags:
                item.asset_data.tags.new(tag)


def make_assets():
    if MARK_ACTIONS:
        for action in bpy.data.actions:
            make_asset(action)

    if MARK_COLLECTIONS:
        for collection in bpy.data.collections:
            if SKIP_HIDDEN and (
                collection not in bpy.context.scene.collection.children_recursive
                or collection.hide_viewport
            ):
                continue
            make_asset(collection)

    if MARK_MATERIALS:
        for material in bpy.data.materials:
            make_asset(material)

    if MARK_NODE_TREES:
        for node_tree in bpy.data.node_groups:
            make_asset(node_tree)

    if MARK_OBJECTS:
        obj_types = {
            obj_type
            for obj_type, condition in obj_type_to_conditions.items()
            if condition
        }
        print(f"|     - {obj_types=}")
        for obj in bpy.data.objects:
            if SKIP_HIDDEN and (
                obj.name not in bpy.context.scene.collection.all_objects
                or obj.hide_viewport
            ):
                continue
            if obj.type in obj_types:
                make_asset(obj)

    if MARK_WORLDS:
        for world in bpy.data.worlds:
            make_asset(world)


if __name__ == "__main__":
    print("|", bpy.data.filepath)

    bpy.ops.file.make_paths_absolute()

    clear_other_assets()

    make_assets()

    if MOVE_TO_LIBRARY:
        p = Path(LIB_DIRECTORY) / Path(bpy.data.filepath).name
        print(f"| Saving to library: {p}")
        bpy.ops.wm.save_as_mainfile(
            filepath=str(p),
            compress=True,
            relative_remap=True,
        )

    if assets_marked:
        print(f"~~FP:{p if MOVE_TO_LIBRARY else bpy.data.filepath}")
        for asset in assets_marked:
            data_type = asset.__class__.__name__.upper()
            if "NODETREE" in data_type:
                data_type = "NODETREE"
            print(f"~~{asset.name},{data_type}")
