from __future__ import annotations

import json
from datetime import UTC, datetime
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError

import pytest

from common import REPO_ROOT, load_json
from osm.fetch import INFRASTRUCTURE_BBOX, LINE_BBOX, QueryJob, _retry_after, query_text, run_inventory
from osm.normalize import normalize_elements, verify_landmarks

SAMPLE = Path(__file__).with_name("test_f04_fixtures") / "overpass_sample.json"
RECORDED = Path(__file__).with_name("test_f04_fixtures") / "overpass_recorded_2026-09-26.json"


class FakeTime:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def response(elements: list[dict] | None = None) -> tuple[bytes, Message]:
    payload = {
        "elements": elements or [],
        "osm3s": {"timestamp_osm_base": "2026-09-26T00:00:00Z"},
        "version": 0.6,
    }
    return json.dumps(payload, separators=(",", ":")).encode(), Message()


def test_normalizer_preserves_context_unknowns_precision_and_coordinate_method():
    payload = load_json(SAMPLE)
    payload["_cache_path"] = "raw/infrastructure-full.json"
    records, counts = normalize_elements([payload])

    assert [record["osm_id"] for record in records] == ["node/101", "node/404", "relation/303", "way/202"]
    thurmond = records[0]
    assert thurmond["norm"] == "THURMOND DAM"
    assert thurmond["lat"] == 33.6601234567 and thurmond["lon"] == -82.1959123456
    assert thurmond["coordinate_method"] == "node_coordinates"
    assert thurmond["raw_cache_paths"] == ["raw/infrastructure-full.json"]
    assert thurmond["tags"]["voltage"] == "230000;115000"

    unnamed = records[1]
    assert unnamed["name"] is None and unnamed["norm"] == "" and unnamed["operator"] is None
    assert unnamed["lat"] is None and unnamed["coordinate_method"] == "unavailable"
    assert records[-1]["coordinate_method"] == "overpass_bbox_center"
    assert records[-1]["county"] == "Effingham County"
    assert counts == {
        "conflicting_duplicates": 0,
        "duplicate_elements": 1,
        "excluded_power_values": {},
        "missing_coordinates": 1,
        "missing_name": 1,
        "missing_operator": 3,
        "normalized": 4,
        "with_operator": 1,
    }


def test_normalizer_on_recorded_overpass_sample_preserves_missing_okatie_name():
    records, counts = normalize_elements([load_json(RECORDED)])
    assert counts["normalized"] == 3 and counts["with_operator"] == 2
    assert records[0]["osm_id"] == "way/52102019" and records[0]["norm"] == "THURMOND"
    assert records[1]["osm_id"] == "way/121624352" and records[1]["norm"] == "MCINTOSH"
    assert records[2]["osm_id"] == "way/1064022697" and records[2]["name"] is None
    verification = verify_landmarks(records)
    assert verification["status"] == "partial" and verification["matched"] == 2
    okatie = next(item for item in verification["items"] if item["keyword"] == "OKATIE")
    assert okatie["status"] == "missing_named_candidate"
    assert okatie["nearest_any"]["osm_id"] == "way/1064022697"
    assert okatie["nearest_any"]["name"] is None and okatie["nearest_any"]["distance_mi"] < 1


def test_queries_begin_with_full_spec_bboxes():
    infrastructure = query_text(QueryJob("infrastructure", INFRASTRUCTURE_BBOX))
    line = query_text(QueryJob("line", LINE_BBOX))
    assert 'nwr["power"~"substation|switch|plant"](30.3,-85.7,35.3,-78.5);' in infrastructure
    assert 'way["power"="line"](31.8,-82.6,33.9,-80.6);' in line


def test_serial_live_run_caches_exact_responses_and_waits_between_full_queries(tmp_path):
    fake_time = FakeTime()
    calls: list[str] = []
    raw_responses = [response([load_json(SAMPLE)["elements"][0]]), response()]

    def transport(query: str) -> tuple[bytes, Message]:
        calls.append(query)
        return raw_responses[len(calls) - 1]

    manifest = run_inventory(
        tmp_path / "osm",
        live=True,
        transport=transport,
        sleep=fake_time.sleep,
        monotonic=fake_time.monotonic,
        clock=lambda: "2026-09-26T12:00:00Z",
    )

    assert manifest["status"] == "complete" and manifest["requests_made"] == 2
    assert manifest["retrieval_requests"] == 2
    assert len(calls) == 2 and fake_time.sleeps == [10.0]
    for index, entry in enumerate(manifest["queries"]):
        assert (tmp_path / "osm" / entry["raw_path"]).read_bytes() == raw_responses[index][0]
        assert (tmp_path / "osm" / entry["query_path"]).read_text(encoding="utf-8") == calls[index]
        assert entry["retrieved_at"] == "2026-09-26T12:00:00Z"
    assert manifest["attribution"]["notice"] == "Data © OpenStreetMap contributors"
    [record] = load_json(tmp_path / "osm" / "substations.json")
    assert record["raw_cache_paths"] == ["raw/infrastructure-full.json"]

    replay = run_inventory(
        tmp_path / "osm",
        live=False,
        transport=lambda query: pytest.fail(f"unexpected request: {query}"),
        clock=lambda: "2099-01-01T00:00:00Z",
    )
    assert replay["status"] == "complete" and replay["requests_made"] == 0
    assert replay["retrieval_requests"] == 2
    assert all(entry["retrieved_at"] == "2026-09-26T12:00:00Z" for entry in replay["queries"])


