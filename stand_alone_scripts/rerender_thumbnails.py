import functools
import math
import os
import random
import sys
import traceback
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

import bpy
from mathutils import Vector
from bpy.types import (
    Area,
    Collection,
    Constraint,
    Context,
    Object,
    Scene,
    ShaderNodeMapping,
    World,
)

ASSET_TYPES_TO_ID_TYPES = {
    "ACTION": "actions",
    "ARMATURE": "armatures",
    "BRUSH": "brushes",
    "CACHEFILE": "cache_files",
    "CAMERA": "cameras",
    "COLLECTION": "collections",
    "CURVE": "curves",
    "CURVES": "curves",
    "FONT": "fonts",
    "GREASEPENCIL": "grease_pencils",
    "GREASEPENCIL_V3": "grease_pencils",
    "IMAGE": "images",
    "KEY": "shape_keys",
    "LATTICE": "lattices",
    "LIBRARY": "libraries",
    "LIGHT": "lights",
    "LIGHT_PROBE": "lightprobes",
    "LINESTYLE": "linestyles",
    "MASK": "masks",
    "MATERIAL": "materials",
    "MESH": "meshes",
    "META": "metaballs",
    "MOVIECLIP": "movieclips",
    "NODETREE": "node_groups",
    "OBJECT": "objects",
    "PAINTCURVE": "paint_curves",
    "PALETTE": "palettes",
    "PARTICLE": "particles",
    "POINTCLOUD": "",
    "SCENE": "scenes",
    "SCREEN": "screens",
    "SOUND": "sounds",
    "SPEAKER": "speakers",
    "TEXT": "texts",
    "TEXTURE": "textures",
    "VOLUME": "volumes",
    "WINDOWMANAGER": "window_managers",
    "WORKSPACE": "workspaces",
    "WORLD": "worlds",
}


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


print()
argv = sys.argv
argv = argv[argv.index("--") + 1 :]
FILEPATHS = argv[0].split(":--separator--:")
ALL_NAMES = argv[1].split(":--separator--:")
ALL_TYPES = argv[2].split(":--separator--:")
SHADING = argv[3]
OBJECTS_PATH = argv[4]
CAMERA_ANGLE = argv[5]
ADD_PLANE = eval(argv[6])
WORLD_STRENGTH = float(argv[7])
FILEPATH = FILEPATHS.pop(0)
TYPES = ALL_TYPES.pop(0).split(":--separator2--:")
NAMES = ALL_NAMES.pop(0).split(":--separator2--:")
RENDER_DEVICE = argv[8]
WORLD_NAME = argv[9]
CAMERA_OFFSET = float(argv[10])
"""Float between 0 and 1"""
ROTATE_WORLD = eval(argv[11])
"""Rotate the world texture along with the camera"""
SETUP_OR_APPLY = eval(argv[12])
"""0 for setup, 1 for render"""
DEBUG_SCENE = eval(argv[13])

IS_SETUP = SETUP_OR_APPLY == 0
IS_RENDER = False  # Unused
IS_APPLY = SETUP_OR_APPLY == 1


print("FILEPATHS (init):", argv[0].split(":--separator--:"))
print("FILEPATHS:", FILEPATHS)
print("ALL_NAMES:", ALL_NAMES)
print("ALL_TYPES:", ALL_TYPES)
print("SHADING:", SHADING)
print("OBJECTS_PATH:", OBJECTS_PATH)
print("CAMERA_ANGLE:", CAMERA_ANGLE)
print("ADD_PLANE:", ADD_PLANE)
print("WORLD_STRENGTH:", WORLD_STRENGTH)
print("FILEPATH:", FILEPATH)
print("TYPES:", TYPES)
print("NAMES:", NAMES)
print("RENDER_DEVICE:", RENDER_DEVICE)
print("WORLD_NAME:", WORLD_NAME)
print("CAMERA_OFFSET:", CAMERA_OFFSET)
if DEBUG_SCENE:
    print("DEBUG_SCENE: True")
print()


context = bpy.context
scene = context.scene
bpy.ops.wm.open_mainfile(filepath=FILEPATH, load_ui=False)


def enable_gpus(device_type, use_cpus=False):
    preferences = bpy.context.preferences
    cycles_preferences = preferences.addons["cycles"].preferences
    devices = cycles_preferences.get_devices_for_type(device_type)

    activated_gpus = []

    for device in devices:
        if device.type == "CPU":
            device.use = use_cpus
        else:
            device.use = True
            activated_gpus.append(device.name)

    cycles_preferences.compute_device_type = device_type

    return activated_gpus


try:
    enable_gpus(RENDER_DEVICE)
except Exception as e:
    print(e)


random_id_source = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"


def get_id(length=6):
    return "".join(random.sample(random_id_source, length))


# supports_thumbnails = ["MESH", "LIGHT"]
supports_thumbnails = ["MESH", "CURVE", "FONT", "VOLUME"]


