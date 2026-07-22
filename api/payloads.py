"""Payload builders and the local-vs-server diff for publishing.

Everything here is plain data (no bpy, no HTTP) so the publish decisions are
unit-testable. Snapshots of Blender assets arrive as `LocalAsset` instances
built on the main thread.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

MAX_FILE_BYTES = 500 * 1024 * 1024
MAX_THUMBNAIL_BYTES = 2 * 1024 * 1024
MAX_TAGS = 50
MAX_TAG_LENGTH = 64


def sha256_file(path: Path | str, chunk_size: int = 1024 * 1024) -> str:
    """Server-format digest ("SHA256:<hex>") of a file's bytes."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            digest.update(chunk)
    return f"SHA256:{digest.hexdigest()}"


def clean_tags(tags: list[str]) -> list[str]:
    cleaned = [tag.strip()[:MAX_TAG_LENGTH] for tag in tags if tag and tag.strip()]
    return cleaned[:MAX_TAGS]


def major_minor(version: str) -> str:
    """ "4.2.1" / "5.2.0 Alpha" -> "4.2" / "5.2"."""
    parts = version.split(" ")[0].split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else version


@dataclass
class LocalAsset:
    """Plain-data snapshot of a marked asset, safe to cross thread boundaries."""

    name: str
    blend_path: str
    id_type: str = ""
    catalog_id: str = ""  # catalog uuid from the asset's Blender metadata
    catalog_path: str = ""  # resolved from cats.txt; "" = uncatalogued
    tags: list[str] = field(default_factory=list)
    description: str = ""
    author: str = ""
    license: str = ""
    copyright: str = ""
    created_blender_version: str = ""
    data_collection: str = (
        ""  # bpy.data collection name ("objects"), for subprocess scripts
    )
    server_id: str | None = None
    sha256: str | None = None
    size: int = 0


@dataclass
class PublishPlan:
    to_upload: list[LocalAsset] = field(default_factory=list)
    metadata_only: list[LocalAsset] = field(default_factory=list)
    unchanged: list[LocalAsset] = field(default_factory=list)
    renames: dict[tuple[str, str, str], str] = field(
        default_factory=dict
    )  # local identity -> server id
    server_only: list[dict] = field(default_factory=list)
    errors: list[tuple[LocalAsset, str]] = field(default_factory=list)


def build_asset_payload(
    local: LocalAsset,
    *,
    file_json: dict | None = None,
    thumbnail_json: dict | None = None,
    previous_asset_id: str | None = None,
) -> dict:
    payload: dict = {"name": local.name}
    if local.id_type:
        payload["id_type"] = local.id_type
    # Catalogs bind by uuid, not path: the declarative catalog sync has already
    # adopted the local cats.txt uuids, and catalog_path's find-or-create would
    # mint a diverging server-side uuid.
    if local.catalog_id:
        payload["catalog_uuid"] = local.catalog_id
    for key in ("description", "author", "license", "copyright"):
        value = getattr(local, key)
        if value:
            payload[key] = value
    tags = clean_tags(local.tags)
    if tags:
        payload["tags"] = tags
    # bl_version_min is deliberately omitted — the server reads it from the
    # .blend header; file_blender_version is only the fallback for undecodable
    # files.
    if local.created_blender_version:
        payload["file_blender_version"] = major_minor(local.created_blender_version)
    if previous_asset_id:
        payload["previous_asset_id"] = previous_asset_id
    if file_json:
        payload["file"] = file_json
    if thumbnail_json:
        payload["thumbnail"] = thumbnail_json
    return payload


def build_catalog_entries(catalogs: list[tuple[str, str, str]]) -> list[dict]:
    """[(uuid, path, simple_name)] -> declarative catalogs PUT entries."""
    return [
        {"uuid": uuid, "path": path, "simple_name": simple_name}
        for uuid, path, simple_name in catalogs
    ]


def local_identity(asset: LocalAsset) -> tuple[str, str, str]:
    """The server's asset identity: (catalog, id_type, case-insensitive name)."""
    return (asset.catalog_id or "", asset.id_type or "", asset.name.casefold())


def remote_identity(remote: dict) -> tuple[str, str, str]:
    return (
        remote.get("catalog_uuid") or "",
        remote.get("id_type") or "",
        remote["name"].casefold(),
    )