def test_504_retries_three_times_then_splits_the_timed_out_region(tmp_path):
    fake_time = FakeTime()
    full_infrastructure_attempts = 0

    def transport(query: str) -> tuple[bytes, Message]:
        nonlocal full_infrastructure_attempts
        if "(30.3,-85.7,35.3,-78.5)" in query:
            full_infrastructure_attempts += 1
            raise HTTPError("https://example.invalid", 504, "timeout", Message(), None)
        return response()

    manifest = run_inventory(
        tmp_path / "osm",
        live=True,
        transport=transport,
        sleep=fake_time.sleep,
        monotonic=fake_time.monotonic,
        clock=lambda: "2026-09-26T12:00:00Z",
    )

    assert full_infrastructure_attempts == 4
    split = next(entry for entry in manifest["queries"] if entry["kind"] == "infrastructure" and entry["depth"] == 0)
    assert split["status"] == "split" and split["attempts"] == 4
    children = [
        entry for entry in manifest["queries"] if entry["kind"] == "infrastructure" and entry["depth"] == 1
    ]
    assert len(children) == 4 and all(entry["status"] == "complete" for entry in children)
    assert manifest["status"] == "complete"

    replay = run_inventory(
        tmp_path / "osm",
        live=False,
        transport=lambda query: pytest.fail(f"unexpected request: {query}"),
        clock=lambda: "2099-01-01T00:00:00Z",
    )
    assert replay["status"] == "complete" and replay["requests_made"] == 0
    assert len([entry for entry in replay["queries"] if entry["kind"] == "infrastructure"]) == 5


def test_exhausted_429_is_partial_and_records_failure_without_splitting(tmp_path):
    fake_time = FakeTime()
    infrastructure_attempts = 0

    def transport(query: str) -> tuple[bytes, Message]:
        nonlocal infrastructure_attempts
        if "nwr" in query:
            infrastructure_attempts += 1
            raise HTTPError("https://example.invalid", 429, "rate limit", Message(), None)
        return response()

    manifest = run_inventory(
        tmp_path / "osm",
        live=True,
        transport=transport,
        sleep=fake_time.sleep,
        monotonic=fake_time.monotonic,
        clock=lambda: "2026-09-26T12:00:00Z",
    )

    assert infrastructure_attempts == 4
    assert manifest["status"] == "partial"
    failed = next(entry for entry in manifest["queries"] if entry["kind"] == "infrastructure")
    assert failed["status"] == "unavailable" and failed["http_status"] == 429
    assert len([entry for entry in manifest["queries"] if entry["kind"] == "infrastructure"]) == 1
    assert any(delay >= 30 for delay in fake_time.sleeps)
    assert load_json(tmp_path / "osm" / "substations.json") == []


def test_http_200_remark_is_not_accepted_as_complete(tmp_path):
    fake_time = FakeTime()

    def transport(query: str) -> tuple[bytes, Message]:
        if "nwr" in query:
            payload = {"elements": [{"type": "node", "id": 1}], "remark": "runtime error: timed out"}
            return json.dumps(payload).encode(), Message()
        return response()

    manifest = run_inventory(
        tmp_path / "osm",
        live=True,
        transport=transport,
        sleep=fake_time.sleep,
        monotonic=fake_time.monotonic,
        clock=lambda: "2026-09-26T12:00:00Z",
    )

    assert manifest["status"] == "partial"
    failed = next(entry for entry in manifest["queries"] if entry["kind"] == "infrastructure")
    assert failed["status"] == "unavailable" and "runtime remark" in failed["reason"]
    assert not (tmp_path / "osm" / "raw" / "infrastructure-full.json").exists()


