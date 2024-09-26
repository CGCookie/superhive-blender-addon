import bpy
import sys
import os
import time
import functools
import mathutils
import random
import uuid
import re

argv = sys.argv
argv = argv[argv.index("--") + 1 :]

FILEPATHS = argv[0].split(":-path-:")
OBJECTS_PATH = argv[1]
OVERRIDE = argv[2]
SHADING = argv[3]
ENGINE = argv[4]
MAX_TIME = float(argv[5])
FORCE_PREVIEWS = argv[6] == "True"
CAMERA_ANGLE = argv[7]
CATALOG = argv[8]
ADD_PLANE = argv[9] == "True"
WORLD_STRENGTH = float(argv[10])

USE_AUTO_BONE_ORIENTATION = argv[11] == "True"  # Better FBX
MY_CALCULATE_ROLL = argv[12]  # Better FBX
MY_BONE_LENGTH = float(argv[13])  # Better FBX
MY_LEAF_BONE = argv[14]  # Better FBX
USE_FIX_BONE_POSES = argv[15] == "True"
USE_FIX_ATTRIBUTES = argv[16] == "True"
USE_ONLY_DEFORM_BONES = argv[17] == "True"
USE_VERTEX_ANIMATION = argv[18] == "True"
USE_ANIMATION = argv[19] == "True"
MY_ANIMATION_OFFSET = float(argv[20])  # Better FBX
USE_ANIMATION_PREFIX = argv[21] == "True"
USE_TRIANGULATE = argv[22] == "True"
MY_IMPORT_NORMAL = argv[23]  # Better FBX
USE_AUTO_SMOOTH = argv[24] == "True"
MY_ANGLE = float(argv[25])  # Better FBX
MY_SHADE_MODE = argv[26]  # Better FBX
MY_SCALE = float(argv[27])  # Better FBX
USE_OPTIMIZE_FOR_BLENDER = argv[28] == "True"
USE_RESET_MESH_ORIGIN = argv[29] == "True"
USE_EDGE_CREASE = argv[30] == "True"
MY_EDGE_CREASE_SCALE = float(argv[31])  # Better FBX
MY_EDGE_SMOOTHING = argv[32]  # Better FBX
USE_IMPORT_MATERIALS = argv[33] == "True"
USE_RENAME_BY_FILENAME = argv[34] == "True"
MY_ROTATION_MODE = argv[35]  # Better FBX
USE_MANUAL_ORIENTATION = argv[36] == "True"
GLOBAL_SCALE = float(argv[37])
BAKE_SPACE_TRANSFORM = argv[38] == "True"
USE_CUSTOM_NORMALS = argv[39] == "True"
COLORS_TYPE = argv[40]
USE_IMAGE_SEARCH = argv[41] == "True"
USE_ALPHA_DECALS = argv[42] == "True"
DECAL_OFFSET = float(argv[43])
USE_ANIM = argv[44] == "True"
ANIM_OFFSET = float(argv[45])
USE_SUBSURF = argv[46] == "True"
USE_CUSTOM_PROPS = argv[47] == "True"
USE_CUSTOM_PROPS_ENUM_AS_STRING = argv[48] == "True"
IGNORE_LEAF_BONES = argv[49] == "True"
FORCE_CONNECT_CHILDREN = argv[50] == "True"
AUTOMATIC_BONE_ORIENTATION = argv[51] == "True"
PRIMARY_BONE_AXIS = argv[52]
SECONDARY_BONE_AXIS = argv[53]
USE_PREPOST_ROT = argv[54] == "True"
AXIS_FORWARD = argv[55]
AXIS_UP = argv[56]
IMPORTER = argv[57]
PACK = argv[58] == "True"
SINGLE_FILE = argv[59] == "True"
MAKE_COLLECTION = argv[60] == "True"

# Assert statements to ensure correct types
assert isinstance(FILEPATHS, list)
assert all(isinstance(path, str) for path in FILEPATHS)
assert isinstance(OBJECTS_PATH, str)
assert isinstance(OVERRIDE, str)
assert isinstance(SHADING, str)
assert isinstance(ENGINE, str)
assert isinstance(MAX_TIME, float)
assert isinstance(FORCE_PREVIEWS, bool)
assert isinstance(CAMERA_ANGLE, str)
assert isinstance(CATALOG, str)
assert isinstance(ADD_PLANE, bool)
assert isinstance(WORLD_STRENGTH, float)

assert isinstance(USE_AUTO_BONE_ORIENTATION, bool)
assert isinstance(MY_CALCULATE_ROLL, str)
assert isinstance(MY_BONE_LENGTH, float)
assert isinstance(MY_LEAF_BONE, str)
assert isinstance(USE_FIX_BONE_POSES, bool)
assert isinstance(USE_FIX_ATTRIBUTES, bool)
assert isinstance(USE_ONLY_DEFORM_BONES, bool)
assert isinstance(USE_VERTEX_ANIMATION, bool)
assert isinstance(USE_ANIMATION, bool)
assert isinstance(MY_ANIMATION_OFFSET, float)
assert isinstance(USE_ANIMATION_PREFIX, bool)
assert isinstance(USE_TRIANGULATE, bool)
assert isinstance(MY_IMPORT_NORMAL, str)
assert isinstance(USE_AUTO_SMOOTH, bool)
assert isinstance(MY_ANGLE, float)
assert isinstance(MY_SHADE_MODE, str)
assert isinstance(MY_SCALE, float)
assert isinstance(USE_OPTIMIZE_FOR_BLENDER, bool)
assert isinstance(USE_RESET_MESH_ORIGIN, bool)
assert isinstance(USE_EDGE_CREASE, bool)
assert isinstance(MY_EDGE_CREASE_SCALE, float)
assert isinstance(MY_EDGE_SMOOTHING, str)
assert isinstance(USE_IMPORT_MATERIALS, bool)
assert isinstance(USE_RENAME_BY_FILENAME, bool)
assert isinstance(MY_ROTATION_MODE, str)
assert isinstance(USE_MANUAL_ORIENTATION, bool)
assert isinstance(GLOBAL_SCALE, float)
assert isinstance(BAKE_SPACE_TRANSFORM, bool)
assert isinstance(USE_CUSTOM_NORMALS, bool)
assert isinstance(COLORS_TYPE, str)
assert isinstance(USE_IMAGE_SEARCH, bool)
assert isinstance(USE_ALPHA_DECALS, bool)
assert isinstance(DECAL_OFFSET, float)
assert isinstance(USE_ANIM, bool)
assert isinstance(ANIM_OFFSET, float)
assert isinstance(USE_SUBSURF, bool)
assert isinstance(USE_CUSTOM_PROPS, bool)
assert isinstance(USE_CUSTOM_PROPS_ENUM_AS_STRING, bool)
assert isinstance(IGNORE_LEAF_BONES, bool)
assert isinstance(FORCE_CONNECT_CHILDREN, bool)
assert isinstance(AUTOMATIC_BONE_ORIENTATION, bool)
assert isinstance(PRIMARY_BONE_AXIS, str)
assert isinstance(SECONDARY_BONE_AXIS, str)
assert isinstance(USE_PREPOST_ROT, bool)
assert isinstance(AXIS_FORWARD, str)
assert isinstance(AXIS_UP, str)
assert isinstance(IMPORTER, str)
assert isinstance(PACK, bool)
assert isinstance(SINGLE_FILE, bool)
assert isinstance(MAKE_COLLECTION, bool)

