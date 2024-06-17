# Utilities for interacting with the blender_assets.cats.txt file
import uuid
from contextlib import contextmanager
from pathlib import Path
from platform import system
from subprocess import Popen
from typing import Union

from bpy.types import AssetRepresentation, UserAssetLibrary


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
            The name or `simple_name` of the Catalog object. Will set `simple_name` and `name` if `path` is not provided.
        id : str, optional
            The unique identifier for the Catalog object. If not provided, a new UUID (uuid4) will be generated.
        path : str, optional
            The path associated with the Catalog object. If provided, the name of the Catalog object will be extracted from the path.
        
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
        """
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
        """
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
        """

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
                if (dir / "blender_assets.cats.txt").exists():
                    found_new = True
                    self.path = dir / "blender_assets.cats.txt"
                    break
            if not found_new:
                raise FileNotFoundError(
                    f"Catalogs file not found in directory: {self.path.parent}"
                )

        self.load_catalogs()

    initial_text = '# This is an Asset Catalog Definition file for Blender.\n#\n# Empty lines and lines starting with `#` will be ignored.\n# The first non-ignored line should be the version indicator.\n# Other lines are of the format "UUID:catalog/path/for/assets:simple catalog name"'

    VERSION = 1

    def exists(self) -> bool:
        return self.path.exists()

    def load_catalogs(self):
        """Load `catalogs` from file"""
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


def gather_assets_of_library(lib: UserAssetLibrary) -> list[AssetRepresentation]:
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