def does_support_thumbnails(ob: Object):
    return (
        isinstance(ob, bpy.types.Material)
        or isinstance(ob, bpy.types.World)
        or (
            isinstance(ob, bpy.types.Object)
            and ob.type in supports_thumbnails
            and not (
                isinstance(ob, bpy.types.Object)
                and ob.type == "MESH"
                and len(
                    ob.evaluated_get(
                        bpy.context.evaluated_depsgraph_get()
                    ).data.polygons
                )
                < 1
            )
        )
        or (
            isinstance(ob, bpy.types.NodeTree)
            and [a for a in ob.interface.items_tree if a.in_out == "OUTPUT"]
        )
        # or SHADING != "Solid"
    )


def delete_object_with_data(obj: Object):
    if obj and obj.name in bpy.data.objects:
        data = obj.data
        isMesh = obj.type == "MESH"
        bpy.data.objects.remove(obj, do_unlink=True)
        if isMesh:
            bpy.data.meshes.remove(data)


def get_bounding_box_of_collection(
    col: Collection, objects_to_ignore: set[Object] = None
) -> tuple[Vector, Vector]:
    corners = []
    if objects_to_ignore is None:
        objects_to_ignore = set()
    for ob in col.all_objects:
        if ob in objects_to_ignore:
            continue

        ob.update_tag()
        if hasattr(ob.data, "update_tag"):
            ob.data.update_tag()
        ob.update_from_editmode()

        corners.extend([(ob.matrix_world @ Vector(b)) for b in ob.bound_box])

    min_z = min(((Vector(b)).z for b in corners))
    max_z = max(((Vector(b)).z for b in corners))
    min_x = min(((Vector(b)).x for b in corners))
    max_x = max(((Vector(b)).x for b in corners))
    min_y = min(((Vector(b)).y for b in corners))
    max_y = max(((Vector(b)).y for b in corners))

    return Vector((min_x, min_y, min_z)), Vector((max_x, max_y, max_z))


def get_bounding_box_of_object(obj: Object) -> tuple[Vector, Vector]:
    min_x = min_y = min_z = 1_000_000
    max_x = max_y = max_z = -1_000_000
    for v in obj.bound_box:
        min_x = min(min_x, v[0])
        max_x = max(max_x, v[0])
        min_y = min(min_y, v[1])
        max_y = max(max_y, v[1])
        min_z = min(min_z, v[2])
        max_z = max(max_z, v[2])

    return Vector((min_x, min_y, min_z)), Vector((max_x, max_y, max_z))


def get_collections_from_scene(scene: Scene) -> list[Collection]:
    return [c for c in bpy.data.collections if scene.user_of_id(c)]


@contextmanager
def store_and_restore_scene_parameters(
    add_plane: bool, scene: Scene = None
) -> Generator[Any | World, Any, None]:
    if not scene:
        scene = bpy.context.scene
    file_format = scene.render.image_settings.file_format
    filepath = scene.render.filepath
    cameraBackUp = scene.camera
    transparent_backup = scene.render.film_transparent
    rendexXbackUp = scene.render.resolution_x
    rendexYbackUp = scene.render.resolution_y
    backup_world = context.scene.world

    scene.render.film_transparent = True
    scene.render.resolution_x = 256
    scene.render.resolution_y = 256
    scene.use_nodes = False
    scene.render.image_settings.file_format = "PNG"

    # WORLD #
    world: World
    world = bpy.data.worlds.get(WORLD_NAME)
    if not world:
        # print(f"Appending World: {WORLD_NAME}")
        asset_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Assets",
            "Assets.blend" if bpy.app.version >= (3, 4, 0) else "Assets_Old.blend",
        )
        # print(f"    - World Blend: {asset_file}")
        with bpy.data.libraries.load(asset_file, link=False) as (data_from, data_to):
            if WORLD_NAME in data_from.worlds:
                data_to.worlds = [WORLD_NAME]
            # else:
            #     print("    - World not found in data")

        world = bpy.data.worlds.get(WORLD_NAME)
        # if world:
        #     print("    - World found!!")
        # else:
        #     print("    - World not found")

    # world.node_tree.nodes.get("Background").inputs[1].default_value = WORLD_STRENGTH
    world.node_tree.nodes.get("Math").inputs[1].default_value = WORLD_STRENGTH

    scene.world = world

    # RENDER AREA FOR MATERIAL #
    view_area = next(
        (
            area
            # for window in context.window_manager.windows
            for area in context.window_manager.windows[0].screen.areas
            # for area in window.screen.areas
            if area.type == "VIEW_3D"
        ),
        None,
    )

    orig_area_type = None
    orig_area_perspective = None

    if not view_area:
        orig_area_type = context.area.type
        orig_area_perspective = context.region_data.view_perspective

        context.area.type = "VIEW_3D"
        context.area.spaces.active.region_3d.view_perspective = "CAMERA"
        view_area = context.area

    # CAMERA OBJECT #
    camera_data = bpy.data.cameras.new(name="Camera")
    camera_data.clip_end = 10_000_000
    camera_data.clip_start = 0.1
    camera_data.lens = 80

    camera_object = bpy.data.objects.new("Camera", camera_data)
    scene.collection.objects.link(camera_object)

    # TRACK OBJECT #
    track_object = bpy.data.objects.new("Track", object_data=None)
    scene.collection.objects.link(track_object)

    # ADD PLANE #
    ground_plane = None
    if add_plane:
        ground_plane = add_ground_plane(scene)

    yield view_area, camera_object, track_object, ground_plane

    if DEBUG_SCENE:
        return
    # bpy.data.objects.remove(track_object)

    if orig_area_type:
        context.area.type = orig_area_type
        context.region_data.view_perspective = orig_area_perspective

    scene.render.image_settings.file_format = file_format
    scene.render.filepath = filepath
    scene.render.film_transparent = transparent_backup
    scene.render.resolution_x = rendexXbackUp
    scene.render.resolution_y = rendexYbackUp
    scene.world = backup_world
    scene.camera = cameraBackUp

    if backup_world != world:
        if world.node_tree.nodes.get("Environment Texture").image:
            bpy.data.images.remove(
                world.node_tree.nodes.get("Environment Texture").image
            )
        bpy.data.worlds.remove(world)

    if camera_object:
        bpy.data.objects.remove(camera_object, do_unlink=True)

    # track_object removed in yield

    if ground_plane:
        delete_object_with_data(ground_plane)