# FILEPATH=FILEPATHS.pop(0)
supports_thumbnails = ["MESH", "LIGHT"]
context = bpy.context
scene = context.scene
st = time.time()

bpy.ops.wm.read_homefile(app_template="")
bpy.context.preferences.system.texture_collection_rate = 5
bpy.context.preferences.system.texture_time_out = 5
for o in bpy.data.objects:
    bpy.data.objects.remove(o)
random_id_source = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
RENDER_DEVICE = argv[61]


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
    print("GPUs enabled")
except Exception as e:
    print(e)


def decode_catalog_name(catalog):
    if catalog == "Filename":
        return os.path.splitext(os.path.basename(FILEPATH))[0]
    elif catalog == "Directory":
        return os.path.basename(os.path.dirname(FILEPATH))
    else:
        return catalog


def get_id(length=6):
    return "".join(random.sample(random_id_source, length))


def find_scene_from_object(object):
    for s in bpy.data.scenes:
        if object in s.objects[:]:
            return s
    return None


def get_random_uuid():
    return str(uuid.uuid4())


def get_name_to_display(name):
    if "/" in name:
        # substr=name[name.rindex("/")+1:]
        return name[name.rindex("/") + 1 :] + f" ({name[: name.rindex('/')]})"
    else:
        return name


def get_catalog_by_name(path, name):
    if os.path.isfile(os.path.join(path, "blender_assets.cats.txt")):
        with open(
            os.path.join(path, "blender_assets.cats.txt"),
            mode="r",
            newline="\n",
            encoding="UTF-8",
        ) as catalog_file:
            for l in catalog_file.readlines():
                if not l.startswith("#") and not l.startswith("VERSION") and ":" in l:
                    if l[l.index(":") + 1 : l.rindex(":")] == name:
                        return l[: l.index(":")]
    return None


def create_new_catalog(path, name):
    uuids = []
    # uuid=get_random_uuid()
    result = [_.start() for _ in re.finditer("/", name)] + [
        len(name),
    ]
    for a in range(len(result)):
        uuids.append(get_random_uuid())
    if not os.path.isfile(os.path.join(path, "blender_assets.cats.txt")):
        with open(
            os.path.join(path, "blender_assets.cats.txt"),
            mode="w+",
            newline="\n",
            encoding="UTF-8",
        ) as catalog_file:
            catalog_file.writelines([
                "\nVERSION 1",
            ])
            for index, i in enumerate(result):
                if not get_catalog_by_name(path, name[:i]):
                    catalog_file.writelines([
                        "\n" + uuids[index] + f":{name[:i]}:{name[:i]}\n",
                    ])
    else:
        if os.path.isfile(os.path.join(path, "blender_assets.cats.txt")):
            with open(
                os.path.join(path, "blender_assets.cats.txt"),
                mode="a",
                newline="\n",
                encoding="UTF-8",
            ) as catalog_file:
                for index, i in enumerate(result):
                    if not get_catalog_by_name(path, name[:i]):
                        catalog_file.writelines([
                            "\n" + uuids[index] + f":{name[:i]}:{name[:i]}\n",
                        ])

    return (
        get_catalog_by_name(path, name)
        if get_catalog_by_name(path, name)
        else "00000000-0000-0000-0000-000000000000"
    )


def delete_object_with_data(obj):
    if obj and obj.name in bpy.data.objects:
        data = obj.data
        isMesh = obj.type == "MESH"
        bpy.data.objects.remove(obj, do_unlink=True)
        if isMesh:
            bpy.data.meshes.remove(data)


def get_bounding_box_of_collection(col):
    corners = []
    for ob in col.all_objects:
        corners.extend([(ob.matrix_world @ mathutils.Vector(b)) for b in ob.bound_box])
    min_z = min(((mathutils.Vector(b)).z for b in corners))
    max_z = max(((mathutils.Vector(b)).z for b in corners))
    min_x = min(((mathutils.Vector(b)).x for b in corners))
    max_x = max(((mathutils.Vector(b)).x for b in corners))
    min_y = min(((mathutils.Vector(b)).y for b in corners))
    max_y = max(((mathutils.Vector(b)).y for b in corners))
    return mathutils.Vector((min_x, min_y, min_z)), mathutils.Vector((
        max_x,
        max_y,
        max_z,
    ))


def get_collections_from_scene(scene):
    return [c for c in bpy.data.collections if scene.user_of_id(c)]


def get_biggest_object_from(col):
    if col.all_objects:
        max_volume_object = col.all_objects[0]
        for object in col.all_objects:
            if (
                object.dimensions.x * object.dimensions.y * object.dimensions.z
                > max_volume_object.dimensions.x
                * max_volume_object.dimensions.y
                * max_volume_object.dimensions.z
            ):
                max_volume_object = object
        return object
    return None


