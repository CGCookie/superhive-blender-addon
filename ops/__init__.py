from . import convert_asset_to_hive, create_hive_asset_library, add_to_library, add_categories_to_library


def _call_globals(attr_name):
    for m in globals().values():
        if hasattr(m, attr_name):
            getattr(m, attr_name)()


def register():
    _call_globals("register")


def unregister():
    _call_globals("unregister")
