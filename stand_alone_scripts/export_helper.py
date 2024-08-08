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

import bpy

DST = sys.argv[6]


if __name__ == "__main__":
    # Separate directory to save the blend file and images named after blend file
    blend_path = Path(bpy.data.filepath)
    d = Path(DST) / blend_path.stem
    d.mkdir(parents=True, exist_ok=True)

    bpy.ops.file.make_paths_absolute()

    def make_rel(path: Path) -> Path:
        return path.relative_to(d)

    images_to_copy = [
        img for img in bpy.data.images if not img.packed_file and not img.packed_files
    ]
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
            print(f"=sub_prog=0")
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
                if f.is_file()
                and f.name.startswith(name_base)
                and f.suffix == base_filepath.suffix
            ]
            for j, f in enumerate(files_to_copy):
                if (
                    f.is_file()
                    and f.name.startswith(name_base)
                    and f.suffix == base_filepath.suffix
                ):
                    dst = d / f.name
                    dst.write_bytes(f.read_bytes())
                    sub_prog = j / len(files_to_copy)
                    print(f"=sub_prog={sub_prog}")
                    seq_prog = f"{sub_prog*100:.2f}"
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
        prog = f"{i/len(bpy.data.images)*100:.2f}"
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
        prog = f"{i/len(bpy.data.sounds)*100:.2f}"
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
                if f.is_file()
                and f.name.startswith(name_base)
                and f.suffix == base_filepath.suffix
            ]
            seq_prog = "0.00"
            print(f"=sub_prog=0")
            for j, f in enumerate(files_to_copy):
                if (
                    f.is_file()
                    and f.name.startswith(name_base)
                    and f.suffix == base_filepath.suffix
                ):
                    dst = d / f.name
                    dst.write_bytes(f.read_bytes())
                    sub_prog = j / len(files_to_copy)
                    print(f"=sub_prog={sub_prog}")
                    seq_prog = f"{sub_prog*100:.2f}"
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
            prog = f"{i/len(bpy.data.volumes)*100:.2f}"
            print(f"|        Progress: {prog.rjust(6)}%+=+r")

    bpy.ops.wm.save_mainfile(filepath=str(d / blend_path.name), compress=True)
