"""Library↔server binding, persisted as .superhive.json in the library dir.

The publish flow is otherwise stateless (asset diffing rides the server's
sha256s, catalog identity rides cats.txt uuids) — the sidecar only remembers
which server library this directory publishes to, plus the name→server-id map
that makes renames expressible (previous_asset_id).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

SIDECAR_NAME = ".superhive.json"
SIDECAR_VERSION = 1


def read_sidecar(library_dir: Path | str) -> dict | None:
    path = Path(library_dir) / SIDECAR_NAME
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not data.get("library_id"):
        return None
    data.setdefault("assets", {})
    return data


def write_sidecar(library_dir: Path | str, data: dict) -> None:
    data = dict(data)
    data["version"] = SIDECAR_VERSION
    data["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path = Path(library_dir) / SIDECAR_NAME
    tmp = path.parent / (SIDECAR_NAME + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def clear_sidecar(library_dir: Path | str) -> None:
    path = Path(library_dir) / SIDECAR_NAME
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def record_asset_ids(library_dir: Path | str, mapping: dict[str, str]) -> None:
    """Merge asset-name -> server-id entries into the sidecar (no-op unbound)."""
    data = read_sidecar(library_dir)
    if data is None or not mapping:
        return
    data["assets"].update(mapping)
    write_sidecar(library_dir, data)


def rename_asset(library_dir: Path | str, old_name: str, new_name: str) -> None:
    """Re-key a sidecar asset entry after a local rename, so the next publish
    sends previous_asset_id instead of creating a duplicate."""
    data = read_sidecar(library_dir)
    if data is None:
        return
    server_id = data["assets"].pop(old_name, None)
    if server_id is None:
        return
    data["assets"][new_name] = server_id
    write_sidecar(library_dir, data)