def test_offline_cache_rejects_query_or_raw_hash_mismatch_without_inventing_timestamp(tmp_path):
    fake_time = FakeTime()
    manifest = run_inventory(
        tmp_path / "osm",
        live=True,
        transport=lambda query: response(),
        sleep=fake_time.sleep,
        monotonic=fake_time.monotonic,
        clock=lambda: "2026-09-26T12:00:00Z",
    )
    assert manifest["status"] == "complete"
    query_path = tmp_path / "osm" / "queries" / "infrastructure-full.overpassql"
    query_path.write_text("stale query", encoding="utf-8")

    replay = run_inventory(tmp_path / "osm", live=False, clock=lambda: "2099-01-01T00:00:00Z")
    failed = next(entry for entry in replay["queries"] if entry["kind"] == "infrastructure")
    assert failed["status"] == "unavailable" and "query text" in failed["reason"]
    assert "retrieved_at" not in failed

    # Restore the query binding but corrupt the exact response: provenance must still reject it.
    (tmp_path / "osm" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    query_path.write_text(query_text(QueryJob("infrastructure", INFRASTRUCTURE_BBOX)), encoding="utf-8")
    raw_path = tmp_path / "osm" / "raw" / "infrastructure-full.json"
    raw_path.write_bytes(response([{"id": 9, "type": "node", "tags": {"power": "substation"}}])[0])
    replay = run_inventory(tmp_path / "osm", live=False, clock=lambda: "2099-01-01T00:00:00Z")
    failed = next(entry for entry in replay["queries"] if entry["kind"] == "infrastructure")
    assert failed["status"] == "unavailable" and "hash" in failed["reason"]


def test_retry_after_http_date_is_parsed_and_excessive_cooldown_stops(tmp_path):
    headers = Message()
    headers["Retry-After"] = "Sat, 26 Sep 2026 12:05:00 GMT"
    assert _retry_after(headers, datetime(2026, 9, 26, 12, 0, tzinfo=UTC)) == 300

    fake_time = FakeTime()
    infrastructure_attempts = 0

    def transport(query: str) -> tuple[bytes, Message]:
        nonlocal infrastructure_attempts
        if "nwr" in query:
            infrastructure_attempts += 1
            long_headers = Message()
            long_headers["Retry-After"] = "600"
            raise HTTPError("https://example.invalid", 429, "rate limit", long_headers, None)
        return response()

    manifest = run_inventory(
        tmp_path / "osm",
        live=True,
        transport=transport,
        sleep=fake_time.sleep,
        monotonic=fake_time.monotonic,
        clock=lambda: "2026-09-26T12:00:00Z",
    )
    assert infrastructure_attempts == 1 and manifest["status"] == "unavailable"
    failed = next(entry for entry in manifest["queries"] if entry["kind"] == "infrastructure")
    assert failed["attempts"] == 1 and "exceeds run budget" in failed["reason"]
    line = next(entry for entry in manifest["queries"] if entry["kind"] == "line")
    assert line["status"] == "unavailable" and line["attempts"] == 0
    assert 600 not in fake_time.sleeps


def test_final_429_cooldown_is_honored_before_next_query(tmp_path):
    fake_time = FakeTime()
    call_times: list[tuple[str, float]] = []

    def transport(query: str) -> tuple[bytes, Message]:
        call_times.append(("infrastructure" if "nwr" in query else "line", fake_time.now))
        if "nwr" in query:
            headers = Message()
            headers["Retry-After"] = "45"
            raise HTTPError("https://example.invalid", 429, "rate limit", headers, None)
        return response()

    manifest = run_inventory(
        tmp_path / "osm",
        live=True,
        transport=transport,
        sleep=fake_time.sleep,
        monotonic=fake_time.monotonic,
        clock=lambda: "2026-09-26T12:00:00Z",
    )
    assert call_times == [
        ("infrastructure", 0.0),
        ("infrastructure", 45.0),
        ("infrastructure", 90.0),
        ("infrastructure", 135.0),
        ("line", 180.0),
    ]
    assert manifest["status"] == "partial"


def test_immediate_non_retryable_error_records_actual_attempt_count(tmp_path):
    fake_time = FakeTime()

    def transport(query: str) -> tuple[bytes, Message]:
        if "nwr" in query:
            raise HTTPError("https://example.invalid", 400, "bad query", Message(), None)
        return response()

    manifest = run_inventory(
        tmp_path / "osm",
        live=True,
        transport=transport,
        sleep=fake_time.sleep,
        monotonic=fake_time.monotonic,
        clock=lambda: "2026-09-26T12:00:00Z",
    )
    failed = next(entry for entry in manifest["queries"] if entry["kind"] == "infrastructure")
    assert failed["attempts"] == 1 and failed["http_status"] == 400


def test_live_cache_contains_named_landmarks_within_one_mile():
    manifest_path = REPO_ROOT / "data" / "osm" / "manifest.json"
    raw_dir = REPO_ROOT / "data" / "osm" / "raw"
    if not manifest_path.exists() or not raw_dir.exists() or not list(raw_dir.glob("infrastructure-*.json")):
        pytest.skip("F04 raw Overpass cache is not present")
    manifest = load_json(manifest_path)
    verification = manifest["landmark_verification"]
    items = {item["keyword"]: item for item in verification["items"]}
    assert verification["status"] == "partial" and set(items) == {"THURMOND", "MCINTOSH", "OKATIE"}
    for keyword in ("THURMOND", "MCINTOSH"):
        assert items[keyword]["status"] == "matched"
        assert items[keyword]["nearest_named_distance_mi"] < 1.0
    assert items["OKATIE"]["status"] == "missing_named_candidate"
    assert items["OKATIE"]["nearest_named_osm_id"] is None
    assert items["OKATIE"]["nearest_any"]["name"] is None
    assert items["OKATIE"]["nearest_any"]["distance_mi"] < 1.0
