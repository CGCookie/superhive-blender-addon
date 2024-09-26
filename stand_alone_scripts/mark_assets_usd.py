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

SCALE = float(argv[11])
SET_FRAME_RANGE = argv[12] == "True"
IMPORT_CAMERAS = argv[13] == "True"
IMPORT_CURVES = argv[14] == "True"
IMPORT_LIGHTS = argv[15] == "True"
IMPORT_MATERIALS = argv[16] == "True"
IMPORT_MESHES = argv[17] == "True"
IMPORT_VOLUMES = argv[18] == "True"
IMPORT_SHAPES = argv[19] == "True"
IMPORT_SKELETONS = argv[20] == "True"
IMPORT_BLENDSHAPES = argv[21] == "True"
IMPORT_POINTS = argv[22] == "True"
IMPORT_SUBDIV = argv[23] == "True"
# IMPORT_INSTANCE_PROXIES = argv[24] == "True"
SUPPORT_SCENE_INSTANCING = argv[24] == "True"
IMPORT_VISIBLE_ONLY = argv[25] == "True"
CREATE_COLLECTION = argv[26] == "True"
READ_MESH_UVS = argv[27] == "True"
READ_MESH_COLORS = argv[28] == "True"
READ_MESH_ATTRIBUTES = argv[29] == "True"
PRIM_PATH_MASK = argv[30]
IMPORT_GUIDE = argv[31] == "True"
IMPORT_PROXY = argv[32] == "True"
IMPORT_RENDER = argv[33] == "True"
IMPORT_USD_PREVIEW = argv[34] == "True"
SET_MATERIAL_BLEND = argv[35] == "True"
LIGHT_INTENSITY_SCALE = float(argv[36])
MTL_NAME_COLLISION_MODE = argv[37]
IMPORT_ALL_MATERIALS = argv[38] == "True"
IMPORT_TEXTURES_MODE = argv[39]
IMPORT_TEXTURES_DIR = argv[40]
TEX_NAME_COLLISION_MODE = argv[41]
ATTR_IMPORT_MODE = argv[42]
CREATE_WORLD_MATERIAL = argv[43] == "True"
IMPORT_DEFINED_ONLY = argv[44] == "True"
PACK = argv[45] == "True"
MAKE_COLLECTION = argv[46] == "True"
RENDER_DEVICE = argv[47]

