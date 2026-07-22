import tempfile
import zipfile
from importlib.util import find_spec
from pathlib import Path
from threading import Thread
from typing import TYPE_CHECKING

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty
from bpy.types import AssetRepresentation, Context, Operator

from .. import utils
from . import polls

if TYPE_CHECKING:
    from ..settings import scene

comp_enum = [
    (
        "ZIP_STORED",
        "None",
        "No compression. Just place files in .zip file. This is the fastest option. (ZIP_STORED)",
    )
]
if find_spec("zlib"):
    comp_enum.append((
        "ZIP_DEFLATED",
        "Standard",
        "Compress files using zlib, ie the normal zip compression algorithm. This option is slow with not the best compression. (ZIP_DEFLATED)",
    ))
if find_spec("bz2"):
    comp_enum.append((
        "ZIP_BZIP2",
        "Maximum",
        "Compress files using bzip2 compression algorithm. This is a good balance between speed and compression ratio. (ZIP_BZIP2)",
    ))
if find_spec("lzma"):
    comp_enum.append((
        "ZIP_LZMA",
        "Ultra",
        "Compress files using LZMA compression algorithm. This is the slowest option but gives the best compression ratio. NOT RECOMMENDED as not all OS's include this library when extracting/importing(ZIP_LZMA)",
    ))


