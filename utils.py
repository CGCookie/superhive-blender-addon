# Utilities for interacting with the blender_assets.cats.txt file
import functools
import json
import subprocess
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path
from platform import system
from typing import TYPE_CHECKING, Generator, Union

import bpy
from bpy.types import ID, Area, AssetRepresentation, Context, UserAssetLibrary, Window
from bpy_extras import asset_utils

from . import hive_mind

if TYPE_CHECKING:
    from .ops import asset_ops, export_library, import_from_directory
    from .settings import asset as asset_settings
    from .ui.prefs import SH_AddonPreferences


ASSET_TYPES_TO_ID_TYPES = {
    "ACTION": "actions",
    "ARMATURE": "armatures",
    "BRUSH": "brushes",
    "CACHEFILE": "cache_files",
    "CAMERA": "cameras",
    "COLLECTION": "collections",
    "CURVE": "curves",
    "CURVES": "curves",
    "FONT": "fonts",
    "GREASEPENCIL": "grease_pencils",
    "GREASEPENCIL_V3": "grease_pencils",
    "IMAGE": "images",
    "KEY": "shape_keys",
    "LATTICE": "lattices",
    "LIBRARY": "libraries",
    "LIGHT": "lights",
    "LIGHT_PROBE": "lightprobes",
    "LINESTYLE": "linestyles",
    "MASK": "masks",
    "MATERIAL": "materials",
    "MESH": "meshes",
    "META": "metaballs",
    "MOVIECLIP": "movieclips",
    "NODETREE": "node_groups",
    "OBJECT": "objects",
    "PAINTCURVE": "paint_curves",
    "PALETTE": "palettes",
    "PARTICLE": "particles",
    "POINTCLOUD": "",
    "SCENE": "scenes",
    "SCREEN": "screens",
    "SOUND": "sounds",
    "SPEAKER": "speakers",
    "TEXT": "texts",
    "TEXTURE": "textures",
    "VOLUME": "volumes",
    "WINDOWMANAGER": "window_managers",
    "WORKSPACE": "workspaces",
    "WORLD": "worlds",
}


class Catalog:
    def __init__(
        self,
        data: Union["CatalogsFile", "Catalog"],
        name: str,
        id: str = None,
        path: str = None,
    ) -> None:
        """
        Initialize a Catalog object.

        Parameters
        ----------
        data : Union["CatalogsFile", "Catalog"]
            The parent Catalog or CatalogsFile object.
        name : str
            The name or `simple_name` of the Catalog object.
            Will set `simple_name` and `name` if `path` is not provided.
        id : str, optional
            The unique identifier for the Catalog object. If not provided, a new UUID (uuid4) will be generated.
        path : str, optional
            The path associated with the Catalog object.
            If provided, the name of the Catalog object will be extracted from the path.

        Returns
        -------
        None
        """
        self.data = data
        """The parent object"""
        self.id: str = id or str(uuid.uuid4())
        """The unique identifier for the catalog"""
        self.path = path
        """The path to the catalog's greatest parent catalog"""
        self.simple_name = name
        if path:
            self.name = path.split("/")[-1]
        else:
            self.name = name.split("-")[-1]

        self.children: dict[str, Catalog] = {}
        """Sub-catalogs of this catalog"""

        if not self.path:
            self.load_path()

    def add_child(self, name: str, id: str = None, path: str = None) -> "Catalog":
        """Add a child catalog to this catalog.

        Parameters
        ----------
        name : str
            The name or `simple_name` of the catalog.
        id : str, optional
            The `uuid4` of an existing catalog you want to retain, by default None
        path : str, optional
            The verbal path from the base catalog to this catalog, by default None

        Returns
        -------
        Catalog
            The child catalog that was added.
        """
        id = id or str(uuid.uuid4())
        self.children[id] = Catalog(self, name, id=id, path=path or self.load_path())
        return self.children[id]

    def remove_child(self, id: str) -> None:
        """
        Removes a child with the specified ID from the list of children.

        Parameters
        ----------
        id : str
            The UUID of the child to be removed.

        Returns
        -------
        None
        """
        if id in self.children:
            del self.children[id]

    def remove_self(self) -> None:
        """Remove this catalog from its parent's children."""
        if isinstance(self.data, Catalog):
            self.data.remove_child(self.id)
        else:
            self.data.remove_catalog(self.id)

    def load_path(self) -> None:
        """
        Load the path of the current data object.
        Will also set `simple_name`

        Returns:
            None
        """
        data = self
        path = []
        while not isinstance(data, CatalogsFile):
            if "/" in data.name:
                path.append(data.name.split("/")[-1])
            else:
                path.append(data.name)
            data = data.data
        self.path = "/".join(reversed(path))
        self.simple_name = "-".join(reversed(path))

    def get_file_lines(self) -> list[str]:
        """Returns a list of lines to write to the catalogs file for itself and each of its children."""
        lines = [self.get_line()]
        for child in self.children.values():
            lines.extend(child.get_file_lines())
        return lines

    def get_line(self) -> str:
        """
        Returns a formatted string representing the line information.

        Returns:
            str: A string in the format "{id}:{path}:{simple_name}\n".
        """
        return f"{self.id}:{self.path}:{self.simple_name}\n"

    def print_catalog_tree(self, indent=0) -> None:
        """
        Print the catalog tree starting from the current catalog.

        Parameters
        ----------
        indent : int, optional
            The number of indentations to apply to the printed tree (default is 0).

        Returns
        -------
        None
            This method does not return anything.
        """
        ind = "  " * indent * 4
        print(f"{ind}{self.name} ({self.id})")
        for catalog in self.children.values():
            catalog.print_catalog_tree(indent + 1)

    def find_catalog(self, id: str) -> "Catalog":
        """
        Find a catalog with the given ID among this catalog's children.

        Parameters:
        - id (str): The ID of the catalog to find.

        Returns:
        - Catalog: The catalog with the given ID, if found. Otherwise, None.
        """

        cat = self.children.get(id)
        if cat:
            return cat

        for catalog in self.children.values():
            cat = catalog.find_catalog(id)
            if cat:
                return cat

    def generate_id_path(self) -> list[tuple[str, str]]:
        """Generate the path of ids to this catalog.
        Returns
        -------
        list[tuple[str, str]]
            A list of tuples of the form (id, simple_name) representing the path to this catalog top down.
        """
        path = []
        data = self
        while not isinstance(data, CatalogsFile):
            path.append((data.id, data.simple_name))
            data = data.data
        return list(reversed(path))

    def get_catalog_by_path(self, path_parts: list[str]) -> "Catalog":
        """
        Get a catalog by its path.

        Parameters
        ----------
        path_parts : list[str]
            The list of path parts representing the catalog's path.

        Returns
        -------
        Catalog
            The catalog object found by the given path.

        Notes
        -----
        This method recursively searches for a catalog by its path in the children catalogs.

        If the `path_parts` list contains only one element and it matches a child catalog's name, that child catalog is returned.

        If the `path_parts` list contains more than one element, the method recursively calls itself with the remaining path parts,
        searching for the catalog in the children catalogs of the current catalog.

        If a catalog is found, it is returned. Otherwise, None is returned.

        Examples
        --------
        >>> path_parts = ["parent", "child", "grandchild"]
        >>> catalog = get_catalog_by_path(path_parts)
        >>> print(catalog)
        <Catalog object at 0x7f8a9c6a7a90>
        """  # noqa: E501
        if len(path_parts) == 1 and path_parts[0] in self.children:
            return self.children.get(path_parts[0])

        for catalog in self.children.values():
            cat = catalog.get_catalog_by_path(path_parts[1:])
            if cat:
                return cat

    def ensure_correct_child_parenting(self) -> None:
        """
        Ensure correct parenting of child catalogs.

        This method iterates over the children catalogs and sets the parent catalog as the data attribute for each child.
        It then recursively calls `ensure_correct_child_parenting` on each child catalog to ensure correct parenting
        throughout the hierarchy.

        Returns:
            None
        """  # noqa: E501
        for catalog in self.children.values():
            catalog.data = self
            catalog.ensure_correct_child_parenting()

    def get_catalogs(self) -> list["Catalog"]:
        """Return a list of all catalogs in the file as a 1-Dimensional list."""
        catalogs = []
        for catalog in self.children.values():
            catalogs.append(catalog)
            catalogs.extend(catalog.get_catalogs())
        return catalogs

    def has_child(self, id: str | set[str], recursive=True):
        for child in self.children.values():
            if isinstance(id, set):
                if child.id in id:
                    return True
            else:
                if child.id == id:
                    return True
            if recursive and child.has_child(id, recursive):
                return True

    def get_catalog_by_name(self, id: str, recursive=True) -> "Catalog":
        for child in self.children.values():
            if child.name == id:
                return child
            if recursive:
                cat = child.get_catalog_by_name(id, recursive)
                if cat:
                    return cat

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "simple_name": self.simple_name,
            "name": self.name,
            "path": self.path,
            "children": [child.to_dict() for child in self.children.values()],
        }


