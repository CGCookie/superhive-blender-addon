from typing import TYPE_CHECKING
import zipfile
from importlib.util import find_spec
from pathlib import Path
import time

import bpy
from bpy.types import Operator, UserAssetLibrary, Context
from bpy.props import EnumProperty, IntProperty
from bpy_extras import asset_utils
from threading import Thread
from concurrent.futures import ThreadPoolExecutor

from .. import utils

if TYPE_CHECKING:
    from ..settings import scene

comp_enum = [(
    "ZIP_STORED", "None",
    "No compression. Just place files in .zip file. This is the fastest option. (ZIP_STORED)"
)]
if find_spec("zlib"):
    comp_enum.append((
        "ZIP_DEFLATED", "Standard",
        "Compress files using zlib, ie the normal zip compression algorithm. This option is slow with not the best compression. (ZIP_DEFLATED)"
    ))
if find_spec("bz2"):
    comp_enum.append((
        "ZIP_BZIP2", "Maximum",
        "Compress files using bzip2 compression algorithm. This is a good balance between speed and compression ratio. (ZIP_BZIP2)"
    ))
if find_spec("lzma"):
    comp_enum.append((
        "ZIP_LZMA", "Ultra",
        "Compress files using LZMA compression algorithm. This is the slowest option but gives the best compression ratio. NOT RECOMMENDED as not all OS's include this library when extracting/importing(ZIP_LZMA)"
    ))

class EmptyCompressor(object):
    def flush(self):
        return bytes(0)
class ZipFileParallel(zipfile.ZipFile):
    """
    Example
    -------
    ```py
    file = ZipFileParallel('file.zip','w',zipfile.ZIP_BZIP2)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []

        for img in enumerate(images):
            fname = f'images/{idx}.raw'
            futures.append(executor.submit(file.writestr, fname ,img.tobytes()))
        
        concurrent.futures.wait(futures)
    ```
    """
    def writestr(self, zinfo_or_arcname, data,
                 compress_type=None, compresslevel=None):
        """Write a file into the archive.  The contents is 'data', which
        may be either a 'str' or a 'bytes' instance; if it is a 'str',
        it is encoded as UTF-8 first.
        'zinfo_or_arcname' is either a ZipInfo instance or
        the name of the file in the archive.
        """
        if isinstance(data, str):
            data = data.encode("utf-8")
        if not isinstance(zinfo_or_arcname, zipfile.ZipInfo):
            zinfo = zipfile.ZipInfo(filename=zinfo_or_arcname,
                                    date_time=time.localtime(time.time())[:6])
            zinfo.compress_type = self.compression
            zinfo._compresslevel = self.compresslevel
            if zinfo.filename[-1] == '/':
                zinfo.external_attr = 0o40775 << 16  # drwxrwxr-x
                zinfo.external_attr |= 0x10  # MS-DOS directory flag
            else:
                zinfo.external_attr = 0o600 << 16  # ?rw-------
        else:
            zinfo = zinfo_or_arcname

        if not self.fp:
            raise ValueError(
                "Attempt to write to ZIP archive that was already closed")

        if compress_type is not None:
            zinfo.compress_type = compress_type

        if compresslevel is not None:
            zinfo._compresslevel = compresslevel

        zinfo.file_size = len(data)  # Uncompressed size
        crc = zipfile.crc32(data, 0)
        # compress data
        compressor = zipfile._get_compressor(
            zinfo.compress_type, zinfo._compresslevel)
        if compressor and hasattr(compressor, 'compress'):
            data = compressor.compress(data)
            data += compressor.flush()

        with self._lock:
            with self.open(zinfo, mode='w') as dest:
                dest._compressor = None  # remove the compressor so it doesn't compress again
                dest.write(data)
                dest._crc = crc
                dest._file_size = zinfo.file_size
                dest._compress_size = len(data)
                dest._compressor = EmptyCompressor()  # use an empty compressor


