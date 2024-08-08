"""The place to grab general settings and lists"""

LICENSES_ENUM: list[tuple[str, str, str, int]] = None
"""Enum for blender UI"""
LICENSES_DICT = None

TAGS_ENUM: list[tuple[str, str, str, int]] = None
"""Enum for blender UI"""
TAGS_DICT = None

CATEGORIES_DICT: dict[tuple[str]] = None
"""Dict of category uuids as keys and category dicts as values"""
SUBCATEGORIES_DICT: dict[tuple[str]] = None
"""Dict of category uuids as keys and subcategory dicts as values"""
CATALOG_ENUM: list[tuple[str, str, str, int]] = None
"""Enum for blender UI"""
CATALOG_DICT: dict = None


def load_licenses():
    # TODO: Get licenses from Superhive API
    # ! Licenses need to be sent with a unique integer id
    global LICENSES_ENUM
    global LICENSES_DICT
    LICENSES_ENUM = [
        # (
        #     "None", "None",
        #     "No license is applied to the product.",
        #     0
        # ),
        (
            "CC-BY",
            "Creative Commons Attribution",
            "Grants users the freedom to copy and redistribute the material in any medium or format and adapt, remix, transform, and build upon the material for any purpose, even commercially. Attribution is required.",
            1,
        ),
        (
            "SRF",
            "Standard Royalty Free",
            "Grants users the ability to make use of the purchased product for personal, educational, or commercial purposes with exceptions",
            2,
        ),
        (
            "EDITORIAL",
            "Editorial",
            "The Editorial License grants users the ability to make single use of the purchased product for editorial use",
            3,
        ),
    ]

    LICENSES_ENUM.append(
        (
            "UNRECOGNIZED",
            "Unrecognized License",
            "The license for this product either doesn't exist or is not recognized by Superhive",
            444,
        ),
    )

    LICENSES_DICT = {
        id: {"index": i, "id": id, "name": name, "description": desc, "id_int": id_int}
        for i, (id, name, desc, id_int) in enumerate(LICENSES_ENUM)
    }


def load_tags():
    # TODO: Get tags from Superhive API
    # ! Tags need to be sent with a unique integer id
    global TAGS_ENUM
    global TAGS_DICT
    TAGS_ENUM = [
        ("Add-on", "Add-on", "Add-on"),
        ("Animation", "Animation", "Animation"),
        ("Architecture", "Architecture", "Architecture"),
        ("Character", "Character", "Character"),
        ("Documentation", "Documentation", "Documentation"),
        ("Environment", "Environment", "Environment"),
        ("FX", "FX", "FX"),
        ("Lighting", "Lighting", "Lighting"),
        ("Material", "Material", "Material"),
        ("Music", "Music", "Music"),
        ("Other", "Other", "Other"),
        ("Plugin", "Plugin", "Plugin"),
        ("Prop", "Prop", "Prop"),
        ("Script", "Script", "Script"),
        ("Sound", "Sound", "Sound"),
        ("Template", "Template", "Template"),
        ("Texture", "Texture", "Texture"),
        ("Tutorial", "Tutorial", "Tutorial"),
        ("UI", "UI", "UI"),
        ("Vehicle", "Vehicle", "Vehicle"),
    ]
    TAGS_DICT = {
        id: {"id": id, "name": name, "description": desc}
        for id, name, desc in TAGS_ENUM
    }


