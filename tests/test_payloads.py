import hashlib

from api.payloads import (
    MAX_FILE_BYTES,
    LocalAsset,
    build_asset_payload,
    build_catalog_entries,
    clean_tags,
    diff_assets,
    local_identity,
    major_minor,
    metadata_matches,
    sha256_file,
)

ROOTS = ["Materials", "Models", "HDRIs"]


def make_local(name="Chair", **kwargs):
    defaults = dict(
        name=name,
        blend_path=f"/lib/{name}.blend",
        id_type="OBJECT",
        catalog_id="cat-uuid-1",
        catalog_path="Models/Furniture",
        tags=["prop"],
        description="A chair",
        author="Ann",
        license="Standard Royalty Free",
        copyright="2026 Ann",
        sha256="SHA256:aaa",
        size=1024,
    )
    defaults.update(kwargs)
    return LocalAsset(**defaults)


def make_remote(name="Chair", **kwargs):
    remote = {
        "id": f"srv-{name.casefold()}",
        "name": name,
        "id_type": "OBJECT",
        "status": "published",
        "catalog_uuid": "cat-uuid-1",
        "tags": ["prop"],
        "description": "A chair",
        "author": "Ann",
        "license": "Standard Royalty Free",
        "copyright": "2026 Ann",
        "file": {"sha256": "SHA256:aaa", "size": 1024},
    }
    remote.update(kwargs)
    return remote


def test_sha256_file(tmp_path):
    f = tmp_path / "x.blend"
    f.write_bytes(b"BLENDER-data")
    expected = hashlib.sha256(b"BLENDER-data").hexdigest()
    assert sha256_file(f) == f"SHA256:{expected}"


def test_clean_tags_caps_count_and_length():
    tags = [f"tag{i}" for i in range(60)] + ["", "  "]
    cleaned = clean_tags(tags)
    assert len(cleaned) == 50
    assert clean_tags(["x" * 100]) == ["x" * 64]
    assert clean_tags(["  padded  "]) == ["padded"]


def test_major_minor():
    assert major_minor("4.2.1") == "4.2"
    assert major_minor("5.2.0 Alpha") == "5.2"
    assert major_minor("5") == "5"


def test_build_asset_payload_full():
    local = make_local(created_blender_version="4.2.1")
    payload = build_asset_payload(
        local,
        file_json={"id": "f1", "storage": "cache", "metadata": {}},
        thumbnail_json={"id": "t1", "storage": "public_cache", "metadata": {}},
        previous_asset_id="srv-old",
    )
    assert payload["name"] == "Chair"
    assert payload["catalog_uuid"] == "cat-uuid-1"
    assert payload["file_blender_version"] == "4.2"
    assert payload["previous_asset_id"] == "srv-old"
    assert "bl_version_min" not in payload
    assert "catalog_path" not in payload
    assert payload["file"]["id"] == "f1"
    assert payload["thumbnail"]["id"] == "t1"


def test_build_asset_payload_omits_blanks():
    local = make_local(
        description="", author="", license="", copyright="", tags=[], catalog_id=""
    )
    payload = build_asset_payload(local)
    for key in (
        "description",
        "author",
        "license",
        "copyright",
        "tags",
        "catalog_uuid",
        "file",
        "thumbnail",
        "previous_asset_id",
    ):
        assert key not in payload


def test_build_catalog_entries():
    entries = build_catalog_entries([("u1", "Models/Chairs", "Models-Chairs")])
    assert entries == [
        {"uuid": "u1", "path": "Models/Chairs", "simple_name": "Models-Chairs"}
    ]


def test_metadata_matches_ignores_tag_order_and_none_vs_blank():
    local = make_local(tags=["b", "a"], description="")
    remote = make_remote(tags=["a", "b"], description=None)
    assert metadata_matches(local, remote)


def test_metadata_matches_case_change_is_a_mismatch():
    assert not metadata_matches(make_local(name="chair"), make_remote(name="Chair"))


def test_diff_new_asset_uploads():
    plan = diff_assets([make_local()], [], ROOTS, {})
    assert [a.name for a in plan.to_upload] == ["Chair"]
    assert not plan.errors


def test_diff_unchanged():
    plan = diff_assets([make_local()], [make_remote()], ROOTS, {})
    assert [a.name for a in plan.unchanged] == ["Chair"]
    assert not plan.to_upload and not plan.metadata_only
    assert not plan.server_only


def test_diff_changed_hash_uploads():
    plan = diff_assets([make_local(sha256="SHA256:bbb")], [make_remote()], ROOTS, {})
    assert [a.name for a in plan.to_upload] == ["Chair"]


def test_diff_metadata_only():
    plan = diff_assets(
        [make_local(description="New words")], [make_remote()], ROOTS, {}
    )
    assert [a.name for a in plan.metadata_only] == ["Chair"]
    assert not plan.to_upload


def test_diff_rename_via_sidecar_id():
    remote = make_remote(name="OldChair")
    local = make_local(name="NewChair")
    plan = diff_assets([local], [remote], ROOTS, {"NewChair": remote["id"]})
    assert plan.renames == {local_identity(local): remote["id"]}
    # hash matches, so the rename rides a metadata-only upsert
    assert [a.name for a in plan.metadata_only] == ["NewChair"]
    assert not plan.server_only