def setup_scene(
    scene: Scene, add_plane: bool = False
) -> tuple[Area, Object, Object, Object]:
    scene.render.film_transparent = True
    scene.render.resolution_x = 256
    scene.render.resolution_y = 256
    scene.use_nodes = False
    scene.render.image_settings.file_format = "PNG"

    # WORLD #
    world: World
    world = bpy.data.worlds.get(WORLD_NAME)
    if not world:
        asset_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Assets",
            "Assets.blend" if bpy.app.version >= (3, 4, 0) else "Assets_Old.blend",
        )
        with bpy.data.libraries.load(asset_file, link=False) as (data_from, data_to):
            if WORLD_NAME in data_from.worlds:
                data_to.worlds = [WORLD_NAME]

        world = bpy.data.worlds.get(WORLD_NAME)

    world.node_tree.nodes.get("Math").inputs[1].default_value = WORLD_STRENGTH

    scene.world = world

    # RENDER AREA FOR MATERIAL #
    view_area = next(
        (
            area
            for area in context.window_manager.windows[0].screen.areas
            if area.type == "VIEW_3D"
        ),
        None,
    )

    if not view_area:
        context.area.type = "VIEW_3D"
        context.area.spaces.active.region_3d.view_perspective = "CAMERA"
        view_area = context.area

    # CAMERA OBJECT #
    camera_data = bpy.data.cameras.new(name="Camera")
    camera_data.clip_end = 10_000_000
    camera_data.clip_start = 0.1
    camera_data.lens = 80

    camera_object = bpy.data.objects.new("Camera", camera_data)
    scene.collection.objects.link(camera_object)

    # TRACK OBJECT #
    track_object = bpy.data.objects.new("Track", object_data=None)
    scene.collection.objects.link(track_object)

    # ADD PLANE #
    ground_plane = None
    if add_plane:
        ground_plane = add_ground_plane(scene)

    return view_area, camera_object, track_object, ground_plane


def setup_camera_and_track(
    min_bb: Vector, max_bb: Vector, camera_object: Object, track_object: Object
) -> Constraint:
    box_diag_vec = max_bb - min_bb

    # Calculate distance from camera to object
    # 0.44262946093977795 = 25.5 degrees in radians = 80mm lens
    dist = box_diag_vec.magnitude / (
        2 * math.tan((0.44262946093977795 * max(0.0001, CAMERA_OFFSET)) / 2)
    )

    if "X" in CAMERA_ANGLE and "Y" in CAMERA_ANGLE:
        x = y = z = math.sqrt(dist**2 / 3)
    else:
        x = y = math.sqrt(dist**2 / 2) * 1.25
        z = x * 0.5

    # Calculate camera position
    camera_object.location = (
        Vector(
            (
                -x if "-X" in CAMERA_ANGLE else (x if "X" in CAMERA_ANGLE else 0),
                -y if "-Y" in CAMERA_ANGLE else (y if "Y" in CAMERA_ANGLE else 0),
                -z if "-Z" in CAMERA_ANGLE else z,
            )
        )
        + track_object.location
    )

    constraint = camera_object.constraints.new("TRACK_TO")
    constraint.name = "SH_Track_To"
    constraint.target = track_object
    constraint.up_axis = "UP_Y"

    return constraint


def add_ground_plane(scene: Scene) -> Object:
    mesh_data = bpy.data.meshes.new("SH_Plane")
    polycoords = [
        (1000, 1000, 0),
        (1000, -1000, 0),
        (-1000, -1000, 0),
        (-1000, 1000, 0),
    ]
    polyIndices = [(i, (i + 1) % (len(polycoords))) for i in range(0, len(polycoords))]
    mesh_data.from_pydata(
        polycoords, polyIndices, [[i for i in range(0, len(polycoords))]]
    )
    mesh_data.validate()

    ground_plane = bpy.data.objects.new("SH_Plane", mesh_data)

    subsurf_mod: bpy.types.SubsurfModifier = ground_plane.modifiers.new(
        type="SUBSURF", name="TA_SUBSURF"
    )
    subsurf_mod.levels = 4
    subsurf_mod.render_levels = 4
    subsurf_mod.subdivision_type = "SIMPLE"

    scene.collection.objects.link(ground_plane)
    context.view_layer.update()

    return ground_plane


