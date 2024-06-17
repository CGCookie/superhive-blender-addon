import bpy
from bpy.types import Operator, UILayout, Context
from bpy.props import StringProperty, EnumProperty


class SH_OT_CreateHiveAssetLibrary(Operator):
    bl_idname = "superhive.create_hive_asset_library"
    bl_label = "Create Hive Asset Library"
    bl_description = "Create a new asset library for the Superhive system"
    bl_options = {'REGISTER', 'UNDO'}

    library_name: StringProperty(
        name="Asset Library Name",
        description="The name of the asset library to create",
    )

    directory: StringProperty(
        name="Asset Library Directory",
        description="The directory to store assets in for the new library",
    )

    draw_phase: EnumProperty(
        items=(
            ("NAME", "Name", "Get a name"),
            ("NAME_EXISTS", "Name Exists", "The name already exists"),
            ("DIR", "Directory", "Get a dir"),
            ("DIR_EXISTS", "Directory Exists", "The directory already exists"),
            ("COMPLETE", "Complete", "Complete the creation of the asset library"),
        )
    )

    def draw(self, context):
        layout = self.layout
        if self.draw_phase == "NAME":
            self.draw_get_name(layout)
        elif self.draw_phase == "NAME_EXISTS":
            self.draw_name_exists(layout)
        elif self.draw_phase == "DIR":
            self.draw_get_dir(layout)
        elif self.draw_phase == "DIR_EXISTS":
            self.draw_dir_exists(layout)
        elif self.draw_phase == "COMPLETE":
            self.draw_complete(layout)

    def draw_get_name(self, layout: UILayout):
        layout.label(text="Enter the name of the new asset library")
        layout.prop(self, "library_name")

    def draw_name_exists(self, layout: UILayout):
        layout.label(text="An asset library with the same name already exists.")
        layout.label(text="Please choose another.")
        layout.prop(self, "library_name")

    def draw_get_dir(self, layout: UILayout):
        layout.label(text="Enter the directory for the new asset library")
        layout.prop(self, "directory")

    def draw_dir_exists(self, layout: UILayout):
        layout.label(text="An asset library with the same directory already exists.")
        layout.label(text="Please choose another.")
        layout.prop(self, "directory")

    def draw_complete(self, layout: UILayout):
        layout.label(text="The asset library has been created.")
        layout.label(text="Enjoy filling it with assets!")

    def invoke(self, context, event):
        self.draw_phase = "NAME"

        self.library_name = ""
        self.directory = ""

        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if not self.library_name and self.draw_phase == "NAME":
            return context.window_manager.invoke_popup(self)
        if self.library_name and self.draw_phase == "NAME":
            return self.check_library_name(context)
        if self.draw_phase == "NAME_EXISTS":
            return self.check_library_name(context)
        if self.draw_phase == "DIR":
            return self.check_dir(context)
        if self.draw_phase == "DIR_EXISTS":
            return self.check_dir(context)
        if self.draw_phase == "COMPLETE":
            return {'FINISHED'}

    def check_library_name(self, context: Context):
        lib = context.preferences.filepaths.asset_libraries.get(self.library_name)
        if lib:
            self.draw_phase = "NAME_EXISTS"
        else:
            self.draw_phase = "DIR"
        return context.window_manager.invoke_popup(self)

    def check_dir(self, context: Context):
        for asset_lib in context.preferences.filepaths.asset_libraries:
            if asset_lib.path == self.directory:
                self.draw_phase = "DIR_EXISTS"
                break
        if self.draw_phase == "DIR":
            self.draw_phase = "COMPLETE"
            self.create_asset_library(context)
        return context.window_manager.invoke_popup(self)

    def create_asset_library(self, context: Context):
        context.preferences.filepaths.asset_libraries.new(
            name=self.library_name,
            directory=self.directory
        )


classes = (
    SH_OT_CreateHiveAssetLibrary,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
