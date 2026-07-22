import pytest

from api import taxonomy
from api.client import ApiError


class StubClient:
    def __init__(self, roots=None, error=None):
        self.roots = roots
        self.error = error
        self.calls = 0

    def get_taxonomy_roots(self):
        self.calls += 1
        if self.error:
            raise self.error
        return list(self.roots)


@pytest.fixture(autouse=True)
def fresh_cache():
    taxonomy.clear_cache()
    yield
    taxonomy.clear_cache()


def test_no_client_returns_fallback():
    assert taxonomy.get_cached_roots(None) == list(taxonomy.FALLBACK_ROOTS)


def test_fetch_and_cache():
    stub = StubClient(roots=["Models"])
    assert taxonomy.get_cached_roots(stub) == ["Models"]
    assert taxonomy.get_cached_roots(stub) == ["Models"]
    assert stub.calls == 1


def test_network_failure_falls_back_to_stale_cache():
    taxonomy.get_cached_roots(StubClient(roots=["Models"]))
    # expire the TTL without clearing the stored roots
    taxonomy._cache["fetched_at"] = -1e9
    stub = StubClient(error=ApiError("down"))
    assert taxonomy.get_cached_roots(stub) == ["Models"]


def test_network_failure_without_cache_returns_fallback():
    stub = StubClient(error=ApiError("down"))
    assert taxonomy.get_cached_roots(stub) == list(taxonomy.FALLBACK_ROOTS)
