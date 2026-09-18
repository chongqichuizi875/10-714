from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from futures_intel.config import ComplianceConfig


class ComplianceError(RuntimeError):
    """Raised when a request would violate the local compliance policy."""


class BudgetExceeded(ComplianceError):
    """Raised when the per-run request budget is exhausted."""


class RemoteStop(ComplianceError):
    """Raised when the remote site returns a stop / block status."""


@dataclass
class HttpResponse:
    url: str
    payload: Any
    cached: bool
    status: int
    fetched_at: str


class PoliteClient:
    """Small JSON client with cache, interval, budget, and fail-closed stops."""

    def __init__(
        self,
        compliance: ComplianceConfig,
        cache_dir: Path,
        *,
        allow_network: bool | None = None,
        sleeper=time.sleep,
        opener=None,
    ) -> None:
        self.compliance = compliance
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.allow_network = compliance.allow_network if allow_network is None else allow_network
        self._sleeper = sleeper
        self._opener = opener or urlopen
        self._last_request_at = 0.0
        self.requests_used = 0

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> HttpResponse:
        query = urlencode(params or {}, doseq=True)
        full_url = f"{url}?{query}" if query else url
        cache_path = self._cache_path(full_url)
        cached = self._read_cache(cache_path)
        if cached is not None:
            return HttpResponse(
                url=full_url,
                payload=cached["payload"],
                cached=True,
                status=int(cached.get("status", 200)),
                fetched_at=str(cached.get("fetched_at", "")),
            )

        if not self.allow_network:
            raise ComplianceError(
                "Network access is disabled. Use --offline with a warm cache, "
                "or set allow_network=true after reading docs/COMPLIANCE.md."
            )
        if self.requests_used >= self.compliance.max_requests_per_run:
            raise BudgetExceeded(
                f"Reached max_requests_per_run={self.compliance.max_requests_per_run}."
            )

        self._throttle()
        request = Request(
            full_url,
            headers={
                "User-Agent": self.compliance.user_agent,
                "Accept": "application/json,text/javascript;q=0.9,*/*;q=0.8",
                "Referer": self.compliance.referer,
            },
            method="GET",
        )
        fetched_at = datetime.now(timezone.utc).isoformat()
        try:
            with self._opener(request, timeout=self.compliance.timeout_seconds) as response:
                status = getattr(response, "status", 200)
                raw = response.read()
        except HTTPError as exc:
            if exc.code in self.compliance.stop_on_status:
                raise RemoteStop(
                    f"Remote returned HTTP {exc.code}. Stopping without retry or evasion."
                ) from exc
            raise
        except URLError as exc:
            raise ComplianceError(f"Network error talking to {url}: {exc.reason}") from exc

        if status in self.compliance.stop_on_status:
            raise RemoteStop(f"Remote returned HTTP {status}. Stopping without retry or evasion.")

        payload = json.loads(raw.decode("utf-8"))
        self.requests_used += 1
        self._write_cache(
            cache_path,
            {
                "url": full_url,
                "status": status,
                "fetched_at": fetched_at,
                "payload": payload,
            },
        )
        return HttpResponse(
            url=full_url,
            payload=payload,
            cached=False,
            status=status,
            fetched_at=fetched_at,
        )

    def _throttle(self) -> None:
        gap = self.compliance.min_interval_seconds
        if self._last_request_at <= 0:
            self._last_request_at = time.monotonic()
            return
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < gap:
            self._sleeper(gap - elapsed)
        self._last_request_at = time.monotonic()

    def _cache_path(self, full_url: str) -> Path:
        digest = hashlib.sha256(full_url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def _read_cache(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        fetched_at = data.get("fetched_at")
        if not fetched_at:
            return None
        try:
            ts = datetime.fromisoformat(str(fetched_at))
        except ValueError:
            return None
        age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        if age_hours > self.compliance.cache_ttl_hours:
            return None
        return data

    def _write_cache(self, path: Path, data: dict[str, Any]) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