class CatalogsFile:
    def __init__(self, dir: Path, is_new=False) -> None:
        """
        Initialize the Utils class.

        Parameters
        ----------
        dir : Path
            The directory path.
        is_new : bool, optional
            Flag indicating if the directory is new, by default False.

        Notes
        -----
        - If `is_new` is False, the catalogs file will be loaded or raised a `FileNotFoundError` if not found.
        - If the catalogs file is not found in the specified directory, the class will attempt to find the catalogs file in parent directories before raising a `FileNotFoundError`.
        - If `is_new` is True, a file won't be created until `write_file` is called.
        """  # noqa: E501

        self.path = Path(dir) / "blender_assets.cats.txt"
        """The path to the catalogs file."""

        self.catalogs: dict[str, Catalog] = {}
        """The catalogs in the catalogs file by uuid."""

        if not self.exists():
            if is_new:
                return

            # Try to find the catalogs file in a parent directory
            dir = self.path.parent
            found_new = False
            while dir != dir.parent:
                dir = dir.parent

                if self.has_file(dir):
                    found_new = True
                    self.path = dir / "blender_assets.cats.txt"
                    break
            if not found_new:
                raise FileNotFoundError(f"Catalogs file not found in directory: {self.path.parent}")

        self.load_catalogs()

    initial_text = '# This is an Asset Catalog Definition file for Blender.\n#\n# Empty lines and lines starting with `#` will be ignored.\n# The first non-ignored line should be the version indicator.\n# Other lines are of the format "UUID:catalog/path/for/assets:simple catalog name"'  # noqa: E501

    VERSION = 1

    @classmethod
    def has_file(cls, path: Path) -> bool:
        """Check if the specified directory contains a `blender_assets.cats.txt` file."""
        return (path / "blender_assets.cats.txt").exists()

    def exists(self) -> bool:
        return self.path.exists()

    def load_catalogs(self):
        """Load `catalogs` from file"""
        self.catalogs.clear()

        unassigned_catalogs: dict[str, Catalog] = {}
        with open(self.path) as file:
            for line in file:
                if line.startswith(("#", "VERSION")) or line == "\n":
                    continue

                id, path, simple_name = line.strip().split(":")

                unassigned_catalogs[path] = Catalog(self, simple_name, id=id, path=path)

        top_level_catalogs: list[Catalog] = []
        for cat_name, catalog in unassigned_catalogs.items():
            path = catalog.path
            if "/" in path:  # is child of another catalog
                parent_catalog = unassigned_catalogs.get("/".join(path.split("/")[:-1]))
                if not parent_catalog:
                    raise ValueError(
                        f"Parent catalog '{path.split('/')[-2]}' not found for catalog '{cat_name}' with path: '{path}'"
                    )

                parent_catalog.children[catalog.id] = catalog
            else:
                top_level_catalogs.append(catalog)

        for catalog in top_level_catalogs:
            self.catalogs[catalog.id] = catalog

        self.ensure_correct_child_parenting()

    def delete_file(self) -> None:
        if self.exists():
            self.path.unlink()

    def add_catalog(self, name: str, id: str = None, path: str = None, auto_place=False) -> Catalog:
        """
        Add a catalog at the root level or under a parent catalog.

        Parameters
        ----------
        name : str
            The name of the catalog.
        id : str, optional
            The ID of the catalog. If not provided, a UUID will be generated.
        path : str, optional
            The path of the catalog. If not provided, the catalog will be added at the root level.
        auto_place : bool, optional
            If True and `path` is provided, the catalog will be automatically placed under the specified path
            if a parent catalog exists. If False, the catalog will be added at the root level.

        Returns
        -------
        Catalog
            The added catalog.

        Notes
        -----
        - If `auto_place` is True and `path` is provided, the method will attempt to find the parent catalog
          based on the provided path. If a parent catalog is found, the new catalog will be added as a child
          of the parent catalog. If no parent catalog is found, the method will recursively call itself with
          `auto_place` set to False to add the catalog at the root level.
        - If `auto_place` is False or `path` is not provided, the method will add the catalog at the root level.

        """
        id = id or str(uuid.uuid4())
        if auto_place and path:
            parent_path = path.split("/")
            if len(parent_path) > 1:
                parent = None
                while not parent and "/" in parent_path:
                    parent = self.get_catalog_by_path(parent_path)
                    if not parent:
                        parent_path = "/".join(parent_path[:-1])

                if parent:
                    return parent.add_child(name, id=id, path=path)
                else:
                    return self.add_catalog(name, id=id, path=path, auto_place=False)
            else:
                self.add_catalog(name, id=id, path=path, auto_place=False)
        else:
            self.catalogs[id] = Catalog(self, name, id=id, path=path)
        return self.catalogs[id]

    def remove_catalog(self, id: str) -> None:
        """Remove a catalog from the catalogs file."""
        if id in self.catalogs:
            del self.catalogs[id]

    def get_catalog_lines(self) -> list[str]:
        """Returns a list of catalog lines to write to the file."""
        a = []
        for catalog in self.catalogs.values():
            a.extend(catalog.get_file_lines())
        return a

    def write_file(self) -> None:
        """Write the catalogs to the blender_assets.cats.txt file."""
        with open(self.path, "w") as file:
            file.write(self.initial_text + "\n\n")
            file.write(f"VERSION {self.VERSION}\n\n")
            for line in self.get_catalog_lines():
                file.write(line)

    def write_empty_file(self) -> None:
        """Write an empty catalogs file."""
        with open(self.path, "w") as file:
            file.write(self.initial_text + "\n\n")
            file.write(f"VERSION {self.VERSION}\n\n")

    def print_catalog_tree(self) -> None:
        """Print the catalog tree to the console."""
        print(f"Catalog file: {self.path}")
        print("Catalog Tree:")
        for catalog in self.catalogs.values():
            catalog.print_catalog_tree()

    def find_catalog(self, id: str) -> Catalog:
        """
        Find a catalog by its ID.

        Parameters
        ----------
        id : str
            The ID of the catalog to find.

        Returns
        -------
        Catalog
            The found catalog, or None if not found.
        """
        cat = self.catalogs.get(id)
        if cat:
            return cat

        for catalog in self.catalogs.values():
            cat = catalog.find_catalog(id)
            if cat:
                return cat

    def get_catalog_by_path(self, path: str) -> Catalog:
        """
        Get a catalog by its path.

        Parameters
        ----------
        path : str
            The path of the catalog.

        Returns
        -------
        Catalog
            The catalog object if found, None otherwise.
        """
        path_parts = path.split("/")
        if len(path_parts) == 1:
            return self.catalogs.get(path)

        for catalog in self.catalogs.values():
            cat = catalog.get_catalog_by_path(path_parts[1:])
            if cat:
                return cat

    def add_catalog_from_other(self, catalog: Catalog) -> None:
        """
        Add a catalog from another catalog.

        Parameters
        ----------
        catalog : Catalog
            The catalog to be added.

        Returns
        -------
        None
        """
        id_path = catalog.generate_id_path()

        id, simple_name = id_path.pop(0)

        act_cat = self.catalogs.get(id)

        if not act_cat:
            act_cat = self.add_catalog(simple_name, id=id)

        for id, simple_name in id_path:
            cat = act_cat.children.get(id)
            if not cat:
                cat = act_cat.add_child(simple_name, id=id)

    def ensure_correct_child_parenting(self) -> None:
        """Ensure that the children of this catalog have the correct parent."""
        for catalog in self.catalogs.values():
            catalog.data = self
            catalog.ensure_correct_child_parenting()

    def get_catalogs(self) -> list[Catalog]:
        """Return a list of all catalogs in the file as a 1-Dimensional list."""
        catalogs = []
        for catalog in self.catalogs.values():
            catalogs.append(catalog)
            catalogs.extend(catalog.get_catalogs())
        return catalogs

    def has_child(self, id: str | set[str], recursive=True):
        for child in self.catalogs.values():
            if isinstance(id, set):
                if child.id in id:
                    return True
            else:
                if child.id == id:
                    return True
            if recursive and child.has_child(id, recursive):
                return True

    def get_catalog_by_name(self, id: str, recursive=True) -> Catalog:
        for child in self.catalogs.values():
            if child.name == id:
                return child
            if recursive:
                cat = child.get_catalog_by_name(id, recursive)
                if cat:
                    return cat

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "catalogs": [cat.to_dict() for cat in self.catalogs.values()],
        }


