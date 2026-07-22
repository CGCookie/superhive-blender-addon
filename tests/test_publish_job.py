from pathlib import Path

from api.client import AuthError, NotFoundError, ValidationError
from api.payloads import LocalAsset, sha256_file
from api.publish import PublishJob

ROOTS = ["Materials", "Models"]


class StubClient:
    def __init__(self, remote=None, upsert_responses=None, poll_statuses=None):
        self.remote = remote or []
        self.upsert_responses = upsert_responses or []
        self.poll_statuses = poll_statuses or {}
        self.calls = []

    def put_catalogs(self, library_id, catalogs):
        self.calls.append(("put_catalogs", catalogs))
        return catalogs

    def list_assets(self, library_id):
        self.calls.append(("list_assets",))
        if isinstance(self.remote, Exception):
            raise self.remote
        return self.remote

    def presign(self, filename, content_type, target):
        self.calls.append(("presign", filename, target))
        return {"id": f"key-{filename}", "storage": "cache", "url": "u", "headers": {}}

    def upload_to_presigned(self, ticket, path, progress_cb=None):
        self.calls.append(("upload", ticket["id"]))
        size = Path(path).stat().st_size
        if progress_cb:
            progress_cb(size, size)
        return {"id": ticket["id"], "storage": ticket["storage"], "metadata": {}}

    def upsert_asset(self, library_id, payload):
        self.calls.append(("upsert", payload))
        response = self.upsert_responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def get_asset(self, library_id, asset_id):
        self.calls.append(("get_asset", asset_id))
        status = self.poll_statuses[asset_id].pop(0)
        if isinstance(status, dict):
            return status
        return {"id": asset_id, "status": status}


def make_blend(tmp_path, name="Chair"):
    blend = tmp_path / f"{name}.blend"
    blend.write_bytes(b"BLENDER-fake-" + name.encode())
    return blend


def make_asset(blend, **kwargs):
    defaults = dict(
        name=blend.stem,
        blend_path=str(blend),
        id_type="OBJECT",
        catalog_id="cat-u1",
        catalog_path="Models/Chairs",
        tags=["prop"],
        description="d",
        author="a",
        license="Standard Royalty Free",
        data_collection="objects",
    )
    defaults.update(kwargs)
    return LocalAsset(**defaults)


def make_job(client, assets, thumbnail_extractor=None, **kwargs):
    return PublishJob(
        client,
        "lib-1",
        assets,
        [{"uuid": "cat-u1", "path": "Models/Chairs", "simple_name": "Models-Chairs"}],
        ROOTS,
        kwargs.pop("name_to_server_id", {}),
        thumbnail_extractor=thumbnail_extractor,
        sleep=lambda s: None,
        **kwargs,
    )


def test_new_asset_uploads_and_publishes(tmp_path):
    blend = make_blend(tmp_path)
    thumb = tmp_path / "Chair_preview.webp"
    thumb.write_bytes(b"webp")
    client = StubClient(
        upsert_responses=[{"id": "srv-1", "status": "processing"}],
        poll_statuses={"srv-1": ["processing", "published"]},
    )
    job = make_job(client, [make_asset(blend)], thumbnail_extractor=lambda a: thumb)
    job.run()

    assert job.fatal_error is None
    assert job.uploaded_ids == {"Chair": "srv-1"}
    presigns = [c for c in client.calls if c[0] == "presign"]
    assert {c[2] for c in presigns} == {"file", "thumbnail"}
    upsert = next(c[1] for c in client.calls if c[0] == "upsert")
    assert upsert["name"] == "Chair"
    assert upsert["catalog_uuid"] == "cat-u1"
    assert upsert["file"]["id"].startswith("key-")
    result = next(r for r in job.results if r.name == "Chair")
    assert result.status == "published"


def test_unchanged_asset_skips_everything(tmp_path):
    blend = make_blend(tmp_path)
    sha = sha256_file(blend)
    remote = [
        {
            "id": "srv-1",
            "name": "Chair",
            "id_type": "OBJECT",
            "catalog_uuid": "cat-u1",
            "tags": ["prop"],
            "description": "d",
            "author": "a",
            "license": "Standard Royalty Free",
            "copyright": "",
            "file": {"sha256": sha, "size": blend.stat().st_size},
        }
    ]
    client = StubClient(remote=remote)
    job = make_job(client, [make_asset(blend)])
    job.run()

    assert job.fatal_error is None
    assert not [c for c in client.calls if c[0] in ("presign", "upload", "upsert")]
    assert [r.status for r in job.results] == ["unchanged"]


def test_validation_error_continues_to_next_asset(tmp_path):
    blend_a = make_blend(tmp_path, "Alpha")
    blend_b = make_blend(tmp_path, "Beta")
    client = StubClient(
        upsert_responses=[
            ValidationError(
                "Validation failed", 422, [{"code": "invalid", "message": "bad"}]
            ),
            {"id": "srv-2", "status": "published"},
        ]
    )
    job = make_job(client, [make_asset(blend_a), make_asset(blend_b)])
    job.run()

    assert job.fatal_error is None
    by_name = {r.name: r for r in job.results}
    assert by_name["Alpha"].status == "error"
    assert "invalid: bad" in by_name["Alpha"].message
    assert by_name["Beta"].status == "published"
    assert job.uploaded_ids == {"Beta": "srv-2"}