class SH_OT_ExportLibrary(Operator):
    """Legacy local zip export. Superseded by bkeeper.publish_library (direct
    API upload); kept as a dev tool behind the Display Extras preference."""

    bl_idname = "bkeeper.export_library"
    bl_label = "Export Active Library (Legacy)"
    bl_description = (
        "Export the active library to a local .zip file. Legacy: publishing to"
        " Superhive now uploads directly (Publish to Superhive)"
    )
    bl_options = {"REGISTER", "UNDO"}

    total_files = 1
    files_written = 0
    updated = False

    movingfiles_main_prog = 0
    movingfiles_sub_prog = 0
    movingfiles_sub_show = False
    movingfiles_file_prog = 0
    file_label = ""
    sub_label = ""
    zipping_bar_prog = 0

    is_zipping = False

    compression_type: EnumProperty(
        name="Type",
        description="The type of compression to use when zipping the pack",
        items=comp_enum,
        default="ZIP_BZIP2",
    )
    deflated_compression_level: IntProperty(
        name="Level",
        description="A value of 1 (Best Speed) is fastest and produces the least compression, while a value of 9 (Best Compression) is slowest and produces the most. 0 is no compression. The default value is 6 which is a good compromise between speed and compression.",
        min=0,
        max=9,
        default=6,
    )
    bzip_compression_level: IntProperty(
        name="Level",
        description="The level of compression to use when using the bzip2 compression type. 1 produces the least compression, and 9 (default) produces the most compression",
        min=1,
        max=9,
        default=9,
    )

    selected_only: BoolProperty(
        name="Selected Only",
        description="Only export selected assets",
    )

    target_zipfile_size: FloatProperty(
        name="Target Size (GBs)",
        description="The target max size each zip file should be cut off at and a new file started in Gigabytes. Would advise going under as each asset and its files will not be split up among zip files",
        default=4.5,
        min=0,
    )

    _target_file_size = 1_000_000_000
    zip_num = 1

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        if not utils.get_prefs().display_extras:
            cls.poll_message_set(
                "Legacy export — enable Display Extras in the add-on preferences"
            )
            return False

        if not polls.is_asset_browser(context, cls=cls):
            return False

        if not context.space_data.params.asset_library_reference != "ALL":
            cls.poll_message_set("Active library must not be 'ALL'")
            return False

        return True

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        layout.prop(self, "selected_only")

        layout.separator()

        text = [("Hover over settings and menu items for more information")]
        col = layout.column(align=True)
        for line in text:
            row = col.row(align=True)
            row.active = False
            row.alignment = "CENTER"
            row.label(text=line)
        layout.label(text="Compression:")
        layout.prop(self, "compression_type")
        if self.compression_type == "ZIP_DEFLATED":
            layout.prop(self, "deflated_compression_level")
        elif self.compression_type == "ZIP_BZIP2":
            layout.prop(self, "bzip_compression_level")

        layout.prop(self, "target_zipfile_size")

    def invoke(self, context, event):
        self.z_to_close = []
        context.window_manager.invoke_props_dialog(self, width=400)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        print()
        print()
        print()
        if self.selected_only:
            self.assets: list[AssetRepresentation] = context.selected_assets[:]
            # Get lib after to ensure that the selected assets are correct
            self.lib = utils.from_active(context, area=context.area, load_assets=True)
        else:
            self.lib = utils.from_active(context, area=context.area, load_assets=True)
            self.assets: list[AssetRepresentation] = self.lib.get_possible_assets()

        self.json_data = self.lib.to_dict()

        self.zip_path = self.lib.path / f"{self.lib.name}.zip"

        self._target_file_size = self.target_zipfile_size * 1_000_000_000

        scn_sets: "scene.SH_Scene" = context.scene.superhive
        self.prog = scn_sets.export_library
        context.window_manager.modal_handler_add(self)
        self._timer = context.window_manager.event_timer_add(0.01, window=context.window)

        utils.ensure_sidepanel_right_is_open(context.space_data)

        self._th = Thread(target=self.handle_files)

        self._th.start()
        self.prog.start()

        return {"RUNNING_MODAL"}

    def handle_files(self):
        with tempfile.TemporaryDirectory() as tempdir:
            tempdir = Path(tempdir)
            print("Moving files to tempdir...")
            print("Progress:   0.00%", end="\r")
            self.movingfiles_main_prog = 0
            self.updated = True
            self.prog.movingfiles_bar.main.update_start_time()
            self.prog.movingfiles_bar.show_sub = True

            for i, asset in enumerate(self.assets):
                p = Path(asset.full_library_path)

                self.file_label = p.name
                self.prog.movingfiles_bar.file.update_start_time()
                self.movingfiles_file_prog = 0
                self.updated = True

                utils.export_helper(p, tempdir, self.json_data, op=self)

                self.movingfiles_main_prog = i / len(self.assets)
                self.updated = True

                prog = f"{self.movingfiles_main_prog * 100:.2f}"
                print(f"Progress: {prog.rjust(6)}%", end="\r")
            self.movingfiles_main_prog = 1
            self.updated = True
            print("Progress: 100.00%")
            print()

            json_file = self.lib.save_json(data=self.json_data, directory=tempdir)

            files_to_write: list[tuple[Path, list[Path]]] = list(
                (d, [f for f in d.rglob("*") if f.is_file()]) for d in tempdir.iterdir()
            )
            """A list of tuples containing the directory and a list of files in that directory"""

            total_files = sum(len(files) for _, files in files_to_write)
            self.is_zipping = True
            # zip_path = tempdir / "export.zip"
            print("Writing to:", self.zip_path)
            print("Progress:   0.00%", end="\r")
            self.prog.zipping_bar.update_start_time()
            is_multi = False
            files_zipped = 0
            while files_to_write:
                if is_multi:
                    self.zip_path.rename(self.zip_path.with_stem(f"{self.zip_path.stem}_{self.zip_num}"))
                    self.zip_num += 1
                with zipfile.ZipFile(self.zip_path, "w") as zipf:
                    zipf.write(json_file, json_file.relative_to(tempdir))
                    for _ in range(len(files_to_write)):
                        _d, files = files_to_write.pop(0)
                        for file in files:
                            zipf.write(file, file.relative_to(tempdir))
                            files_zipped += 1

                            self.zipping_bar_prog = files_zipped / total_files
                            self.updated = True

                            prog = f"{self.zipping_bar_prog * 100:.2f}"
                            print(f"Progress: {prog.rjust(6)}%", end="\r")

                        if zipf.fp.tell() > self._target_file_size:
                            is_multi = True
                            break

            if is_multi:
                self.zip_path = self.zip_path.rename(self.zip_path.with_stem(f"{self.zip_path.stem}_{self.zip_num}"))
            self.zipping_bar_prog = 1
            self.updated = True
            print("Progress: 100.00%")

    def modal(self, context, event):
        context.area.tag_redraw()

        if self.is_zipping:
            self.prog.zipping_bar.update_formated_time()
        else:
            self.prog.movingfiles_bar.update_formated_time()

        if self.updated:
            self.updated = False
            self.prog.movingfiles_bar.main.progress = self.movingfiles_main_prog
            self.prog.movingfiles_bar.file.progress = self.movingfiles_file_prog
            self.prog.movingfiles_bar.file_label = self.file_label
            self.prog.zipping_bar.progress = self.zipping_bar_prog
            # self.prog.upload_bar.progress = self.upload_bar_prog

            if self.movingfiles_sub_show:
                self.prog.movingfiles_bar.show_sub = True
                self.prog.movingfiles_bar.sub_label = self.sub_label
                self.prog.movingfiles_bar.sub.progress = self.movingfiles_sub_prog
            else:
                self.prog.movingfiles_bar.show_sub = False

        if not self._th.is_alive():
            self.finished(context)
            return {"FINISHED"}

        if event.type in {"MIDDLEMOUSE", "WHEELUPMOUSE", "WHEELDOWNMOUSE"}:
            return {"PASS_THROUGH"}

        return {"RUNNING_MODAL"}

    def finished(self, context: Context) -> None:
        self._th.join()
        context.window_manager.event_timer_remove(self._timer)
        try:
            utils.open_location(str(self.zip_path))
        except Exception as e:
            print("Unable to open export folder:", e)
        bpy.app.timers.register(self.delayed_close, first_interval=1)
        print()
        print()
        print()

    def delayed_close(self):
        self.prog.end()
        for area in bpy.context.screen.areas:
            area.tag_redraw()


classes = (SH_OT_ExportLibrary,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
