import bpy
from bpy.types import Context, Operator

from .. import utils


def online_access_poll(cls, context: Context) -> bool:
    """Shared poll gate for every operator that talks to the server: the
    manifest declares the network permission, so Blender's global
    "Allow Online Access" toggle must be honored."""
    if not bpy.app.online_access:
        cls.poll_message_set(
            "Online access is disabled (Preferences > System > Network)"
        )
        return False
    return True


class SH_OT_VerifyApiToken(Operator):
    bl_idname = "bkeeper.verify_api_token"
    bl_label = "Verify Token"
    bl_description = (
        "Check the API token against the Superhive server. A publish also needs"
        " the assets:write scope, which can only be confirmed by publishing"
    )
    bl_options = {"INTERNAL"}

    @classmethod
    def poll(cls, context):
        return online_access_poll(cls, context)

    def execute(self, context):
        from ..api import client as api_client
        from ..api import taxonomy

        prefs = utils.get_prefs()
        try:
            client = prefs.get_api_client()
            roots = client.get_taxonomy_roots()
        except api_client.AuthError:
            prefs.api_token_status = "Invalid or revoked token"
        except api_client.ScopeError:
            prefs.api_token_status = (
                "Token lacks the assets scopes — recreate it with the"
                " 'Asset publishing (BeeKeeper)' preset"
            )
        except (api_client.ApiError, RuntimeError) as error:
            prefs.api_token_status = str(error)
        else:
            prefs.api_token_status = f"OK — connected ({len(roots)} catalog roots)"
            taxonomy.clear_cache()
            taxonomy.get_cached_roots(client)
            self.report({"INFO"}, prefs.api_token_status)
            return {"FINISHED"}

        self.report({"ERROR"}, prefs.api_token_status)
        return {"CANCELLED"}


classes = (SH_OT_VerifyApiToken,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