def join_meshes_with_same_parent(scene):
    return
    # print(parent,objects)
    objects = scene.objects
    for col in bpy.data.collections:
        objects = col.all_objects
        if objects:
            override = context.copy()
            for area in context.window_manager.windows[0].screen.areas:
                area.type = "VIEW_3D"
                # override['scene']=scene
                override["area"] = area
                override["space_data"] = area.spaces[0]
                override["screen"] = context.window_manager.windows[0].screen
                override["window"] = context.window_manager.windows[0]
                override["selected_objects"] = objects
                override["object"] = objects[0]
                override["active_object"] = objects[0]
                override["selected_editable_objects"] = objects
                view_area = area
                break
            if not SINGLE_FILE:
                objects[0].name = os.path.splitext(os.path.basename(FILEPATH))[0]
            try:
                bpy.ops.object.make_single_user(
                    override,
                    type="ALL",
                    object=True,
                    obdata=True,
                    material=False,
                    animation=False,
                    obdata_animation=False,
                )
            except:
                print("Could not make single user!")
            # for obj in objects:
            #     print(obj)
            # bpy.ops.object.convert(override,target='MESH', keep_original=False)

            # if APPLY_ROTATION:

            bpy.ops.object.transform_apply(
                override, location=False, rotation=True, scale=False, isolate_users=True
            )
            # if CLEAR_PARENT:
            #     bpy.ops.object.parent_clear(override,type='CLEAR_KEEP_TRANSFORM')
            if not MAKE_COLLECTION:
                if len(objects) > 1:
                    bpy.ops.object.join(override)
            # else:
            #     #print("Moving..",objects,parent)
            #     bpy.ops.object.move_to_collection(override,collection_index=0, is_new=True, new_collection_name=parent)


def capture_thumbnail_for_collection(
    context, col, path, shading="Material", angle="X", add_plane=True
):
    # print(object)
    hidden = []
    # if object not in context.window_manager.windows[0].scene.objects[:]:
    #     context.window_manager.windows[0].scene=find_scene_from_object(object) if find_scene_from_object(object) else context.window_manager.windows[0].scene
    #     print("New Scene",context.window_manager.windows[0].scene)

    scene = context.scene
    scene.render.image_settings.file_format = "PNG"
    if col not in get_collections_from_scene(scene):
        scene.collection.children.link(col)
    view_area = None
    filepath = scene.render.filepath

    render_path = os.path.join(
        path, bpy.path.clean_name(col.name + "_" + get_id(8)) + ".png"
    )
    scene.render.filepath = render_path
    cameraBackUp = scene.camera
    camera_data = bpy.data.cameras.new(name="Camera")
    camera_data.clip_end = 10000000
    camera_object = bpy.data.objects.new("Camera", camera_data)
    scene.collection.objects.link(camera_object)
    track_object = bpy.data.objects.new("Track", object_data=None)
    scene.collection.objects.link(track_object)
    bottom_left, top_right = get_bounding_box_of_collection(col)
    local_bbox_center = (bottom_left + top_right) / 2
    ground_plane = None
    if add_plane:
        mesh_data = bpy.data.meshes.new("TA_Plane")
        polycoords = [
            (1000, 1000, 0),
            (1000, -1000, 0),
            (-1000, -1000, 0),
            (-1000, 1000, 0),
        ]
        polyIndices = [
            (i, (i + 1) % (len(polycoords))) for i in range(0, len(polycoords))
        ]
        mesh_data.from_pydata(
            polycoords, polyIndices, [[i for i in range(0, len(polycoords))]]
        )
        mesh_data.validate()
        ground_plane = bpy.data.objects.new("TA_Plane", mesh_data)
        subsurf_mod = ground_plane.modifiers.new(type="SUBSURF", name="TA_SUBSURF")
        subsurf_mod.levels = 4
        subsurf_mod.render_levels = 4
        subsurf_mod.subdivision_type = "SIMPLE"
        scene.collection.objects.link(ground_plane)
        min_z = bottom_left.z
        ground_plane.location = (local_bbox_center.x, local_bbox_center.y, min_z)
    global_bbox_center = local_bbox_center
    track_object.location = global_bbox_center
    dist = (
        max([
            abs(top_right.x - bottom_left.x),
            abs(top_right.y - bottom_left.y),
            abs(top_right.z - bottom_left.z),
        ])
        * 2
    )
    object = get_biggest_object_from(col)
    if object:
        object_matrix = mathutils.Matrix.LocRotScale(
            track_object.location, object.rotation_quaternion, [1, 1, 1]
        )
        camera_object.location = object_matrix @ mathutils.Vector((
            -dist if "-X" in CAMERA_ANGLE else (dist if "X" in CAMERA_ANGLE else 0),
            dist if "-Y" in CAMERA_ANGLE else (-dist if "Y" in CAMERA_ANGLE else 0),
            dist * (-1 if "-Z" in CAMERA_ANGLE else 1),
        ))
    else:
        camera_object.location = mathutils.Vector((
            -dist if "-X" in CAMERA_ANGLE else (dist if "X" in CAMERA_ANGLE else 0),
            dist if "-Y" in CAMERA_ANGLE else (-dist if "Y" in CAMERA_ANGLE else 0),
            dist * (-1 if "-Z" in CAMERA_ANGLE else 1),
        ))

    constraint = camera_object.constraints.new("TRACK_TO")
    constraint.name = "TA_Track_To"
    constraint.target = track_object
    constraint.up_axis = "UP_Y"
    # override = context.copy()
    # override["object"] = camera_object
    with context.temp_override(object=camera_object):
        bpy.ops.constraint.apply(constraint=constraint.name)
    bpy.data.objects.remove(track_object)
    scene.camera = camera_object
    camera_data.lens = 80
    transparent_backup = scene.render.film_transparent
    scene.render.film_transparent = True
    rendexXbackUp = scene.render.resolution_x
    rendexYbackUp = scene.render.resolution_y
    scene.render.resolution_x = 256
    scene.render.resolution_y = 256
    scene.use_nodes = False
    override = context.copy()
    for area in context.window_manager.windows[0].screen.areas:
        area.type = "VIEW_3D"
        # override['scene']=scene
        override["area"] = area
        override["space_data"] = area.spaces[0]
        override["screen"] = context.window_manager.windows[0].screen
        override["window"] = context.window_manager.windows[0]
        area.spaces[0].region_3d.view_perspective = "CAMERA"
        override["active"] = col.all_objects[0] if col.all_objects else None
        if col.all_objects:
            override["selected_objects"] = [
                col.all_objects[0],
            ]
        view_area = area
        break

    if not bpy.data.worlds.get("TA_Thumbnail_World"):
        asset_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Assets",
            "Assets.blend" if bpy.app.version >= (3, 4, 0) else "Assets_Old.blend",
            "World",
        )
        with context.temp_override(**override):
            bpy.ops.wm.append(
                directory=asset_file, filename="TA_Thumbnail_World", autoselect=False
            )
    context.scene.world = bpy.data.worlds.get("TA_Thumbnail_World")
    map_node = context.scene.world.node_tree.nodes.get("Mapping")
    context.scene.world.node_tree.nodes.get("Background").inputs[
        1
    ].default_value = WORLD_STRENGTH
    if map_node:
        map_node.inputs[2].default_value = [
            map_node.inputs[2].default_value[0],
            map_node.inputs[2].default_value[1],
            0.785398 - camera_object.rotation_euler.z,
        ]
    if shading == "Material" or shading == "Solid-TA":
        view_area.spaces[0].shading.type = (
            "MATERIAL" if shading == "Material" else "SOLID"
        )
        view_area.spaces[0].overlay.show_overlays = False
        unselected = [a for a in scene.objects if a.name not in col.all_objects]
        for obj in unselected:
            if obj.hide_viewport == False:
                obj.hide_viewport = True
                hidden.append(obj)
        with context.temp_override(**override):
            bpy.ops.render.opengl(write_still=True)
        for obj in hidden:
            obj.hide_viewport = False

    elif shading == "Eevee":
        engine = scene.render.engine
        scene.render.engine = "BLENDER_EEVEE"
        unselected = [a for a in scene.objects if a.name not in col.all_objects]
        for obj in unselected:
            if obj.hide_render == False:
                obj.hide_render = True
                hidden.append(obj)
        bpy.ops.render.render(write_still=True)
        scene.render.engine = engine
        for obj in hidden:
            obj.hide_render = False
    else:
        samples = context.scene.cycles.samples
        context.scene.cycles.samples = 64
        engine = scene.render.engine
        scene.render.engine = "CYCLES"
        unselected = [a for a in scene.objects if a.name not in col.all_objects]
        for obj in unselected:
            if obj.hide_render == False:
                obj.hide_render = True
                hidden.append(obj)
        bpy.ops.render.render(write_still=True)
        context.scene.cycles.samples = samples
        scene.render.engine = engine
        for obj in hidden:
            obj.hide_render = False

    scene.render.resolution_x = rendexXbackUp
    scene.render.resolution_y = rendexYbackUp
    scene.render.film_transparent = transparent_backup
    scene.render.filepath = filepath
    if camera_object:
        bpy.data.objects.remove(camera_object, do_unlink=True)
    if ground_plane:
        delete_object_with_data(ground_plane)
    scene.camera = cameraBackUp
    return render_path