def load_categories():
    # TODO: Get catalogs from Superhive API
    # ! Catalogs need to be sent with a unique integer id
    global CATEGORIES_DICT
    global SUBCATEGORIES_DICT
    global CATALOG_ENUM
    global CATALOG_DICT

    def enum_list_to_dict(*lst: tuple) -> dict:
        lst = sorted(lst, key=lambda x: x[1])
        return {
            item[0]: {
                "id": item[0],
                "name": item[1].replace("-", ""),
                "description": item[2],
                "id_int": item[3] if len(item) > 3 else None,
            }
            for item in lst
        }

    models_uuid = "21dafe8b-0f28-4b5b-9db1-3cb08836fa19"
    CATEGORIES_DICT = enum_list_to_dict(
        ("750c1acf-b947-4ee3-9377-ac71df9703e2", "Render Setups", "Render Setups"),
        ("74b09ef6-606c-40c0-ab08-bfe997971147", "Modifier Setups", "Modifier Setups"),
        ("504d79b3-5cca-455f-a571-99f131beb3fe", "Surfacing", "Surfacing"),
        (models_uuid, "Models", "Models"),
        ("f2fdf7d8-2172-4b8c-afd9-5fabfadc1608", "Addons", "Addons"),
        ("81da85a3-3553-4ad3-a58d-3dd7f5e71faf", "Training", "Training"),
    )

    SUBCATEGORIES_DICT = {
        "750c1acf-b947-4ee3-9377-ac71df9703e2": enum_list_to_dict(  # Render Setups
            (
                "1e118c47-4c11-4b3e-959b-7757e5293988",
                "Compositing Presets",
                "Compositing Presets",
            ),
            (
                "b0191cf5-6b33-494d-98f7-0919c36a9c7b",
                "Studio Lighting",
                "Studio Lighting",
            ),
        ),
        "74b09ef6-606c-40c0-ab08-bfe997971147": enum_list_to_dict(  # Modifier Setups
            (
                "eafcd18b-b840-4107-b4f5-1ce1b582eedc",
                "Procedural Generators",
                "Procedural Generators",
            ),
            (
                "aae64fda-7129-4163-ad83-6866154ce62d",
                "Geometry Node Groups",
                "Geometry Node Groups",
            ),
            (
                "0e8e8293-9845-4e3a-9af6-4f3b44c1e4c2",
                "Simulations & Effects",
                "Simulations & Effects",
            ),
        ),
        "504d79b3-5cca-455f-a571-99f131beb3fe": enum_list_to_dict(  # Surfacing
            ("a5357448-5044-42ff-a7c4-306709252c9c", "Animals", "Animals"),
            ("1f392f1a-52b3-4e33-8b4e-82e9e057676c", "Ice", "Ice"),
            ("fbff7298-b68e-4f47-bb87-c89fb20904a9", "Metal", "Metal"),
            ("6c4b444d-2ff8-47f3-968b-3523c4897d15", "Buildings", "Buildings"),
            ("faf7ea71-1592-4ad9-a024-31292bd2c567", "Ceramic", "Ceramic"),
            ("7bb9a7a0-b756-4533-a7d6-390149968d87", "HDRI Images", "HDRI Images"),
            ("4edcc29e-80d9-464d-8a97-d469cf3465b6", "Water", "Water"),
            ("885a5f9f-cb4e-4ec0-9063-dbb473e7d575", "Marble", "Marble"),
            ("307f5e4a-598d-4f6d-862d-508bb1e2e4eb", "Fabric", "Fabric"),
            ("de2995c4-c81b-4b92-853c-5f09423da3f0", "Glass", "Glass"),
            ("d592b47f-51ac-4eaa-b94e-31cff6d78524", "Stone", "Stone"),
            ("8f9a7d60-605c-4aaa-9610-767aca706529", "Ground", "Ground"),
            ("6820e963-9537-43de-a5f8-309aad4f972b", "Organic", "Organic"),
            ("46962d8a-e6c3-4efa-a075-118092899e9e", "Plastic", "Plastic"),
            ("39ce62c7-b0e0-40dc-b7f7-292301746731", "Sci Fi", "Sci Fi"),
            ("6f5bde3c-2d29-40df-a74f-66c9d819244f", "Ornaments", "Ornaments"),
            ("a21419d5-be92-4a26-aa27-8d1ac711a203", "Plants", "Plants"),
            ("837f6a8d-2e0a-4a4d-ac8d-40c7961770d5", "Humans", "Humans"),
            ("06cfee02-da21-476d-9623-945c2046f1f9", "Miscellaneous", "Miscellaneous"),
            ("a3eec9d0-e6dd-46b1-8712-c6777e025006", "Wood", "Wood"),
            ("2e9f1a40-a240-4dc6-b15d-0bd6dc9d76bd", "Concrete", "Concrete"),
        ),
        models_uuid: enum_list_to_dict(  # Models
            ("c8ff7dc6-80c7-4d30-920d-6664238d9b89", "3D Printable", "3D Printable", 0),
            ("88162bd5-a098-41d3-a8ca-fb2d44782e25", "Anatomy", "Anatomy", 1),
            ("8c45d1e6-87aa-4add-9530-a1742b468aa2", "Animation", "Animation", 2),
            ("b6218691-814f-47aa-bae8-d9ac6d2339a9", "Animals", "Animals", 3),
            ("540b025e-772f-4756-b452-c37c94c89be0", "Architecture", "Architecture", 4),
            (
                "f5f944f4-1599-4fd6-841f-0a2e8c712a36",
                "Asset Libraries",
                "Asset Libraries",
                5,
            ),
            ("dfecfe11-d5b7-4bd7-bc05-d68b8fbd72b2", "Base Meshes", "Base Meshes", 6),
            ("34eb4c8c-4278-49a7-a18b-e5d1baaa848f", "Buildings", "Buildings", 7),
            ("ae651e01-64f5-4c89-8c9e-405a13c70bb9", "Characters", "Characters", 8),
            (
                "870b2998-c290-4956-83e2-491a48975d5e",
                "Clothes & Accessories",
                "Clothes & Accessories",
                9,
            ),
            ("5e8e183f-cb84-4164-ba35-7af448cc47e8", "Creatures", "Creatures", 10),
            ("5a1fc884-a2b0-45d6-8858-d506f274a700", "Decals", "Decals", 11),
            (
                "93e4af11-e524-46a4-8d60-abed0cf91231",
                "Design Elements",
                "Design Elements",
                12,
            ),
            ("3d756712-b8d0-4619-8f92-e491d4aeb43e", "Electronics", "Electronics", 13),
            (
                "abecd690-510c-439f-a29c-95cbdc0b919f",
                "Engines & Parts",
                "Engines & Parts",
                14,
            ),
            (
                "f7bfd511-0913-4c96-8e65-5be285e879e6",
                "Fantasy & Fiction",
                "Fantasy & Fiction",
                15,
            ),
            (
                "7b0faac1-eb4b-4888-bd66-d3cecf04cb5d",
                "Food & Drinks",
                "Food & Drinks",
                16,
            ),
            ("1edfacc6-fd4a-437c-8a38-5adb2f93d950", "Furnishings", "Furnishings", 17),
            ("ae5885e3-ba3c-4e35-9e45-444f0a4079ac", "Game Ready", "Game Ready", 18),
            ("1ee5f173-997b-4c23-9e85-5cad98c9e1b0", "Humans", "Humans", 19),
            (
                "80522baf-b443-408c-826e-f655a4246bb6",
                "Miscellaneous",
                "Miscellaneous",
                20,
            ),
            (
                "2b186ef1-5bbb-4e6a-8c82-c7d7f926cba5",
                "Motion Graphics",
                "Motion Graphics",
                21,
            ),
            ("e6d16081-248a-49ea-bf06-785cc407caa7", "Music", "Music", 22),
            ("66a54ffe-175b-4381-a35a-64bd90338259", "Nature", "Nature", 23),
            (
                "ad7a8519-355b-464a-8319-b3407a2ba29f",
                "Parametric Models",
                "Parametric Models",
                24,
            ),
            ("7286a6c5-9ed2-4279-a7bb-fd7c7a9ac155", "Products", "Products", 25),
            ("19ad727c-3d84-497b-94cd-4e4f62c06f8a", "Sci-Fi", "Sci-Fi", 26),
            ("d86db79d-ff29-4d61-a3e5-6ecca19862dd", "Science", "Science", 27),
            ("a13af679-3718-4b3b-8d09-9d1e07a2ec07", "Sports", "Sports", 28),
            ("139791a5-51f5-4bde-88b3-d7045641dc75", "Tools", "Tools", 29),
            (
                "0738c45f-8f82-4f75-b7f7-2aff67de79dd",
                "Toys & Games",
                "Toys & Games",
                30,
            ),
            ("09e2e3ba-881c-4612-b435-33e7fb7fcc84", "Urban", "Urban", 31),
            ("77393a0c-9007-4e7e-baa3-b7e476a6f1bc", "Vehicles", "Vehicles", 32),
            (
                "2fe148e3-781c-41ce-8676-f6870778da77",
                "Weapons & Armor",
                "Weapons & Armor",
                33,
            ),
        ),
        "f2fdf7d8-2172-4b8c-afd9-5fabfadc1608": enum_list_to_dict(  # Addons
            (
                "a4fb032b-68b1-460b-b67a-529c38072618",
                "Import & Export",
                "Import & Export",
            ),
            (
                "77fcf941-5d72-4500-880c-10a62092fef3",
                "Theme Packages",
                "Theme Packages",
            ),
            (
                "223445c7-da0a-481c-b8dc-25e909270f14",
                "Materials and Shading",
                "Materials and Shading",
            ),
            ("e34f6ee9-09f0-48fa-8c9a-f4ab2c8b64f4", "Presets", "Presets"),
            ("535238db-8d9b-46f1-bc96-ff4af3fa51d0", "Interface", "Interface"),
            (
                "7adf23e4-83f0-4639-876f-24752c8e7efd",
                "Asset Management",
                "Asset Management",
            ),
            ("5c12c6a3-51db-4bac-998f-667ca4f87008", "Rendering", "Rendering"),
            ("a55acdfb-1f6f-4767-9393-33f93cac576b", "Rigging", "Rigging"),
            ("02f5296c-2931-43ec-bf70-dcae301473a4", "Animation", "Animation"),
            ("894d43c5-918f-460b-bf58-dfdd67231409", "Modeling", "Modeling"),
            ("5be69cf6-d6bb-4bc2-93cf-df6bbc84a8bb", "VSE", "VSE"),
        ),
        "81da85a3-3553-4ad3-a58d-3dd7f5e71faf": enum_list_to_dict(  # Training
            ("5b5702e7-c3ef-4d59-b8b9-cbc1aa1a72cb", "e-Books", "e-Books"),
            (
                "33d0113b-01d3-4809-a51b-d5e4b655bbf6",
                "Video Tutorials",
                "Video Tutorials",
            ),
        ),
    }

    CATALOG_ENUM = [
        (
            subcat["id"],
            subcat["name"],
            subcat["description"],
            subcat["id_int"] if "id_int" in subcat else None,
        )
        for subcat in SUBCATEGORIES_DICT.get(models_uuid, {}).values()
    ]
    CATALOG_ENUM.append(
        (
            "UNRECOGNIZED",
            "Unrecognized Catalog",
            "The set catalog is not supported by Superhive",
            444,
        )
    )

    CATALOG_DICT = {
        id: {
            "id": id,
            "name": name,
            "description": desc,
            "id_int": id_int,
        }
        for id, name, desc, id_int in CATALOG_ENUM
    }


def get_licenses(_=None, __=None) -> tuple[tuple[str]]:
    """Get the licenses enum for Blender UI"""
    global LICENSES_ENUM
    return LICENSES_ENUM


def get_license_by_name(name: str) -> dict:
    """Get the license by name"""
    global LICENSES_DICT

    return next((val for val in LICENSES_DICT.values() if val["name"] == name), None)


def get_tags(_=None, __=None) -> tuple[tuple[str]]:
    """Get the tags enum for Blender UI"""
    global TAGS_ENUM
    return TAGS_ENUM


def get_categories(_=None, __=None) -> tuple[tuple[str]]:
    """Get the catalog enum for Blender UI"""
    global CATALOG_ENUM
    return CATALOG_ENUM


def get_catalog_by_name(name: str, is_catalog_simple_name=False) -> dict:
    """Get the catalog by name"""
    global CATALOG_DICT

    if is_catalog_simple_name and "-" in name:
        name = name.split("-")[-1]

    return next((val for val in CATALOG_DICT.values() if val["name"] == name), None)


load_categories()
load_licenses()
load_tags()