def setup_scene_for_render(
    scene: Scene, camera_object: Object, path: Path, path_id_name: str
):
    render_path = path / (bpy.path.clean_name(path_id_name + "_" + get_id(8)) + ".png")

    scene.render.filepath = str(render_path)
    scene.camera = camera_object

    return render_path


def _setup_scene_for_render(
    scene: Scene, camera_object: Object, path: Path, path_id_name: str
):
    render_path = path / (bpy.path.clean_name(path_id_name + "_" + get_id(8)) + ".png")

    scene.render.filepath = str(render_path)
    scene.camera = camera_object

    return render_path


def render_image(
    context: Context,
    view_area: Area,
    shading: str,
    scene: Scene,
    material_render_func: callable,
):
    engine = scene.render.engine
    if shading == "Material":
        view_area.spaces[0].shading.type = "MATERIAL"
        view_area.spaces[0].overlay.show_overlays = False
        if not DEBUG_SCENE and IS_RENDER:
            material_render_func()
    elif shading == "Eevee":
        scene.render.engine = (
            "BLENDER_EEVEE_NEXT" if bpy.app.version >= (4, 2) else "BLENDER_EEVEE"
        )
        if not DEBUG_SCENE and IS_RENDER:
            bpy.ops.render.render(write_still=True)
    else:  # Cycles
        samples = context.scene.cycles.samples
        context.scene.cycles.samples = 64
        scene.render.engine = "CYCLES"
        if not DEBUG_SCENE and IS_RENDER:
            bpy.ops.render.render(write_still=True)
            context.scene.cycles.samples = samples
    if not DEBUG_SCENE and IS_RENDER:
        scene.render.engine = engine


def calc_camera_position(obj: Object, camera_fov: float) -> Vector:
    """Calculate the camera's position so that the object is in the center of the image and fully visible."""
    # Get min/max of bounding box
    min_x = min_y = min_z = 1_000_000
    max_x = max_y = max_z = -1_000_000
    for v in obj.bound_box:
        min_x = min(min_x, v[0])
        max_x = max(max_x, v[0])
        min_y = min(min_y, v[1])
        max_y = max(max_y, v[1])
        min_z = min(min_z, v[2])
        max_z = max(max_z, v[2])

    # Calculate center of bounding box
    center = (
        Vector(((max_x + min_x) / 2, (max_y + min_y) / 2, (max_z + min_z) / 2))
        + obj.location
    )

    min_t = Vector((min_x, min_y, min_z))
    max_t = Vector((max_x, max_y, max_z))

    box_diag_vec = max_t - min_t

    # Calculate distance from camera to object
    dist = box_diag_vec.magnitude / (2 * math.tan(camera_fov / 2))

    # Calculate camera position
    camera_pos = Vector((center.x, center.y - dist, center.z))

    return camera_pos


def setup_engine(context: Context, shading: str, scene: Scene, view_area: Area):
    if shading == "Material":
        view_area.spaces[0].shading.type = "MATERIAL"
        view_area.spaces[0].overlay.show_overlays = False
    elif shading == "Eevee":
        scene.render.engine = (
            "BLENDER_EEVEE_NEXT" if bpy.app.version >= (4, 2) else "BLENDER_EEVEE"
        )
    else:  # Cycles
        context.scene.cycles.samples = 64
        scene.render.engine = "CYCLES"


def setup_scene_collection(
    context: Context, col: bpy.types.Collection, shading="Material", add_plane=True
):
    scene: Scene = context.scene

    if col not in get_collections_from_scene(scene):
        scene.collection.children.link(col)
        context.view_layer.update()

    selected_objects: list[Object] = set(col.all_objects)

    # // Put in function to share with single_id // #
    view_area, camera_object, track_object, ground_plane = setup_scene(
        scene, add_plane=add_plane
    )

    # bottom_left, top_right = get_bounding_box_of_collection(col, objects_to_ignore=set((ground_plane,)))
    min_bb, max_bb = get_bounding_box_of_collection(col)
    track_object.location = local_bbox_center = (min_bb + max_bb) / 2

    if add_plane and ground_plane:
        min_z = min_bb.z
        ground_plane.location = (local_bbox_center.x, local_bbox_center.y, min_z)

    constraint = setup_camera_and_track(min_bb, max_bb, camera_object, track_object)

    if not DEBUG_SCENE:
        # Must come after extra camera location stuff
        with context.temp_override(object=camera_object):
            bpy.ops.constraint.apply(constraint=constraint.name)

        bpy.data.objects.remove(track_object)

    scene.camera = camera_object

    view_area.spaces.active.region_3d.view_perspective = "CAMERA"

    if ROTATE_WORLD:
        map_node: ShaderNodeMapping = scene.world.node_tree.nodes.get("Mapping")
        if map_node:
            rot_inp = map_node.inputs[2]
            rot_inp.default_value = [
                rot_inp.default_value[0],
                rot_inp.default_value[1],
                0.785398 - camera_object.rotation_euler.z,
            ]

    unselected: list[Object] = [
        a for a in scene.objects if a.name not in selected_objects and a.type != "LIGHT"
    ]

    for obj in unselected:
        obj.hide_render = True
        obj.hide_viewport = True

    for obj in selected_objects:
        obj.hide_render = False
        obj.hide_viewport = False

    if ground_plane:
        ground_plane.hide_render = False
        ground_plane.hide_viewport = False

    setup_engine(context, shading, scene, view_area)
    # // Put in function to share with single_id // #