# Assert statements to ensure correct type
assert isinstance(FILEPATHS, list), f"Expected list, got {type(FILEPATHS).__name__}"
assert all(
    isinstance(path, str) for path in FILEPATHS
), "All elements in FILEPATHS should be strings"
assert isinstance(OBJECTS_PATH, str), f"Expected str, got {type(OBJECTS_PATH).__name__}"
assert isinstance(OVERRIDE, str), f"Expected str, got {type(OVERRIDE).__name__}"
assert isinstance(SHADING, str), f"Expected str, got {type(SHADING).__name__}"
assert isinstance(ENGINE, str), f"Expected str, got {type(ENGINE).__name__}"
assert isinstance(MAX_TIME, float), f"Expected float, got {type(MAX_TIME).__name__}"
assert isinstance(
    FORCE_PREVIEWS, bool
), f"Expected bool, got {type(FORCE_PREVIEWS).__name__}"
assert isinstance(CAMERA_ANGLE, str), f"Expected str, got {type(CAMERA_ANGLE).__name__}"
assert isinstance(CATALOG, str), f"Expected str, got {type(CATALOG).__name__}"
assert isinstance(ADD_PLANE, bool), f"Expected bool, got {type(ADD_PLANE).__name__}"
assert isinstance(
    WORLD_STRENGTH, float
), f"Expected float, got {type(WORLD_STRENGTH).__name__}"
assert isinstance(SCALE, float), f"Expected float, got {type(SCALE).__name__}"
assert isinstance(
    SET_FRAME_RANGE, bool
), f"Expected bool, got {type(SET_FRAME_RANGE).__name__}"
assert isinstance(
    IMPORT_CAMERAS, bool
), f"Expected bool, got {type(IMPORT_CAMERAS).__name__}"
assert isinstance(
    IMPORT_CURVES, bool
), f"Expected bool, got {type(IMPORT_CURVES).__name__}"
assert isinstance(
    IMPORT_LIGHTS, bool
), f"Expected bool, got {type(IMPORT_LIGHTS).__name__}"
assert isinstance(
    IMPORT_MATERIALS, bool
), f"Expected bool, got {type(IMPORT_MATERIALS).__name__}"
assert isinstance(
    IMPORT_MESHES, bool
), f"Expected bool, got {type(IMPORT_MESHES).__name__}"
assert isinstance(
    IMPORT_VOLUMES, bool
), f"Expected bool, got {type(IMPORT_VOLUMES).__name__}"
assert isinstance(
    IMPORT_SHAPES, bool
), f"Expected bool, got {type(IMPORT_SHAPES).__name__}"
assert isinstance(
    IMPORT_SKELETONS, bool
), f"Expected bool, got {type(IMPORT_SKELETONS).__name__}"
assert isinstance(
    IMPORT_BLENDSHAPES, bool
), f"Expected bool, got {type(IMPORT_BLENDSHAPES).__name__}"
assert isinstance(
    IMPORT_POINTS, bool
), f"Expected bool, got {type(IMPORT_POINTS).__name__}"
assert isinstance(
    IMPORT_SUBDIV, bool
), f"Expected bool, got {type(IMPORT_SUBDIV).__name__}"
assert isinstance(
    SUPPORT_SCENE_INSTANCING, bool
), f"Expected bool, got {type(SUPPORT_SCENE_INSTANCING).__name__}"
assert isinstance(
    IMPORT_VISIBLE_ONLY, bool
), f"Expected bool, got {type(IMPORT_VISIBLE_ONLY).__name__}"
assert isinstance(
    CREATE_COLLECTION, bool
), f"Expected bool, got {type(CREATE_COLLECTION).__name__}"
assert isinstance(
    READ_MESH_UVS, bool
), f"Expected bool, got {type(READ_MESH_UVS).__name__}"
assert isinstance(
    READ_MESH_COLORS, bool
), f"Expected bool, got {type(READ_MESH_COLORS).__name__}"
assert isinstance(
    READ_MESH_ATTRIBUTES, bool
), f"Expected bool, got {type(READ_MESH_ATTRIBUTES).__name__}"
assert isinstance(
    PRIM_PATH_MASK, str
), f"Expected str, got {type(PRIM_PATH_MASK).__name__}"
assert isinstance(
    IMPORT_GUIDE, bool
), f"Expected bool, got {type(IMPORT_GUIDE).__name__}"
assert isinstance(
    IMPORT_PROXY, bool
), f"Expected bool, got {type(IMPORT_PROXY).__name__}"
assert isinstance(
    IMPORT_RENDER, bool
), f"Expected bool, got {type(IMPORT_RENDER).__name__}"
assert isinstance(
    IMPORT_USD_PREVIEW, bool
), f"Expected bool, got {type(IMPORT_USD_PREVIEW).__name__}"
assert isinstance(
    SET_MATERIAL_BLEND, bool
), f"Expected bool, got {type(SET_MATERIAL_BLEND).__name__}"
assert isinstance(
    LIGHT_INTENSITY_SCALE, float
), f"Expected float, got {type(LIGHT_INTENSITY_SCALE).__name__}"
assert isinstance(
    MTL_NAME_COLLISION_MODE, str
), f"Expected str, got {type(MTL_NAME_COLLISION_MODE).__name__}"
assert isinstance(
    IMPORT_ALL_MATERIALS, bool
), f"Expected bool, got {type(IMPORT_ALL_MATERIALS).__name__}"
assert isinstance(
    IMPORT_TEXTURES_MODE, str
), f"Expected str, got {type(IMPORT_TEXTURES_MODE).__name__}"
assert isinstance(
    IMPORT_TEXTURES_DIR, str
), f"Expected str, got {type(IMPORT_TEXTURES_DIR).__name__}"
assert isinstance(
    TEX_NAME_COLLISION_MODE, str
), f"Expected str, got {type(TEX_NAME_COLLISION_MODE).__name__}"
assert isinstance(
    ATTR_IMPORT_MODE, str
), f"Expected str, got {type(ATTR_IMPORT_MODE).__name__}"
assert isinstance(
    CREATE_WORLD_MATERIAL, bool
), f"Expected bool, got {type(CREATE_WORLD_MATERIAL).__name__}"
assert isinstance(
    IMPORT_DEFINED_ONLY, bool
), f"Expected bool, got {type(IMPORT_DEFINED_ONLY).__name__}"
assert isinstance(PACK, bool), f"Expected bool, got {type(PACK).__name__}"
assert isinstance(
    MAKE_COLLECTION, bool
), f"Expected bool, got {type(MAKE_COLLECTION).__name__}"
assert isinstance(
    RENDER_DEVICE, str
), f"Expected str, got {type(MAKE_COLLECTION).__name__}"