def capture_thumbnail(
    context, object, path, shading="Material", angle="X", add_plane=True
):
    # print(object)
    hidden = []
    # if object not in context.window_manager.windows[0].scene.objects[:]:
    #     context.window_manager.windows[0].scene=find_scene_from_object(object) if find_scene_from_object(object) else context.window_manager.windows[0].scene
    #     print("New Scene",context.window_manager.windows[0].scene)

    scene = context.scene
    scene.render.image_settings.file_format = "PNG"
    if object not in scene.objects[:]:
        scene.collection.objects.link(object)
    view_area = None
    filepath = scene.render.filepath

    render_path = os.path.join(
        path, bpy.path.clean_name(object.name + "_" + get_id(8)) + ".png"
    )
    scene.render.filepath = render_path
    cameraBackUp = scene.camera
    camera_data = bpy.data.cameras.new(name="Camera")
    camera_data.clip_end = 10000000
    camera_object = bpy.data.objects.new("Camera", camera_data)
    scene.collection.objects.link(camera_object)
    track_object = bpy.data.objects.new("Track", object_data=None)
    scene.collection.objects.link(track_object)
    local_bbox_center = 0.125 * sum(
        (mathutils.Vector(b) for b in object.bound_box), mathutils.Vector()
    )
    ground_plane = None
    if add_plane:
        mesh_data = bpy.data.meshes.new("TA_Plane")
        polycoords = [
            (1000, 1000, 0),
            (1000, -1000, 0),
            (-1000, -1000, 0),
            (-1000, 1000, 0),
        ]
        polyIndices = [
            (i, (i + 1) % (len(polycoords))) for i in range(0, len(polycoords))
        ]
        mesh_data.from_pydata(
            polycoords, polyIndices, [[i for i in range(0, len(polycoords))]]
        )
        mesh_data.validate()
        ground_plane = bpy.data.objects.new("TA_Plane", mesh_data)
        subsurf_mod = ground_plane.modifiers.new(type="SUBSURF", name="TA_SUBSURF")
        subsurf_mod.levels = 4
        subsurf_mod.render_levels = 4
        subsurf_mod.subdivision_type = "SIMPLE"
        scene.collection.objects.link(ground_plane)
        min_z = min(
            ((object.matrix_world @ mathutils.Vector(b)).z for b in object.bound_box)
        )
        ground_plane.location = (object.location.x, object.location.y, min_z)
    global_bbox_center = object.matrix_world @ local_bbox_center
    track_object.location = global_bbox_center
    dist = max(object.dimensions[:]) * 2
    object_matrix = mathutils.Matrix.LocRotScale(
        track_object.location, object.rotation_quaternion, [1, 1, 1]
    )
    camera_object.location = object_matrix @ mathutils.Vector((
        -dist if "-X" in CAMERA_ANGLE else (dist if "X" in CAMERA_ANGLE else 0),
        dist if "-Y" in CAMERA_ANGLE else (-dist if "Y" in CAMERA_ANGLE else 0),
        dist * (-1 if "-Z" in CAMERA_ANGLE else 1),
    ))

    constraint = camera_object.constraints.new("TRACK_TO")
    constraint.name = "TA_Track_To"
    constraint.target = track_object
    constraint.up_axis = "UP_Y"
    # override = context.copy()
    # override["object"] = camera_object
    with context.temp_override(object=camera_object):
        bpy.ops.constraint.apply(constraint=constraint.name)
    bpy.data.objects.remove(track_object)
    scene.camera = camera_object
    camera_data.lens = 80
    transparent_backup = scene.render.film_transparent
    scene.render.film_transparent = True
    rendexXbackUp = scene.render.resolution_x
    rendexYbackUp = scene.render.resolution_y
    scene.render.resolution_x = 256
    scene.render.resolution_y = 256
    scene.use_nodes = False
    override = context.copy()
    for area in context.window_manager.windows[0].screen.areas:
        area.type = "VIEW_3D"
        # override['scene']=scene
        override["area"] = area
        override["space_data"] = area.spaces[0]
        override["screen"] = context.window_manager.windows[0].screen
        override["window"] = context.window_manager.windows[0]
        area.spaces[0].region_3d.view_perspective = "CAMERA"
        override["active"] = object
        override["selected_objects"] = [
            object,
        ]
        view_area = area
        break

    if not bpy.data.worlds.get("TA_Thumbnail_World"):
        asset_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Assets",
            "Assets.blend" if bpy.app.version >= (3, 4, 0) else "Assets_Old.blend",
            "World",
        )
        with context.temp_override(**override):
            bpy.ops.wm.append(
                directory=asset_file, filename="TA_Thumbnail_World", autoselect=False
            )
    context.scene.world = bpy.data.worlds.get("TA_Thumbnail_World")
    map_node = context.scene.world.node_tree.nodes.get("Mapping")
    context.scene.world.node_tree.nodes.get("Background").inputs[
        1
    ].default_value = WORLD_STRENGTH
    if map_node:
        map_node.inputs[2].default_value = [
            map_node.inputs[2].default_value[0],
            map_node.inputs[2].default_value[1],
            0.785398 - camera_object.rotation_euler.z,
        ]
    if shading == "Material" or shading == "Solid-TA":
        view_area.spaces[0].shading.type = (
            "MATERIAL" if shading == "Material" else "SOLID"
        )
        view_area.spaces[0].overlay.show_overlays = False
        unselected = [a for a in scene.objects if a != object and a != ground_plane]
        for obj in unselected:
            if obj.hide_get() == False:
                obj.hide_set(True)
                hidden.append(obj)
        og_hide_render = object.hide_render
        object.hide_render = False
        bpy.ops.render.render(write_still=True)
        object.hide_render = og_hide_render
        for obj in hidden:
            obj.hide_set(False)
    elif shading == "Eevee":
        engine = scene.render.engine
        scene.render.engine = "BLENDER_EEVEE"
        unselected = [a for a in scene.objects if a != object and a != ground_plane]
        for obj in unselected:
            if obj.type != "LIGHT" and obj.hide_render == False:
                obj.hide_render = True
                hidden.append(obj)
        bpy.ops.render.render(write_still=True)
        scene.render.engine = engine
        for obj in hidden:
            obj.hide_render = False
    else:
        samples = context.scene.cycles.samples
        context.scene.cycles.samples = 64
        engine = scene.render.engine
        scene.render.engine = "CYCLES"
        unselected = [a for a in scene.objects if a != object and a != ground_plane]
        for obj in unselected:
            if obj.type != "LIGHT" and obj.hide_render == False:
                obj.hide_render = True
                hidden.append(obj)
        bpy.ops.render.render(write_still=True)
        context.scene.cycles.samples = samples
        scene.render.engine = engine
        for obj in hidden:
            obj.hide_render = False

    scene.render.resolution_x = rendexXbackUp
    scene.render.resolution_y = rendexYbackUp
    scene.render.film_transparent = transparent_backup
    scene.render.filepath = filepath
    if camera_object:
        bpy.data.objects.remove(camera_object, do_unlink=True)
    if ground_plane:
        delete_object_with_data(ground_plane)
    scene.camera = cameraBackUp
    return render_path


