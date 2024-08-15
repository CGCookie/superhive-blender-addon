"""
CLI Script to save out the previews of all assets:

Argument Order:
     0. blender executable
     1. background arg
     2. factory startup arg: str
     3. blend file to open: str
     4. run python script arg
     5. script to run
     6. output directory: str
     7. asset name: str
     8. asset type: str
     9. do whole file: bool
"""

import sys
from pathlib import Path
from typing import Any

import bpy
import numpy as np
import OpenImageIO.OpenImageIO as oiio
from OpenImageIO import ROI, ImageBuf, ImageSpec

DIRECTORY = Path(sys.argv[6])
ASSET_NAME = sys.argv[7]
ASSET_TYPE = sys.argv[8]
DO_WHOLE_FILE = sys.argv[9] == "True"

print(f"{DIRECTORY=}")
print(f"{ASSET_NAME=}")
print(f"{ASSET_TYPE=}")
print(f"{DO_WHOLE_FILE=}")


def set_compression(spec: ImageSpec, extension: str, quality: int = 100, quality_other: Any = None) -> None:
    if extension == ".bmp":
        spec.attribute("compression", quality_other)  # "rle4" or "rle8"
    elif extension in {".jpg", ".jpeg", ".jpe", ".jif", ".jfif", ".jfi"}:
        spec.attribute("Compression", f"jpeg:{quality}")
    elif extension == ".exr":
        # quality_other= "none", "rle", "zips", "zip", "piz", "pxr24", "b44", "b44a", "dwaa", "dwab"
        spec.attribute("compression", quality_other)
    elif extension == ".png":
        # quality needs to be between 0 and 9
        quality = quality / 100 * 9
        spec.attribute("png:compressionLevel", quality)
    elif extension in {".tif", ".tiff", ".tx", ".env", ".sm", ".vsm"}:
        # quality_other= "none", "lzw", "zip", "ccittrle", "jpeg", "backbits"
        spec.attribute("compression", quality_other)
        spec.attribute("tiff:compression", quality)


def numpy_to_image(
    buf: np.ndarray,
    save_path: Path | str = None,
    quality: int = 100,
    quality_other: Any = None,
) -> ImageBuf:
    """
    Convert a numpy array to an image.

    Parameters
    ----------
    buf : np.ndarray
        The numpy array to convert.
    path_path : Path or str
        The path to the image file to write. If not path is supplied the image will not be saved.
    quality : int, optional
        The quality of the image to save. Only applies if `save_path` is provided.

    Returns
    -------
    ImageBuf
        The image.

    """
    image = ImageBuf(ImageSpec(buf.shape[1], buf.shape[0], buf.shape[2], oiio.FLOAT))
    image.set_pixels(ROI(0, buf.shape[1], 0, buf.shape[0]), buf)
    if save_path is not None:
        set_compression(
            image.spec(),
            Path(save_path).suffix,
            quality=quality,
            quality_other=quality_other,
        )
        save_path.parent.mkdir(parents=True, exist_ok=True)
        image.write(str(save_path))
        if image.has_error:
            error = image.geterror()
            print("Error saving image:", error)
            raise Exception(error)
    return image


def save_out_preview(item: bpy.types.ID):
    if item.preview:
        pixels = np.array(item.preview.image_pixels_float)

        d3 = 4
        if len(pixels) == item.preview.image_size[0] * item.preview.image_size[1] * 3:
            d3 = 3
        pixels.resize(list(item.preview.image_size) + [d3])
        fp = (
            DIRECTORY
            / "Thumbnails"
            / f"{Path(bpy.data.filepath).stem}_{item.__class__.__name__.lower()}_{item.name}_preview.webp"
        )
        print(f"Saving preview for {item.name} to {fp}")
        numpy_to_image(
            pixels[::-1],
            save_path=fp,
        )

    else:
        print(f"No preview found for {item.name}")


if __name__ == "__main__":
    DIRECTORY.mkdir(parents=True, exist_ok=True)

    if DO_WHOLE_FILE:
        for item in bpy.data.actions:
            if item.asset_data:
                save_out_preview(item)

        for item in bpy.data.collections:
            if item.asset_data:
                save_out_preview(item)

        for item in bpy.data.materials:
            if item.asset_data:
                save_out_preview(item)

        for item in bpy.data.node_groups:
            if item.asset_data:
                save_out_preview(item)

        for item in bpy.data.objects:
            if item.asset_data:
                save_out_preview(item)

        for item in bpy.data.worlds:
            if item.asset_data:
                save_out_preview(item)
    else:
        item = getattr(bpy.data, ASSET_TYPE).get(ASSET_NAME)
        print(f"Getting item: Name:{ASSET_NAME}, Type:{ASSET_TYPE}  |  item: {item}")
        if item:
            save_out_preview(item)
        else:
            print(f"Item {ASSET_NAME} not found in {ASSET_TYPE}")