def test_diff_rename_with_changed_file_uploads():
    remote = make_remote(name="OldChair")
    local = make_local(name="NewChair", sha256="SHA256:bbb")
    plan = diff_assets([local], [remote], ROOTS, {"NewChair": remote["id"]})
    assert plan.renames == {local_identity(local): remote["id"]}
    assert [a.name for a in plan.to_upload] == ["NewChair"]


def test_diff_server_only_reported_never_deleted():
    plan = diff_assets([], [make_remote(name="Ghost")], ROOTS, {})
    assert [a["name"] for a in plan.server_only] == ["Ghost"]


def test_diff_oversize_rejected():
    plan = diff_assets([make_local(size=MAX_FILE_BYTES + 1)], [], ROOTS, {})
    assert not plan.to_upload
    assert "500 MB" in plan.errors[0][1]


def test_diff_non_curated_root_rejected():
    plan = diff_assets([make_local(catalog_path="Render Setups/Studio")], [], ROOTS, {})
    assert not plan.to_upload
    assert "curated" in plan.errors[0][1]


def test_diff_uncatalogued_is_fine():
    plan = diff_assets([make_local(catalog_path="", catalog_id="")], [], ROOTS, {})
    assert [a.name for a in plan.to_upload] == ["Chair"]


def test_diff_case_insensitive_local_collision():
    # Same catalog, same type, names differing only by case: identical
    # server identity, so both are refused.
    plan = diff_assets(
        [make_local(name="Chair"), make_local(name="chair")], [], ROOTS, {}
    )
    assert len(plan.errors) == 2
    assert not plan.to_upload


def test_diff_same_name_different_catalogs_no_collision():
    plan = diff_assets(
        [
            make_local(catalog_id="cat-2k", catalog_path="Models/Furniture/2K"),
            make_local(catalog_id="cat-4k", catalog_path="Models/Furniture/4K"),
        ],
        [],
        ROOTS,
        {},
    )
    assert not plan.errors
    assert len(plan.to_upload) == 2


def test_diff_same_name_two_catalogs_both_match():
    locals_ = [
        make_local(catalog_id="cat-2k", catalog_path="Models/Furniture/2K"),
        make_local(
            catalog_id="cat-4k", catalog_path="Models/Furniture/4K", sha256="SHA256:bbb"
        ),
    ]
    remotes = [
        make_remote(id="srv-2k", catalog_uuid="cat-2k"),
        make_remote(
            id="srv-4k",
            catalog_uuid="cat-4k",
            file={"sha256": "SHA256:bbb", "size": 1024},
        ),
    ]
    plan = diff_assets(locals_, remotes, ROOTS, {})
    assert len(plan.unchanged) == 2
    assert not plan.to_upload and not plan.metadata_only
    assert not plan.server_only


def test_diff_catalog_move_is_a_rename():
    remote = make_remote(name="Oak", catalog_uuid="cat-2k")
    local = make_local(
        name="Oak", catalog_id="cat-4k", catalog_path="Models/Furniture/4K"
    )
    plan = diff_assets([local], [remote], ROOTS, {"Oak": remote["id"]})
    assert plan.renames == {local_identity(local): remote["id"]}
    assert [a.name for a in plan.metadata_only] == ["Oak"]
    assert not plan.server_only


def test_diff_new_duplicate_does_not_steal_id():
    # Remote Oak lives in cat-2k; locally there is the unchanged Oak in cat-2k
    # AND a brand-new Oak in cat-4k. The sidecar's name map points at the
    # existing server asset — the new duplicate must NOT claim its id (that
    # would move the server asset), it must upload as new.
    remote = make_remote(name="Oak", catalog_uuid="cat-2k")
    existing = make_local(
        name="Oak", catalog_id="cat-2k", catalog_path="Models/Furniture/2K"
    )
    new = make_local(
        name="Oak", catalog_id="cat-4k", catalog_path="Models/Furniture/4K"
    )
    plan = diff_assets([existing, new], [remote], ROOTS, {"Oak": remote["id"]})
    assert [a.catalog_id for a in plan.unchanged] == ["cat-2k"]
    assert [a.catalog_id for a in plan.to_upload] == ["cat-4k"]
    assert plan.renames == {}
    assert not plan.server_only


def test_diff_ambiguous_claim_uploads_both():
    # Two pending locals resolve to the same unclaimed server id: identity is
    # ambiguous, so neither gets it — both upload as new and the remote is
    # reported server_only.
    remote = make_remote(name="Oak", catalog_uuid="cat-old", id="srv-oak")
    locals_ = [
        make_local(
            name="Oak",
            catalog_id="cat-2k",
            catalog_path="Models/Furniture/2K",
            server_id="srv-oak",
        ),
        make_local(
            name="Oak",
            catalog_id="cat-4k",
            catalog_path="Models/Furniture/4K",
            server_id="srv-oak",
        ),
    ]
    plan = diff_assets(locals_, [remote], ROOTS, {})
    assert len(plan.to_upload) == 2
    assert plan.renames == {}
    assert [a["id"] for a in plan.server_only] == ["srv-oak"]