def create_thumbnail(context, ob, shading="Solid"):
    if not os.path.isdir(os.path.join(OBJECTS_PATH, "Thumbnails")):
        os.mkdir(os.path.join(OBJECTS_PATH, "Thumbnails"))
    if shading != "Solid":
        if isinstance(ob, bpy.types.Collection):
            path = capture_thumbnail_for_collection(
                context,
                ob,
                os.path.join(OBJECTS_PATH, "Thumbnails"),
                shading,
                add_plane=ADD_PLANE,
            )
        else:
            path = capture_thumbnail(
                context,
                ob,
                os.path.join(OBJECTS_PATH, "Thumbnails"),
                shading,
                add_plane=ADD_PLANE,
            )
        if os.path.isfile(path):
            with context.temp_override(id=ob):
                bpy.ops.ed.lib_id_load_custom_preview(filepath=path)
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


def create_preview(type, objects, objects_to_check_previews):
    global FILEPATH, FILEPATHS, st
    obs = objects_to_check_previews[:]
    obs = objects_to_check_previews[:]
    while obs:
        ob = obs[0]
        if (
            not ob.preview
            or any(ob.preview.image_pixels[:])
            or ((type == "COLLECTIONS" or type == "OBJECTS") and SHADING != "Solid")
            or (type == "MATS" and check_if_volumetric(ob))
        ):
            obs.pop(0)
        else:
            return 1
    if type != "COLLECTIONS":
        write_to_blend(type, objects)
    if type == "COLLECTIONS":
        Create_Mesh_Assets(objects)
    else:
        if FILEPATHS:
            FILEPATH = FILEPATHS.pop(0)
            bpy.ops.wm.read_homefile(app_template="")
            bpy.context.preferences.system.texture_collection_rate = 5
            bpy.context.preferences.system.texture_time_out = 5
            for o in bpy.data.objects:
                bpy.data.objects.remove(o)
            if IMPORTER == "Better FBX":
                bpy.ops.better_import.fbx(
                    filepath=FILEPATH,
                    use_auto_bone_orientation=USE_AUTO_BONE_ORIENTATION,
                    my_calculate_roll=MY_CALCULATE_ROLL,
                    my_bone_length=MY_BONE_LENGTH,
                    my_leaf_bone=MY_LEAF_BONE,
                    use_fix_bone_poses=USE_FIX_BONE_POSES,
                    use_fix_attributes=USE_FIX_ATTRIBUTES,
                    use_only_deform_bones=USE_ONLY_DEFORM_BONES,
                    use_vertex_animation=USE_VERTEX_ANIMATION,
                    use_animation=USE_ANIMATION,
                    my_animation_offset=MY_ANIMATION_OFFSET,
                    use_animation_prefix=USE_ANIMATION_PREFIX,
                    use_triangulate=USE_TRIANGULATE,
                    my_import_normal=MY_IMPORT_NORMAL,
                    use_auto_smooth=USE_AUTO_SMOOTH,
                    my_angle=MY_ANGLE,
                    my_shade_mode=MY_SHADE_MODE,
                    my_scale=MY_SCALE,
                    use_optimize_for_blender=USE_OPTIMIZE_FOR_BLENDER,
                    use_reset_mesh_origin=USE_RESET_MESH_ORIGIN,
                    use_edge_crease=USE_EDGE_CREASE,
                    my_edge_crease_scale=MY_EDGE_CREASE_SCALE,
                    my_edge_smoothing=MY_EDGE_SMOOTHING,
                    use_import_materials=USE_IMPORT_MATERIALS,
                    use_rename_by_filename=USE_RENAME_BY_FILENAME,
                    my_rotation_mode=MY_ROTATION_MODE,
                )
            else:
                print(
                    f"INNER ::: bpy.ops.import_scene.fbx(filepath='{FILEPATH}', ui_tab='MAIN', use_manual_orientation={USE_MANUAL_ORIENTATION}, global_scale={GLOBAL_SCALE}, bake_space_transform={BAKE_SPACE_TRANSFORM}, use_custom_normals={USE_CUSTOM_NORMALS}, use_image_search={USE_IMAGE_SEARCH}, use_alpha_decals={USE_ALPHA_DECALS}, decal_offset={DECAL_OFFSET}, use_anim={USE_ANIM}, anim_offset={ANIM_OFFSET}, use_subsurf={USE_SUBSURF}, use_custom_props={USE_CUSTOM_PROPS}, use_custom_props_enum_as_string={USE_CUSTOM_PROPS_ENUM_AS_STRING}, ignore_leaf_bones={IGNORE_LEAF_BONES}, force_connect_children={FORCE_CONNECT_CHILDREN}, automatic_bone_orientation={AUTOMATIC_BONE_ORIENTATION}, primary_bone_axis='{PRIMARY_BONE_AXIS}', secondary_bone_axis='{SECONDARY_BONE_AXIS}', use_prepost_rot={USE_PREPOST_ROT}, axis_forward='{AXIS_FORWARD}', axis_up='{AXIS_UP}')"
                )
                bpy.ops.import_scene.fbx(
                    filepath=FILEPATH,
                    ui_tab="MAIN",
                    use_manual_orientation=USE_MANUAL_ORIENTATION,
                    global_scale=GLOBAL_SCALE,
                    bake_space_transform=BAKE_SPACE_TRANSFORM,
                    use_custom_normals=USE_CUSTOM_NORMALS,
                    colors_type=COLORS_TYPE,
                    use_image_search=USE_IMAGE_SEARCH,
                    use_alpha_decals=USE_ALPHA_DECALS,
                    decal_offset=DECAL_OFFSET,
                    use_anim=USE_ANIM,
                    anim_offset=ANIM_OFFSET,
                    use_subsurf=USE_SUBSURF,
                    use_custom_props=USE_CUSTOM_PROPS,
                    use_custom_props_enum_as_string=USE_CUSTOM_PROPS_ENUM_AS_STRING,
                    ignore_leaf_bones=IGNORE_LEAF_BONES,
                    force_connect_children=FORCE_CONNECT_CHILDREN,
                    automatic_bone_orientation=AUTOMATIC_BONE_ORIENTATION,
                    primary_bone_axis=PRIMARY_BONE_AXIS,
                    secondary_bone_axis=SECONDARY_BONE_AXIS,
                    use_prepost_rot=USE_PREPOST_ROT,
                    axis_forward=AXIS_FORWARD,
                    axis_up=AXIS_UP,
                )

            if PACK:
                try:
                    bpy.ops.file.pack_all()
                except Exception as e:
                    print(e)
            bpy.ops.file.make_paths_absolute()
            if not MAKE_COLLECTION:
                for scene in bpy.data.scenes:
                    join_meshes_with_same_parent(scene)
            Create_Collection_Assets()
        else:
            # pass
            bpy.ops.wm.quit_blender()
    return None


