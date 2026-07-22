"""Publish-pipeline steps that are pure data + HTTP (no bpy).

The Blender-side operators snapshot their data on the main thread and hand it
here; everything in this module may run on a worker thread.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import payloads
from .client import (
    ApiError,
    AuthError,
    NetworkError,
    NotFoundError,
    ScopeError,
    SuperhiveClient,
    ValidationError,
)
from .payloads import LocalAsset, PublishPlan


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


@dataclass
class AssetResult:
    """One row of the publish report. `status` is one of: uploaded, metadata,
    unchanged, processing, published, pending, rejected, error, server_only,
    warning."""

    name: str
    status: str
    message: str = ""
    server_id: str = ""


class _Cancelled(Exception):
    pass


class PublishJob:
    """The whole library-publish state machine. Runs on a worker thread; the
    operator's modal handler reads the observable attributes below and paints
    them into progress bars.

    Everything passed in is plain data or thread-safe callables — no bpy
    handles cross into here.
    """

    POLL_BUDGET = 600.0
    POLL_CAP = 30.0

    def __init__(
        self,
        client: SuperhiveClient,
        library_id: str,
        local_assets: list[LocalAsset],
        catalog_entries: list[dict],
        roots: list[str],
        name_to_server_id: dict[str, str],
        thumbnail_extractor: Callable[[LocalAsset], Path | None] | None = None,
        pack_fn: Callable[[str], None] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        report_server_only: bool = True,
    ):
        self.client = client
        self.library_id = library_id
        self.local_assets = local_assets
        self.catalog_entries = catalog_entries
        self.roots = roots
        self.name_to_server_id = name_to_server_id
        self.thumbnail_extractor = thumbnail_extractor
        self.pack_fn = pack_fn
        self._sleep = sleep
        self.report_server_only = report_server_only

        # ---- observable state (worker writes, modal reads) ----
        self.phase = "Starting"
        self.current_asset = ""
        self.assets_done = 0
        self.assets_total = 0
        self.bytes_sent = 0
        self.bytes_total = 0
        self.results: list[AssetResult] = []
        self.uploaded_ids: dict[str, str] = {}  # local name -> server asset id
        self.cancel_requested = False
        self.cancelled = False
        self.fatal_error: str | None = None
        self.binding_gone = False
        self.updated = False

        self._bytes_before = 0

    # ---- lifecycle ----

    def run(self):
        try:
            self._set_phase("Syncing catalogs")
            self._sync_catalogs()
            self._set_phase("Hashing local files")
            self._hash_local()
            self._set_phase("Fetching Superhive listing")
            remote = self.client.list_assets(self.library_id)
            plan = payloads.diff_assets(
                self.local_assets, remote, self.roots, self.name_to_server_id
            )
            self._record_plan(plan)
            self._publish_assets(plan)
            self._poll_processing()
            self._set_phase("Done")
        except _Cancelled:
            self.cancelled = True
            self._set_phase("Cancelled")
        except NotFoundError:
            self.binding_gone = True
            self.fatal_error = (
                "The linked Superhive library no longer exists — the link was"
                " cleared; run Publish again to create or pick one"
            )
        except AuthError:
            self.fatal_error = (
                "Invalid or revoked API token — fix it in the Bkeeper add-on"
                " preferences"
            )
        except ScopeError:
            self.fatal_error = (
                "This token can't publish — it needs the assets:write scope"
                " (recreate it with the 'Asset publishing (BeeKeeper)' preset)"
            )
        except NetworkError as error:
            if self.cancel_requested:
                # aborting a stream mid-upload surfaces as a transport error
                self.cancelled = True
                self._set_phase("Cancelled")
            else:
                self.fatal_error = (
                    f"{error} — re-run Publish; already-uploaded assets are"
                    " skipped by the hash diff"
                )
        except ApiError as error:
            self.fatal_error = str(error)
        except Exception as error:  # never let the worker thread die silently
            self.fatal_error = f"Unexpected error: {error!r}"
        finally:
            self.updated = True

    def _set_phase(self, phase: str):
        self.phase = phase
        self.updated = True

    def _check_cancel(self):
        if self.cancel_requested:
            raise _Cancelled

    # ---- phases ----

    def _sync_catalogs(self):
        result = sync_catalogs(
            self.client, self.library_id, self.catalog_entries, self.roots
        )
        for path, reason in result.skipped:
            self.results.append(
                AssetResult(path, "warning", f"Catalog kept local-only: {reason}")
            )

    def _hash_local(self):
        hashes: dict[str, tuple[str, int]] = {}
        missing: list[LocalAsset] = []
        for asset in self.local_assets:
            self._check_cancel()
            path = asset.blend_path
            if path not in hashes:
                self.current_asset = asset.name
                self.updated = True
                try:
                    if self.pack_fn:
                        self.pack_fn(path)  # must precede hashing (rewrites the file)
                    hashes[path] = (
                        payloads.sha256_file(path),
                        Path(path).stat().st_size,
                    )
                except OSError as error:
                    hashes[path] = (None, error)
            digest, size = hashes[path]
            if digest is None:
                self.results.append(
                    AssetResult(asset.name, "error", f"Could not read file: {size}")
                )
                missing.append(asset)
            else:
                asset.sha256 = digest
                asset.size = size
        for asset in missing:
            self.local_assets.remove(asset)

    def _record_plan(self, plan: PublishPlan):
        for asset in plan.unchanged:
            self.results.append(AssetResult(asset.name, "unchanged"))
        for asset, message in plan.errors:
            self.results.append(AssetResult(asset.name, "error", message))
        if self.report_server_only:
            for remote in plan.server_only:
                self.results.append(
                    AssetResult(
                        remote["name"],
                        "server_only",
                        "Exists on Superhive but not in this library — never"
                        " deleted automatically",
                        server_id=remote["id"],
                    )
                )
        self.updated = True

    def _publish_assets(self, plan: PublishPlan):
        work = [(asset, True) for asset in plan.to_upload]
        work += [(asset, False) for asset in plan.metadata_only]
        self.assets_total = len(work)
        self.bytes_total = sum(asset.size for asset in plan.to_upload)
        self.updated = True

        for asset, with_file in work:
            self._check_cancel()
            self.current_asset = asset.name
            self._set_phase(
                f"Uploading {asset.name}" if with_file else f"Updating {asset.name}"
            )
            try:
                result = self._publish_one(
                    asset,
                    with_file=with_file,
                    previous_asset_id=plan.renames.get(asset.name),
                )
            except ValidationError as error:
                message = str(error)
                if error.errors:
                    message = "; ".join(
                        f"{e.get('code', 'invalid')}: {e.get('message', '')}"
                        for e in error.errors
                    )
                result = AssetResult(asset.name, "error", message)
            self.results.append(result)
            self.assets_done += 1
            self.updated = True

    def _publish_one(
        self, asset: LocalAsset, *, with_file: bool, previous_asset_id: str | None
    ) -> AssetResult:
        file_json = None
        thumbnail_json = None
        thumbnail_warning = ""

        if with_file:
            thumbnail_json, thumbnail_warning = self._upload_thumbnail(asset)

            ticket = self.client.presign(
                Path(asset.blend_path).name, "application/x-blend", "file"
            )
            file_json = self.client.upload_to_presigned(
                ticket, asset.blend_path, progress_cb=self._on_upload_progress
            )
            self._bytes_before += asset.size
            self.bytes_sent = self._bytes_before
            self.updated = True

        payload = payloads.build_asset_payload(
            asset,
            file_json=file_json,
            thumbnail_json=thumbnail_json,
            previous_asset_id=previous_asset_id,
        )
        response = self.client.upsert_asset(self.library_id, payload)

        server_id = response.get("id", "")
        if server_id:
            self.uploaded_ids[asset.name] = server_id
        status = response.get("status") or "processing"
        if not with_file:
            status = "metadata" if status in ("published", "pending") else status
        return AssetResult(asset.name, status, thumbnail_warning, server_id=server_id)

    def _upload_thumbnail(self, asset: LocalAsset) -> tuple[dict | None, str]:
        """Extract and upload the asset's preview; failures only warn — the
        upsert proceeds without a thumbnail."""
        if self.thumbnail_extractor is None:
            return None, ""
        try:
            thumb_path = self.thumbnail_extractor(asset)
        except Exception as error:
            return None, f"Thumbnail extraction failed: {error}"
        if thumb_path is None:
            return None, "No preview found in the .blend — published without thumbnail"
        size = Path(thumb_path).stat().st_size
        if size > payloads.MAX_THUMBNAIL_BYTES:
            return None, (
                f"Thumbnail is {size / (1024 * 1024):.1f} MB (max 2 MB) —"
                " published without thumbnail"
            )
        suffix = Path(thumb_path).suffix.lstrip(".") or "webp"
        ticket = self.client.presign(
            Path(thumb_path).name, f"image/{suffix}", "thumbnail"
        )
        return self.client.upload_to_presigned(ticket, thumb_path), ""

    def _on_upload_progress(self, sent: int, total: int):
        self.bytes_sent = self._bytes_before + sent
        self.updated = True
        # a cancel during a large upload should not wait for the file to finish
        if self.cancel_requested:
            raise _Cancelled

    def _poll_processing(self):
        pending = {
            r.name: r for r in self.results if r.status == "processing" and r.server_id
        }
        if not pending:
            return

        started = time.monotonic()
        interval = max(3.0, 0.8 * len(pending))
        while pending and time.monotonic() - started < self.POLL_BUDGET:
            self._check_cancel()
            self._set_phase(f"Waiting on file scans ({len(pending)} left)")
            self._sleep(interval)
            for name, result in list(pending.items()):
                self._check_cancel()
                asset = self.client.get_asset(self.library_id, result.server_id)
                status = asset.get("status")
                if status == "processing":
                    continue
                result.status = status or "processing"
                if status == "rejected":
                    reasons = asset.get("rejection_reasons") or []
                    result.message = (
                        "; ".join(
                            f"{r.get('code', '')}: {r.get('message', '')}"
                            for r in reasons
                        )
                        or "Rejected by the file scan"
                    )
                del pending[name]
                self.updated = True
            interval = min(interval * 1.5, self.POLL_CAP)

        for result in pending.values():
            result.status = "processing"
            result.message = (
                "Still scanning after 10 minutes — check the library on Superhive"
                " or re-run Publish later"
            )
        self.updated = True
