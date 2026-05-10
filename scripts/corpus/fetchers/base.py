"""Polite, retrying HTTP fetcher base class.

All public-archive scrapers should inherit from this. Defaults:
- 1 request/second floor (rate limit defensive against shared infrastructure)
- Identifying User-Agent (some endpoints, e.g. SEC EDGAR, require it)
- Exponential backoff on 5xx and 429
- Streaming download to disk (no in-memory PDF buffering)
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import httpx

DEFAULT_USER_AGENT = "Velix Corpus Builder bhumishdayal@gmail.com"
DEFAULT_MIN_INTERVAL_S = 1.0
DEFAULT_TIMEOUT_S = 60.0
DEFAULT_MAX_RETRIES = 4


@dataclass
class FetchTask:
    """A single document the fetcher wants to download."""

    source_id: str
    url: str
    relative_path: str  # e.g., "10K/0000950170-25-012345/lease-exhibit.pdf"
    content_type: str = "application/pdf"
    title: str = ""
    metadata: dict | None = None


class Fetcher(ABC):
    """Abstract base class for source-specific corpus fetchers."""

    source_name: str

    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        min_interval_s: float = DEFAULT_MIN_INTERVAL_S,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self._client = httpx.Client(
            headers={"User-Agent": user_agent, "Accept": "*/*"},
            timeout=timeout_s,
            follow_redirects=True,
        )
        self._min_interval_s = min_interval_s
        self._max_retries = max_retries
        self._last_request_at = 0.0

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Fetcher:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self._min_interval_s:
            time.sleep(self._min_interval_s - elapsed)
        self._last_request_at = time.monotonic()

    def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        for attempt in range(self._max_retries):
            self._throttle()
            try:
                response = self._client.request(method, url, **kwargs)
            except httpx.HTTPError as exc:
                if attempt == self._max_retries - 1:
                    raise
                backoff = 2**attempt
                time.sleep(backoff)
                continue
            if response.status_code in {429, 500, 502, 503, 504}:
                if attempt == self._max_retries - 1:
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After")
                backoff = float(retry_after) if retry_after else 2**attempt
                time.sleep(backoff)
                continue
            response.raise_for_status()
            return response
        raise RuntimeError("unreachable: retry loop exited without returning")

    def download(self, url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(self._max_retries):
            self._throttle()
            try:
                with self._client.stream("GET", url) as response:
                    if response.status_code in {429, 500, 502, 503, 504}:
                        if attempt == self._max_retries - 1:
                            response.raise_for_status()
                        backoff = 2**attempt
                        time.sleep(backoff)
                        continue
                    response.raise_for_status()
                    tmp = dest.with_suffix(dest.suffix + ".part")
                    with open(tmp, "wb") as f:
                        for chunk in response.iter_bytes(65536):
                            f.write(chunk)
                    tmp.replace(dest)
                    return
            except httpx.HTTPError:
                if attempt == self._max_retries - 1:
                    raise
                time.sleep(2**attempt)

    @abstractmethod
    def discover(self, max_docs: int) -> Iterator[FetchTask]:
        """Yield FetchTasks the orchestrator should download.

        Implementations should be lazy (generator) so the orchestrator can
        stop early once a target page count is hit.
        """