def get_available_name(path, name):
    name = name.replace(".blend", "")
    new_name = name
    if os.path.isdir(path):
        files = [file for file in os.listdir(path)]
        final_name = name
        i = 1
        while final_name + ".blend" in files:
            final_name = name + f"_{i}"
            i = i + 1
        new_name = final_name
    return new_name + ".blend"


def write_to_blend(type, objects):
    blend_name = os.path.basename(FILEPATH)
    blend_name = (
        blend_name.replace("fbx", "blend")
        .replace("obj", "blend")
        .replace("OBJ", "blend")
        .replace("FBX", "blend")
    )
    print("Write to Blend ", blend_name, OVERRIDE)
    if objects:
        if type == "OBJECTS":
            if OVERRIDE == "COPY":
                blend_name = get_available_name(OBJECTS_PATH, blend_name)
            path = os.path.join(OBJECTS_PATH, blend_name)
        bpy.data.libraries.write(path, set(objects), fake_user=True)


def Create_Collection_Assets():
    objects = []
    objects_to_check_previews = []
    data_used = []
    if MAKE_COLLECTION and (
        OVERRIDE != "SKIP"
        or not os.path.isfile(os.path.join(OBJECTS_PATH, os.path.basename(FILEPATH)))
    ):
        for scene in bpy.data.scenes:
            for ob in [c for c in bpy.data.collections if scene.user_of_id(c)]:
                if (
                    not ob.hide_viewport
                    and ob not in data_used
                    and [a for a in ob.all_objects if a.type != "EMPTY"]
                ):
                    data_used.append(ob)
                    if not SINGLE_FILE:
                        ob.name = os.path.splitext(os.path.basename(FILEPATH))[0]
                    ob.asset_mark()
                    ob.asset_data.tags.new(ob.name)
                    if CATALOG != "NONE":
                        ob.asset_data.catalog_id = create_new_catalog(
                            OBJECTS_PATH,
                            ob.name
                            if SINGLE_FILE and CATALOG == "Filename"
                            else decode_catalog_name(CATALOG),
                        )
                    objects.append(ob)
                    objects_to_check_previews.append(ob)
                    if (
                        not (ob.preview and any(ob.preview.image_pixels[:]))
                        or FORCE_PREVIEWS
                    ):
                        create_thumbnail(context, ob, SHADING)

                    # ob.asset_generate_preview()
    if SHADING == "Solid":
        bpy.app.timers.register(
            functools.partial(
                create_preview, "COLLECTIONS", objects, objects_to_check_previews
            )
        )
    else:
        print("Creating Preview")
        create_preview("COLLECTIONS", objects, objects_to_check_previews)


