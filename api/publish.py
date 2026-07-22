"""Publish-pipeline steps that are pure data + HTTP (no bpy).

The Blender-side operators snapshot their data on the main thread and hand it
here; everything in this module may run on a worker thread.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .client import SuperhiveClient, ValidationError


@dataclass
class CatalogSyncResult:
    synced: list[dict] = field(default_factory=list)  # server's resulting listing
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (path, reason)


def sync_catalogs(
    client: SuperhiveClient,
    library_id: str,
    entries: list[dict],
    roots: list[str],
) -> CatalogSyncResult:
    """Declarative catalogs PUT (the payload is the complete desired set;
    anything omitted is deleted server-side).

    Entries whose first path segment isn't a curated root are excluded and
    reported as skipped rather than sent: `unknown_root` would reject the
    whole atomic payload, and legacy trees (e.g. "Render Setups/…") must not
    block publishing the valid subtree. Assets bound to a skipped catalog get
    flagged separately in the asset diff.
    """
    publishable = []
    skipped = []
    for entry in entries:
        path = entry.get("path") or ""
        root = path.split("/")[0]
        if root in roots:
            publishable.append(entry)
        else:
            skipped.append((path, f"'{root}' is not a curated Superhive root"))

    try:
        catalogs = client.put_catalogs(library_id, publishable)
    except ValidationError as error:
        raise _with_paths(error, publishable) from error
    return CatalogSyncResult(synced=catalogs, skipped=skipped)


def _with_paths(error: ValidationError, entries: list[dict]) -> ValidationError:
    """Map the server's per-entry {index, code, message} errors back to the
    offending entry's path so the report is actionable."""
    if not error.errors:
        return error
    lines = []
    for item in error.errors:
        index = item.get("index")
        path = None
        if index is not None and 0 <= index < len(entries):
            path = entries[index].get("path")
        prefix = f"{path}: " if path else ""
        code = item.get("code", "invalid")
        message = item.get("message", "")
        lines.append(f"{prefix}{code} — {message}")
    return ValidationError(
        "Catalog sync failed:\n" + "\n".join(lines), error.status, error.errors
    )