FILEPATH = FILEPATHS.pop(0)
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


def decode_catalog_name(catalog):
    if catalog == "Filename":
        return os.path.splitext(os.path.basename(FILEPATH))[0]
    elif catalog == "Directory":
        return os.path.basename(os.path.dirname(FILEPATH))
    else:
        return catalog


def extract_texture_2d(file):
    texture_2d_list = []
    other_data = []
    with open(file, "r") as f:
        data = f.read()
    with open(file, "r") as f:
        for line in f:
            if "texture_2d" in line:
                texture_2d = re.findall(r'"([^"]*)"', line)[0]
                trim_data = data[: data.index(texture_2d)]
                trim_data = trim_data[: trim_data.rindex("template")]
                trim_data = trim_data[trim_data.rindex("\n") + 2 :]
                type = trim_data.replace(" ", "").replace(":", "")
                texture_2d_list.append((
                    type,
                    os.path.join(os.path.dirname(file), texture_2d),
                ))
            elif "metalness" in line:
                value = re.findall(r"([0-9]*\.[0-9]*)", line)
                if value:
                    value = value[0]
                    other_data.append(("Metallic", value))
            elif "Roughness" in line:
                value = re.findall(r"([0-9]*\.[0-9]*)", line)
                if value:
                    value = value[0]
                    other_data.append(("Roughness", value))
    # print(other_data)
    return texture_2d_list


def sortTextures(textures):
    BaseColor = None
    Roughness = None
    Normal = None
    Height = None
    Metal = None
    Specular = None
    opacity = None
    ao = None
    emit = None
    len = 0
    BaseColorTags = ["diffuse", "diff", "albedo", "base", "col", "color", "map"]
    RoughnessTags = ["roughness", "rough", "rgh", "reflection"]
    NormalTags = ["normal", "nor", "nrm", "nrml", "norm"]
    HeightTags = [
        "displacement",
        "displace",
        "disp",
        "dsp",
        "height",
        "heightmap",
        "bmp",
        "bump",
        "texmap_bump",
    ]
    MetallicTags = ["metallic", "metalness", "mtl"]
    SpecularTags = ["specularity", "specular", "spec", "spc"]
    opacityTags = ["opacity", "alpha", " transparen"]
    aoTags = ["ao", "occlusion"]
    emitTags = ["emis", "emit"]
    for tex in textures:
        if any(x in tex[0].lower() for x in BaseColorTags) and BaseColor is None:
            BaseColor = tex[1]
            len = len + 1
        elif any(x in tex[0].lower() for x in RoughnessTags) and Roughness is None:
            Roughness = tex[1]
            len = len + 1
        elif any(x in tex[0].lower() for x in NormalTags) and Normal is None:
            Normal = tex[1]
            len = len + 1
        elif any(x in tex[0].lower() for x in HeightTags) and Height is None:
            Height = tex[1]
            len = len + 1
        elif any(x in tex[0].lower() for x in MetallicTags) and Metal is None:
            Metal = tex[1]
            len = len + 1
        elif any(x in tex[0].lower() for x in SpecularTags) and Specular is None:
            Specular = tex[1]
            len = len + 1
        elif any(x in tex[0].lower() for x in opacityTags) and opacity is None:
            opacity = tex[1]
            len = len + 1
        elif any(x in tex[0].lower() for x in aoTags) and ao is None:
            ao = tex[1]
            len = len + 1
        elif any(x in tex[0].lower() for x in emitTags) and emit is None:
            emit = tex[1]
            len = len + 1
    print([
        BaseColor,
        Roughness,
        Normal,
        Height,
        Metal,
        Specular,
        opacity,
        ao,
        emit,
        len,
    ])
    return [
        BaseColor,
        Roughness,
        Normal,
        Height,
        Metal,
        Specular,
        opacity,
        ao,
        emit,
        len,
    ]