def does_support_thumbnails(ob):
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
        or SHADING != "Solid"
    )


def get_all_nodegroups_from_material(node_tree):
    groups = []
    for node in node_tree.nodes:
        if node.type == "GROUP":
            groups.append(node.node_tree)
            groups.extend(get_all_nodegroups_from_material(node.node_tree))
    return groups


def Create_Mesh_Assets(collection_objects):
    objects = []
    objects_to_check_previews = []
    data_used = []
    if not MAKE_COLLECTION and (
        OVERRIDE != "SKIP"
        or not os.path.isfile(os.path.join(OBJECTS_PATH, os.path.basename(FILEPATH)))
    ):
        for scene in bpy.data.scenes:
            for ob in scene.objects:
                if ob.type == "MESH" and ob.data not in data_used:
                    data_used.append(ob.data)
                    if ob.type == "MESH" and (
                        ob.display_type == "WIRE" or ob.display_type == "BOUNDS"
                    ):
                        continue
                    if ob.type in {"MESH", "CURVE", "SURFACE", "TEXT", "META"}:
                        ob.display_type = "TEXTURED"
                    ob.asset_mark()
                    ob.asset_data.tags.new(ob.name)
                    ob.asset_data.tags.new(ob.type.title())
                    if CATALOG != "NONE":
                        ob.asset_data.catalog_id = create_new_catalog(
                            OBJECTS_PATH, decode_catalog_name(CATALOG)
                        )
                    objects.append(ob)
                    if does_support_thumbnails(ob):
                        objects_to_check_previews.append(ob)
                        if (
                            not (ob.preview and any(ob.preview.image_pixels[:]))
                            or FORCE_PREVIEWS
                        ):
                            create_thumbnail(context, ob, SHADING)

                    # ob.asset_generate_preview()
    if SHADING == "Solid":
        bpy.app.timers.register(
            functools.partial(
                create_preview,
                "OBJECTS",
                objects + collection_objects,
                objects + collection_objects,
            ),
            first_interval=0,
        )
    else:
        create_preview(
            "OBJECTS", objects + collection_objects, objects + collection_objects
        )


