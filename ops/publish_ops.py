import shutil
import subprocess
import tempfile
from pathlib import Path
from threading import Thread
from typing import TYPE_CHECKING

import bpy
from bpy.props import BoolProperty, EnumProperty
from bpy.types import Context, Operator, UILayout, UIList

from .. import hive_mind, utils
from . import polls
from .api_ops import online_access_poll

if TYPE_CHECKING:
    from ..settings import scene


def snapshot_local_assets(lib: "utils.AssetLibrary") -> list:
    """Build thread-safe LocalAsset snapshots from the active library.

    Publishes the SAVED state of each .blend (native metadata), because the
    file bytes being uploaded are the saved file — unsaved sh_* edits are
    reported as warnings, not silently included.
    """
    from ..api import payloads, sidecar

    binding = sidecar.read_sidecar(lib.path) or {}
    id_map = binding.get("assets", {})
    catalogs_by_id = (
        {c.id: c for c in lib.catalogs.get_catalogs()} if lib.catalogs else {}
    )

    snapshots = []
    for asset in lib.assets:
        metadata = asset.orig_asset.metadata
        catalog = catalogs_by_id.get(metadata.catalog_id)
        snapshots.append(
            payloads.LocalAsset(
                name=asset.name,
                blend_path=asset.blend_path,
                id_type=asset.id_type,
                catalog_id=metadata.catalog_id if catalog else "",
                catalog_path=catalog.path if catalog else "",
                tags=list(asset.bpy_tags),
                description=metadata.description or "",
                author=metadata.author or "",
                license=hive_mind.license_to_server_string(metadata.license or ""),
                copyright=metadata.copyright or "",
                created_blender_version=metadata.sh_created_blender_version or "",
                data_collection=utils.ASSET_TYPES_TO_ID_TYPES.get(asset.id_type, ""),
                server_id=id_map.get(asset.name) or (asset.uuid or None),
            )
        )
    return snapshots


def dirty_asset_warnings(lib: "utils.AssetLibrary") -> list[tuple[str, str]]:
    warnings = []
    for asset in lib.assets:
        if asset.orig_asset.metadata.sh_is_dirty():
            warnings.append(
                (
                    asset.name,
                    "Has unsaved metadata changes — Save Changes and re-publish"
                    " to include them",
                )
            )
    return warnings


def make_thumbnail_extractor(blender_exe: str, out_dir: Path):
    """Extractor callable for PublishJob: runs save_out_previews.py in a
    headless Blender against the asset's own .blend. bpy-free by design so it
    is safe to call from the worker thread."""
    script = (
        Path(utils.__file__).parent / "stand_alone_scripts" / "save_out_previews.py"
    )

    def extract(asset) -> Path | None:
        if not asset.data_collection:
            return None
        args = [
            blender_exe,
            "-b",
            "--factory-startup",
            str(asset.blend_path),
            "-P",
            str(script),
            str(out_dir),
            asset.name,
            asset.data_collection,
            "False",
        ]
        subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        thumb_dir = out_dir / "Thumbnails"
        if not thumb_dir.is_dir():
            return None
        suffix = f"_{asset.name}_preview.webp"
        return next((f for f in thumb_dir.iterdir() if f.name.endswith(suffix)), None)

    return extract


