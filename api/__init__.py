"""Superhive assets API layer.

Deliberately bpy-free: everything in this package is plain Python so it can
be unit-tested outside Blender (see tests/). It has no register/unregister,
so the extension's `_call_globals` registration pattern skips it.
"""

from . import client, payloads, sidecar, taxonomy  # noqa: F401