if __name__ == "__main__":
    TOTAL_FILES = len(FILEPATHS)
    # if IMPORTER == "Better FBX":
    if False:
        for i in range(TOTAL_FILES):
            FILEPATH = FILEPATHS.pop(0)
            init_objs = bpy.data.objects[:]
            bpy.ops.better_import.fbx(
                filepath=FILEPATH,
                use_auto_bone_orientation=USE_AUTO_BONE_ORIENTATION,
                my_calculate_roll=MY_CALCULATE_ROLL,
                my_bone_length=MY_BONE_LENGTH,
                my_leaf_bone=MY_LEAF_BONE,
                use_fix_bone_poses=USE_FIX_BONE_POSES,
                use_fix_attributes=USE_FIX_ATTRIBUTES,
                use_only_deform_bones=USE_ONLY_DEFORM_BONES,
                use_vertex_animation=USE_VERTEX_ANIMATION,
                use_animation=USE_ANIMATION,
                my_animation_offset=MY_ANIMATION_OFFSET,
                use_animation_prefix=USE_ANIMATION_PREFIX,
                use_triangulate=USE_TRIANGULATE,
                my_import_normal=MY_IMPORT_NORMAL,
                use_auto_smooth=USE_AUTO_SMOOTH,
                my_angle=MY_ANGLE,
                my_shade_mode=MY_SHADE_MODE,
                my_scale=MY_SCALE,
                use_optimize_for_blender=USE_OPTIMIZE_FOR_BLENDER,
                use_reset_mesh_origin=USE_RESET_MESH_ORIGIN,
                use_edge_crease=USE_EDGE_CREASE,
                my_edge_crease_scale=MY_EDGE_CREASE_SCALE,
                my_edge_smoothing=MY_EDGE_SMOOTHING,
                use_import_materials=USE_IMPORT_MATERIALS,
                use_rename_by_filename=USE_RENAME_BY_FILENAME,
                my_rotation_mode=MY_ROTATION_MODE,
            )
            # if i!=0:
            if (
                os.path.splitext(os.path.basename(FILEPATH))[0]
                not in bpy.data.collections
            ):
                col = bpy.data.collections.new(
                    name=os.path.splitext(os.path.basename(FILEPATH))[0]
                )
                bpy.context.scene.collection.children.link(col)
            for obj in bpy.data.objects:
                if obj not in init_objs:
                    for c in obj.users_collection:
                        c.name = os.path.splitext(os.path.basename(FILEPATH))[0]
                        try:
                            c.objects.unlink(obj)
                        except Exception:
                            pass

                    col.objects.link(obj)
            if not SINGLE_FILE:
                break
    else:
        orig_total_objects = len(bpy.data.objects)
        orig_total_materials = len(bpy.data.materials)
        orig_total_worlds = len(bpy.data.worlds)
        orig_total_collections = len(bpy.data.collections)
        orig_total_actions = len(bpy.data.actions)
        orig_total_images = len(bpy.data.images)
        orig_total_node_groups = len(bpy.data.node_groups)
        orig_total_pointclouds = len(bpy.data.pointclouds)
        orig_total_volumes = len(bpy.data.volumes)

        for i in range(TOTAL_FILES):
            FILEPATH = FILEPATHS.pop(0)
            init_objs = bpy.data.objects[:]
            print(
                f"OUTER ::: bpy.ops.import_scene.fbx(\n\tfilepath='{FILEPATH}',\n\tui_tab='MAIN',\n\tuse_manual_orientation={USE_MANUAL_ORIENTATION},\n\tglobal_scale={GLOBAL_SCALE},\n\tbake_space_transform={BAKE_SPACE_TRANSFORM},\n\tuse_custom_normals={USE_CUSTOM_NORMALS},\n\tcolors_type='{COLORS_TYPE}',\n\tuse_image_search={USE_IMAGE_SEARCH},\n\tuse_alpha_decals={USE_ALPHA_DECALS},\n\tdecal_offset={DECAL_OFFSET},\n\tuse_anim={USE_ANIM},\n\tanim_offset={ANIM_OFFSET},\n\tuse_subsurf={USE_SUBSURF},\n\tuse_custom_props={USE_CUSTOM_PROPS},\n\tuse_custom_props_enum_as_string={USE_CUSTOM_PROPS_ENUM_AS_STRING},\n\tignore_leaf_bones={IGNORE_LEAF_BONES},\n\tforce_connect_children={FORCE_CONNECT_CHILDREN},\n\tautomatic_bone_orientation={AUTOMATIC_BONE_ORIENTATION},\n\tprimary_bone_axis='{PRIMARY_BONE_AXIS}',\n\tsecondary_bone_axis='{SECONDARY_BONE_AXIS}',\n\tuse_prepost_rot={USE_PREPOST_ROT},\n\taxis_forward='{AXIS_FORWARD}',\n\taxis_up='{AXIS_UP}'\n)"
            )
            bpy.ops.import_scene.fbx(
                filepath=FILEPATH,
                ui_tab="MAIN",
                use_manual_orientation=USE_MANUAL_ORIENTATION,
                global_scale=GLOBAL_SCALE,
                bake_space_transform=BAKE_SPACE_TRANSFORM,
                use_custom_normals=USE_CUSTOM_NORMALS,
                colors_type=COLORS_TYPE,
                use_image_search=USE_IMAGE_SEARCH,
                use_alpha_decals=USE_ALPHA_DECALS,
                decal_offset=DECAL_OFFSET,
                use_anim=USE_ANIM,
                anim_offset=ANIM_OFFSET,
                use_subsurf=USE_SUBSURF,
                use_custom_props=USE_CUSTOM_PROPS,
                use_custom_props_enum_as_string=USE_CUSTOM_PROPS_ENUM_AS_STRING,
                ignore_leaf_bones=IGNORE_LEAF_BONES,
                force_connect_children=FORCE_CONNECT_CHILDREN,
                automatic_bone_orientation=AUTOMATIC_BONE_ORIENTATION,
                primary_bone_axis=PRIMARY_BONE_AXIS,
                secondary_bone_axis=SECONDARY_BONE_AXIS,
                use_prepost_rot=USE_PREPOST_ROT,
                axis_forward=AXIS_FORWARD,
                axis_up=AXIS_UP,
            )

            if (
                os.path.splitext(os.path.basename(FILEPATH))[0]
                not in bpy.data.collections
            ):
                col = bpy.data.collections.new(
                    name=os.path.splitext(os.path.basename(FILEPATH))[0]
                )
                bpy.context.scene.collection.children.link(col)
            for obj in bpy.data.objects:
                if obj not in init_objs:
                    for c in obj.users_collection:
                        c.name = os.path.splitext(os.path.basename(FILEPATH))[0]
                        try:
                            c.objects.unlink(obj)
                        except Exception:
                            pass

                    col.objects.link(obj)
            if not SINGLE_FILE:
                break

        total_objects = len(bpy.data.objects)
        total_materials = len(bpy.data.materials)
        total_worlds = len(bpy.data.worlds)
        total_collections = len(bpy.data.collections)
        total_actions = len(bpy.data.actions)
        total_images = len(bpy.data.images)
        total_node_groups = len(bpy.data.node_groups)
        total_pointclouds = len(bpy.data.pointclouds)
        total_volumes = len(bpy.data.volumes)

        if not any((
            total_objects - orig_total_objects,
            total_materials - orig_total_materials,
            total_worlds - orig_total_worlds,
            total_collections - orig_total_collections,
            total_actions - orig_total_actions,
            total_images - orig_total_images,
            total_node_groups - orig_total_node_groups,
            total_pointclouds - orig_total_pointclouds,
            total_volumes - orig_total_volumes,
        )):
            print("~NOTHING IMPORTED~")
            bpy.ops.wm.quit_blender()

    if PACK:
        try:
            bpy.ops.file.pack_all()
        except Exception as e:
            print(e)
    bpy.ops.file.make_paths_absolute()
    if not MAKE_COLLECTION:
        for scene in bpy.data.scenes:
            join_meshes_with_same_parent(scene)
    print("Creating Assets")
    Create_Collection_Assets()
    # Create_Mesh_Assets()