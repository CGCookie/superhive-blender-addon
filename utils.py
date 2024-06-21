# Utilities for interacting with the blender_assets.cats.txt file
import subprocess
import uuid
from contextlib import contextmanager
from pathlib import Path
from platform import system
from subprocess import Popen
from typing import TYPE_CHECKING, Union

import bpy
from bpy.types import Area, AssetRepresentation, Context, UserAssetLibrary
from bpy_extras import asset_utils

from . import hive_mind


if TYPE_CHECKING:
    from .ui.prefs import SH_AddonPreferences
    from .settings import asset as asset_settings


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
        self.id = id or str(uuid.uuid4())
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

    def get_catalogs(self) -> list['Catalog']:
        """Return a list of all catalogs in the file as a 1-Dimensional list."""
        catalogs = []
        for catalog in self.children.values():
            catalogs.append(catalog)
            catalogs.extend(catalog.get_catalogs())
        return catalogs


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
                raise FileNotFoundError(
                    f"Catalogs file not found in directory: {self.path.parent}"
                )

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

    def add_catalog(
        self, name: str, id: str = None, path: str = None, auto_place=False
    ) -> Catalog:
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


# Context manager for opening and then saving the catalogs file
@contextmanager
def open_catalogs_file(path: Path, is_new=False) -> CatalogsFile:
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
        self.license = asset.metadata.sh_license
        self.copyright = asset.metadata.sh_copyright
        self.catalog_simple_name = asset.metadata.catalog_simple_name
        """The original `catalog_simple_name` of the asset. Not a new one"""
        self.catalog_id = asset.metadata.sh_catalog
        self.tags = [
            tag.name
            for tag in asset.metadata.sh_tags.tags
        ]
        self.icon_path = None

    def update_asset(self, blender_exe: str) -> None:
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
        if proc.returncode:
            print(f"    - Error: {proc.stderr.decode()}")
        print("".center(100, "-"))
        text = proc.stdout.decode()
        text.splitlines()
        new_text = "\n".join(
            line
            for line in text.splitlines()
            if line.startswith("|")
        )
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

        sh_tags: 'asset_settings.SH_AssetTags' = self.orig_asset.metadata.sh_tags
        sh_tags.clear(context)
        for tag in self.orig_asset.metadata.tags:
            sh_tags.new_tag(tag.name, context)
        self.orig_asset.metadata.sh_is_dirty_tags = False


class Assets:
    def __init__(self, assets: list[AssetRepresentation]) -> None:
        self._dict: dict[str, Asset] = {}
        self._list: list[Asset] = []

        for asset in assets:
            a = Asset(asset)
            self._dict[a.name] = a
            self._list.append(a)

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
    def __init__(self, library: UserAssetLibrary, context: Context = None, load_assets=False, load_catalogs=False) -> None:
        if not library:
            raise ValueError("No library provided.")

        self.context: Context = context
        self.area: Area = None
        if context:
            self.area = next((
                area
                for window in context.window_manager.windows
                for area in window.screen.areas
                if area.type == "FILE_BROWSER" and asset_utils.SpaceAssetInfo.is_asset_browser(area.spaces.active)
            ), None)

        self.library: UserAssetLibrary = library
        self.name = library.name
        self.path: Path = Path(library.path)

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
        C = self.get_context()
        with display_all_assets_in_library(C):
            return C.selected_assets[:] if C.selected_assets else []

    def load_assets(self):
        self.assets = Assets(self.get_possible_assets())

    @contextmanager
    def open_catalogs_file(self) -> CatalogsFile:
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
    def create_new_library(cls, name: str, path: str, context: Context = None, load_assets=False, load_catalogs=False) -> 'AssetLibrary':
        """Create a new `UserAssetLibrary` in Blender and then create a new `AssetLibrary` object from that library."""
        lib = cls.create_bpy_library(name, path)
        return cls(
            lib,
            context=context,
            load_assets=load_assets,
            load_catalogs=load_catalogs,
        )


def get_active_bpy_library_from_context(context: Context, area: Area = None) -> UserAssetLibrary:
    if not area:
        area = next((
            area
            for window in context.window_manager.windows
            for area in window.screen.areas
            if area.type == "FILE_BROWSER" and asset_utils.SpaceAssetInfo.is_asset_browser(area.spaces.active)
        ), None)

    if not area:
        raise ValueError("No areas set to an Asset Browser found.")

    lib_name: str = context.space_data.params.asset_library_reference
    return context.preferences.filepaths.asset_libraries.get(lib_name)


def from_name(name: str, context: Context = None, load_assets=False, load_catalogs=False) -> AssetLibrary:
    """Gets a library by name and returns an AssetLibrary object."""
    lib = bpy.context.preferences.filepaths.asset_libraries.get(name)
    if not lib:
        raise ValueError(f"Library with name '{name}' not found.")
    return AssetLibrary(
        lib, context=context, load_assets=load_assets, load_catalogs=load_catalogs
    )


def from_active(context: Context, area: Area = None, load_assets=False, load_catalogs=False) -> AssetLibrary:
    """Gets the active library from the UI context and returns an AssetLibrary object."""
    return AssetLibrary(
        get_active_bpy_library_from_context(context, area=area),
        context=context, load_assets=load_assets, load_catalogs=load_catalogs
    )


def create_new(name: str, directory: Path, context: Context = None, load_assets=False, load_catalogs=False) -> AssetLibrary:
    """Creates a new UserAssetLibrary from a passed directory and returns an AssetLibrary object."""
    return AssetLibrary.create_new_library(
        name, directory,
        context=context,
        load_assets=load_assets,
        load_catalogs=load_catalogs
    )


@contextmanager
def display_all_assets_in_library(context: Context) -> None:
    """Makes all possible assets visible in the UI for the duration of the context manager. Assets are all selected so running `context.selected_assets` will return all assets."""
    ## Gather Current State ##
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
    bpy.ops.file.select_all(action='SELECT')

    yield

    ## Restore State ##
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
            Popen(["explorer", "/select,", fpath])
    elif os == "Darwin":
        Popen(["open", fpath])
    else:
        Popen(["xdg-open", fpath])


def get_prefs() -> 'SH_AddonPreferences':
    return bpy.context.preferences.addons[__package__].preferences

