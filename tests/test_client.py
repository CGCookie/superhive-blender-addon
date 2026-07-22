import json as jsonlib
import types

import pytest

import api.client as client_mod
from api.client import (
    ApiError,
    AuthError,
    NotFoundError,
    ProgressFileReader,
    RateLimitedError,
    ScopeError,
    SuperhiveClient,
    ValidationError,
)


class FakeResponse:
    def __init__(self, status_code=200, body=None, headers=None):
        self.status_code = status_code
        self.headers = headers or {}
        if body is None:
            self.content = b""
            self.text = ""
        else:
            self.text = jsonlib.dumps(body)
            self.content = self.text.encode()

    def json(self):
        return jsonlib.loads(self.text)


class FakeSession:
    def __init__(self):
        self.headers = {}
        self.queue = []
        self.calls = []

    def request(self, method, url, json=None, params=None, timeout=None):
        self.calls.append(
            {"method": method, "url": url, "json": json, "params": params}
        )
        response = self.queue.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeRequestException(Exception):
    pass


@pytest.fixture
def fake_requests(monkeypatch):
    fake = types.SimpleNamespace(
        Session=FakeSession,
        RequestException=FakeRequestException,
        put=None,  # set per-test when exercising uploads
    )
    monkeypatch.setattr(client_mod, "requests", fake)
    monkeypatch.setattr(client_mod.time, "sleep", lambda s: fake.sleeps.append(s))
    fake.sleeps = []
    return fake


def make_client():
    return SuperhiveClient("http://test/", "shk_x", min_request_interval=0)


def test_session_carries_token_header(fake_requests):
    client = make_client()
    assert client._session.headers["SH-Auth-Token"] == "shk_x"
    assert client.base_url == "http://test"


def test_success_parses_json(fake_requests):
    client = make_client()
    client._session.queue = [FakeResponse(200, {"roots": [{"name": "Models"}]})]
    assert client.get_taxonomy_roots() == ["Models"]
    call = client._session.calls[0]
    assert call["url"] == "http://test/api/v1/assets/taxonomy/roots"


def test_204_returns_none(fake_requests):
    client = make_client()
    client._session.queue = [FakeResponse(204)]
    assert client.delete_asset("lib", "a1") is None


@pytest.mark.parametrize(
    "status,expected",
    [
        (401, AuthError),
        (403, ScopeError),
        (404, NotFoundError),
        (422, ValidationError),
        (500, ApiError),
    ],
)
def test_error_mapping(fake_requests, status, expected):
    client = make_client()
    client._session.queue = [
        FakeResponse(status, {"error": {"code": status, "message": "nope"}})
    ]
    with pytest.raises(expected) as exc:
        client.get_library("lib")
    assert exc.value.status == status


def test_422_structured_details_become_errors(fake_requests):
    client = make_client()
    details = [{"code": "unknown_root", "message": "bad root", "index": 0}]
    client._session.queue = [
        FakeResponse(
            422,
            {
                "error": {
                    "code": 422,
                    "message": "Catalog sync failed",
                    "details": details,
                }
            },
        )
    ]
    with pytest.raises(ValidationError) as exc:
        client.put_catalogs("lib", [])
    assert exc.value.errors == details


def test_string_details_folded_into_message(fake_requests):
    client = make_client()
    client._session.queue = [
        FakeResponse(
            422,
            {
                "error": {
                    "code": 422,
                    "message": "Validation failed",
                    "details": "Name has already been taken",
                }
            },
        )
    ]
    with pytest.raises(ValidationError) as exc:
        client.create_library("x")
    assert "Name has already been taken" in str(exc.value)
    assert exc.value.errors == []


def test_429_retries_then_succeeds(fake_requests):
    client = make_client()
    client._session.queue = [
        FakeResponse(429, headers={"Retry-After": "2"}),
        FakeResponse(200, {"roots": []}),
    ]
    assert client.get_taxonomy_roots() == []
    assert fake_requests.sleeps == [2.0]


def test_429_exhausts_retries(fake_requests):
    client = make_client()
    client._session.queue = [FakeResponse(429)] * 4
    with pytest.raises(RateLimitedError):
        client.get_taxonomy_roots()
    assert len(fake_requests.sleeps) == 3


def test_connection_error_raises_network_error(fake_requests):
    client = make_client()
    client._session.queue = [FakeRequestException("boom")]
    with pytest.raises(client_mod.NetworkError):
        client.get_taxonomy_roots()


def test_pagination_follows_next_page(fake_requests):
    client = make_client()
    client._session.queue = [
        FakeResponse(
            200,
            {"assets": [{"id": "a1"}], "pagination": {"next_page": 2}},
        ),
        FakeResponse(
            200,
            {"assets": [{"id": "a2"}], "pagination": {"next_page": None}},
        ),
    ]
    assets = client.list_assets("lib")
    assert [a["id"] for a in assets] == ["a1", "a2"]
    assert client._session.calls[0]["params"]["page"] == 1
    assert client._session.calls[1]["params"]["page"] == 2


def test_upload_to_presigned_builds_uploaded_file_json(fake_requests, tmp_path):
    blend = tmp_path / "Chair.blend"
    blend.write_bytes(b"BLENDER" * 100)
    seen = {}

    def fake_put(url, data=None, headers=None, timeout=None):
        seen["url"] = url
        seen["headers"] = headers
        seen["body"] = data.read()
        return FakeResponse(200)

    fake_requests.put = fake_put
    client = make_client()
    progress = []
    ticket = {
        "id": "abc.blend",
        "storage": "cache",
        "url": "http://s3/put",
        "headers": {"Content-Type": "application/x-blend"},
    }
    uploaded = client.upload_to_presigned(
        ticket, blend, progress_cb=lambda sent, total: progress.append((sent, total))
    )
    assert seen["url"] == "http://s3/put"
    assert "SH-Auth-Token" not in seen["headers"]
    assert seen["body"] == b"BLENDER" * 100
    assert uploaded == {
        "id": "abc.blend",
        "storage": "cache",
        "metadata": {
            "filename": "Chair.blend",
            "size": 700,
            "mime_type": "application/x-blend",
        },
    }
    assert progress[-1] == (700, 700)


def test_upload_failure_status_raises(fake_requests, tmp_path):
    blend = tmp_path / "x.blend"
    blend.write_bytes(b"data")
    fake_requests.put = lambda *a, **k: FakeResponse(403)
    client = make_client()
    with pytest.raises(ApiError):
        client.upload_to_presigned(
            {"id": "i", "storage": "cache", "url": "u", "headers": {}}, blend
        )


def test_progress_file_reader_len_and_chunks(tmp_path):
    f = tmp_path / "f.bin"
    f.write_bytes(b"x" * 10)
    ticks = []
    with ProgressFileReader(f, lambda sent, total: ticks.append(sent)) as reader:
        assert len(reader) == 10
        assert reader.read(4) == b"xxxx"
        assert reader.read() == b"x" * 6
        assert reader.read() == b""
    assert ticks == [4, 10]
