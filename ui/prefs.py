import bpy
from bpy.types import AddonPreferences
from bpy.props import StringProperty, EnumProperty
from .. import __package__ as base_package
import os


class SH_AddonPreferences(AddonPreferences):
    bl_idname = base_package

    display_extras: bpy.props.BoolProperty(
        name="Display Extras",
        description="Display extra information",
        default=False,
    )

    default_auther_name: StringProperty(
        name="Author Name",
        description="The name to put by default in the author field",
    )

    default_license: EnumProperty(
        name="Default License",
        description="The default license to use for new assets",
        items=(
            ("CC0", "CC0", "CC0"),
            ("CC-BY", "CC-BY", "CC-BY"),
            ("CC-BY-SA", "CC-BY-SA", "CC-BY-SA"),
            ("CC-BY-NC", "CC-BY-NC", "CC-BY-NC"),
            ("CC-BY-ND", "CC-BY-ND", "CC-BY-ND"),
            ("CC-BY-NC-SA", "CC-BY-NC-SA", "CC-BY-NC-SA"),
            ("CC-BY-NC-ND", "CC-BY-NC-ND", "CC-BY-NC-ND"),
        ),
        default="CC0",
    )

    library_directory: StringProperty(
        name="Asset Library Directory",
        description="The directory to create new asset libraries in for the Superhive system",
        subtype="DIR_PATH",
        default=os.path.join(os.path.expanduser("~"), "Superhive Libraries"),
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "display_extras")
        layout.prop(self, "default_auther_name")
        layout.prop(self, "default_license")
        layout.prop(self, "library_directory")


classes = (
    SH_AddonPreferences,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)