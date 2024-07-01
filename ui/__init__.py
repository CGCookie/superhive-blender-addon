from . import (asset_browser, asset_browser_context_menu, object_context_menu,
               outliner_context_menu, prefs)


def _call_globals(attr_name):
    for m in globals().values():
        if hasattr(m, attr_name):
            getattr(m, attr_name)()


def register():
    _call_globals("register")


def unregister():
    _call_globals("unregister")