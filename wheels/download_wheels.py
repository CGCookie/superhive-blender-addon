import subprocess
from pathlib import Path

PY_VERSION = "3.11"

module_names = (
    "fuzzywuzzy",
)

compiled_modules = (
    "levenshtein", # will download rapidfuzz
)

platforms = (
    "win_amd64",
    "manylinux_2_24_x86_64",
    "manylinux_2_24_i686",
    "manylinux2014_x86_64",
    "manylinux2010_x86_64",
    "manylinux2014_i686",
    "manylinux2010_i686",
    "manylinux1_x86_64",
    "manylinux1_i686",
    "macosx_10_9_x86_64",
    "macosx_10_9_universal2",
    "macosx_11_0_arm64",
    "macosx_11_0_x86_64",
)

if __name__ == "__main__":
    print()
    print("Downloading Wheels:")

    wheel_names_for_manifest = []

    def download_wheels(args: tuple[str]):
        a = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if a.returncode:  # a.returncode != 0
            print(f"         - FAILED | Reason:  {str(a.stderr, 'utf-8')}")
        else:
            # Get the wheel name for the manifest
            out = str(a.stdout, 'utf-8')
            wheel_name = None
            if "File was already downloaded" in out:
                wheel_name = out.split(
                    "File was already downloaded")[-1].strip().split(".whl")[0] + ".whl"
            elif "Saved" in out:
                wheel_name = out.split("Saved")[-1].strip().split(".whl")[0] + ".whl"

            if wheel_name:
                wheel_names_for_manifest.append(
                    f"./wheels/{Path(wheel_name).name}")
            print("         - Success")

    print("   Platform Independent Modules...")
    for module_name in module_names:
        print(f"      Module: '{module_name}'")
        args = (
            "pip",
            "wheel",
            module_name,
            "-w",
            "./wheels",
        )
        download_wheels(args)

    print("   Compiled Modules...")
    for module_name in compiled_modules:
        for platform in platforms:
            print(f"      Module: '{module_name}',  Platform: '{platform}'")
            args = (
                "pip",
                "download",
                module_name,
                "--dest",
                "./wheels",
                "--only-binary=:all:",
                f"--python-version={PY_VERSION}",
                f"--platform={platform}",
            )
            download_wheels(args)

    print()
    print("Wheels For Manifest:")
    print("wheels = [")
    for wheel_name in wheel_names_for_manifest:
        print(f'  "{wheel_name}",')
    print("]")
    print()
    print("Download Complete")
    print()
    print()
