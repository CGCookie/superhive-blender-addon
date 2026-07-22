import pytest

from api.client import ValidationError
from api.publish import sync_catalogs

ROOTS = ["Materials", "Models"]


class StubClient:
    def __init__(self, error=None):
        self.error = error
        self.sent = None

    def put_catalogs(self, library_id, catalogs):
        self.sent = (library_id, catalogs)
        if self.error:
            raise self.error
        return catalogs


def entry(path, uuid="u1"):
    return {"uuid": uuid, "path": path, "simple_name": path.replace("/", "-")}


def test_sync_prefilters_non_curated_roots():
    stub = StubClient()
    result = sync_catalogs(
        stub,
        "lib-1",
        [entry("Models/Chairs", "u1"), entry("Render Setups/Studio", "u2")],
        ROOTS,
    )
    library_id, sent = stub.sent
    assert library_id == "lib-1"
    assert [e["path"] for e in sent] == ["Models/Chairs"]
    assert result.synced == sent
    assert result.skipped == [
        ("Render Setups/Studio", "'Render Setups' is not a curated Superhive root")
    ]


def test_sync_maps_indexed_errors_to_paths():
    error = ValidationError(
        "Catalog sync failed",
        422,
        [{"index": 1, "code": "duplicate_path", "message": "path taken"}],
    )
    stub = StubClient(error=error)
    with pytest.raises(ValidationError) as exc:
        sync_catalogs(
            stub, "lib-1", [entry("Models/A", "u1"), entry("Models/B", "u2")], ROOTS
        )
    assert "Models/B: duplicate_path — path taken" in str(exc.value)
    assert exc.value.errors == error.errors


def test_sync_unstructured_error_passes_through():
    error = ValidationError("Catalog sync failed: boom", 422, [])
    stub = StubClient(error=error)
    with pytest.raises(ValidationError) as exc:
        sync_catalogs(stub, "lib-1", [entry("Models/A")], ROOTS)
    assert str(exc.value) == "Catalog sync failed: boom"
