"""Bounded, serial Overpass retrieval with exact raw-response caching and provenance."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import Message
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from common import REPO_ROOT, write_json

from .normalize import normalize_elements, verify_landmarks

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "GridBridge/0.1 (https://github.com/fradicus/Shellhacks-2026)"
INFRASTRUCTURE_BBOX = (30.3, -85.7, 35.3, -78.5)
LINE_BBOX = (31.8, -82.6, 33.9, -80.6)
MAX_RETRIES = 3
MIN_REQUEST_GAP_SECONDS = 10.0
MAX_REQUESTS = 32
MAX_SPLIT_DEPTH = 3
MAX_RAW_FILE_BYTES = 25 * 1024 * 1024
MAX_TOTAL_RAW_BYTES = 64 * 1024 * 1024
MAX_SERVER_COOLDOWN_SECONDS = 120.0

Transport = Callable[[str], tuple[bytes, Message]]
Clock = Callable[[], str]


@dataclass(frozen=True)
class QueryJob:
    kind: str
    bbox: tuple[float, float, float, float]
    depth: int = 0
    suffix: str = "full"


class RequestLimitError(RuntimeError):
    pass


class QueryFailed(RuntimeError):
    def __init__(self, status: int | None, message: str, attempts: int, *, stop_live_requests: bool = False):
        super().__init__(message)
        self.status = status
        self.attempts = attempts
        self.stop_live_requests = stop_live_requests


class RateLimiter:
    def __init__(self, sleep: Callable[[float], None] = time.sleep, monotonic: Callable[[], float] = time.monotonic):
        self._sleep = sleep
        self._monotonic = monotonic
        self._last_request: float | None = None
        self._not_before = 0.0

    def defer(self, seconds: float) -> None:
        self._not_before = max(self._not_before, self._monotonic() + seconds)

    def wait(self) -> None:
        now = self._monotonic()
        next_allowed = self._not_before
        if self._last_request is not None:
            next_allowed = max(next_allowed, self._last_request + MIN_REQUEST_GAP_SECONDS)
        delay = next_allowed - now
        if delay > 0:
            self._sleep(delay)
        self._last_request = self._monotonic()


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def query_text(job: QueryJob) -> str:
    bbox = ",".join(str(value) for value in job.bbox)
    selector = (
        f'nwr["power"~"substation|switch|plant"]({bbox});'
        if job.kind == "infrastructure"
        else f'way["power"="line"]({bbox});'
    )
    output = "out center tags;" if job.kind == "infrastructure" else "out tags center;"
    return f"[out:json][timeout:90][maxsize:134217728];\n{selector}\n{output}\n"


def _default_transport(query: str) -> tuple[bytes, Message]:
    body = urlencode({"data": query}).encode()
    request = Request(
        OVERPASS_URL,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    with urlopen(request, timeout=120) as response:  # noqa: S310 - fixed public endpoint
        return response.read(), response.headers


def _retry_after(headers: Message | None, now: datetime | None = None) -> float:
    if headers is not None:
        value = headers.get("Retry-After")
        if value and value.isdigit():
            return max(30.0, float(value))
        if value:
            try:
                retry_at = parsedate_to_datetime(value)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=UTC)
                return max(30.0, (retry_at - (now or datetime.now(UTC))).total_seconds())
            except (TypeError, ValueError, OverflowError):
                pass
    return 30.0


def _request(
    query: str,
    transport: Transport,
    limiter: RateLimiter,
    request_counter: list[int],
) -> tuple[bytes, Message, int]:
    last_status: int | None = None
    last_message = "request failed"
    attempts = 0
    for retry in range(MAX_RETRIES + 1):
        if request_counter[0] >= MAX_REQUESTS:
            raise RequestLimitError(f"bounded request limit ({MAX_REQUESTS}) reached")
        limiter.wait()
        request_counter[0] += 1
        attempts += 1
        try:
            raw, headers = transport(query)
            return raw, headers, retry + 1
        except HTTPError as exc:
            last_status = exc.code
            last_message = f"HTTP {exc.code}"
            if exc.code == 429:
                delay = _retry_after(exc.headers)
                limiter.defer(delay)
                if delay > MAX_SERVER_COOLDOWN_SECONDS:
                    message = f"HTTP {exc.code}; Retry-After {delay:.0f}s exceeds run budget"
                    raise QueryFailed(exc.code, message, attempts, stop_live_requests=True) from exc
                if retry == MAX_RETRIES:
                    break
                continue
            if exc.code != 504 or retry == MAX_RETRIES:
                break
            limiter.defer(10.0 * (2**retry))
        except (TimeoutError, URLError) as exc:
            last_message = type(exc).__name__
            if retry == MAX_RETRIES:
                break
            limiter.defer(10.0 * (2**retry))
    raise QueryFailed(last_status, last_message, attempts)


def _split(job: QueryJob) -> list[QueryJob]:
    south, west, north, east = job.bbox
    mid_lat = (south + north) / 2
    mid_lon = (west + east) / 2
    boxes = [
        (south, west, mid_lat, mid_lon),
        (south, mid_lon, mid_lat, east),
        (mid_lat, west, north, mid_lon),
        (mid_lat, mid_lon, north, east),
    ]
    return [QueryJob(job.kind, bbox, job.depth + 1, f"{job.suffix}-{index}") for index, bbox in enumerate(boxes)]


def _paths(output_root: Path, job: QueryJob) -> tuple[Path, Path]:
    stem = f"{job.kind}-{job.suffix}"
    return output_root / "queries" / f"{stem}.overpassql", output_root / "raw" / f"{stem}.json"


def _payload(raw: bytes) -> dict[str, Any]:
    parsed = json.loads(raw)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("elements"), list):
        raise ValueError("Overpass response is not a JSON object with an elements array")
    if parsed.get("remark"):
        raise ValueError(f"Overpass returned a runtime remark: {parsed['remark']}")
    return parsed


def _query_sha(query: str) -> str:
    return hashlib.sha256(query.encode()).hexdigest()


def _entry_base(output_root: Path, job: QueryJob, query_path: Path, query: str) -> dict[str, Any]:
    return {
        "bbox": list(job.bbox),
        "depth": job.depth,
        "kind": job.kind,
        "query_path": query_path.relative_to(output_root).as_posix(),
        "query_sha256": _query_sha(query),
        "suffix": job.suffix,
    }


def _prior_matches(
    output_root: Path,
    job: QueryJob,
    query_path: Path,
    raw_path: Path,
    query: str,
    prior: dict[str, Any] | None,
    *,
    require_raw: bool,
) -> tuple[bool, str]:
    if prior is None:
        return False, "cache has no provenance entry"
    expected = _entry_base(output_root, job, query_path, query)
    for key in ("bbox", "depth", "kind", "query_path", "query_sha256", "suffix"):
        if prior.get(key) != expected[key]:
            return False, f"cache provenance mismatch: {key}"
    if not query_path.exists() or query_path.read_text(encoding="utf-8") != query:
        return False, "cached query text does not match"
    if not require_raw:
        return True, ""
    raw_rel = raw_path.relative_to(output_root).as_posix()
    if prior.get("status") != "complete" or prior.get("raw_path") != raw_rel:
        return False, "cache provenance does not identify a complete raw response"
    if not isinstance(prior.get("retrieved_at"), str):
        return False, "cache has no retained retrieval timestamp"
    if not raw_path.exists():
        return False, "raw cache file is missing"
    raw = raw_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != prior.get("sha256"):
        return False, "raw cache hash does not match provenance"
    return True, ""


def _cache_entry(
    output_root: Path,
    job: QueryJob,
    query_path: Path,
    raw_path: Path,
    raw: bytes,
    payload: dict[str, Any],
    attempts: int,
    retrieved_at: str,
) -> dict[str, Any]:
    raw_rel = raw_path.relative_to(output_root).as_posix()
    return {
        **_entry_base(output_root, job, query_path, query_text(job)),
        "attempts": attempts,
        "bytes": len(raw),
        "cache_hit": False,
        "elements": len(payload["elements"]),
        "osm_base_timestamp": payload.get("osm3s", {}).get("timestamp_osm_base"),
        "raw_path": raw_rel,
        "retrieved_at": retrieved_at,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "status": "complete",
    }


def run_inventory(
    output_root: Path | None = None,
    *,
    live: bool = False,
    transport: Transport = _default_transport,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    clock: Clock = utc_now,
) -> dict[str, Any]:
    """Fetch/cache both specified regions and write a normalized inventory with honest status."""
    output_root = output_root or REPO_ROOT / "data" / "osm"
    output_root.mkdir(parents=True, exist_ok=True)
    started_at = clock()
    limiter = RateLimiter(sleep=sleep, monotonic=monotonic)
    request_counter = [0]
    pending = [QueryJob("infrastructure", INFRASTRUCTURE_BBOX), QueryJob("line", LINE_BBOX)]
    entries: list[dict[str, Any]] = []
    infrastructure_payloads: list[dict[str, Any]] = []
    completed_kinds: set[str] = set()
    failed_kinds: set[str] = set()
    total_raw_bytes = 0
    prior_by_job: dict[tuple[str, str], dict[str, Any]] = {}
    manifest_path = output_root / "manifest.json"
    if manifest_path.exists():
        try:
            prior = json.loads(manifest_path.read_text(encoding="utf-8"))
            prior_by_job = {
                (entry["kind"], entry["suffix"]): entry
                for entry in prior.get("queries", [])
                if isinstance(entry, dict)
                and isinstance(entry.get("kind"), str)
                and isinstance(entry.get("suffix"), str)
            }
        except (OSError, ValueError):
            prior_by_job = {}

    while pending:
        job = pending.pop(0)
        query = query_text(job)
        query_path, raw_path = _paths(output_root, job)
        query_path.parent.mkdir(parents=True, exist_ok=True)
        prior_entry = prior_by_job.get((job.kind, job.suffix))
        prior_is_split, _ = _prior_matches(
            output_root, job, query_path, raw_path, query, prior_entry, require_raw=False
        )
        if prior_is_split and prior_entry is not None and prior_entry.get("status") == "split":
            replayed_split = dict(prior_entry)
            replayed_split["cache_hit"] = True
            entries.append(replayed_split)
            pending[0:0] = _split(job)
            continue
        try:
            cache_matches, cache_reason = _prior_matches(
                output_root, job, query_path, raw_path, query, prior_entry, require_raw=True
            )
            if cache_matches:
                raw = raw_path.read_bytes()
                payload = _payload(raw)
                entry = dict(prior_entry)
                entry["cache_hit"] = True
                entry["attempts"] = max(1, int(entry.get("attempts", 0)))
            elif not live:
                if not query_path.exists():
                    query_path.write_text(query, encoding="utf-8")
                raise QueryFailed(None, f"{cache_reason}; live retrieval disabled", 0)
            else:
                query_path.write_text(query, encoding="utf-8")
                raw, _, attempts = _request(query, transport, limiter, request_counter)
                payload = _payload(raw)
                if len(raw) > MAX_RAW_FILE_BYTES:
                    if job.depth >= MAX_SPLIT_DEPTH:
                        raise QueryFailed(None, f"response exceeds {MAX_RAW_FILE_BYTES} bytes", attempts)
                    entries.append(
                        {
                            **_entry_base(output_root, job, query_path, query),
                            "attempts": attempts,
                            "bytes": len(raw),
                            "reason": "response_too_large",
                            "status": "split",
                        }
                    )
                    pending[0:0] = _split(job)
                    continue
                if total_raw_bytes + len(raw) > MAX_TOTAL_RAW_BYTES:
                    raise QueryFailed(None, f"run exceeds {MAX_TOTAL_RAW_BYTES} cached bytes", attempts)
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_path.write_bytes(raw)
                entry = _cache_entry(output_root, job, query_path, raw_path, raw, payload, attempts, clock())
            entries.append(entry)
            total_raw_bytes += len(raw)
            if job.kind == "infrastructure":
                payload["_cache_path"] = entry["raw_path"]
                infrastructure_payloads.append(payload)
            completed_kinds.add(job.kind)
        except QueryFailed as exc:
            if exc.stop_live_requests:
                live = False
            if exc.status == 504 and job.depth < MAX_SPLIT_DEPTH:
                entries.append(
                    {
                        **_entry_base(output_root, job, query_path, query),
                        "attempts": exc.attempts,
                        "http_status": exc.status,
                        "reason": str(exc),
                        "status": "split",
                    }
                )
                pending[0:0] = _split(job)
                continue
            failed_kinds.add(job.kind)
            entries.append(
                {
                    **_entry_base(output_root, job, query_path, query),
                    "attempts": exc.attempts,
                    "http_status": exc.status,
                    "reason": str(exc),
                    "status": "unavailable",
                }
            )
        except (RequestLimitError, ValueError) as exc:
            failed_kinds.add(job.kind)
            entries.append(
                {
                    **_entry_base(output_root, job, query_path, query),
                    "reason": str(exc),
                    "status": "unavailable",
                }
            )

    normalized, counts = normalize_elements(infrastructure_payloads)
    required_kinds = {"infrastructure", "line"}
    if completed_kinds == required_kinds and not failed_kinds:
        status = "complete"
    elif completed_kinds:
        status = "partial"
    else:
        status = "unavailable"

    # A partial inventory is retained for inspection, but the status is explicit so F09
    # does not silently treat incomplete coverage as complete evidence.
    write_json(output_root / "substations.json", normalized)
    manifest = {
        "attribution": {
            "license": "Open Data Commons Open Database License (ODbL) 1.0",
            "license_url": "https://opendatacommons.org/licenses/odbl/1.0/",
            "notice": "Data © OpenStreetMap contributors",
            "source_url": "https://www.openstreetmap.org/copyright",
        },
        "bboxes": {
            "infrastructure": list(INFRASTRUCTURE_BBOX),
            "line": list(LINE_BBOX),
        },
        "counts": {
            **counts,
            "infrastructure_elements": sum(
                entry.get("elements", 0) for entry in entries if entry["kind"] == "infrastructure"
            ),
            "line_elements": sum(entry.get("elements", 0) for entry in entries if entry["kind"] == "line"),
        },
        "endpoint": OVERPASS_URL,
        "finished_at": clock(),
        "landmark_verification": verify_landmarks(normalized),
        "normalization_version": "osm-inventory-v1",
        "queries": entries,
        "requests_made": request_counter[0],
        "retrieval_requests": sum(entry.get("attempts", 0) for entry in entries),
        "started_at": started_at,
        "status": status,
        "total_raw_bytes": total_raw_bytes,
    }
    write_json(output_root / "manifest.json", manifest)
    return manifest
