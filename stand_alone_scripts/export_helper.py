"""
CLI Script to save the current blend file to a new location with updated relative paths and compression:

Argument Order:
     0. blender executable
     1. background arg
     2. factory startup arg
     3. blend file to open: str
     4. run python script arg
     5. script to run
     6. destination dir path: str
"""

import sys
from pathlib import Path
from typing import Any

import bpy
import numpy as np
import OpenImageIO.OpenImageIO as oiio
from OpenImageIO import ROI, ImageBuf, ImageSpec

DST = sys.argv[6]


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


def save_out_preview(item: bpy.types.ID, directory: Path) -> None:
    """Will save out the thumbnail of the item to the (assumed temporary) directory to be zipped."""
    if item.asset_data and item.preview:
        pixels = np.array(item.preview.image_pixels_float)

        d3 = 4
        if len(pixels) == item.preview.image_size[0] * item.preview.image_size[1] * 3:
            d3 = 3
        pixels.resize(list(item.preview.image_size) + [d3])
        fp = (
            directory
            / "Thumbnails"
            / f"{Path(bpy.data.filepath).stem}_{item.__class__.__name__.lower()}_{item.name}_preview.webp"
        )
        print(f"Saving preview for {item.name} to {fp}")
        numpy_to_image(
            pixels[::-1],
            save_path=fp,
        )


if __name__ == "__main__":
    # Separate directory to save the blend file and images named after blend file
    blend_path = Path(bpy.data.filepath)
    d = Path(DST) / blend_path.stem
    d.mkdir(parents=True, exist_ok=True)

    bpy.ops.file.make_paths_absolute()

    def make_rel(path: Path) -> Path:
        return path.relative_to(d)

    images_to_copy = [img for img in bpy.data.images if not img.packed_file and not img.packed_files]
    sounds_to_copy = [sound for sound in bpy.data.sounds if not sound.packed_file]
    volumes_to_copy = [volume for volume in bpy.data.volumes if not volume.packed_file]

    total_assets = len(images_to_copy) + len(sounds_to_copy) + len(volumes_to_copy)

    print(f"|    Images: {len(images_to_copy)}")
    print("|        Progress:   0.00%+=+r")
    prog = str(0)
    for i, img in enumerate(images_to_copy):
        if img.source == "SEQUENCE":
            print(f"|        Progress: {prog.rjust(6)}%")
            print("|            Sequence:   0.00%+=+r")
            print("=sub_label=Sequence")
            print("=sub_show=True")
            print("=sub_prog=0")
            seq_prog = str(0)
            base_filepath = Path(img.filepath)
            vol_dir = base_filepath.parent
            if not vol_dir.exists():
                print(f"|        Volume Sequence Directory does't exist: {vol_dir}")
                continue
            *name_parts, frame = base_filepath.stem.split("_")
            name_base = "_".join(name_parts)
            files_to_copy = [
                f
                for f in vol_dir.iterdir()
                if f.is_file() and f.name.startswith(name_base) and f.suffix == base_filepath.suffix
            ]
            for j, f in enumerate(files_to_copy):
                if f.is_file() and f.name.startswith(name_base) and f.suffix == base_filepath.suffix:
                    dst = d / f.name
                    dst.write_bytes(f.read_bytes())
                    sub_prog = j / len(files_to_copy)
                    print(f"=sub_prog={sub_prog}")
                    seq_prog = f"{sub_prog * 100:.2f}"
                    print(f"|        Progress: {seq_prog.rjust(6)}%+=+r")
            print("=sub_show=False")
        else:
            src = Path(img.filepath)
            if src.exists() and src != Path() and src.is_file():
                dst = d / src.name
                dst.write_bytes(src.read_bytes())
                img.filepath = str(make_rel(dst))
        prg = i / total_assets
        print(f"=prog={prg}")
        prog = f"{i / len(bpy.data.images) * 100:.2f}"
        print(f"|        Progress: {prog.rjust(6)}%+=+r")
    print("|        Progress: 100.00%")
    print("|")
    assets_moved = len(images_to_copy)

    print(f"|    Sounds: {len(sounds_to_copy)}")
    print("|        Progress:   0.00%+=+r")
    prog = str(0)
    for i, sound in enumerate(sounds_to_copy):
        if sound.packed_file:
            continue

        src = Path(sound.filepath)
        if src.exists() and src != Path() and src.is_file():
            dst = d / src.name
            dst.write_bytes(src.read_bytes())
            sound.filepath = str(make_rel(dst))
        prg = (i + assets_moved) / total_assets
        print(f"=prog={prg}")
        prog = f"{i / len(bpy.data.sounds) * 100:.2f}"
        print(f"|        Progress: {prog.rjust(6)}%+=+r")
    print("|")

    print(f"|    Volumes: {len(volumes_to_copy)}")
    print("|        Progress:   0.00%+=+r")
    prog = str(0)
    for i, volume in enumerate(volumes_to_copy):
        if volume.packed_file:
            continue

        if volume.is_sequence:
            print(f"|        Progress: {prog.rjust(6)}%")
            print("|            Sequence:   0.00%+=+r")
            print("=sub_label=Sequence")
            print("=sub_show=True")
            base_filepath = Path(volume.filepath)
            vol_dir = base_filepath.parent
            if not vol_dir.exists():
                print(f"|        Volume Sequence Directory does't exist: {vol_dir}")
                continue
            *name_parts, frame = base_filepath.stem.split("_")
            name_base = "_".join(name_parts)
            files_to_copy = [
                f
                for f in vol_dir.iterdir()
                if f.is_file() and f.name.startswith(name_base) and f.suffix == base_filepath.suffix
            ]
            seq_prog = "0.00"
            print("=sub_prog=0")
            for j, f in enumerate(files_to_copy):
                if f.is_file() and f.name.startswith(name_base) and f.suffix == base_filepath.suffix:
                    dst = d / f.name
                    dst.write_bytes(f.read_bytes())
                    sub_prog = j / len(files_to_copy)
                    print(f"=sub_prog={sub_prog}")
                    seq_prog = f"{sub_prog * 100:.2f}"
                    print(f"|        Progress: {seq_prog.rjust(6)}%+=+r")
            print("=sub_show=False")
            print("|            Sequence: 100.00%")
        else:
            src = Path(volume.filepath)  # TODO: Handle volume sequence
            if src.exists() and src != Path() and src.is_file():
                dst = d / src.name
                dst.write_bytes(src.read_bytes())
                volume.filepath = str(make_rel(dst))
            prg = (i + assets_moved) / total_assets
            print(f"=prog={prg}")
            prog = f"{i / len(bpy.data.volumes) * 100:.2f}"
            print(f"|        Progress: {prog.rjust(6)}%+=+r")

    # Export thumbnails of all assets
    for action in bpy.data.actions:
        save_out_preview(action, d)
    for collection in bpy.data.collections:
        save_out_preview(collection, d)
    for material in bpy.data.materials:
        save_out_preview(material, d)
    for node_tree in bpy.data.node_groups:
        save_out_preview(node_tree, d)
    for obj in bpy.data.objects:
        save_out_preview(obj, d)
    for world in bpy.data.worlds:
        save_out_preview(world, d)

    bpy.ops.wm.save_mainfile(filepath=str(d / blend_path.name), compress=True)
