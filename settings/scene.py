import bpy
import bpy.utils
from bpy.types import PropertyGroup, UILayout
from bpy.props import EnumProperty, PointerProperty, FloatProperty, BoolProperty, StringProperty
from time import time


class ProgressBar(PropertyGroup):
    progress: FloatProperty(subtype="PERCENTAGE", min=0, max=100)
    show: BoolProperty()
    label: StringProperty()
    """Label for the progress bar. This is the text that will be displayed on the progress bar."""

    formated_time: StringProperty()
    start_time = 0

    cancel: BoolProperty(
        name="Cancel",
        description="Cancel the current process",
        default=False,
    )
    is_complete: BoolProperty()

    def start(self):
        self.progress = 0
        self.show = True
        self.cancel = False
        self.start_time = time()

        self.is_complete = False

    def end(self):
        self.is_complete = True
        self.show = False

    def update_formated_time(self) -> None:
        """Converts the time taken to import the pack to a string and returns it. The string will be formatted to two decimal places."""
        hrs = 0
        mins = 0
        secs = 0
        timer = time() - self.start_time
        # Hours
        if timer > 3600:
            hrs = timer // 3600
        # Minutes
        elif timer > 60:
            mins = (timer - hrs * 3600) // 60
        # Seconds
        secs = timer - hrs * 3600 - mins * 60

        if hrs:
            self.formated_time = f"{hrs:.0f}h, {mins:.0f}m, {secs:.2f}s"
        elif mins:
            self.formated_time = f"{mins:.0f}m, {secs:.2f}s"
        else:
            self.formated_time = f"{secs:.2f}s"

    def draw(self, layout: UILayout) -> None:
        row = layout.row(align=True)
        row.prop(self, "progress", text=self.label)
        row.label(text=self.formated_time)


class SH_Scene(PropertyGroup):
    header_progress_bar: PointerProperty(type=ProgressBar)

    library_mode: EnumProperty(
        items=(
            ("BLENDER", "Blender",
             "Blender's default asset library settings and options"),
            ("SUPERHIVE", "SuperHive", "Settings and options for uploading to Superhive's asset system"),
        ),
        name="Library Mode",
        description="Choose which asset library settings to use",
    )

    def __ignore__(self):
        self.header_progress_bar: ProgressBar


classes = (
    ProgressBar,
    SH_Scene,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.superhive = PointerProperty(type=SH_Scene)


def unregister():
    del bpy.types.Scene.superhive
    for cls in classes:
        bpy.utils.unregister_class(cls)
