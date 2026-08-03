# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**BeeKeeper** (manifest id `superhive_creator_extension`) is a Blender extension (4.2+ extension platform, not a legacy add-on) for Superhive market creators to create, manage, and publish asset libraries. Originally developed under contract by True VFX as `superhive-blender-addon`; now a native Superhive tool owned by Autotroph/CGCookie. Distribution will be through Superhive's own extensions repository so the add-on and server API can ship in lockstep.

**Current state (2026-07-21, branch `1.0-Alpha`):** the add-on manages local "hive" libraries (one self-contained `.blend` per asset, uuid-preserving `blender_assets.cats.txt` round-trip, `sh_*` metadata editing with dirty flags) **and is wired to the Superhive assets API**. Publishing works end-to-end: `bkeeper.publish_library` (header menu "Publish to Superhive") syncs catalogs declaratively then uploads only new/changed assets (sha256 diff against the server listing), and `bkeeper.publish_asset` does single-asset pushes from the side panel. The legacy zip export survives behind the Display Extras pref. Remaining: manual e2e against a local markets-rails (checklist in the repo plan), then real-creator beta.

## Repo layout

- `__init__.py` — extension entry; `_call_globals` pattern registers every imported submodule that has `register`
- `blender_manifest.toml` — manifest (id `bkeeper`, v0.1.0, `blender_version_min = "4.2.0"`, `wheels = [requests + pure-python deps]`, network+files permissions)
- `api/` — **bpy-free** Superhive API layer (unit-tested without Blender): `client.py` (paced `SuperhiveClient`, typed errors, 429 retries, streaming presigned uploads), `payloads.py` (`LocalAsset` snapshots, sha256, `diff_assets` publish planner), `publish.py` (`sync_catalogs`, `PublishJob` state machine), `sidecar.py` (`.superhive.json` library↔server binding + name→server-id rename map), `taxonomy.py` (cached curated roots)
- `hive_mind.py` — licenses/tags enums (still static) + `ROOTS`/`load_roots()` (server-fetched) + `license_to_server_string`; the hardcoded category tree is deprecated
- `ops/` — operators; notably `publish_ops.py` (`publish_library`, `publish_asset`, `bind_library`, `sync_catalogs`, `delete_server_asset`, publish report), `api_ops.py` (`verify_api_token`, shared `online_access_poll`), `add_to_library.py` (per-asset blend split), `asset_ops.py` (Save Changes via headless-Blender `update_asset.py`; re-keys the sidecar on rename)
- `settings/` — per-asset `sh_*` props on `AssetMetaData` (`asset.py`), scene state + progress bars + publish results (`scene.py`)
- `stand_alone_scripts/` — headless-Blender subprocess scripts (`update_asset.py`, `save_out_previews.py`, `pack_files.py` — packs AND saves, …)
- `ui/` — asset browser panels/menus + prefs (`SH_AddonPreferences`: Superhive Account box with `server_url`, `api_token`, verify button)
- `wheels/` — committed universal wheels + `download_wheels.py` regenerator
- `tests/` — pytest suite for `api/` (no bpy). `tests/pytest.ini` anchors rootdir there so pytest never imports the repo-root `__init__.py` (which imports bpy).

## Development workflow

- Tests: `.venv/bin/python -m pytest tests/` (venv at repo root, `pip install pytest ruff`). Keep `api/` bpy-free so this stays possible.
- Lint/format: `.venv/bin/ruff check` / `ruff format` (repo ruff.toml).
- Build: `blender --command extension build --output-dir __ignore__/builds` (wheels ship in the zip; `.venv`/`tests`/`CLAUDE.md` are excluded).
- Smoke: `blender -b --factory-startup --online-mode --command extension install-file --repo user_default --enable <zip>` registers everything headless.
- Local server: markets-rails at `http://localhost:3000` (`just start`); set prefs Server URL + a token from /account/api_tokens.

## Publish flow (how the pieces fit)