def _capture_thumbnail_for_collection(
    context: Context,
    col: bpy.types.Collection,
    path: Path,
    shading="Material",
    angle="X",
    add_plane=True,
):
    with store_and_restore_scene_parameters(add_plane, context.scene) as (
        view_area,
        camera_object,
        track_object,
        ground_plane,
    ):
        view_area: Area
        camera_object: Object
        track_object: Object
        ground_plane: Object
        scene: Scene = context.scene

        if col not in get_collections_from_scene(scene):
            scene.collection.children.link(col)

        bottom_left, top_right = get_bounding_box_of_collection(
            col, objects_to_ignore=set((ground_plane,))
        )
        local_bbox_center = (bottom_left + top_right) / 2

        if add_plane and ground_plane:
            min_z = bottom_left.z
            ground_plane.location = (local_bbox_center.x, local_bbox_center.y, min_z)

        global_bbox_center = local_bbox_center
        track_object.location = global_bbox_center
        # dist = max([
        #     abs(top_right.x - bottom_left.x),
        #     abs(top_right.y - bottom_left.y),
        #     abs(top_right.z - bottom_left.z)
        # ])*2
        min_bb, max_bb = get_bounding_box_of_collection(col)
        constraint = setup_camera_and_track(min_bb, max_bb, camera_object, track_object)

        # Must come after extra camera location stuff
        with context.temp_override(object=camera_object):
            bpy.ops.constraint.apply(constraint=constraint.name)

        bpy.data.objects.remove(track_object)

        render_path = _setup_scene_for_render(scene, camera_object, path, col.name)

        override = context.copy()
        view_area.spaces.active.region_3d.view_perspective = "CAMERA"
        override["area"] = view_area
        override["space_data"] = view_area.spaces.active
        override["screen"] = context.window_manager.windows[0].screen
        override["window"] = context.window_manager.windows[0]
        override["active"] = col.all_objects[0] if col.all_objects else None
        if col.all_objects:
            override["selected_objects"] = [
                col.all_objects[0],
            ]

        if ROTATE_WORLD:
            map_node: ShaderNodeMapping = scene.world.node_tree.nodes.get("Mapping")
            if map_node:
                rot_inp = map_node.inputs[2]
                rot_inp.default_value = [
                    rot_inp.default_value[0],
                    rot_inp.default_value[1],
                    0.785398 - camera_object.rotation_euler.z,
                ]

        hidden_render: list[Object] = []
        hidden_viewport: list[Object] = []
        unselected: list[Object] = [
            a for a in scene.objects if a.name not in col.all_objects
        ]

        for obj in unselected:
            if obj.hide_render == False:
                obj.hide_render = True
                hidden_render.append(obj)
            if obj.hide_viewport == False:
                obj.hide_viewport = True
                hidden_viewport.append(obj)

        def render_material():
            with context.temp_override(**override):
                bpy.ops.render.opengl(write_still=True)

        render_image(context, view_area, shading, scene, render_material)

        if DEBUG_SCENE:
            return None

        for obj in hidden_render:
            obj.hide_render = False
        for obj in hidden_viewport:
            obj.hide_viewport = False

    return render_path


