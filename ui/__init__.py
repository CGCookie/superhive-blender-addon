from . import (
    asset_browser as asset_browser,
)
from . import (
    asset_browser_context_menu as asset_browser_context_menu,
)
from . import (
    object_context_menu as object_context_menu,
)
from . import (
    outliner_context_menu as outliner_context_menu,
)
from . import (
    prefs as prefs,
)


def _call_globals(attr_name):
    for m in globals().values():
        if hasattr(m, attr_name):
            getattr(m, attr_name)()


def register():
    _call_globals("register")


def unregister():
    _call_globals("unregister")