1. `bkeeper.publish_library`: prefs client → sidecar binding (else `bind_library` create-or-pick dialog, which re-invokes) → main-thread `LocalAsset` snapshot (SAVED blend state; unsaved sh_* edits become report warnings) → `PublishJob` on a worker thread.
2. `PublishJob` phases: declarative catalog PUT (cats.txt uuids adopted server-side; non-curated roots prefiltered to warnings) → optional pack (before hashing!) → sha256 → GET server assets → diff (new/changed/metadata-only/renames via sidecar ids/unchanged/server-only) → per asset: thumbnail extract (subprocess, webp ≤2MB, failure = warning) + presigned uploads + upsert → poll `processing` until published/rejected (10 min budget). **(Stale vs the 2026-07/08 server changes: the PUT is now an additive mapping report, and unfiled assets finish `pending`, which this poll loop doesn't expect — see the catalog rules TODO below.)**
3. Everything is idempotent — re-running after any failure skips completed work via the hash diff. Server-only assets are never auto-deleted (explicit report-row delete only). Client paces ~1 req/s (server throttles: 300/5min assets + 100/min general).

## The server contract (what the API work is building toward)

The Rails app (`~/Web/markets-rails`, branch `feature/assets-project`, PR CGCookie/markets-rails#2911) exposes the write API this add-on must drive. Hand-maintained OpenAPI spec at `/api-docs` (swagger/v1/swagger.yaml in that repo) is the source of truth.

### Auth

- Header tokens (`shk_` prefix), sent as `SH-Auth-Token: <token>` or `Authorization: Bearer <token>`. Scopes: publishing needs `assets:read` + `assets:write` — creators mint one via /account/api_tokens with the **"Asset publishing"** preset (renamed from "Asset publishing (BeeKeeper)" 2026-08-03; the API is now documented client-neutral). Tokens are shown once; store securely in add-on preferences.
- The API is token-only (a Devise session cannot use it). Rate limit: 300 requests / 5 min per token.

### Endpoints (`/api/v1/assets` namespace)

- Library CRUD (delete refuses while the library is attached to a product).
- `GET /uploads/presign` — token-auth S3 presign: `.blend` files go to the private bucket, thumbnails to the public bucket. (The site's `/s3/params` endpoints are session-gated — never use them from the add-on.)
- `POST .../assets` — **name-keyed upsert**: asset identity is (library, **catalog**, `id_type`, case-insensitive name) — the same name may exist in different catalogs (2026-07-22 change; Blender names are unique per file, not per library). Re-posting a name replaces in place; supply `catalog_uuid`/`catalog_path` to disambiguate same-name assets in different catalogs (a catalog-less upsert resolves the oldest name match). `previous_asset_id` renames. New assets require a file; replaces may be metadata-only. Catalog binding is central-taxonomy-only (2026-07-29): a `catalog_uuid` matching a central catalog files the asset (depth ≥ 2 or `catalog_not_selectable` error); an **unknown uuid is soft-accepted as detected context** — the asset stays *unfiled* and waits in the web Filing tab; a `catalog_path` must resolve to a central catalog or the upsert fails with `unknown_catalog`.
- `PUT .../catalogs` — **additive mapping report** (2026-07-29; formerly declarative desired-set sync — **nothing is deleted anymore**). Send the local catalog set from `blender_assets.cats.txt`; entries register as detected context and each comes back `{uuid, path, status: matched|unmapped, central_uuid}` with a `{matched, unmapped, assets_filed}` summary. `matched` = the uuid or path resolves to a central catalog (assets carrying it are filed automatically); `unmapped` = needs remapping in the web Filing tab. `GET .../catalogs` returns the full central taxonomy tree.
- Asset statuses: `processing → pending → published / rejected`. **Auto-publish on scan promote is now gated on central-catalog filing (2026-08-03):** a staged upload whose asset is filed to a central catalog publishes as before, but an *unfiled* asset lands `pending` with its file promoted and deliverable-to-the-owner, awaiting filing (web Filing tab, or a re-upsert with a central `catalog_uuid`) plus publish. So `pending` is a **successful terminal state** for the staged path, not a transient one — don't poll it as if publish is still coming.
- Rejections carry structured `rejection_reasons` `[{code, message}]` — render them to the creator.

### File requirements

- Each asset is one **self-contained** `.blend` (pack external references; Blender delivers per-asset files, no archives/linking).
- Server validates magic bytes (`BLENDER`, or zstd-compressed 4.2+ saves), size, SHA256. gzip (pre-3.0) is rejected — re-save on publish.
- `bl_version_min` is optional: the server reads the saving-Blender version from the file header and fills blanks (creator-supplied values always win). `file_blender_version` param covers undetectable files.
- Thumbnails: jpeg/png/webp ≤ 2 MB, uploaded via the public presign. Server derives a 256px thumb.
- Files uploaded through this add-on's staged path are **not** scanned by the Blender shim (that's the web-upload path only) — the add-on supplies all metadata itself.

### Catalog rules (central taxonomy, 2026-07-29)

- The customer-facing taxonomy is an **admin-curated central catalog tree** (`CentralCatalog` in Rails) — creators cannot create catalogs at all anymore. Valid filing targets are active central nodes at least **2 levels deep** (roots are headings, not targets). Fetch the tree via `GET .../catalogs`.
- The creator's own `blender_assets.cats.txt` catalogs are kept server-side only as *detected context* (labels for the Filing tab's bulk remap); they never reach customers. Still ship the real uuids — the server retro-binds unfiled assets by uuid when a mapping appears, and a creator marking assets with official central uuids directly is the zero-friction path.
- **TODO — BeeKeeper must grow central-catalog filing support** (2026-08-03, required now that unfiled uploads land `pending` instead of publishing): fetch the central tree, let the creator map their local catalogs (or pick a filing target per asset/catalog) before publish, send the central `catalog_uuid` on upserts, surface the PUT mapping report's `unmapped` entries, and treat `pending` publish results as "needs filing on the website" rather than failure or forever-processing. `PublishJob`'s poll loop (published/rejected in 10 min) and the publish report both assume the old auto-publish — update them.

### Related repos

- `~/Web/markets-rails` — the marketplace + API (Rails). Its CLAUDE.md and PR #2911 describe the full assets project.
- `~/Web/superhive-blender-shim` — server-side headless-Blender scanner for **web** uploads (Cloudflare Worker + Container). BeeKeeper never calls it, but its metadata extraction mirrors what this add-on should produce client-side.

## Conventions & cautions

- `sh_uuid` is minted client-side today (`uuid.uuid4()` in `asset_helper`) — reconcile with the server's identity model (name-keyed, not uuid-keyed) before leaning on it.
- **Asset identity (2026-07-22):** `payloads.diff_assets` keys the publish plan by the server's full identity — `(catalog_uuid, id_type, casefolded name)` via `local_identity`/`remote_identity` — so the same name in two catalogs (2K/4K variants) publishes fine. A catalog move is an identity change and rides `previous_asset_id`, same as a rename. The diff is two-pass: direct identity matches first, then sidecar-id claims for renames/moves — an id already matched, or claimed by more than one pending local, is never granted (a new duplicate must upload as new, not move the existing server asset). The sidecar `assets` map stays `{name: server_id}` (best-effort for duplicate names; the two-pass guard keeps stale entries harmless).
- `hive_mind.py`'s hardcoded licenses/tags/categories are placeholders; the TODOs say to fetch from the API. Server-side, tags are free strings (max 50/asset, 64 chars) and license is a free string.
- Local dev server: markets-rails runs at `http://localhost:3000` (`just start` in that repo); mint a dev token from /account/api_tokens. Make the API base URL configurable in preferences.
- Registration lists live in each package's `__init__.py` (`classes` tuples + `register/unregister`); follow that pattern for new modules.