def metadata_matches(local: LocalAsset, remote: dict) -> bool:
    """Would a metadata-only upsert change anything the server stores?"""
    if local.name != remote.get("name"):  # case change is a real rename
        return False
    if local.id_type and local.id_type != remote.get("id_type"):
        return False
    if (local.catalog_id or None) != remote.get("catalog_uuid"):
        return False
    if sorted(clean_tags(local.tags)) != sorted(remote.get("tags") or []):
        return False
    for key in ("description", "author", "license", "copyright"):
        if (getattr(local, key) or "") != (remote.get(key) or ""):
            return False
    return True


def diff_assets(
    local: list[LocalAsset],
    remote: list[dict],
    roots: list[str],
    name_to_server_id: dict[str, str],
) -> PublishPlan:
    """Decide, per local asset, what (if anything) to send.

    Identity is the server's: (catalog, id_type, case-insensitive name) within
    the library — the same name may exist in different catalogs. A local asset
    whose identity is absent remotely but whose sidecar-known server id still
    exists is a rename or catalog move (previous_asset_id). Server assets no
    local asset accounts for are reported, never deleted.
    """
    plan = PublishPlan()
    remote_by_key = {remote_identity(a): a for a in remote}
    remote_by_id = {a["id"]: a for a in remote}

    # Identity collisions among the local assets themselves: the server would
    # silently fold them into one asset, so refuse both.
    by_key: dict[tuple[str, str, str], list[LocalAsset]] = {}
    for asset in local:
        by_key.setdefault(local_identity(asset), []).append(asset)
    collided = {key for key, group in by_key.items() if len(group) > 1}
    for key in sorted(collided):
        names = ", ".join(f"'{a.name}'" for a in by_key[key])
        for asset in by_key[key]:
            plan.errors.append(
                (
                    asset,
                    f"Duplicate asset ({names}): same name ignoring case, same"
                    " type, same catalog — rename or re-catalog one and"
                    " re-publish",
                )
            )

    matched_remote_ids: set[str] = set()

    def classify(asset: LocalAsset, existing: dict, renamed: bool):
        matched_remote_ids.add(existing["id"])
        remote_sha = (existing.get("file") or {}).get("sha256")
        if asset.sha256 and asset.sha256 == remote_sha:
            if renamed or not metadata_matches(asset, existing):
                plan.metadata_only.append(asset)
            else:
                plan.unchanged.append(asset)
        else:
            plan.to_upload.append(asset)

    # Pass 1: validation + direct identity matches, reserving their server ids.
    pending: list[LocalAsset] = []
    for asset in local:
        if local_identity(asset) in collided:
            continue
        if asset.catalog_path and asset.catalog_path.split("/")[0] not in roots:
            plan.errors.append(
                (
                    asset,
                    f"Catalog '{asset.catalog_path}' is not under a curated"
                    " Superhive root — re-catalog the asset and re-publish",
                )
            )
            continue
        if asset.size > MAX_FILE_BYTES:
            plan.errors.append(
                (
                    asset,
                    f"File is {asset.size / (1024 * 1024):.0f} MB — the"
                    " server caps asset files at 500 MB",
                )
            )
            continue

        existing = remote_by_key.get(local_identity(asset))
        if existing is not None:
            classify(asset, existing, renamed=False)
        else:
            pending.append(asset)

    # Pass 2: rename/catalog-move fallback via sidecar-known server ids. Ids
    # already matched in pass 1 are off-limits, and an id claimed by more than
    # one pending local is granted to none (never guess identity — uploading
    # as new is safe, moving the wrong server asset is not).
    claims: dict[str, list[LocalAsset]] = {}
    for asset in pending:
        server_id = asset.server_id or name_to_server_id.get(asset.name)
        if (
            server_id
            and server_id in remote_by_id
            and server_id not in matched_remote_ids
        ):
            claims.setdefault(server_id, []).append(asset)
        else:
            plan.to_upload.append(asset)
    for server_id, group in claims.items():
        if len(group) == 1:
            plan.renames[local_identity(group[0])] = server_id
            classify(group[0], remote_by_id[server_id], renamed=True)
        else:
            plan.to_upload.extend(group)

    plan.server_only = [a for a in remote if a["id"] not in matched_remote_ids]
    return plan
