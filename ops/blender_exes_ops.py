import os
import platform
from pathlib import Path

import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from .. import utils

from time import time


class SH_OT_GatherBlenderExes(Operator):
    bl_idname = "bkeeper.gather_blender_exes"
    bl_label = "Gather Blender Executables"
    bl_description = "Gather Blender executables from expected places"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        paths, executable_name = self._get_blender_paths()

        prefs = utils.get_prefs()

        print()
        for path in paths:
            p = Path(path)
            
            t = time()
            bexes = self.find_blender_executables(str(p), executable_name)
            
            if not bexes:
                continue
            
            print(f"Search: {time() - t:.2f}s")
            t = time()
            
            for bexe in bexes:
                prefs.add_blender_version(
                    bexe.parent.name.replace("-", " ").title(), str(bexe)
                )
        print()

        return {"FINISHED"}
    
    def find_blender_executables(self, path: str, executable_name: str) -> list[Path]:
        if not os.path.exists(path):
            return []
        found_files = []

        def scan_dir(directory):
            with os.scandir(directory) as it:
                for entry in it:
                    if entry.is_file() and entry.name == executable_name:
                        found_files.append(Path(entry.path))
                    elif entry.is_dir():
                        scan_dir(entry.path)
        
        scan_dir(path)
        return found_files

    def _get_blender_paths(self) -> list[str]:
        system = platform.system()

        if system == "Windows":
            possible_paths = [
                os.path.expandvars(r"%PROGRAMFILES%\Blender Foundation\Blender"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Blender Foundation\Blender"),
                os.path.expandvars(r"%LOCALAPPDATA%\Blender Foundation\Blender"),
                os.path.expanduser(r"~\Documents\Blender_Versions"),  # TODO: Remove
            ]
            executable_name = "blender.exe"

        elif system == "Darwin":  # macOS
            possible_paths = [
                "/Applications/Blender.app/Contents/MacOS/",
                os.path.expanduser("~/Applications/Blender.app/Contents/MacOS/"),
            ]
            executable_name = "Blender"

        elif system == "Linux":
            possible_paths = [
                "/usr/bin/",
                "/usr/local/bin/",
                os.path.expanduser("~/bin/"),
            ]
            executable_name = "blender"

        else:
            raise Exception(f"Unsupported operating system: {system}")

        return possible_paths, executable_name


class SH_OT_AddBlenderExes(Operator):
    bl_idname = "bkeeper.add_blender_exes"
    bl_label = "Add Blender Executables"
    bl_description = "Add Blender executable"
    bl_options = {"REGISTER", "UNDO"}

    name: StringProperty(
        name="Name",
        description="Name of the Blender version to display in the UI",
    )

    path: StringProperty(
        name="Path",
        description="Path to the Blender executable",
        subtype="FILE_PATH",
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "name")
        layout.prop(self, "path")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        prefs = utils.get_prefs()

        p = Path(self.path)
        if not p.exists():
            self.report({"ERROR"}, f"Path does not exist: {self.path}")
            return {"CANCELLED"}

        if not self.check_executable(p):
            self.report({"ERROR"}, f"Invalid Blender executable: {p.name}")
            return {"CANCELLED"}

        prefs.add_blender_version(self.name, self.path)

        return {"FINISHED"}

    def check_executable(self, path: Path) -> bool:
        system = platform.system()

        if system == "Windows" and path.name == "blender.exe":
            return True
        if system == "Darwin" and path.name == "Blender":
            return True
        if system == "Linux" and path.name == "blender":
            return True

        return False


class SH_OT_RemoveBlenderExes(Operator):
    bl_idname = "bkeeper.remove_blender_exes"
    bl_label = "Remove Blender Executables"
    bl_description = "Remove the active Blender executable"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        prefs = utils.get_prefs()

        prefs.remove_blender_version(prefs.active_blender_version_index)

        return {"FINISHED"}


classes = (
    SH_OT_AddBlenderExes,
    SH_OT_RemoveBlenderExes,
    SH_OT_GatherBlenderExes,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
