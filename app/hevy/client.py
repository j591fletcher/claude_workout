"""Read-only Hevy API client.

Only GET endpoints are implemented — this app never writes to Hevy. Auth is the
`api-key` header (Hevy Pro required). Pagination via page/pageSize; transient
errors retried with backoff; 4xx/5xx surfaced as typed errors, never stack traces.
"""

from __future__ import annotations

import logging
import time

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)


class HevyError(RuntimeError):
    """A Hevy API call failed. `status` is the HTTP code (0 for network errors)."""

    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


class HevyClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        s = get_settings()
        key = api_key or s.hevy_api_key
        if not key:
            raise HevyError("HEVY_API_KEY is not configured")
        self._client = httpx.Client(
            base_url=(base_url or s.hevy_base_url).rstrip("/"),
            headers={"api-key": key, "accept": "application/json"},
            timeout=30.0,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HevyClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _get(self, path: str, params: dict | None = None) -> dict:
        for attempt in range(4):
            try:
                resp = self._client.get(path, params=params)
            except httpx.HTTPError as e:
                if attempt == 3:
                    raise HevyError(f"network error calling {path}: {e}") from e
                time.sleep(2 ** attempt)
                continue
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt < 3:
                    log.warning("Hevy %s on %s; retrying", resp.status_code, path)
                    time.sleep(int(resp.headers.get("retry-after", 2 ** attempt)))
                    continue
            if resp.status_code >= 400:
                raise HevyError(f"Hevy {resp.status_code} on {path}: {resp.text[:200]}",
                                status=resp.status_code)
            return resp.json()
        raise HevyError(f"exhausted retries calling {path}")

    # ------------------------------------------------------------------ endpoints

    def get_workouts(self, page: int = 1, page_size: int = 10) -> dict:
        return self._get("/v1/workouts", {"page": page, "pageSize": page_size})

    def get_routines(self, page: int = 1, page_size: int = 10) -> dict:
        return self._get("/v1/routines", {"page": page, "pageSize": page_size})

    def get_exercise_templates(self, page: int = 1, page_size: int = 100) -> dict:
        return self._get("/v1/exercise_templates", {"page": page, "pageSize": page_size})

    def iter_workouts(self, page_size: int = 10):
        """Yield every workout across all pages."""
        page = 1
        while True:
            data = self.get_workouts(page=page, page_size=page_size)
            yield from data.get("workouts", [])
            if page >= data.get("page_count", page):
                return
            page += 1

    def iter_routines(self, page_size: int = 10):
        page = 1
        while True:
            data = self.get_routines(page=page, page_size=page_size)
            yield from data.get("routines", [])
            if page >= data.get("page_count", page):
                return
            page += 1
