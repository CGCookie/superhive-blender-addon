"""HTTP client for the Superhive assets API (/api/v1/assets).

Contract: swagger at superhivemarket.com/api-docs (source of truth lives in
the markets-rails repo, swagger/v1/swagger.yaml).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

try:
    import requests
except ImportError:  # wheels not bundled (dev checkout run without a build)
    requests = None


_LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]", "0.0.0.0"}


def normalize_base_url(url: str) -> str:
    """Fill in the scheme when the user typed a bare host — requests refuses
    URLs without one ("No connection adapters were found"). https by default,
    http for local dev hosts, which won't have TLS."""
    url = url.strip().rstrip("/")
    if not url or "://" in url:
        return url
    host, _, port = url.split("/", 1)[0].rpartition(":")
    if not host or not port.isdigit():
        host = url.split("/", 1)[0]
    scheme = "http" if host in _LOCAL_HOSTS else "https"
    return f"{scheme}://{url}"


def require_requests():
    if requests is None:
        raise RuntimeError(
            "The bundled 'requests' wheel is missing. Rebuild the extension with"
            " wheels (python wheels/download_wheels.py, then"
            " blender --command extension build), or pip-install 'requests' into"
            " Blender's Python for development."
        )


class ApiError(Exception):
    """Base error for Superhive API failures.

    `errors` carries the server's structured error list ([{code, message, ...}])
    when the response included one; otherwise it's empty and the exception
    message is the best description available.
    """

    def __init__(
        self,
        message: str,
        status: int | None = None,
        errors: list[dict] | None = None,
    ):
        super().__init__(message)
        self.status = status
        self.errors = errors or []


class NetworkError(ApiError):
    """Connection failure, timeout, or DNS error — no HTTP response."""


class AuthError(ApiError):
    """401 — invalid or revoked token."""


class ScopeError(ApiError):
    """403 — token lacks a required scope, or the account isn't allowed."""


class NotFoundError(ApiError):
    """404 — e.g. a sidecar-bound library that was deleted server-side."""


class ValidationError(ApiError):
    """422 — `errors` holds the per-entry/per-field list when structured."""


class RateLimitedError(ApiError):
    """429 that persisted through retries."""


class ProgressFileReader:
    """File wrapper whose read() reports progress via a callback.

    Defines __len__ so requests sends Content-Length instead of chunked
    transfer encoding (S3 presigned PUTs reject chunked bodies).
    """

    def __init__(
        self,
        path: Path,
        progress_cb: Callable[[int, int], None] | None = None,
    ):
        self._file = open(path, "rb")
        self.total = path.stat().st_size
        self.sent = 0
        self._progress_cb = progress_cb

    def __len__(self) -> int:
        return self.total

    def read(self, size: int = -1) -> bytes:
        chunk = self._file.read(size)
        if chunk:
            self.sent += len(chunk)
            if self._progress_cb:
                self._progress_cb(self.sent, self.total)
        return chunk

    def close(self):
        self._file.close()

    def __enter__(self) -> "ProgressFileReader":
        return self

    def __exit__(self, *exc):
        self.close()