def setup_materials(name, images):
    mats_created = []
    filename = "True-BSDF"
    images_used = []
    file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "Assets",
        "Assets.blend" if bpy.app.version >= (3, 4, 0) else "Assets_Old.blend",
        "Material",
    )

    matInit = []

    for m in bpy.data.materials:
        matInit.append(m.name)
    override = context.copy()
    for area in context.window_manager.windows[0].screen.areas:
        area.type = "VIEW_3D"
        override["window"] = context.window_manager.windows[0]
        break
    with context.temp_override(**override):
        bpy.ops.wm.append(directory=file_path, filename=filename, autoselect=False)
    matAfter = []

    for m in bpy.data.materials:
        matAfter.append(m.name)
    mat = [a for a in matAfter if a not in matInit]
    mat = bpy.data.materials.get(mat[0])
    tex = sortTextures(images)
    if tex[9] > 1 or (tex[0] is not None):
        newMat = mat.copy()

        for obj in bpy.data.objects:
            for slot in obj.material_slots:
                if slot.material == bpy.data.materials[name]:
                    slot.material = newMat
        newMat.name = name
        newMat.use_fake_user = True

        nodes_to_arrange = []
        node_group = newMat

        if node_group:
            if node_group.node_tree.nodes.get("AO"):
                if tex[7] is not None:
                    node_group.node_tree.nodes["AO"].image = bpy.data.images.load(
                        tex[7]
                    )
                    node_group.node_tree.links.new(
                        node_group.node_tree.nodes["AO"].outputs[0],
                        node_group.node_tree.nodes["AO Mix"].inputs[
                            7
                            if len(node_group.node_tree.nodes["AO Mix"].inputs) > 5
                            else 2
                        ],
                    )
                    images_used.append(node_group.node_tree.nodes["AO"].image)
                    nodes_to_arrange.append(node_group.node_tree.nodes["AO"])
            if node_group.node_tree.nodes.get("BaseColor"):
                if tex[0] is not None:
                    node_group.node_tree.nodes[
                        "BaseColor"
                    ].image = bpy.data.images.load(tex[0])
                    images_used.append(node_group.node_tree.nodes["BaseColor"].image)
                    nodes_to_arrange.append(node_group.node_tree.nodes["BaseColor"])
            if node_group.node_tree.nodes.get("Metallic"):
                if tex[4] is not None:
                    node_group.node_tree.nodes["Metallic"].image = bpy.data.images.load(
                        tex[4]
                    )
                    images_used.append(node_group.node_tree.nodes["Metallic"].image)
                    node_group.node_tree.nodes[
                        "Metallic"
                    ].image.colorspace_settings.is_data = True
                    nodes_to_arrange.append(node_group.node_tree.nodes["Metallic"])
                else:
                    node_group.node_tree.nodes.remove(
                        node_group.node_tree.nodes["Metallic"]
                    )
            if node_group.node_tree.nodes.get("Specular"):
                if tex[5] is not None:
                    node_group.node_tree.nodes["Specular"].image = bpy.data.images.load(
                        tex[5]
                    )
                    images_used.append(node_group.node_tree.nodes["Specular"].image)
                    node_group.node_tree.nodes[
                        "Specular"
                    ].image.colorspace_settings.is_data = True
                    nodes_to_arrange.append(node_group.node_tree.nodes["Specular"])
                else:
                    node_group.node_tree.nodes.remove(
                        node_group.node_tree.nodes["Specular"]
                    )
            if node_group.node_tree.nodes.get("Roughness"):
                if tex[1] is not None:
                    node_group.node_tree.nodes[
                        "Roughness"
                    ].image = bpy.data.images.load(tex[1])
                    images_used.append(node_group.node_tree.nodes["Roughness"].image)
                    node_group.node_tree.nodes[
                        "Roughness"
                    ].image.colorspace_settings.is_data = True
                    nodes_to_arrange.append(node_group.node_tree.nodes["Roughness"])
                else:
                    node_group.node_tree.nodes.remove(
                        node_group.node_tree.nodes["Roughness"]
                    )
            if node_group.node_tree.nodes.get("Emission"):
                if tex[8] is not None:
                    node_group.node_tree.nodes["Emission"].image = bpy.data.images.load(
                        tex[8]
                    )
                    images_used.append(node_group.node_tree.nodes["Emission"].image)
                    nodes_to_arrange.append(node_group.node_tree.nodes["Emission"])
                else:
                    node_group.node_tree.nodes.remove(
                        node_group.node_tree.nodes["Emission"]
                    )
            if node_group.node_tree.nodes.get("Height"):
                if tex[3] is not None:
                    node_group.node_tree.nodes["Height"].image = bpy.data.images.load(
                        tex[3]
                    )
                    images_used.append(node_group.node_tree.nodes["Height"].image)
                    node_group.node_tree.nodes[
                        "Height"
                    ].image.colorspace_settings.is_data = True
                    nodes_to_arrange.append(node_group.node_tree.nodes["Height"])
                else:
                    node_group.node_tree.nodes.remove(
                        node_group.node_tree.nodes["Height"]
                    )
            if node_group.node_tree.nodes.get("Normal"):
                if tex[2] is not None:
                    node_group.node_tree.nodes["Normal"].image = bpy.data.images.load(
                        tex[2]
                    )
                    images_used.append(node_group.node_tree.nodes["Normal"].image)
                    node_group.node_tree.nodes[
                        "Normal"
                    ].image.colorspace_settings.is_data = True
                    nodes_to_arrange.append(node_group.node_tree.nodes["Normal"])
                else:
                    node_group.node_tree.nodes.remove(
                        node_group.node_tree.nodes["Normal"]
                    )

            if node_group.node_tree.nodes.get("Opacity"):
                if tex[6] is not None:
                    newMat.blend_method = (
                        "CLIP"
                        if newMat.blend_method == "OPAQUE"
                        else newMat.blend_method
                    )
                    node_group.node_tree.nodes["Opacity"].image = bpy.data.images.load(
                        tex[6]
                    )
                    images_used.append(node_group.node_tree.nodes["Opacity"].image)
                    node_group.node_tree.nodes[
                        "Opacity"
                    ].image.colorspace_settings.is_data = True
                    nodes_to_arrange.append(node_group.node_tree.nodes["Opacity"])
                else:
                    node_group.node_tree.nodes.remove(
                        node_group.node_tree.nodes["Opacity"]
                    )
            if len(nodes_to_arrange) > 1:
                for index, n in enumerate(nodes_to_arrange[1:]):
                    n.location.y = nodes_to_arrange[index].location.y - (
                        nodes_to_arrange[index].height
                        * (3 if not nodes_to_arrange[index].hide else 1)
                    )

            mats_created.append(newMat)


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
            objects[0].name = col.name
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
    # print(type,objects)  # Debugging purpose
    global FILEPATH, FILEPATHS

    obs = objects_to_check_previews[:]
    obs = objects_to_check_previews[:]
    # print(type,objects)
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
            # print("Waiting")
            return 1.0

    if type == "COLLECTIONS":
        # print("Writing")
        write_to_blend(type, objects)
    if type == "asCOLLECTIONS":
        Create_Mesh_Assets(objects)
    else:
        if FILEPATHS:
            FILEPATH = FILEPATHS.pop(0)
            print("LOADING", FILEPATH)
            bpy.ops.wm.read_homefile(app_template="")
            # bpy.context.preferences.system.texture_collection_rate=5
            # bpy.context.preferences.system.texture_time_out=5
            for o in bpy.data.objects:
                bpy.data.objects.remove(o)
            override = context.copy()
            for area in context.window_manager.windows[0].screen.areas:
                area.type = "VIEW_3D"
                override["window"] = context.window_manager.windows[0]
                break
            with context.temp_override(**override):
                bpy.ops.wm.usd_import(
                    filepath=FILEPATH,
                    scale=SCALE,
                    set_frame_range=SET_FRAME_RANGE,
                    import_cameras=IMPORT_CAMERAS,
                    import_curves=IMPORT_CURVES,
                    import_lights=IMPORT_LIGHTS,
                    import_materials=IMPORT_MATERIALS,
                    import_meshes=IMPORT_MESHES,
                    import_volumes=IMPORT_VOLUMES,
                    import_shapes=IMPORT_SHAPES,
                    import_skeletons=IMPORT_SKELETONS,
                    import_blendshapes=IMPORT_BLENDSHAPES,
                    import_points=IMPORT_POINTS,
                    import_subdiv=IMPORT_SUBDIV,
                    # import_instance_proxies=IMPORT_INSTANCE_PROXIES,
                    support_scene_instancing=SUPPORT_SCENE_INSTANCING,
                    import_visible_only=IMPORT_VISIBLE_ONLY,
                    create_collection=CREATE_COLLECTION,
                    read_mesh_uvs=READ_MESH_UVS,
                    read_mesh_colors=READ_MESH_COLORS,
                    read_mesh_attributes=READ_MESH_ATTRIBUTES,
                    prim_path_mask=PRIM_PATH_MASK,
                    import_guide=IMPORT_GUIDE,
                    import_proxy=IMPORT_PROXY,
                    import_render=IMPORT_RENDER,
                    import_usd_preview=IMPORT_USD_PREVIEW,
                    set_material_blend=SET_MATERIAL_BLEND,
                    light_intensity_scale=LIGHT_INTENSITY_SCALE,
                    mtl_name_collision_mode=MTL_NAME_COLLISION_MODE,
                    import_all_materials=IMPORT_ALL_MATERIALS,
                    import_textures_mode=IMPORT_TEXTURES_MODE,
                    import_textures_dir=IMPORT_TEXTURES_DIR,
                    tex_name_collision_mode=TEX_NAME_COLLISION_MODE,
                    attr_import_mode=ATTR_IMPORT_MODE,
                    create_world_material=CREATE_WORLD_MATERIAL,
                    import_defined_only=IMPORT_DEFINED_ONLY,
                )

            if PACK:
                try:
                    bpy.ops.file.pack_all()
                except Exception as e:
                    print(e)
            # bpy.ops.file.make_paths_absolute()
            if not MAKE_COLLECTION:
                for scene in bpy.data.scenes:
                    join_meshes_with_same_parent(scene)
            Create_Collection_Assets()
            # print(FILEPATH,type,objects_to_check_previews,"Unregister Timer")
        else:
            bpy.ops.wm.quit_blender()
    # print(FILEPATH,type,objects_to_check_previews,"Unregister Timer")
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
    blend_name = os.path.splitext(blend_name)[0] + ".blend"
    # print(blend_name,OVERRIDE)
    if objects:
        if type == "COLLECTIONS":
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
                    ob.name = os.path.splitext(os.path.basename(FILEPATH))[0]
                    ob.asset_mark()
                    ob.asset_data.tags.new(ob.name)
                    if CATALOG != "NONE":
                        ob.asset_data.catalog_id = create_new_catalog(
                            OBJECTS_PATH, decode_catalog_name(CATALOG)
                        )
                    objects.append(ob)
                    objects_to_check_previews.append(ob)
                    if (
                        not (ob.preview and any(ob.preview.image_pixels[:]))
                        or FORCE_PREVIEWS
                    ):
                        create_thumbnail(context, ob, SHADING)

                    # ob.asset_generate_preview()
    # print("IN COL",objects,objects_to_check_previews)

    if SHADING == "Solid":
        bpy.app.timers.register(
            functools.partial(
                create_preview, "COLLECTIONS", objects, objects_to_check_previews
            )
        )
    else:
        create_preview("COLLECTIONS", objects, objects_to_check_previews)
    # print("Registered",FILEPATH)


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
    # print("IN MESH",objects+collection_objects)

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


