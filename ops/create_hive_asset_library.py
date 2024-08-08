from pathlib import Path
from typing import TYPE_CHECKING

import bpy
from bpy.props import EnumProperty, StringProperty
from bpy.types import Context, Operator, UILayout

from .. import __package__ as base_package

if TYPE_CHECKING:
    from ..ui import prefs


class SH_OT_CreateHiveAssetLibrary(Operator):
    bl_idname = "bkeeper.create_hive_asset_library"
    bl_label = "Create Hive Asset Library"
    bl_description = "Create a new asset library for the Superhive system"
    bl_options = {"REGISTER", "UNDO"}

    ui_width = 400

    library_name: StringProperty(
        name="Asset Library Name",
        description="The name of the asset library to create",
    )

    draw_phase: EnumProperty(
        items=(
            ("NAME", "Name", "Get a name"),
            ("NAME_EXISTS", "Name Exists", "The name already exists"),
            ("COMPLETE", "Complete", "Complete the creation of the asset library"),
        )
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.activate_init = True
        if self.draw_phase == "NAME":
            self.draw_get_name(layout)
        elif self.draw_phase == "NAME_EXISTS":
            self.draw_name_exists(layout)
        elif self.draw_phase == "COMPLETE":
            self.draw_complete(layout)

    def draw_get_name(self, layout: UILayout):
        row = layout.row()
        row.alignment = "CENTER"
        row.label(text="Enter the name of the new asset library")

        lib_exists = bool(self.asset_lib_prefs.get(self.library_name))
        row = layout.row()
        row.activate_init = True
        row.alert = lib_exists
        row.prop(self, "library_name")
        if lib_exists:
            row = layout.row()
            row.alert = True
            row.alignment = "RIGHT"
            row.label(text="An asset library with the same name already exists.")

    def draw_name_exists(self, layout: UILayout):
        row = layout.row()
        row.alert = True
        row.alignment = "CENTER"
        row.label(text="An asset library with the same name already exists.")

        row = layout.row()
        row.alignment = "CENTER"
        row.label(text="Please choose another.")

        lib_exists = bool(self.asset_lib_prefs.get(self.library_name))
        row = layout.row()
        row.alert = lib_exists
        row.activate_init = True
        row.prop(self, "library_name")
        if lib_exists:
            row = layout.row()
            row.alert = True
            row.alignment = "RIGHT"
            row.label(text="An asset library with the same name already exists.")

    def draw_complete(self, layout: UILayout):
        row = layout.row()
        row.alignment = "CENTER"
        row.label(text="The asset library has been created.")
        row = layout.row()
        row.alignment = "CENTER"
        row.label(text="Enjoy filling it with assets!")

    def invoke(self, context, event):
        self.draw_phase = "NAME"

        self.library_name = ""

        self.asset_lib_prefs = context.preferences.filepaths.asset_libraries

        return context.window_manager.invoke_props_dialog(self, width=self.ui_width)

    def execute(self, context):
        if self.library_name and self.draw_phase == "NAME":
            return self.check_library_name(context)
        elif self.draw_phase == "NAME_EXISTS":
            return self.check_library_name(context)
        if self.draw_phase == "COMPLETE":
            # context.space_data.params.asset_library_reference = self.library_name
            return {"FINISHED"}

    def check_library_name(self, context: Context):
        lib = self.asset_lib_prefs.get(self.library_name)
        if lib:
            self.draw_phase = "NAME_EXISTS"
            context.window_manager.invoke_props_dialog(self, width=self.ui_width)
            return {"RUNNING_MODAL"}
        else:
            self.create_asset_library(context)
            self.draw_phase = "COMPLETE"
            context.window_manager.invoke_props_dialog(self, width=self.ui_width)
            return {"RUNNING_MODAL"}

    def create_asset_library(self, context: Context):
        pref_settings: "prefs.SH_AddonPreferences" = context.preferences.addons[
            base_package
        ].preferences
        dir: Path = (
            Path(pref_settings.library_directory)
            / self.library_name.replace(" ", "_").casefold()
        )
        dir.mkdir(parents=True, exist_ok=True)

        self.asset_lib_prefs.new(name=self.library_name, directory=str(dir))


classes = (SH_OT_CreateHiveAssetLibrary,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