def test_metadata_only_change_sends_no_file(tmp_path):
    blend = make_blend(tmp_path)
    sha = sha256_file(blend)
    remote = [
        {
            "id": "srv-1",
            "name": "Chair",
            "id_type": "OBJECT",
            "catalog_uuid": "cat-u1",
            "tags": ["prop"],
            "description": "OLD",
            "author": "a",
            "license": "Standard Royalty Free",
            "copyright": "",
            "file": {"sha256": sha, "size": 1},
        }
    ]
    client = StubClient(
        remote=remote, upsert_responses=[{"id": "srv-1", "status": "published"}]
    )
    job = make_job(client, [make_asset(blend)])
    job.run()

    assert not [c for c in client.calls if c[0] in ("presign", "upload")]
    upsert = next(c[1] for c in client.calls if c[0] == "upsert")
    assert "file" not in upsert
    assert [r.status for r in job.results] == ["metadata"]


def test_rejection_reasons_reach_the_result(tmp_path):
    blend = make_blend(tmp_path)
    client = StubClient(
        upsert_responses=[{"id": "srv-1", "status": "processing"}],
        poll_statuses={
            "srv-1": [
                {
                    "id": "srv-1",
                    "status": "rejected",
                    "rejection_reasons": [
                        {"code": "not_a_blend", "message": "magic bytes wrong"}
                    ],
                }
            ]
        },
    )
    job = make_job(client, [make_asset(blend)])
    job.run()

    result = next(r for r in job.results if r.name == "Chair")
    assert result.status == "rejected"
    assert "not_a_blend: magic bytes wrong" in result.message


def test_auth_error_is_fatal(tmp_path):
    blend = make_blend(tmp_path)
    client = StubClient(remote=AuthError("nope", 401))
    job = make_job(client, [make_asset(blend)])
    job.run()
    assert "token" in job.fatal_error.lower()


def test_deleted_server_library_flags_binding_gone(tmp_path):
    blend = make_blend(tmp_path)
    client = StubClient(remote=NotFoundError("gone", 404))
    job = make_job(client, [make_asset(blend)])
    job.run()
    assert job.binding_gone
    assert "no longer exists" in job.fatal_error


def test_cancel_before_upload(tmp_path):
    blend = make_blend(tmp_path)
    client = StubClient()
    job = make_job(client, [make_asset(blend)])
    job.cancel_requested = True
    job.run()
    assert job.cancelled
    assert not [c for c in client.calls if c[0] == "upsert"]


def test_missing_file_is_reported_not_fatal(tmp_path):
    ghost = make_asset(tmp_path / "Ghost.blend")  # never written
    real = make_asset(make_blend(tmp_path, "Real"))
    client = StubClient(upsert_responses=[{"id": "srv-r", "status": "published"}])
    job = make_job(client, [ghost, real])
    job.run()

    assert job.fatal_error is None
    by_name = {r.name: r for r in job.results}
    assert by_name["Ghost"].status == "error"
    assert "Could not read file" in by_name["Ghost"].message
    assert by_name["Real"].status == "published"


def test_oversized_thumbnail_warns_but_publishes(tmp_path):
    blend = make_blend(tmp_path)
    big_thumb = tmp_path / "big_preview.webp"
    big_thumb.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
    client = StubClient(upsert_responses=[{"id": "srv-1", "status": "published"}])
    job = make_job(client, [make_asset(blend)], thumbnail_extractor=lambda a: big_thumb)
    job.run()

    result = next(r for r in job.results if r.name == "Chair")
    assert result.status == "published"
    assert "max 2 MB" in result.message
    thumbnail_presigns = [
        c for c in client.calls if c[0] == "presign" and c[2] == "thumbnail"
    ]
    assert not thumbnail_presigns


def test_rename_sends_previous_asset_id(tmp_path):
    blend = make_blend(tmp_path, "NewName")
    sha = sha256_file(blend)
    remote = [
        {
            "id": "srv-old",
            "name": "OldName",
            "id_type": "OBJECT",
            "catalog_uuid": "cat-u1",
            "tags": ["prop"],
            "description": "d",
            "author": "a",
            "license": "Standard Royalty Free",
            "copyright": "",
            "file": {"sha256": sha, "size": 1},
        }
    ]
    client = StubClient(
        remote=remote, upsert_responses=[{"id": "srv-old", "status": "published"}]
    )
    job = make_job(
        client,
        [make_asset(blend)],
        name_to_server_id={"NewName": "srv-old"},
    )
    job.run()

    upsert = next(c[1] for c in client.calls if c[0] == "upsert")
    assert upsert["previous_asset_id"] == "srv-old"
    assert upsert["name"] == "NewName"