def setup_scene_single_id(
    context: bpy.types.Context,
    object: bpy.types.Object,
    shading="Material",
    add_plane=True,
) -> Path:
    scene: Scene = context.scene

    selected_objects: list[Object] = {object}

    if object not in scene.objects[:]:
        scene.collection.objects.link(object)
        context.view_layer.update()

    # // Put in function to share with single_id // #
    view_area, camera_object, track_object, ground_plane = setup_scene(
        scene, add_plane=add_plane
    )

    min_bb, max_bb = get_bounding_box_of_object(object)

    # local_bbox_center = 0.125 * sum(
    #     (
    #         Vector(b)
    #         for b in object.bound_box
    #     ),
    #     Vector()
    # )
    local_bbox_center = (min_bb + max_bb) / 2

    if add_plane and ground_plane:
        # min_z = min((
        #     (object.matrix_world @ Vector(b)).z
        #     for b in object.bound_box
        # ))
        min_z = min_bb.z
        ground_plane.location = (object.location.x, object.location.y, min_z)

    global_bbox_center = object.matrix_world @ local_bbox_center
    track_object.location = global_bbox_center

    constraint = setup_camera_and_track(
        min_bb @ object.matrix_world,
        max_bb @ object.matrix_world,
        camera_object,
        track_object,
    )

    if not DEBUG_SCENE:
        # Must come after extra camera location stuff
        with context.temp_override(object=camera_object):
            bpy.ops.constraint.apply(constraint=constraint.name)

        bpy.data.objects.remove(track_object)

    scene.camera = camera_object

    view_area.spaces.active.region_3d.view_perspective = "CAMERA"

    if ROTATE_WORLD:
        map_node: ShaderNodeMapping = scene.world.node_tree.nodes.get("Mapping")
        if map_node:
            rot_inp = map_node.inputs[2]
            rot_inp.default_value = [
                rot_inp.default_value[0],
                rot_inp.default_value[1],
                0.785398 - camera_object.rotation_euler.z,
            ]

    unselected: list[Object] = [
        a for a in scene.objects if a.name not in selected_objects and a.type != "LIGHT"
    ]

    for obj in unselected:
        obj.hide_render = True
        obj.hide_viewport = True

    for ob in selected_objects:
        ob.hide_render = False
        ob.hide_viewport = False

    if ground_plane:
        ground_plane.hide_render = False
        ground_plane.hide_viewport = False

    setup_engine(context, shading, scene, view_area)
    # // Put in function to share with single_id // #


def _capture_thumbnail(
    context: bpy.types.Context,
    object: bpy.types.Object,
    path: Path,
    shading="Material",
    add_plane=True,
) -> Path:
    with store_and_restore_scene_parameters(add_plane, context.scene) as (
        view_area,
        camera_object,
        track_object,
        ground_plane,
    ):
        view_area: Area
        camera_object: Object
        track_object: Object
        ground_plane: Object
        scene: Scene = context.scene

        if object not in scene.objects[:]:
            scene.collection.objects.link(object)

        local_bbox_center = 0.125 * sum((Vector(b) for b in object.bound_box), Vector())

        if add_plane and ground_plane:
            min_z = min(((object.matrix_world @ Vector(b)).z for b in object.bound_box))
            ground_plane.location = (object.location.x, object.location.y, min_z)

        global_bbox_center = object.matrix_world @ local_bbox_center
        track_object.location = global_bbox_center
        # dist = max(object.dimensions[:])*2
        min_bb, max_bb = get_bounding_box_of_object(object)
        constraint = setup_camera_and_track(min_bb, max_bb, camera_object, track_object)
        # object_matrix = Matrix.LocRotScale(
        #     track_object.location, object.rotation_quaternion, (1,1,1)
        # )
        # camera_object.location = object_matrix @ camera_object.location

        # Must come after extra camera location stuff
        with context.temp_override(object=camera_object):
            bpy.ops.constraint.apply(constraint=constraint.name)

        bpy.data.objects.remove(track_object)

        render_path = _setup_scene_for_render(scene, camera_object, path, object.name)

        view_area.spaces.active.region_3d.view_perspective = "CAMERA"

        if ROTATE_WORLD:
            map_node: ShaderNodeMapping = scene.world.node_tree.nodes.get("Mapping")
            if map_node:
                rot_inp = map_node.inputs[2]
                rot_inp.default_value = [
                    rot_inp.default_value[0],
                    rot_inp.default_value[1],
                    0.785398 - camera_object.rotation_euler.z,
                ]

        hidden_render: list[Object] = []
        hidden_viewport: list[Object] = []
        unselected: list[Object] = [
            a for a in scene.objects if a != object and a != ground_plane
        ]

        for obj in unselected:
            if obj.type != "LIGHT" and obj.hide_render == False:
                obj.hide_render = True
                hidden_render.append(obj)
            if obj.hide_get() == False:
                obj.hide_set(True)
                hidden_viewport.append(obj)

        def render_material():
            og_hide_render = object.hide_render
            object.hide_render = False
            bpy.ops.render.render(write_still=True)
            object.hide_render = og_hide_render

        render_image(context, view_area, shading, scene, render_material)

        if DEBUG_SCENE:
            return None

        for obj in hidden_viewport:
            obj.hide_set(False)
        for obj in hidden_render:
            obj.hide_render = False

    return render_path


def setup_scene_for_thumbnail(context, ob, shading="Solid"):
    thumbnail_path = Path(OBJECTS_PATH, "Thumbanils")
    thumbnail_path.mkdir(parents=True, exist_ok=True)

    if shading != "Solid":
        if isinstance(ob, bpy.types.Collection):
            setup_scene_collection(context, ob, shading=shading, add_plane=ADD_PLANE)
        else:
            setup_scene_single_id(context, ob, shading=shading, add_plane=ADD_PLANE)
        # print(path)
        # if os.path.isfile(path):
        #     with context.temp_override(id=ob):
        #         bpy.ops.ed.lib_id_load_custom_preview(filepath=str(path))
    else:
        ob.asset_generate_preview()


