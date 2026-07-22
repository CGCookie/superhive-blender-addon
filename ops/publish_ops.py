import bpy
from bpy.types import Operator

from .. import hive_mind, utils
from . import polls
from .api_ops import online_access_poll


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


classes = (SH_OT_SyncCatalogs,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