def make_pack_fn(blender_exe: str):
    """Pack external references into the .blend and SAVE it. Runs before
    hashing (PublishJob guarantees the order), so the uploaded bytes match
    the computed sha256."""
    script = Path(utils.__file__).parent / "stand_alone_scripts" / "pack_files.py"

    def pack(blend_path: str):
        subprocess.run(
            [blender_exe, "-b", str(blend_path), "-P", str(script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    return pack


class SH_OT_BindLibrary(Operator):
    bl_idname = "bkeeper.bind_library"
    bl_label = "Link Library to Superhive"
    bl_description = (
        "Choose which Superhive asset library this local library publishes to."
        " The link is stored in .superhive.json inside the library directory"
    )
    bl_options = {"INTERNAL"}

    _items_cache: list = []

    def _library_items(self, context):
        return SH_OT_BindLibrary._items_cache

    library_choice: EnumProperty(
        name="Superhive Library",
        description="The server library to publish into",
        items=_library_items,
    )

    @classmethod
    def poll(cls, context):
        if not polls.is_not_all_library(context, cls=cls):
            return False
        return online_access_poll(cls, context)

    def invoke(self, context, event):
        from ..api import client as api_client

        self._lib = utils.from_active(context, area=context.area)
        try:
            client = utils.get_prefs().get_api_client()
            libraries = client.list_libraries()
        except (api_client.ApiError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        items = [
            (
                "NEW",
                f"Create new: '{self._lib.name}'",
                "Create a new Superhive library with this library's name",
                "ADD",
                0,
            )
        ]
        for i, library in enumerate(libraries, start=1):
            items.append(
                (
                    library["id"],
                    library["name"],
                    library.get("description") or "",
                    "ASSET_MANAGER",
                    i,
                )
            )
        SH_OT_BindLibrary._items_cache = items

        match = next((lib for lib in libraries if lib["name"] == self._lib.name), None)
        self.library_choice = match["id"] if match else "NEW"

        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Local library: {self._lib.name}")
        layout.prop(self, "library_choice")
        if self.library_choice == "NEW":
            layout.label(text="A new library will be created on Superhive", icon="INFO")
        else:
            layout.label(
                text="Publishing replaces this server library's catalogs"
                " and same-named assets",
                icon="INFO",
            )

    def execute(self, context):
        from ..api import client as api_client
        from ..api import sidecar

        prefs = utils.get_prefs()
        if self.library_choice == "NEW":
            try:
                client = prefs.get_api_client()
                library = client.create_library(self._lib.name)
            except (api_client.ApiError, RuntimeError) as error:
                self.report({"ERROR"}, str(error))
                return {"CANCELLED"}
            library_id = library["id"]
        else:
            library_id = self.library_choice

        sidecar.write_sidecar(
            self._lib.path,
            {
                "library_id": library_id,
                "base_url": prefs.server_url,
                "assets": {},
            },
        )
        self.report({"INFO"}, "Library linked — starting publish")
        bpy.ops.bkeeper.publish_library("INVOKE_DEFAULT")
        return {"FINISHED"}


class SH_OT_PublishLibrary(Operator):
    bl_idname = "bkeeper.publish_library"
    bl_label = "Publish to Superhive"
    bl_description = (
        "Sync this library to Superhive: catalogs first, then upload new or"
        " changed assets (diffed by file hash — unchanged assets are skipped)."
        " Large first publishes can take several minutes due to server rate"
        " limits"
    )
    bl_options = {"REGISTER"}

    pack_files: BoolProperty(
        name="Pack External Files First",
        description=(
            "Pack textures and other external references into each asset's"
            " .blend before upload, so downloaded assets are self-contained."
            " Slower (re-saves every file, so every asset re-uploads); use when"
            " the library was created without packing"
        ),
        default=False,
    )

    @classmethod
    def poll(cls, context):
        if not polls.is_not_all_library(context, cls=cls):
            return False
        return online_access_poll(cls, context)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "pack_files")
        col = layout.column(align=True)
        col.active = False
        col.label(text="Unchanged assets are skipped automatically.")
        col.label(text="Assets removed locally are never deleted on Superhive.")

    def execute(self, context):
        from ..api import publish, sidecar

        prefs = utils.get_prefs()
        try:
            client = prefs.get_api_client()
        except RuntimeError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        lib = utils.from_active(
            context, area=context.area, load_assets=True, load_catalogs=True
        )
        binding = sidecar.read_sidecar(lib.path)
        if binding is None:
            bpy.ops.bkeeper.bind_library("INVOKE_DEFAULT")
            return {"CANCELLED"}

        self._lib_path = lib.path
        self._orig_assets = {
            asset.name: asset.orig_asset for asset in (lib.assets or [])
        }

        local_assets = snapshot_local_assets(lib)
        if not local_assets and not (lib.catalogs and lib.catalogs.catalogs):
            self.report({"WARNING"}, "Nothing to publish — the library is empty")
            return {"CANCELLED"}

        self._warnings = dirty_asset_warnings(lib)

        self._tmpdir = Path(tempfile.mkdtemp(prefix="bkeeper_publish_"))
        roots = hive_mind.load_roots(client)
        self._job = publish.PublishJob(
            client,
            binding["library_id"],
            local_assets,
            lib.catalogs.to_dict() if lib.catalogs else [],
            roots,
            binding.get("assets", {}),
            thumbnail_extractor=make_thumbnail_extractor(
                bpy.app.binary_path, self._tmpdir
            ),
            pack_fn=make_pack_fn(bpy.app.binary_path) if self.pack_files else None,
        )

        scn_sets: "scene.SH_Scene" = context.scene.superhive
        self.prog = scn_sets.publish
        self.prog.start()

        context.window_manager.modal_handler_add(self)
        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        utils.ensure_sidepanel_right_is_open(context.space_data)

        self._thread = Thread(target=self._job.run, daemon=True)
        self._thread.start()

        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        context.area.tag_redraw()
        self.prog.update_formated_time()

        if event.type == "ESC" or self.prog.cancel:
            self.prog.cancel = True
            self._job.cancel_requested = True

        if self._job.updated:
            self._job.updated = False
            self.prog.phase_label = self._job.phase
            if self._job.assets_total:
                self.prog.assets_bar.progress = (
                    self._job.assets_done / self._job.assets_total
                )
                self.prog.assets_bar.label = (
                    f"{self._job.assets_done}/{self._job.assets_total} assets"
                )
                self.prog.assets_bar.show_label_in_bar = True
            if self._job.bytes_total:
                self.prog.show_upload = True
                self.prog.upload_bar.progress = (
                    self._job.bytes_sent / self._job.bytes_total
                )

        if not self._thread.is_alive():
            self.finished(context)
            return {"FINISHED"}

        if event.type in {"MIDDLEMOUSE", "WHEELUPMOUSE", "WHEELDOWNMOUSE"}:
            return {"PASS_THROUGH"}

        return {"RUNNING_MODAL"}

    def finished(self, context: Context):
        from ..api import sidecar

        self._thread.join()
        context.window_manager.event_timer_remove(self._timer)
        shutil.rmtree(self._tmpdir, ignore_errors=True)

        job = self._job
        if job.binding_gone:
            sidecar.clear_sidecar(self._lib_path)
        if job.uploaded_ids:
            sidecar.record_asset_ids(self._lib_path, job.uploaded_ids)
            for name, server_id in job.uploaded_ids.items():
                orig = self._orig_assets.get(name)
                if orig is None:
                    continue
                try:  # session-only UI nicety; refs can go stale mid-publish
                    orig.metadata.sh_uuid = server_id
                except ReferenceError:
                    pass

        scn_sets: "scene.SH_Scene" = context.scene.superhive
        results = scn_sets.publish_results
        results.clear()
        for name, message in self._warnings:
            row = results.add()
            row.name = name
            row.status = "warning"
            row.message = message
        for item in job.results:
            row = results.add()
            row.name = item.name
            row.status = item.status if item.status != "uploaded" else "processing"
            row.message = item.message
            row.server_id = item.server_id
        if job.fatal_error:
            row = results.add()
            row.name = "Publish stopped"
            row.status = "error"
            row.message = job.fatal_error
            self.report({"ERROR"}, job.fatal_error)
        elif job.cancelled:
            self.report({"WARNING"}, "Publish cancelled")
        else:
            uploaded = sum(
                1
                for item in job.results
                if item.status in ("published", "pending", "processing", "metadata")
            )
            self.report({"INFO"}, f"Publish finished — {uploaded} assets synced")

        interesting = any(row.status != "unchanged" for row in results)
        if interesting and not job.cancelled:
            bpy.app.timers.register(_show_report_deferred, first_interval=0.1)

        bpy.app.timers.register(self.delayed_close, first_interval=1)

    def delayed_close(self):
        self.prog.end()
        for area in bpy.context.screen.areas:
            area.tag_redraw()


def _show_report_deferred():
    try:
        bpy.ops.bkeeper.show_publish_report("INVOKE_DEFAULT")
    except RuntimeError:
        pass  # no valid context (e.g. window closed) — results stay in the scene


class SH_UL_PublishResults(UIList):
    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        split = layout.split(factor=0.35)
        row = split.row()
        row.label(text=item.name, icon=item.icon)
        row = split.row()
        row.active = item.status not in ("error", "rejected")
        row.alert = item.status in ("error", "rejected")
        status_label = item.bl_rna.properties["status"].enum_items[item.status].name
        row.label(text=f"{status_label}  {item.message}".strip())


class SH_OT_ShowPublishReport(Operator):
    bl_idname = "bkeeper.show_publish_report"
    bl_label = "Superhive Publish Report"
    bl_description = "Show the results of the last Publish to Superhive"
    bl_options = {"INTERNAL"}

    @classmethod
    def poll(cls, context):
        return bool(context.scene.superhive.publish_results)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=650)

    def draw(self, context):
        layout: UILayout = self.layout
        scn_sets: "scene.SH_Scene" = context.scene.superhive

        layout.template_list(
            "SH_UL_PublishResults",
            "",
            scn_sets,
            "publish_results",
            scn_sets,
            "publish_results_index",
            rows=min(max(len(scn_sets.publish_results), 3), 12),
        )

        index = scn_sets.publish_results_index
        if 0 <= index < len(scn_sets.publish_results):
            active = scn_sets.publish_results[index]
            if active.message:
                box = layout.box()
                col = box.column(align=True)
                col.scale_y = 0.8
                for chunk in _wrap(active.message, 90):
                    col.label(text=chunk)

    def execute(self, context):
        return {"FINISHED"}


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


class SH_OT_SyncCatalogs(Operator):
    bl_idname = "bkeeper.sync_catalogs"
    bl_label = "Sync Catalogs to Superhive"
    bl_description = (
        "Replace the Superhive library's catalog tree with this library's"
        " catalogs (declarative: catalogs removed here are removed there)."
        " Catalogs outside the curated Superhive roots stay local-only"
    )
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        if not polls.is_not_all_library(context, cls=cls):
            return False
        return online_access_poll(cls, context)

    def execute(self, context):
        from ..api import client as api_client
        from ..api import publish, sidecar

        lib = utils.from_active(context, load_catalogs=True)
        binding = sidecar.read_sidecar(lib.path)
        if not binding:
            self.report(
                {"ERROR"},
                "This library isn't linked to Superhive yet — use"
                " Publish to Superhive first",
            )
            return {"CANCELLED"}

        try:
            client = utils.get_prefs().get_api_client()
            roots = hive_mind.load_roots(client)
            result = publish.sync_catalogs(
                client, binding["library_id"], lib.catalogs.to_dict(), roots
            )
        except (api_client.ApiError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        for path, reason in result.skipped:
            self.report({"WARNING"}, f"Kept local-only: {path} ({reason})")
        self.report({"INFO"}, f"Synced {len(result.synced)} catalogs to Superhive")
        return {"FINISHED"}


classes = (
    SH_OT_BindLibrary,
    SH_OT_PublishLibrary,
    SH_UL_PublishResults,
    SH_OT_ShowPublishReport,
    SH_OT_SyncCatalogs,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