def _create_thumbnail(context, ob, shading="Solid"):
    thumbnail_path = Path(OBJECTS_PATH, "Thumbanils")
    thumbnail_path.mkdir(parents=True, exist_ok=True)

    if shading != "Solid":
        if isinstance(ob, bpy.types.Collection):
            path = _capture_thumbnail_for_collection(
                context, ob, thumbnail_path, shading, add_plane=ADD_PLANE
            )
        else:
            path = _capture_thumbnail(
                context, ob, thumbnail_path, shading, add_plane=ADD_PLANE
            )
        # print(path)
        if os.path.isfile(path):
            with context.temp_override(id=ob):
                bpy.ops.ed.lib_id_load_custom_preview(filepath=str(path))
    else:
        ob.asset_generate_preview()


def check_if_volumetric(mat):
    if mat.use_nodes:
        output_nodes = [
            node
            for node in mat.node_tree.nodes
            if node.bl_idname == "ShaderNodeOutputMaterial"
        ]
        for node in output_nodes:
            if node.inputs[1].is_linked:
                return True


def apply_thumbnail():
    pP = Path(FILEPATH)
    dir = pP.parent

    print("Applying Thumbnail")

    for i, id_type in enumerate(TYPES):
        id_name = NAMES[i]
        thumbnail_path = dir / f"{pP.stem}=+={id_name}=+={id_type}_thumbnail_1.png"
        print("Thumbnail Path:", thumbnail_path)

        if not thumbnail_path.is_file():
            print("  - Not found")
            data_type = ASSET_TYPES_TO_ID_TYPES.get(id_type)
            data = getattr(bpy.data, data_type)
            item = data.get(id_name)
            if hasattr(item, "asset_generate_preview"):
                print("  - Generating Preview")
                item.asset_generate_preview()
            elif hasattr(item, "data") and hasattr(item.data, "asset_generate_preview"):
                print("  - Generating Preview")
                item.data.asset_generate_preview()
            continue

        if id_type == "COLLECTION":
            ob = bpy.data.collections.get(NAMES[i])
            print("  - Is Collection:", ob)
            if ob:
                with context.temp_override(id=ob):
                    bpy.ops.ed.lib_id_load_custom_preview(filepath=str(thumbnail_path))
                    print("  - Thumbnail set")
        elif id_type == "MATERIAL":
            print("  - Is Material:", ob)
            ob = bpy.data.materials.get(NAMES[i])
            print("  - Not Implemented?")
            continue
        else:
            ob = bpy.data.objects.get(NAMES[i])
            print("  - Is Single ID:", ob)
            if ob:
                if ob.type in {
                    "MESH",
                    "CURVE",
                    "SURFACE",
                    "FONT",
                    "TEXT",
                    "META",
                    "VOLUME",
                } and does_support_thumbnails(ob):
                    with context.temp_override(id=ob):
                        bpy.ops.ed.lib_id_load_custom_preview(
                            filepath=str(thumbnail_path)
                        )
                        print("  - Thumbnail set")
                else:
                    print(f"  - Object type '{ob.type}' not supported")
            else:
                print("  - Object not found:", NAMES[i])

        if not DEBUG_SCENE:
            thumbnail_path.unlink(missing_ok=True)
    # bpy.ops.wm.save_as_mainfile(filepath=FILEPATH)
    bpy.ops.wm.save_as_mainfile()
    p = Path(bpy.data.filepath)
    p.with_stem(p.stem + "_1").unlink(missing_ok=True)
    advance()


def create_preview(objects: list[bpy.types.ID]):
    print("Create Preview:", len(objects))
    global FILEPATHS, FILEPATH, ALL_NAMES, ALL_TYPES, NAMES, TYPES
    obs = objects[:]
    while obs:
        ob = obs[0]
        if (
            not ob.preview
            or any(ob.preview.image_pixels[:])
            or SHADING != "Solid"
            or (type == "MATS" and check_if_volumetric(ob))
        ):
            obs.pop(0)
        else:
            print("Trying again in 1sec")
            return 1

    print("Saving File: Has Camera:", bpy.context.scene.camera)
    bpy.ops.wm.save_mainfile()
    p = Path(bpy.data.filepath)
    p.with_stem(p.stem + "_1").unlink(missing_ok=True)

    bk = FILEPATH + "1"
    if os.path.exists(bk):
        os.remove(bk)

    if FILEPATHS and ALL_NAMES and ALL_TYPES:
        FILEPATH = FILEPATHS.pop(0)
        NAMES = ALL_NAMES.pop(0).split(":--separator--:")
        TYPES = ALL_TYPES.pop(0).split(":--separator--:")
        print(f"Next File: {FILEPATH}, Names: {NAMES}, Types: {TYPES}")
        bpy.ops.wm.open_mainfile(filepath=FILEPATH, load_ui=False)
        if IS_SETUP:
            setup_blend()
        else:
            apply_thumbnail()
    else:
        print("Finished All Previews")
        bpy.ops.wm.quit_blender()
    return None


