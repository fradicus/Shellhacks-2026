"""C46 shared route client and store. No network: the HTTP opener and the router are faked."""

import io
import json
import urllib.error

import pytest

from common import match_id, validate
from matches import osrm
from matches.routes import drives_for, fetch_missing, is_current, route_summary

A = {"lat": 32.3, "lon": -80.9}
B = {"lat": 32.2, "lon": -81.0}
BASE = "https://osrm.test"

OK_PAYLOAD = {
    "code": "Ok",
    "routes": [{"distance": 16093.4, "duration": 1234.4, "geometry": "abc"}],
    "waypoints": [{"location": [-80.91, 32.31], "distance": 42.04}, {"location": [-81.01, 32.19], "distance": 7.0}],
}


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def opener_returning(*outcomes):
    calls = []

    def opener(req, timeout):
        calls.append(req.full_url)
        outcome = outcomes[len(calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return FakeResponse(json.dumps(outcome).encode())

    opener.calls = calls
    return opener


def http_error(code, body=b'{"code":"x"}'):
    return urllib.error.HTTPError(BASE, code, "err", {}, io.BytesIO(body))


def test_request_url_is_lon_lat_driving_full_geometry():
    url = osrm.request_url(A, B, BASE)
    assert url.startswith(f"{BASE}/route/v1/driving/-80.9000000,32.3000000;-81.0000000,32.2000000?")
    assert "overview=full" in url and "alternatives=false" in url


def test_parse_ok_route():
    r = osrm.parse_response(OK_PAYLOAD)
    assert r["status"] == "ok"
    assert r["drive_mi"] == pytest.approx(16093.4 / 1609.344)
    assert r["duration_s"] == 1234
    assert r["start"] == {"lat": 32.31, "lon": -80.91}
    assert r["snap_m"] == [42.0, 7.0]


@pytest.mark.parametrize("payload", [{"code": "NoRoute"}, {"code": "NoSegment"}, {"code": "Ok", "routes": []}])
def test_no_route_stays_null(payload):
    r = osrm.parse_response(payload)
    assert r["status"] == "no_route" and r["drive_mi"] is None and r["polyline"] is None


def test_unknown_code_is_an_error():
    with pytest.raises(osrm.RoutesError, match="InvalidQuery"):
        osrm.parse_response({"code": "InvalidQuery"})


def test_compute_route_stamps_provenance():
    r = osrm.compute_route(A, B, base=BASE, opener=opener_returning(OK_PAYLOAD))
    assert r["provider"] == "osrm:osrm.test" and r["travel_mode"] == "DRIVE"
    assert r["data_source"].startswith("OpenStreetMap")
    assert r["computed_at"].endswith("Z")


def test_no_route_http_400_is_a_result_not_an_error():
    r = osrm.compute_route(A, B, base=BASE, opener=opener_returning(http_error(400, b'{"code":"NoRoute"}')))
    assert r["status"] == "no_route"


def test_transient_errors_retry(monkeypatch):
    monkeypatch.setattr(osrm.time, "sleep", lambda s: None)
    opener = opener_returning(http_error(429), OK_PAYLOAD)
    assert osrm.compute_route(A, B, base=BASE, opener=opener)["status"] == "ok"
    assert len(opener.calls) == 2


def test_client_error_does_not_retry(monkeypatch):
    monkeypatch.setattr(osrm.time, "sleep", lambda s: None)
    opener = opener_returning(http_error(400))
    with pytest.raises(osrm.RoutesError, match="HTTP 400"):
        osrm.compute_route(A, B, base=BASE, opener=opener)
    assert len(opener.calls) == 1


def _pair():
    pa = {"project_key": "DESC:1", "center": dict(A)}
    pb = {"project_key": "GPC:1", "center": dict(B)}
    return pa, pb, 7.0


MID = match_id("DESC:1", "GPC:1")


def test_drives_for_states():
    c = [_pair()]
    ok = {"_id": MID, "origin": A, "destination": B, "status": "ok", "drive_mi": 9.5}
    assert drives_for(c, {}) == ({MID: None}, {MID: "missing"})
    assert drives_for(c, {MID: ok}) == ({MID: 9.5}, {MID: "ok"})
    moved = {**ok, "origin": {"lat": 32.4, "lon": -80.9}}
    assert drives_for(c, {MID: moved}) == ({MID: None}, {MID: "stale"})
    none = {**ok, "status": "no_route", "drive_mi": None}
    assert drives_for(c, {MID: none}) == ({MID: None}, {MID: "no_route"})


def test_is_current_needs_both_ends():
    assert is_current({"origin": A, "destination": B}, A, B)
    assert not is_current({"origin": A}, A, B)
    assert not is_current(None, A, B)


def fake_compute(result):
    calls = []

    def compute(origin, destination):
        calls.append((origin, destination))
        if isinstance(result, Exception):
            raise result
        return osrm.compute_route(origin, destination, base=BASE, opener=opener_returning(result))

    compute.calls = calls
    return compute


def test_fetch_missing_requests_only_missing_and_validates():
    compute = fake_compute(OK_PAYLOAD)
    records, failures = fetch_missing([_pair()], {}, compute=compute, sleep=lambda s: None, log=lambda m: None)
    assert failures == 0 and len(compute.calls) == 1
    [record] = records
    validate(record, "route")
    assert (record["_id"], record["origin"], record["destination"]) == (MID, A, B)
    assert set(route_summary(record)) >= {"provider", "polyline", "start", "end", "snap_m"}
    again, _ = fetch_missing([_pair()], {MID: record}, compute=compute, sleep=lambda s: None, log=lambda m: None)
    assert again == [record] and len(compute.calls) == 1  # current routes are never re-requested


def test_fetch_failure_stays_unknown_and_drops_stale_record():
    stale = {"_id": MID, "origin": {"lat": 0.0, "lon": 0.0}, "destination": B, "status": "ok", "drive_mi": 1.0}
    compute = fake_compute(osrm.RoutesError("down"))
    records, failures = fetch_missing([_pair()], {MID: stale}, compute=compute, sleep=lambda s: None,
                                      log=lambda m: None)
    assert failures == 1 and records == []


def test_fetch_keeps_only_current_candidates():
    orphan = {"_id": "DESC:9__GPC:9"}
    records, _ = fetch_missing([], {"DESC:9__GPC:9": orphan}, sleep=lambda s: None, log=lambda m: None)
    assert records == []