override = context.copy()
for area in context.window_manager.windows[0].screen.areas:
    area.type = "VIEW_3D"
    override["window"] = context.window_manager.windows[0]
    break

orig_total_objects = len(bpy.data.objects)
orig_total_materials = len(bpy.data.materials)
orig_total_worlds = len(bpy.data.worlds)
orig_total_collections = len(bpy.data.collections)
orig_total_actions = len(bpy.data.actions)
orig_total_images = len(bpy.data.images)
orig_total_node_groups = len(bpy.data.node_groups)
orig_total_pointclouds = len(bpy.data.pointclouds)
orig_total_volumes = len(bpy.data.volumes)

with context.temp_override(**override):
    bpy.ops.wm.usd_import(
        filepath=FILEPATH,
        scale=SCALE,
        set_frame_range=SET_FRAME_RANGE,
        import_cameras=IMPORT_CAMERAS,
        import_curves=IMPORT_CURVES,
        import_lights=IMPORT_LIGHTS,
        import_materials=IMPORT_MATERIALS,
        import_meshes=IMPORT_MESHES,
        import_volumes=IMPORT_VOLUMES,
        import_shapes=IMPORT_SHAPES,
        import_skeletons=IMPORT_SKELETONS,
        import_blendshapes=IMPORT_BLENDSHAPES,
        import_points=IMPORT_POINTS,
        import_subdiv=IMPORT_SUBDIV,
        # import_instance_proxies=IMPORT_INSTANCE_PROXIES,
        support_scene_instancing=SUPPORT_SCENE_INSTANCING,
        import_visible_only=IMPORT_VISIBLE_ONLY,
        create_collection=CREATE_COLLECTION,
        read_mesh_uvs=READ_MESH_UVS,
        read_mesh_colors=READ_MESH_COLORS,
        read_mesh_attributes=READ_MESH_ATTRIBUTES,
        prim_path_mask=PRIM_PATH_MASK,
        import_guide=IMPORT_GUIDE,
        import_proxy=IMPORT_PROXY,
        import_render=IMPORT_RENDER,
        import_usd_preview=IMPORT_USD_PREVIEW,
        set_material_blend=SET_MATERIAL_BLEND,
        light_intensity_scale=LIGHT_INTENSITY_SCALE,
        mtl_name_collision_mode=MTL_NAME_COLLISION_MODE,
        import_all_materials=IMPORT_ALL_MATERIALS,
        import_textures_mode=IMPORT_TEXTURES_MODE,
        import_textures_dir=IMPORT_TEXTURES_DIR,
        tex_name_collision_mode=TEX_NAME_COLLISION_MODE,
        attr_import_mode=ATTR_IMPORT_MODE,
        create_world_material=CREATE_WORLD_MATERIAL,
        import_defined_only=IMPORT_DEFINED_ONLY,
    )
for a in os.listdir(os.path.dirname(FILEPATH)):
    if a.endswith("mdl") and os.path.splitext(a)[0] in [
        m.name for m in bpy.data.materials
    ]:
        mdl_path = os.path.join(os.path.dirname(FILEPATH), a)
        images = extract_texture_2d(mdl_path)
        setup_materials(os.path.splitext(a)[0], images)
        print(os.path.splitext(a)[0], images)
# bpy.app.handlers.load_post.append(start_creating)

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
# else:
#     print(f"{total_objects=}")
#     print(f"{total_materials=}")
#     print(f"{total_worlds=}")
#     print(f"{total_collections=}")
#     print(f"{total_actions=}")
#     print(f"{total_images=}")
#     print(f"{total_node_groups=}")
#     print(f"{total_pointclouds=}")
#     print(f"{total_volumes=}")

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
# Create_Mesh_Assets()
