# Puts the repo root on sys.path so tests can `import api` directly.
# (The root __init__.py is the Blender extension entry and imports bpy, so the
# repo root must NOT be imported as a package — no conftest.py at the root.)
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