class SH_OT_ExportLibrary(Operator):
    bl_idname = "superhive.export_library"
    bl_label = "Export Active Library"
    bl_description = "Export the active library to a .zip file"
    bl_options = {"REGISTER", "UNDO"}

    # TODO: This should zip to a temporary location and then upload to the server

    total_files = 1
    files_written = 0
    updated = False

    compression_type: EnumProperty(
        name="Type",
        description="The type of compression to use when zipping the pack",
        items=comp_enum,
        default="ZIP_BZIP2"
    )
    deflated_compression_level: IntProperty(
        name="Level",
        description="A value of 1 (Best Speed) is fastest and produces the least compression, while a value of 9 (Best Compression) is slowest and produces the most. 0 is no compression. The default value is 6 which is a good compromise between speed and compression.",
        min=0,
        max=9,
        default=6
    )
    bzip_compression_level: IntProperty(
        name="Level",
        description="The level of compression to use when using the bzip2 compression type. 1 produces the least compression, and 9 (default) produces the most compression",
        min=1,
        max=9,
        default=9
    )

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        if not asset_utils.SpaceAssetInfo.is_asset_browser(context.space_data):
            cls.poll_message_set("`context.space_data` must be Asset Browser")
            return False

        scene_sets: 'scene.SH_Scene' = context.scene.superhive
        if scene_sets.library_mode != "SUPERHIVE":
            cls.poll_message_set("Library mode must be 'SUPERHIVE'")
            return False

        if not context.space_data.params.asset_library_reference != "ALL":
            cls.poll_message_set("Active library must not be 'ALL'")
            return False

        return True

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

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

    def invoke(self, context, event):
        self.z_to_close = []
        context.window_manager.invoke_props_dialog(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        lib_name: str = context.space_data.params.asset_library_reference
        self.lib: UserAssetLibrary = context.preferences.filepaths.asset_libraries.get(lib_name)
        if not self.lib:
            self.report({"ERROR"}, f"Asset library '{lib_name}' not found")
            return {"CANCELLED"}

        # TODO: Run Library Checks

        self.directory = Path(self.lib.path)
        self.files: list[Path] = [file for file in self.directory.rglob("*") if file.is_file()]
        self.total_files: int = len(self.files)
        self.files_written = 0
        self.updated = False
        scene_sets: scene.SH_Scene = context.scene.superhive
        self.prog = scene_sets.header_progress_bar
        self.zip_path = Path(f"{self.lib.path}.zip")
        self.z = ZipFileParallel(
            self.zip_path, "w",
            getattr(zipfile, self.compression_type),
            compresslevel=self.deflated_compression_level if self.compression_type == "ZIP_DEFLATED" else self.bzip_compression_level
        )

        # Setup export thread
        self._th = Thread(target=self.zip_files_parallel)
        context.window_manager.modal_handler_add(self)
        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        self.prog.start()
        self._th.start()

        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        context.area.tag_redraw()

        if self.updated:
            self.updated = False
            self.prog.progress = int(self.files_written / self.total_files * 100)
        self.prog.update_formated_time()

        if (event.type == "ESC" and event.mouse_region_x > 0 and event.mouse_region_y > 0) or self.prog.cancel:
            self.prog.cancel = True
            self.finished(context)
            return {"CANCELLED"}
        elif not self._th or not self._th.is_alive():
            self.finished(context)
            return {"FINISHED"}

        return {"RUNNING_MODAL"}

    def zip_files(self):
        if self.zip_path.exists():
            self.zip_path.unlink()

        with zipfile.ZipFile(self.zip_path, "w") as zipf:
            for file in self.files:
                zipf.write(file, file.relative_to(self.directory))
                self.files_written += 1
                self.updated = True

    def finished(self, context: Context) -> None:
        self._th.join()
        self.z.close()
        context.window_manager.event_timer_remove(self._timer)
        self.prog.end()
        try:
            utils.open_location(str(self.zip_path))
        except Exception as e:
            print("Unable to open export folder:", e)

    def zip_files_parallel(self) -> None:
        with ThreadPoolExecutor() as executor:
            futures = []
            for file in self.files:
                future = executor.submit(self._compress_file_auto_split, file)
                futures.append(future)
            # wait for all threads to finish and report errors
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f"Error compressing file: {e}")

    def _compress_file_auto_split(self, file: Path) -> None:
        if self.prog.cancel:
            return

        self.z.writestr(str(file.relative_to(self.directory)), file.read_bytes())
        self.files_written += 1
        self.updated = True


classes = (
    SH_OT_ExportLibrary,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)