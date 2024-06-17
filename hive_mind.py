"""The place to grab general settings and lists"""

LICENSES: tuple[tuple[str]] = None
TAGS: tuple[tuple[str]] = None
CATEGORIES: tuple[tuple[str]] = None


def get_licenses() -> tuple[tuple[str]]:
    # TODO: Get licenses from Superhive API
    global LICENSES
    if LICENSES is None:
        LICENSES = (
            ("CC0", "CC0", "CC0"),
            ("CC-BY", "CC-BY", "CC-BY"),
            ("CC-BY-SA", "CC-BY-SA", "CC-BY-SA"),
            ("CC-BY-NC", "CC-BY-NC", "CC-BY-NC"),
            ("CC-BY-ND", "CC-BY-ND", "CC-BY-ND"),
            ("CC-BY-NC-SA", "CC-BY-NC-SA", "CC-BY-NC-SA"),
            ("CC-BY-NC-ND", "CC-BY-NC-ND", "CC-BY-NC-ND"),
        )
    return LICENSES


def get_tags() -> tuple[tuple[str]]:
    # TODO: Get tags from Superhive API
    global TAGS
    if TAGS is None:
        TAGS = [
            ("Architecture", "Architecture", "Architecture"),
            ("Vehicle", "Vehicle", "Vehicle"),
            ("Prop", "Prop", "Prop"),
            ("Environment", "Environment", "Environment"),
            ("Character", "Character", "Character"),
            ("Material", "Material", "Material"),
            ("Texture", "Texture", "Texture"),
            ("Animation", "Animation", "Animation"),
            ("FX", "FX", "FX"),
            ("Lighting", "Lighting", "Lighting"),
            ("Sound", "Sound", "Sound"),
            ("Music", "Music", "Music"),
            ("UI", "UI", "UI"),
            ("Script", "Script", "Script"),
            ("Plugin", "Plugin", "Plugin"),
            ("Addon", "Addon", "Addon"),
            ("Template", "Template", "Template"),
            ("Tutorial", "Tutorial", "Tutorial"),
            ("Documentation", "Documentation", "Documentation"),
            ("Other", "Other", "Other"),
        ]
    return TAGS


def get_categories() -> tuple[tuple[str]]:
    # TODO: Get categories from Superhive API
    global CATEGORIES
    if CATEGORIES is None:
        CATEGORIES = [
            ("Model", "Model", "Model"),
            ("Rig", "Rig", "Rig"),
            ("Animation", "Animation", "Animation"),
            ("Material", "Material", "Material"),
            ("Texture", "Texture", "Texture"),
            ("Sound", "Sound", "Sound"),
            ("Music", "Music", "Music"),
            ("FX", "FX", "FX"),
            ("Lighting", "Lighting", "Lighting"),
            ("Script", "Script", "Script"),
            ("Plugin", "Plugin", "Plugin"),
            ("Addon", "Addon", "Addon"),
            ("Template", "Template", "Template"),
            ("Tutorial", "Tutorial", "Tutorial"),
            ("Documentation", "Documentation", "Documentation"),
            ("Other", "Other", "Other"),
        ]
    return CATEGORIES