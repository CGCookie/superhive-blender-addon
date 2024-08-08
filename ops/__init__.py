from . import (
    add_categories_to_library,
    add_to_library,
    asset_ops,
    blender_exes_ops,
    create_hive_asset_library,
    export_library,
    import_from_directory,
    remove_empty_catalogs,
)


def _call_globals(attr_name):
    for m in globals().values():
        if hasattr(m, attr_name):
            getattr(m, attr_name)()


def register():
    _call_globals("register")


def unregister():
    _call_globals("unregister")