# Context manager for opening and then saving the catalogs file
@contextmanager
def open_catalogs_file(path: Path, is_new=False) -> Generator[CatalogsFile, None, None]:
    a = CatalogsFile(path, is_new=is_new)
    yield a
    a.write_file()


class Asset:
    def __init__(self, asset: AssetRepresentation) -> None:
        self.orig_asset = asset
        self.name = asset.name
        """The original `name` of the asset. Not a new one"""
        self.new_name = asset.metadata.sh_name
        self.blend_path = asset.full_library_path
        """The original `full_library_path` of the asset. Not a new one"""
        # asset.full_path
        self.id_type = asset.id_type
        """The original `id_type` of the asset. Not a new one"""
        self.uuid = asset.metadata.sh_uuid
        self.author = asset.metadata.sh_author
        self.description = asset.metadata.sh_description
        if asset.metadata.sh_license == "CUSTOM":
            self.license = asset.metadata.sh_license_custom
        else:
            self.license = asset.metadata.sh_license
        self.copyright = asset.metadata.sh_copyright
        self.catalog_simple_name = asset.metadata.catalog_simple_name
        """The original `catalog_simple_name` of the asset. Not a new one"""
        self.catalog_id = asset.metadata.sh_catalog
        self.tags: list[str] = [tag.name for tag in asset.metadata.sh_tags.tags]
        self.bpy_tags: list[str] = [tag.name for tag in asset.metadata.tags]
        self.icon_path = None

    def update_asset(self, blender_exe: str, debug: bool = False) -> None:
        """Open asset's blend file and update the asset's metadata."""
        python_file = Path(__file__).parent / "stand_alone_scripts" / "update_asset.py"
        proc: subprocess.CompletedProcess = subprocess.run(
            [
                blender_exe,
                "-b",
                "--factory-startup",
                str(self.blend_path),
                "-P",
                str(python_file),
                self.name,  # old asset name
                self.new_name,  # new asset name
                ASSET_TYPES_TO_ID_TYPES.get(self.id_type),
                self.author,
                self.description,
                self.license,
                self.copyright,
                self.catalog_id,
                ",".join(self.tags),
                str(self.icon_path),
            ],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        if proc.returncode > 1:
            print(f"    - Error {proc.returncode}: {proc.stderr.decode()}")

        if debug or proc.returncode > 1:
            print("".center(100, "-"))
            text = proc.stdout.decode()
            text.splitlines()
            new_text = "\n".join(line for line in text.splitlines() if line.startswith("|"))
            print(new_text)
            print("".center(100, "-"))
            print()

    def reset_metadata(self, context: Context) -> None:
        """Reset the metadata of the asset."""
        self.orig_asset.metadata.sh_name = self.name
        self.orig_asset.metadata.sh_is_dirty_name = False

        self.orig_asset.metadata.sh_author = self.orig_asset.metadata.author
        self.orig_asset.metadata.sh_is_dirty_author = False

        self.orig_asset.metadata.sh_description = self.orig_asset.metadata.description
        self.orig_asset.metadata.sh_is_dirty_description = False

        self.orig_asset.metadata.sh_copyright = self.orig_asset.metadata.copyright
        self.orig_asset.metadata.sh_is_dirty_copyright = False

        license = hive_mind.LICENSES_DICT.get(self.orig_asset.metadata.license)
        if not license:
            license = hive_mind.get_license_by_name(self.orig_asset.metadata.license)
        if license:
            self.orig_asset.metadata.sh_license = license["id"]
        else:
            self.orig_asset.metadata.sh_license = "UNRECOGNIZED"
        self.orig_asset.metadata.sh_is_dirty_license = False

        catalog = hive_mind.CATALOG_DICT.get(self.orig_asset.metadata.catalog_id)
        if not catalog:
            catalog = hive_mind.get_catalog_by_name(
                self.orig_asset.metadata.catalog_simple_name,
                is_catalog_simple_name=True,
            )
        if catalog:
            self.orig_asset.metadata.sh_catalog = catalog["id"]
        else:
            self.orig_asset.metadata.sh_catalog = "UNRECOGNIZED"
        self.orig_asset.metadata.sh_is_dirty_catalog = False

        sh_tags: "asset_settings.SH_AssetTags" = self.orig_asset.metadata.sh_tags
        sh_tags.clear(context)
        for tag in self.orig_asset.metadata.tags:
            sh_tags.new_tag(tag.name, context)
        self.orig_asset.metadata.sh_is_dirty_tags = False

    def rerender_thumbnail(self, path, directory, objects, shading, angle="X", add_plane=False):
        prefs = get_prefs()
        cmd = [bpy.app.binary_path]
        # cmd.append("--background")
        # cmd.append(path[0])
        cmd.append("--factory-startup")
        cmd.append("--python")
        # cmd.append(os.path.join(os.path.dirname(
        #     os.path.abspath(__file__)), "rerender_thumbnails.py"))
        cmd.append(str(Path(__file__).parent / "stand_alone_scripts" / "rerender_thumbnails.py"))
        cmd.append("--")
        cmd.append(":--separator--:".join(path))
        names = []
        types = []
        for o in objects:
            names.append(":--separator2--:".join([a[0] for a in o]))
            types.append(":--separator2--:".join([a[1] for a in o]))
        cmd.append(":--separator--:".join(names))
        cmd.append(":--separator--:".join(types))
        cmd.append(shading)
        cmd.append(directory)
        cmd.append(angle)
        cmd.append(str(add_plane))
        cmd.append(str(prefs.world_strength))
        cmd.append(
            bpy.context.preferences.addons["cycles"].preferences.compute_device_type
            if "cycles" in bpy.context.preferences.addons.keys()
            else "NONE"
        )
        if prefs.non_blocking:
            t1 = threading.Thread(target=functools.partial(subprocess.run, cmd))
            t1.start()
            return t1
        else:
            subprocess.run(cmd)
            return None

    def save_out_preview(self, directory: Path) -> None:
        """Save out the preview image of the asset."""
        python_file = Path(__file__).parent / "stand_alone_scripts" / "save_out_previews.py"

        args = [
            bpy.app.binary_path,
            "-b",
            "--factory-startup",
            str(self.orig_asset.full_library_path),
            "-P",
            str(python_file),
            str(directory),
            self.orig_asset.name,
            ASSET_TYPES_TO_ID_TYPES.get(self.id_type),
            "False",
        ]

        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode > 1:
            print(f"Error: {proc.stderr.decode()}")
        print(f"Output: {proc.stdout.decode()}")

    def to_dict(self, apply_changes=False) -> dict:
        return {
            "name": self.new_name if apply_changes else self.name,
            "blend_path": self.blend_path,
            "id_type": self.id_type,
            "uuid": self.uuid,
            "author": self.author if apply_changes else self.orig_asset.metadata.author,
            "description": self.description if apply_changes else self.orig_asset.metadata.description,
            "license": self.license if apply_changes else self.orig_asset.metadata.license,
            "catalog_simple_name": self.catalog_simple_name
            if apply_changes
            else self.orig_asset.metadata.catalog_simple_name,
            "catalog_id": self.catalog_id if apply_changes else self.orig_asset.metadata.catalog_id,
            "tags": self.tags if apply_changes else self.bpy_tags,
        }


class Assets:
    def __init__(self, assets: list[AssetRepresentation]) -> None:
        self._dict: dict[str, Asset] = {}
        self._list: list[Asset] = []

        for asset in assets:
            a = Asset(asset)
            self._dict[a.name] = a
            self._list.append(a)

    def to_dict(self, apply_changes=False) -> list[dict]:
        return [asset.to_dict(apply_changes=apply_changes) for asset in self._list]

    def __getitem__(self, key_or_index: str | int) -> Asset:
        if isinstance(key_or_index, str):
            return self._dict[key_or_index]
        return self._list[key_or_index]

    def __iter__(self):
        return iter(self._list)

    def __len__(self):
        return len(self._list)

    def __contains__(self, item: str):
        return item in self._dict

    def __repr__(self):
        return f"Assets({self._list})"

    def __str__(self):
        return str(self._list)


class AssetLibrary:
    def __init__(
        self,
        library: UserAssetLibrary,
        context: Context = None,
        load_assets=False,
        load_catalogs=False,
    ) -> None:
        if not library:
            raise ValueError("No library provided.")

        self.context: Context = context
        self.area: Area = None
        if context:
            self.area = next(
                (
                    area
                    for window in context.window_manager.windows
                    for area in window.screen.areas
                    if area.type == "FILE_BROWSER" and asset_utils.SpaceAssetInfo.is_asset_browser(area.spaces.active)
                ),
                None,
            )

        self.library: UserAssetLibrary = library
        self.name = library.name
        self.path: Path = Path(library.path)
        """The path to the library's directory"""

        self.assets: Assets = None
        self.catalogs: CatalogsFile = None

        if load_catalogs:
            self.load_catalogs()

        if load_assets:
            if not context:
                raise ValueError("Context must be provided to load assets.")
            self.load_assets()

    def get_context(self) -> Context:
        if not self.context:
            raise ValueError("Context not set. Please set `context` before calling this method.")
        return self.context

    def load_catalogs(self):
        is_new = not CatalogsFile.has_file(self.path)
        self.catalogs = CatalogsFile(self.path, is_new=is_new)

    def get_possible_assets(self) -> list[AssetRepresentation]:
        """Get all assets available"""
        C = self.get_context()
        with display_all_assets_in_library(C):
            return C.selected_assets[:] if C.selected_assets else []

    def load_assets(self):
        self.assets = Assets(self.get_possible_assets())

    @contextmanager
    def open_catalogs_file(self) -> Generator[CatalogsFile, None, None]:
        if not self.catalogs:
            yield None
        else:
            yield self.catalogs
            self.catalogs.write_file()

    @classmethod
    def create_bpy_library(cls, name: str, path: str) -> UserAssetLibrary:
        """Create a new UserAssetLibrary in Blender."""
        return bpy.context.preferences.filepaths.asset_libraries.new(name=name, directory=path)

    @classmethod
    def create_new_library(
        cls,
        name: str,
        path: str,
        context: Context = None,
        load_assets=False,
        load_catalogs=False,
        save_prefs=True,
    ) -> "AssetLibrary":
        """Create a new `UserAssetLibrary` in Blender and then create a new `AssetLibrary` object from that library."""
        lib = cls.create_bpy_library(name, path)

        if save_prefs and not bpy.context.preferences.use_preferences_save:
            cls.save_repository_prefs(name, path)

        return cls(
            lib,
            context=context,
            load_assets=load_assets,
            load_catalogs=load_catalogs,
        )

    @classmethod
    def save_repository_prefs(cls, name: str, path: str):
        p = Path(__file__)
        while p.parent.name != "Blender":
            p = p.parent
        prefs_blend = p / "config" / "userpref.blend"

        if not prefs_blend.exists():
            return

        python_file = Path(__file__).parent / "stand_alone_scripts" / "add_repository_to_userpref.py"

        args = [
            bpy.app.binary_path,
            "-b",
            # str(prefs_blend),
            "-P",
            str(python_file),
            name,
            path,
        ]
        print(" ".join(args))

        subprocess.run(args)

    def to_dict(self, apply_changes=False) -> dict:
        # modeled after https://projects.blender.org/blender/blender/issues/125597
        return {
            "name": self.name,
            "schema_version": 1,
            "asset_size_bytes": 0,  # TODO: Implement
            "index_size_bytes": 0,  # TODO: Implement
            "path": str(self.path),
            "assets": (self.assets.to_dict(apply_changes=apply_changes) if self.assets else []),
            "catalogs": self.catalogs.to_dict() if self.catalogs else [],
        }

    def save_json(self, data: dict = None, directory: Path = None) -> Path:
        """
        Save the library data to a JSON file.

        Args:
            data (dict, optional): Dictionary to write. If None, defualts to running `to_dict`. Defaults to None.
            directory (Path, optional): The directory to save the json file. Defaults to the library's path. Defaults to None.

        Returns:
            Path: The path to the saved JSON file.
        """
        json_path = (directory or self.path) / "library.json"
        if json_path.exists():
            orig_data = json.loads(json_path.read_text())
            orig_data["libaries"] = data or self.to_dict()
            data = orig_data
        elif not data:
            data = self.to_dict()

        with open(json_path, "w") as file:
            json.dump(data, file, indent=4)

        return json_path


def get_active_bpy_library_from_context(context: Context, area: Area = None) -> UserAssetLibrary:
    if not area:
        area = next(
            (
                area
                for window in context.window_manager.windows
                for area in window.screen.areas
                if area.type == "FILE_BROWSER" and asset_utils.SpaceAssetInfo.is_asset_browser(area.spaces.active)
            ),
            None,
        )

    if not area:
        raise ValueError("No areas set to an Asset Browser found.")

    lib_name: str = context.space_data.params.asset_library_reference
    return context.preferences.filepaths.asset_libraries.get(lib_name)


def from_name(name: str, context: Context = None, load_assets=False, load_catalogs=False) -> AssetLibrary:
    """Gets a library by name and returns an AssetLibrary object."""
    lib = bpy.context.preferences.filepaths.asset_libraries.get(name)
    if not lib:
        raise ValueError(f"Library with name '{name}' not found.")
    return AssetLibrary(lib, context=context, load_assets=load_assets, load_catalogs=load_catalogs)


def from_active(context: Context, area: Area = None, load_assets=False, load_catalogs=False) -> AssetLibrary:
    """Gets the active library from the UI context and returns an AssetLibrary object."""
    return AssetLibrary(
        get_active_bpy_library_from_context(context, area=area),
        context=context,
        load_assets=load_assets,
        load_catalogs=load_catalogs,
    )


def create_new(
    name: str,
    directory: Path,
    context: Context = None,
    load_assets=False,
    load_catalogs=False,
) -> AssetLibrary:
    """Creates a new UserAssetLibrary from a passed directory and returns an AssetLibrary object."""
    return AssetLibrary.create_new_library(
        name,
        directory,
        context=context,
        load_assets=load_assets,
        load_catalogs=load_catalogs,
    )


def id_to_asset_id_type(id: ID) -> str:
    return type(id).__name__.upper()


@contextmanager
def display_all_assets_in_library(context: Context) -> None:
    """Makes all possible assets visible in the UI for the duration of the context manager. Assets are all selected so running `context.selected_assets` will return all assets."""
    # Gather Current State ##
    # Params
    active_params = {
        item: getattr(context.space_data.params.filter_asset_id, item)
        for item in dir(context.space_data.params.filter_asset_id)
        if "filter" in item
    }

    # Search
    orig_search = context.space_data.params.filter_search

    # Selected Items
    orig_selected_assets = context.selected_assets or []

    context.space_data.deselect_all()
    bpy.ops.file.select_all(action="SELECT")

    yield

    # Restore State ##
    # Params
    for item, value in active_params.items():
        setattr(context.space_data.params.filter_asset_id, item, value)

    # Search
    context.space_data.params.filter_search = orig_search

    # Selected Items
    context.space_data.deselect_all()
    for asset in orig_selected_assets:
        context.space_data.activate_asset_by_id(asset.local_id)
        # context.space_data.activate_file_by_relative_path(
        #     relative_path=asset.name
        # )


def gather_assets_of_library(lib: Context) -> list[AssetRepresentation]:
    """
    Gather all assets of a library.

    Parameters
    ----------
    lib : UserAssetLibrary
        The library to gather assets from.

    Returns
    -------
    list[AssetRepresentation]
        A list of all assets in the library.
    """
    assets = []

    # Go through all assets and see if their path is relative to the library path
    # ! Currently no way to access all assets, only those visible in the UI

    return assets


def open_location(fpath: str, win_open=False):
    """
    Opens the file explorer or finder window to the specified file path.

    Args:
    - fpath (str): The file path to open.
    - win_open (bool): If True and the operating system is Windows, the file will be opened with the default program.

    Returns:
    - None
    """
    os = system()
    if os == "Windows":
        if win_open:
            from os import startfile

            startfile(fpath)
        else:
            subprocess.Popen(["explorer", "/select,", fpath])
    elif os == "Darwin":
        subprocess.Popen(["open", fpath])
    else:
        subprocess.Popen(["xdg-open", fpath])


def get_prefs() -> "SH_AddonPreferences":
    return bpy.context.preferences.addons[__package__].preferences


def rerender_thumbnail(
    paths: list[str],
    directory: str,
    objects: list[tuple[str, str]],
    shading: str,
    angle: str = "X",
    add_plane: bool = False,
    world_name: str = "Studio Soft",
    world_strength: float = 1.0,
    padding: float = 0.0,
    rotate_world: bool = False,
    debug_scene: bool = False,
    op: "asset_ops.SH_OT_BatchUpdateAssetsFromScene" = None,
) -> None:
    """
    Rerenders the thumbnail using the specified parameters.

    Parameters:
    - path (str): The path of the blend files.
    - directory (str): The directory where the thumbnail will be saved.
    - objects: A list of tuples containing the object name and type.
    - shading (str): The shading mode to be used for rendering.
    - angle (str, optional): The angle of the camera. Defaults to 'X'.
    - add_plane (bool, optional): Whether to add a plane object to the scene. Defaults to False.
    - world_name (str, optional): The name of the world to be used. Defaults to "Studio Soft".
    - world_strength (float, optional): The strength of the world. Defaults to 1.0.
    - padding (float, optional): The padding around the objects in the thumbnail. Defaults to 0.0.
    - rotate_world (bool, optional): Whether to rotate the world. Defaults to False.
    - debug_scene (bool, optional): Whether to enable debug mode for the scene. Defaults to False.

    Returns:
    - t1 (Thread): The thread object if non-blocking mode is enabled, None otherwise.
    """
    ptt = op is None or debug_scene
    """Print to Terminal"""

    if ptt:
        print("*" * 115)
        print("Thread Starting".center(100, "*"))
        print("*" * 115)
    python_file = Path(__file__).parent / "stand_alone_scripts" / "rerender_thumbnails.py"

    names = []
    types = []
    for o in objects:
        names.append(":--separator2--:".join([a[0] for a in o]))
        types.append(":--separator2--:".join([a[1] for a in o]))

    # proc: subprocess.CompletedProcess = subprocess.run(

    # Make copies of the blend files
    # thumbnail_blends: list[Path] = []
    # for p,n,t in zip(paths, names, types):
    #     pP = Path(p)
    #     thumbnail_blend = pP.with_stem(f"{pP.stem}=+={n}=+={t}=+=_thumbnail_copy")
    #     thumbnail_blends.append(thumbnail_blend)
    #     thumbnail_blend.write_bytes(pP.read_bytes())

    # Setup Scene
    if ptt:
        print()
        print("-" * 70)
        print("Setting Up Scenes:".center(70, "-"))
        print("-" * 70)
    if op:
        op.label = "Setting Up Scenes"
        op.update = True
    args = [
        bpy.app.binary_path,
        "-b",
        "--factory-startup",
        "-P",
        str(python_file),
        "--",
        ":--separator--:".join(str(p) for p in paths),
        ":--separator--:".join(names),
        ":--separator--:".join(types),
        shading,
        directory,
        angle,
        str(add_plane),
        str(world_strength),
        (
            bpy.context.preferences.addons["cycles"].preferences.compute_device_type
            if "cycles" in bpy.context.preferences.addons.keys()
            else "NONE"
        ),
        world_name,
        str(padding),
        str(rotate_world),
        "0",  # 0 for setup
        str(debug_scene),
    ]
    if ptt:
        print("     - Terminal Command:", " ".join(args))
    # for p in thumbnail_blends:
    e = None
    try:
        proc = subprocess.run(args, stdout=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError as e:
        print(f"- Error: {e}")
        print(f"- Output: {proc.stdout.decode()}")
    if ptt and not e:
        print(proc.stdout.decode())

    if ptt:
        print()
        print("-" * 70)
        print("Rendering Assets:".center(70, "-"))
        print("-" * 70)
    if op:
        op.setup_progress = 1.0
        op.start_icon_render = True
        op.update = True

    # Render
    thumbnail_blends: list[Path] = list(
        set(
            item
            for p in paths
            for item in Path(p).parent.iterdir()
            if item.stem.endswith("_thumbnail_copy") and "=+=" in item.stem
        )
    )
    if ptt:
        print()
        print(f"Rendering {len(thumbnail_blends)} Thumbnails:")
        for tbp in thumbnail_blends:
            print(f" - {tbp}")
        print()
    thumbnails_by_blend = {}
    for i, tbp in enumerate(thumbnail_blends):
        orig_stem = tbp.stem.split("=+=")[0]
        orig_blend_path = tbp.with_stem(orig_stem)
        thumbnail_path = orig_blend_path.parent / f"{tbp.stem.replace('_thumbnail_copy', '')}_thumbnail_1.png"
        thumbnail_path_for_terminal = orig_blend_path.parent / f"{tbp.stem.replace('_thumbnail_copy', '')}_thumbnail_#"
        args = [
            bpy.app.binary_path,
            "-b",
            "--factory-startup",
            str(tbp),
            "-o",
            str(thumbnail_path_for_terminal),
            "-F",
            "PNG",
            "-f",
            "1",
        ]
        if ptt:
            print()
            print(f"({i + 1}/{len(thumbnail_blends)}) Rendering To: {thumbnail_path}")
            print(" - From:", tbp)
            print("   - exists", tbp.exists())
            print("CMD:", " ".join(args))
        try:
            proc: subprocess.CompletedProcess = subprocess.run(args, stdout=subprocess.PIPE, check=True)
            proc.returncode
        except subprocess.CalledProcessError as e:
            print(f"- Error: {e}")
            print(f"- Output: {proc.stdout.decode()}")
        thumbnails_by_blend[orig_blend_path] = thumbnail_path
        if not debug_scene:
            tbp.unlink(missing_ok=True)
        if op:
            op.render_progress = (i + 1) / len(thumbnail_blends)
            op.update = True

    if ptt:
        print()
        print("-" * 70)
        print("Applying Thumbnails:".center(70, "-"))
        print("-" * 70)
    if op:
        op.start_icon_apply = True
        op.update = True
    # Set thumbnail
    args = [
        bpy.app.binary_path,
        "-b",
        "--factory-startup",
        # str(self.blend_path),
        "-P",
        str(python_file),
        "--",
        ":--separator--:".join(paths),
        ":--separator--:".join(names),
        ":--separator--:".join(types),
        shading,
        directory,
        angle,
        str(add_plane),
        str(world_strength),
        (
            bpy.context.preferences.addons["cycles"].preferences.compute_device_type
            if "cycles" in bpy.context.preferences.addons.keys()
            else "NONE"
        ),
        world_name,
        str(padding),
        str(rotate_world),
        "1",  # 1 for applying thumbnail
        str(debug_scene),
    ]
    if ptt:
        print("     - Terminal Command:", " ".join(args))
    e = None
    try:
        proc = subprocess.run(args, stdout=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError as e:
        print(f"- Error: {e}")
        print(f"- Output: {proc.stdout.decode()}")
    if ptt and not e:
        print(proc.stdout.decode())
    print(proc.stdout.decode())

    if ptt:
        print("*" * 115)
        print("Thread Finished".center(100, "*"))
        print("*" * 115)
    if op:
        op.apply_progress = 1.0
        op.update = True
    # cmd = [bpy.app.binary_path]
    # #cmd.append("--background")
    # #cmd.append(path[0])
    # cmd.append("--factory-startup")
    # # cmd.append("--python")
    # cmd.append("-P")
    # # cmd.append(os.path.join(os.path.dirname(
    # #     os.path.abspath(__file__)), "rerender_thumbnails.py"))
    # cmd.append(str(Path(__file__).parent / "stand_alone_scripts" / "rerender_thumbnails.py"))
    # cmd.append('--')
    # cmd.append(":--separator--:".join(path))
    # names=[]
    # types=[]
    # for o in objects:
    #     names.append(":--separator2--:".join([a[0] for a in o]))
    #     types.append(":--separator2--:".join([a[1] for a in o]))
    # cmd.append(":--separator--:".join(names))
    # cmd.append(":--separator--:".join(types))
    # cmd.append(shading)
    # cmd.append(directory)
    # cmd.append(angle)
    # cmd.append(str(add_plane))
    # cmd.append(str(prefs.world_strength))
    # cmd.append(bpy.context.preferences.addons['cycles'].preferences.compute_device_type if 'cycles' in bpy.context.preferences.addons.keys() else 'NONE')
    # if get_prefs().non_blocking:
    #     t1=threading.Thread(
    #         target=functools.partial(
    #             run,
    #             cmd,
    #         )
    #     )
    #     t1.start()
    #     return t1
    # else:
    #     proc: subprocess.CompletedProcess = run(
    #         cmd,
    #         stderr=subprocess.PIPE,
    #         stdout=subprocess.PIPE,
    #     )

    #     if proc.returncode:
    #         print(f"    - Error: {proc.stderr.decode()}")
    #     print("".center(100, "-"))
    #     text = proc.stdout.decode()
    #     text.splitlines()
    #     new_text = "\n".join(
    #         line
    #         for line in text.splitlines()
    #         if line.startswith("|")
    #     )
    #     print(new_text)
    #     print("".center(100, "-"))
    #     print()

    #     return None


def resolve_angle(angle: str, flip_x: str, flip_y: str, flip_z: str):
    if flip_x:
        angle = angle.replace("X", "-X")
    if flip_y:
        angle = angle.replace("Y", "-Y")
    if flip_z:
        angle = angle.replace("Z", "-Z")
    return angle


def mouse_in_window(window: Window, x, y) -> bool:
    """
    Check if the mouse coordinates (x, y) are within the boundaries of the given window.

    Parameters:
    window (Window): The window object to check against.
    x (int): The x-coordinate of the mouse.
    y (int): The y-coordinate of the mouse.

    Returns:
    bool: True if the mouse is within the window boundaries, False otherwise.
    """
    return window.x <= x <= window.x + window.width and window.y <= y <= window.y + window.height


def pack_files(blend_file: Path):
    python_file = Path(__file__).parent / "stand_alone_scripts" / "pack_files.py"

    args = [bpy.app.binary_path, "-b", str(blend_file), "-P", str(python_file)]
    print(" ".join(args))

    subprocess.run(args)


def move_blend_file(src: Path, dst: Path, pack: bool = False):
    """Save the blend file to the new location with remapped filepaths and compression."""
    python_file = Path(__file__).parent / "stand_alone_scripts" / "move_blend_file.py"

    args = [
        bpy.app.binary_path,
        "-b",
        "--factory-startup",
        str(src),
        "-P",
        str(python_file),
        str(dst),
        str(pack),
    ]

    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode > 1:
        print(f"Error: {proc.stderr.decode()}")
        print(f"Output: {proc.stdout.decode()}")


def clean_blend_file(
    blend_file: Path,
    ids_to_keep: list[ID] = None,
    ids_to_remove: list[ID | AssetRepresentation] = None,
    types: list[str] = None,
):
    python_file = Path(__file__).parent / "stand_alone_scripts" / "clear_blend_file.py"

    args = [
        bpy.app.binary_path,
        "-b",
        "--factory-startup",
        str(blend_file),
        "-P",
        str(python_file),
        ":--separator--:".join(ids_to_keep) if ids_to_keep else "None",
        ":--separator--:".join(ids_to_remove) if ids_to_remove else "None",
        ":--separator--:".join(types),
    ]

    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode > 1:
        print(f"Error: {proc.stderr.decode()}")
        print(f"Output: {proc.stdout.decode()}")


def export_helper(
    blend_file: Path,
    destination_dir: Path,
    op: "export_library.SH_OT_ExportLibrary" = None,
):
    python_file = Path(__file__).parent / "stand_alone_scripts" / "export_helper.py"

    args = [
        bpy.app.binary_path,
        "-b",
        "--factory-startup",
        str(blend_file),
        "-P",
        str(python_file),
        str(destination_dir),
    ]

    proc = subprocess.Popen(args, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, text=True)
    # proc = subprocess.Popen(args)

    if op:
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line.startswith("="):
                prop, value = line[1:].split("=")
                value = value.replace("\n", "")
                match prop:
                    case "prog":
                        op.movingfiles_file_prog = float(value)
                    case "sub_show":
                        op.movingfiles_sub_show = value == "True"
                    case "sub_label":
                        op.sub_label = value
                    case "sub_prog":
                        op.movingfiles_sub_prog = float(value)
                    case _:
                        print("Unhandled Property:", prop, ", value:", value)
                op.updated = True
    else:
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            elif line and line[0] == "|":
                if line == "|":
                    print()
                    continue

                line_split = line.split("+=+")
                if len(line_split) == 2:
                    text, end = line_split
                    if end == "r\n":
                        end = "\r"
                else:
                    text = line_split[0]
                    end = "\n"
                print(text, end=end)

    if proc.returncode > 1:
        print()
        print(f"Error: {proc.stderr.decode()}")
        print(f"Output: {proc.stdout.decode()}")


def update_asset_browser_areas(context: Context = None, tag_redraw=True, update_library=True):
    C = context or bpy.context

    for area in C.screen.areas:
        if asset_utils.SpaceAssetInfo.is_asset_browser(area.spaces.active):
            if tag_redraw:
                area.tag_redraw()
            if update_library:
                try:
                    with C.temp_override(area=area):
                        bpy.ops.asset.library_refresh()
                except Exception as e:
                    print(f"Error while refreshing all asset browser areas: {e}")


def mark_assets_in_blend(
    lib: AssetLibrary,
    directory: str,
    mark_actions: bool,
    mark_collections: bool,
    mark_materials: bool,
    mark_node_trees: bool,
    mark_objects: bool,
    mark_obj_armatures: bool,
    mark_obj_cameras: bool,
    mark_obj_curves: bool,
    mark_obj_empties: bool,
    mark_obj_fonts: bool,
    mark_obj_gpencils: bool,
    mark_obj_lattices: bool,
    mark_obj_lights: bool,
    mark_obj_light_probes: bool,
    mark_obj_meshes: bool,
    mark_obj_metas: bool,
    mark_obj_point_clouds: bool,
    mark_obj_speakers: bool,
    mark_obj_surfaces: bool,
    mark_obj_volumes: bool,
    mark_worlds: bool,
    clear_other_assets: bool,
    skip_hidden: bool,
    catalog_source: str,
    new_catalog_name: str,
    author: str,
    description: str,
    license: str,
    copyright: str,
    tags: list[str],
    move_to_library: bool,
    override_existing_data: bool = False,
    recursive: bool = True,
    op: "import_from_directory.SH_OT_ImportFromDirectory" = None,
) -> dict[str, tuple[str, str]]:
    """
    Mark assets in a blend file and add them to the library.
    Returns a dictionary of assets marked in the blend files for rendering icons
        Key: Blend File Path
        Value: Tuple of (Asset Name, Asset Type)
    """
    python_file = Path(__file__).parent / "stand_alone_scripts" / "mark_assets_in_blend_file.py"

    blends = list(Path(directory).rglob("**/*.blend")) if recursive else list(Path(directory).glob("*.blend"))

    tags_to_add = []
    for tag_name, tag_bool in zip(hive_mind.TAGS_DICT.keys(), tags):
        if tag_bool:
            tags_to_add.append(tag_name)

    match catalog_source:
        case "Directory":
            dpath = Path(directory)
            catalog = lib.catalogs.get_catalog_by_name(dpath.name)
            if not catalog:
                catalog = lib.catalogs.add_catalog(dpath.name)
            catalog_id = catalog.id
        case "Filename":
            for blend_file in blends:
                catalog = lib.catalogs.get_catalog_by_name(blend_file.stem)
                if not catalog:
                    catalog = lib.catalogs.add_catalog(blend_file.stem)
            lib.catalogs.write_file()
        case "NONE":
            catalog_id = "NONE"
        case "NEW":
            catalog_id = lib.catalogs.add_catalog(new_catalog_name).id

    assets_marked: dict[str, list[str, str]] = {}
    for i, blend_file in enumerate(blends):
        if catalog_source == "Filename":
            catalog = lib.catalogs.get_catalog_by_name(blend_file.stem)
            catalog_id = catalog.id
        args = (
            bpy.app.binary_path,
            "-b",
            "--factory-startup",
            str(blend_file),
            "-P",
            str(python_file),
            str(mark_actions),
            str(mark_collections),
            str(mark_materials),
            str(mark_node_trees),
            str(mark_objects),
            str(mark_obj_armatures),
            str(mark_obj_cameras),
            str(mark_obj_curves),
            str(mark_obj_empties),
            str(mark_obj_fonts),
            str(mark_obj_gpencils),
            str(mark_obj_lattices),
            str(mark_obj_lights),
            str(mark_obj_light_probes),
            str(mark_obj_meshes),
            str(mark_obj_metas),
            str(mark_obj_point_clouds),
            str(mark_obj_speakers),
            str(mark_obj_surfaces),
            str(mark_obj_volumes),
            str(mark_worlds),
            str(clear_other_assets),
            str(skip_hidden),
            catalog_source,
            catalog_id,
            str(override_existing_data),
            author,
            description,
            license,
            copyright,
            ",".join(tags_to_add),
            str(move_to_library),
            str(lib.path),
        )

        proc = subprocess.Popen(
            # proc = subprocess.run(
            args,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
            text=True,
            # args
        )

        """{blend file path, (asset name, asset type)}"""
        active_blend_path = None
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            elif line and line[:2] == "~~":
                if line.startswith("~~FP:"):
                    active_blend_path = line[5:-1]
                    assets_marked[active_blend_path] = []
                else:
                    assets_marked[active_blend_path].append(line[2:-1].split(","))

        if op:
            op.metadata_progress = (i + 1) / len(blends)
            op.update = True
        #     elif line and line[0] == "|":
        #         if line == "|":
        #             print()
        #             continue

        #         line_split = line.split("+=+")
        #         if len(line_split) == 2:
        #             text, end = line_split
        #             if end == "r\n":
        #                 end = "\r"
        #         else:
        #             text = line_split[0]
        #             end = "\n"
        #         print(text, end=end)

        # if proc.returncode > 1:
        #     print()
        #     print(f"Error: {proc.stderr.decode()}")
        #     print(f"Output: {proc.stdout.decode()}")
    return assets_marked
