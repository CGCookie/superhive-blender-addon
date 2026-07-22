from api.sidecar import (
    SIDECAR_NAME,
    clear_sidecar,
    read_sidecar,
    record_asset_ids,
    rename_asset,
    write_sidecar,
)


def test_round_trip(tmp_path):
    write_sidecar(tmp_path, {"library_id": "lib-1", "base_url": "http://x"})
    data = read_sidecar(tmp_path)
    assert data["library_id"] == "lib-1"
    assert data["version"] == 1
    assert data["assets"] == {}
    assert data["updated_at"]
    assert not list(tmp_path.glob("*.tmp"))


def test_read_missing_returns_none(tmp_path):
    assert read_sidecar(tmp_path) is None


def test_read_corrupt_returns_none(tmp_path):
    (tmp_path / SIDECAR_NAME).write_text("{not json", encoding="utf-8")
    assert read_sidecar(tmp_path) is None


def test_read_without_library_id_returns_none(tmp_path):
    (tmp_path / SIDECAR_NAME).write_text('{"assets": {}}', encoding="utf-8")
    assert read_sidecar(tmp_path) is None


def test_record_asset_ids_merges(tmp_path):
    write_sidecar(tmp_path, {"library_id": "lib-1", "assets": {"A": "srv-a"}})
    record_asset_ids(tmp_path, {"B": "srv-b"})
    assert read_sidecar(tmp_path)["assets"] == {"A": "srv-a", "B": "srv-b"}


def test_record_asset_ids_no_sidecar_is_noop(tmp_path):
    record_asset_ids(tmp_path, {"B": "srv-b"})
    assert read_sidecar(tmp_path) is None


def test_rename_asset_rekeys(tmp_path):
    write_sidecar(tmp_path, {"library_id": "lib-1", "assets": {"Old": "srv-1"}})
    rename_asset(tmp_path, "Old", "New")
    assert read_sidecar(tmp_path)["assets"] == {"New": "srv-1"}


def test_rename_unknown_is_noop(tmp_path):
    write_sidecar(tmp_path, {"library_id": "lib-1"})
    rename_asset(tmp_path, "Ghost", "New")
    assert read_sidecar(tmp_path)["assets"] == {}


def test_clear_sidecar(tmp_path):
    write_sidecar(tmp_path, {"library_id": "lib-1"})
    clear_sidecar(tmp_path)
    assert read_sidecar(tmp_path) is None
    clear_sidecar(tmp_path)  # idempotent
