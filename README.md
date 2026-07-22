# BeeKeeper (superhive-blender-addon)

A Blender extension for creators on [Superhive](https://superhivemarket.com/) (formerly Blender Market) to create, manage, and publish asset libraries — directly from Blender to the Superhive assets API.

> This add-on is in active development by Autotroph and True VFX.

## What it does

- **Local library management** — create "hive" asset libraries (one self-contained `.blend` per asset), mark and catalog assets, batch-edit metadata (name, description, author, license, copyright, tags), and render or extract thumbnails.
- **Publish to Superhive** — one click syncs the whole library: the catalog tree is synced first (your catalog UUIDs are preserved end-to-end), then only new or changed assets upload (diffed by file hash against the server). Renames are tracked, interrupted publishes resume safely, and a report shows every asset's outcome — including server scan rejections with reasons.
- **Per-asset publish** — push a single asset from the asset browser side panel without re-syncing everything.
- **Import pipelines** — build assets from directories of `.blend`, OBJ, FBX, and USD files.

## Getting started

1. Install the extension zip (see Releases) via `Edit > Preferences > Get Extensions > Install from Disk`, or build it yourself (below).
2. On Superhive, create an API token under `Account > API Tokens` using the **"Asset publishing (BeeKeeper)"** preset. Tokens are shown once.
3. Paste the token into the add-on preferences (`Superhive Account` box) and click **Verify Token**. Make sure Blender's *Allow Online Access* (Preferences > System > Network) is enabled.
4. In the Asset Browser, switch the header dropdown to **Bkeeper**, build your library, then use the Bkeeper menu → **Publish to Superhive**. The first publish asks whether to create a new Superhive library or link an existing one; the link is remembered in a `.superhive.json` file inside the library directory.

Notes:
- Catalog paths must start with one of Superhive's curated roots (Materials, Models, HDRIs, Node Groups, Brushes, Poses & Animations, Worlds — fetched live from the server). Use *Add Categories to Library* to seed them. Catalogs outside these roots stay local-only and are reported.
- Large first publishes take a few minutes by design — uploads go direct to storage, but API calls are paced to respect the server's rate limits.
- Assets you delete locally are **never** deleted from Superhive automatically; the publish report lists them with an explicit delete action.

## [Releases](https://github.com/CGCookie/superhive-blender-addon/releases)

Release builds can be found on the [release page](https://github.com/CGCookie/superhive-blender-addon/releases). Minor releases will include bug fixes, major releases will include features. Please check the release notes.

## [Documentation](https://github.com/CGCookie/superhive-blender-addon/wiki)

* [Installation](https://github.com/CGCookie/superhive-blender-addon/wiki/Installation)
* [Preferences](https://github.com/CGCookie/superhive-blender-addon/wiki/User-Preferences)
* [Using BKeeper](https://github.com/CGCookie/superhive-blender-addon/wiki/Using-BKeeper)

## Development

- The `api/` package (HTTP client, publish pipeline, diff planner) is deliberately bpy-free and unit-tested: `python -m pytest tests/` (needs `pip install pytest` in a venv at the repo root).
- Lint/format with `ruff` (config in `ruff.toml`).
- Build the installable zip: `blender --command extension build --output-dir <dir>` from the repo root. The bundled `requests` wheels ship inside the zip; regenerate them with `python wheels/download_wheels.py` when bumping dependencies.
- The server contract is the OpenAPI spec at `https://superhivemarket.com/api-docs` (`/api/v1/assets` namespace).