def advance() -> None:
    global FILEPATHS, FILEPATH, ALL_NAMES, ALL_TYPES, NAMES, TYPES
    if FILEPATHS and ALL_NAMES and ALL_TYPES:
        FILEPATH = FILEPATHS.pop(0)
        NAMES = ALL_NAMES.pop(0).split(":--separator--:")
        if len(NAMES) == 1 and ":--separator2--:" in NAMES[0]:
            NAMES = NAMES[0].split(":--separator2--:")
        TYPES = ALL_TYPES.pop(0).split(":--separator--:")
        if len(TYPES) == 1 and ":--separator2--:" in TYPES[0]:
            TYPES = TYPES[0].split(":--separator2--:")
        print()
        print(f"Next File: {FILEPATH}, Names: {NAMES}, Types: {TYPES}".center(100, "-"))
        print()
        bpy.ops.wm.open_mainfile(filepath=FILEPATH, load_ui=False)
        if IS_SETUP:
            setup_blend()
        else:
            apply_thumbnail()
    else:
        print("Finished All Previews")
        bpy.ops.wm.quit_blender()


def setup_blend():
    global TYPES
    global NAMES
    global FILEPATHS
    global ALL_NAMES
    global ALL_TYPES
    print("Setup Types:", TYPES)
    print("Setup Names:", NAMES)
    try:
        objects = []
        for i, id_type in enumerate(TYPES):
            id_name = NAMES[i]
            if id_type == "COLLECTION":
                ob = bpy.data.collections.get(id_name)
                if ob:
                    objects.append(ob)
                    setup_scene_for_thumbnail(bpy.context, ob, shading=SHADING)
                    p = Path(bpy.data.filepath)
                    new_path = p.with_stem(
                        f"{p.stem}=+={ob.name}=+=COLLECTION_thumbnail_copy"
                    )
                    print("Saving as:", new_path)
                    bpy.ops.wm.save_as_mainfile(filepath=str(new_path), copy=True)
                    new_path.with_stem(new_path.stem + "_1").unlink(missing_ok=True)
            elif id_type == "MATERIAL":
                mat = bpy.data.materials.get(id_name)
                objects.append(mat)
                if mat:
                    print("  - Generating Preview: mat")
                    mat.asset_generate_preview()
            elif id_type == "OBJECT":
                ob = bpy.data.objects.get(id_name)
                if ob:
                    if ob.type in {"MESH", "CURVE", "SURFACE", "TEXT", "META"}:
                        ob.display_type = "TEXTURED"
                    if does_support_thumbnails(ob):
                        print(f"Is renderable Object: {ob.type}")
                        print(
                            f"     - {ob.type in supports_thumbnails} = {ob.type} in {supports_thumbnails}"
                        )
                        objects.append(ob)
                        setup_scene_for_thumbnail(bpy.context, ob, shading=SHADING)
                        p = Path(bpy.data.filepath)
                        new_path = p.with_stem(
                            f"{p.stem}=+={ob.name}=+={id_type}_thumbnail_copy"
                        )
                        print("Saving as:", new_path)
                        bpy.ops.wm.save_as_mainfile(filepath=str(new_path), copy=True)
                        new_path.with_stem(new_path.stem + "_1").unlink(missing_ok=True)
                    else:
                        print(f"Object type '{ob.type}' not renderable")
                        if hasattr(ob, "asset_generate_preview"):
                            print("  - Generating Preview: ob")
                            ob.asset_generate_preview()
                        elif hasattr(ob, "data") and hasattr(
                            ob.data, "asset_generate_preview"
                        ):
                            print("  - Generating Preview: ob.data")
                            ob.data.asset_generate_preview()
        # bpy.app.timers.register(
        #     functools.partial(
        #         create_preview,
        #         objects
        #     ),
        #     first_interval=0
        # )
        # print("  - Added Timer")
        advance()
    except Exception as e:
        traceback.print_exc()
        print(e, "An Error Ocurred!")


def _start_regenerating():
    print("Types:", TYPES)
    print("Names:", NAMES)
    try:
        objects = []
        for i, a in enumerate(TYPES):
            if a == "COLLECTION":
                ob = bpy.data.collections.get(NAMES[i])
                if ob:
                    objects.append(ob)
                    _create_thumbnail(bpy.context, ob, SHADING)
            elif a == "MATERIAL":
                ob = bpy.data.materials.get(NAMES[i])
                objects.append(ob)
                if ob:
                    ob.asset_generate_preview()
            else:
                ob = bpy.data.objects.get(NAMES[i])
                if ob:
                    if ob.type in {"MESH", "CURVE", "SURFACE", "TEXT", "META"}:
                        ob.display_type = "TEXTURED"
                    if does_support_thumbnails(ob):
                        objects.append(ob)
                        _create_thumbnail(bpy.context, ob, SHADING)
        bpy.app.timers.register(
            functools.partial(create_preview, objects), first_interval=0
        )
    except Exception as e:
        traceback.print_exc()
        print(e, "An Error Ocurred!")


if __name__ == "__main__":
    if IS_SETUP:
        setup_blend()
    else:
        apply_thumbnail()
    # _start_regenerating()
    print("REACHED END OF SCRIPT".center(100, "*"))