class SuperhiveClient:
    """Paced, typed-error client for the assets API.

    Every API call funnels through `_request`, which spaces requests
    `min_request_interval` apart. The server throttles tokens at 300 req/5min
    on the assets namespace AND 100 req/min API-wide, so the sustained budget
    is 1 req/sec — 1.05s keeps us under both. Direct-to-storage uploads
    (`upload_to_presigned`) don't count against either throttle.
    """

    MAX_RETRIES_429 = 3
    MAX_RETRY_AFTER = 60.0
    UPLOAD_TIMEOUT = 1800.0  # .blend files up to 500MB on slow uplinks
    PER_PAGE = 100  # server MAX_PER_PAGE

    def __init__(
        self,
        base_url: str,
        token: str,
        timeout: float = 30.0,
        min_request_interval: float = 1.05,
    ):
        require_requests()
        self.base_url = normalize_base_url(base_url)
        self.timeout = timeout
        self.min_request_interval = min_request_interval
        self._last_request_at = 0.0
        self._session = requests.Session()
        self._session.headers.update(
            {
                "SH-Auth-Token": token,
                "Accept": "application/json",
            }
        )

    # ---- endpoints ----

    def get_taxonomy_roots(self) -> list[str]:
        data = self._request("GET", "/api/v1/assets/taxonomy/roots")
        return [root["name"] for root in data.get("roots", [])]

    def list_libraries(self) -> list[dict]:
        return self._collect_pages("/api/v1/assets/libraries", "libraries")

    def create_library(self, name: str, description: str | None = None) -> dict:
        payload = {"name": name}
        if description:
            payload["description"] = description
        return self._request("POST", "/api/v1/assets/libraries", json_body=payload)

    def get_library(self, library_id: str) -> dict:
        return self._request("GET", f"/api/v1/assets/libraries/{library_id}")

    def put_catalogs(self, library_id: str, catalogs: list[dict]) -> list[dict]:
        data = self._request(
            "PUT",
            f"/api/v1/assets/libraries/{library_id}/catalogs",
            json_body={"catalogs": catalogs},
        )
        return data.get("catalogs", [])

    def list_assets(self, library_id: str) -> list[dict]:
        return self._collect_pages(
            f"/api/v1/assets/libraries/{library_id}/assets", "assets"
        )

    def get_asset(self, library_id: str, asset_id: str) -> dict:
        return self._request(
            "GET", f"/api/v1/assets/libraries/{library_id}/assets/{asset_id}"
        )

    def delete_asset(self, library_id: str, asset_id: str) -> None:
        self._request(
            "DELETE", f"/api/v1/assets/libraries/{library_id}/assets/{asset_id}"
        )

    def upsert_asset(self, library_id: str, payload: dict) -> dict:
        return self._request(
            "POST", f"/api/v1/assets/libraries/{library_id}/assets", json_body=payload
        )

    def presign(self, filename: str, content_type: str, target: str) -> dict:
        """target is "file" (private .blend storage) or "thumbnail" (public CDN)."""
        return self._request(
            "GET",
            "/api/v1/assets/uploads/presign",
            params={"filename": filename, "type": content_type, "target": target},
        )

    def upload_to_presigned(
        self,
        ticket: dict,
        path: Path | str,
        progress_cb: Callable[[int, int], None] | None = None,
    ) -> dict:
        """PUT the file to the presigned URL; returns the uploaded-file JSON
        to pass as the asset POST's `file`/`thumbnail` param.

        Deliberately NOT sent through the session — the API token must never
        reach the storage host.
        """
        path = Path(path)
        headers = dict(ticket.get("headers") or {})
        try:
            with ProgressFileReader(path, progress_cb) as body:
                response = requests.put(
                    ticket["url"],
                    data=body,
                    headers=headers,
                    timeout=self.UPLOAD_TIMEOUT,
                )
        except requests.RequestException as error:
            raise NetworkError(f"Upload of {path.name} failed: {error}") from error
        if not (200 <= response.status_code < 300):
            raise ApiError(
                f"Storage upload of {path.name} failed (HTTP {response.status_code})",
                status=response.status_code,
            )
        return {
            "id": ticket["id"],
            "storage": ticket["storage"],
            "metadata": {
                "filename": path.name,
                "size": path.stat().st_size,
                "mime_type": headers.get("Content-Type") or "application/octet-stream",
            },
        }

    # ---- plumbing ----

    def _pace(self):
        wait = self._last_request_at + self.min_request_interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        params: dict | None = None,
    ):
        url = self.base_url + path
        retries = 0
        while True:
            self._pace()
            try:
                response = self._session.request(
                    method, url, json=json_body, params=params, timeout=self.timeout
                )
            except requests.RequestException as error:
                raise NetworkError(
                    f"Could not reach {self.base_url}: {error}"
                ) from error

            if response.status_code == 429 and retries < self.MAX_RETRIES_429:
                retries += 1
                try:
                    retry_after = float(response.headers.get("Retry-After", ""))
                except ValueError:
                    retry_after = 5.0 * retries
                time.sleep(min(max(retry_after, 1.0), self.MAX_RETRY_AFTER))
                continue

            return self._handle_response(response)

    def _handle_response(self, response):
        if 200 <= response.status_code < 300:
            if response.status_code == 204 or not response.content:
                return None
            return response.json()

        message, errors = self._parse_error(response)
        status = response.status_code
        if status == 401:
            raise AuthError(message or "Invalid or revoked API token", status, errors)
        if status == 403:
            raise ScopeError(
                message or "Token or account lacks the required permission",
                status,
                errors,
            )
        if status == 404:
            raise NotFoundError(message or "Resource not found", status, errors)
        if status == 422:
            raise ValidationError(message or "Validation failed", status, errors)
        if status == 429:
            raise RateLimitedError(
                "Rate limited by the server — wait a minute and retry", status, errors
            )
        raise ApiError(message or f"Server error (HTTP {status})", status, errors)

    @staticmethod
    def _parse_error(response) -> tuple[str, list[dict]]:
        """The API wraps errors as {"error": {code, message, details}} where
        details is either a string or the structured [{code, message, ...}] list."""
        try:
            error = response.json().get("error") or {}
        except ValueError:
            return f"HTTP {response.status_code}: {response.text[:200]}", []
        message = error.get("message") or ""
        details = error.get("details")
        if isinstance(details, list):
            return message, details
        if details:
            message = f"{message}: {details}" if message else str(details)
        return message, []

    def _collect_pages(self, path: str, key: str) -> list[dict]:
        items: list[dict] = []
        page = 1
        while True:
            data = self._request(
                "GET", path, params={"page": page, "per_page": self.PER_PAGE}
            )
            items.extend(data.get(key, []))
            next_page = (data.get("pagination") or {}).get("next_page")
            if not next_page:
                return items
            page = next_page
