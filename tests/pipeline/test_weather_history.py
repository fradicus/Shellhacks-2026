import json

from common.io import REPO_ROOT
from weather_history.core import WINDOW, aligned, candidates, completeness, days, nearest, project_centers


def loc(pid, key, lat, lon, confidence="high", utility="DESC"):
    return {"project_id": pid, "project_key": key, "project_utility": utility,
            "lat": lat, "lon": lon, "confidence": confidence}


def test_centers_use_the_canonical_rule_and_skip_rejected_or_unlocated_endpoints():
    rows = [
        loc("DESC:1@desc-2025", "DESC:1", 32.0, -81.0), loc("DESC:1@desc-2025", "DESC:1", 33.0, -80.0),
        loc("DESC:2@desc-2025", "DESC:2", 30.0, -80.0, confidence="rejected"),
        loc("GPC:3@gpc-2025", "GPC:3", None, None, utility="GPC"),
        loc("X:4@x", "X:4", 31.0, -81.0, utility="OTHER"),
    ]
    out = project_centers(rows)
    assert [c["project_key"] for c in out] == ["DESC:1"]
    assert (out[0]["lat"], out[0]["lon"]) == (32.5, -80.5)


def station(sid, lat, lon, types):
    dt = [{"id": t, "startDate": s, "endDate": e} for t, (s, e) in types.items()]
    st = {"id": sid, "name": sid, "dataTypes": dt, "platforms": [{"id": "COOP"}]}
    return {"location": {"coordinates": [lon, lat]}, "stations": [st]}


FULL = ("1990-01-01T00:00:00", "2026-09-01T23:59:59")


def test_candidates_require_prcp_and_tmax_spanning_the_whole_window():
    results = [
        station("A", 32, -81, {"PRCP": FULL, "TMAX": FULL, "WSF2": FULL}),
        station("B", 32, -81, {"PRCP": FULL}),
        station("C", 32, -81, {"PRCP": ("2018-01-01", FULL[1]), "TMAX": FULL}),
    ]
    got = candidates(results)
    assert [s["id"] for s in got] == ["A"]
    assert got[0]["has_wind"] is True


def test_series_align_to_every_window_day_and_missing_stays_missing():
    rows = [{"DATE": WINDOW[0].isoformat(), "PRCP": "0.41", "TMAX": "66", "WSF2": "13.0"},
            {"DATE": "2016-01-03", "PRCP": "", "TMAX": "70"}]
    s = aligned(rows)
    assert len(s["prcp_in"]) == len(days()) == 3653
    assert s["prcp_in"][:3] == [0.41, None, None]
    assert s["tmax_f"][:3] == [66, None, 70]
    assert s["wsf2_mph"][0] == 13.0
    assert completeness([1.0, None, 2.0, None]) == 0.5


def test_nearest_skips_rejected_stations_and_respects_the_distance_cap():
    stations = [{"id": "near", "lat": 32.0, "lon": -81.0}, {"id": "next", "lat": 32.1, "lon": -81.0},
                {"id": "far", "lat": 35.0, "lon": -81.0}]
    point = {"lat": 32.0, "lon": -81.0}
    s, miles = nearest(point, stations, 30, lambda st: st["id"] != "near")
    assert s["id"] == "next" and 6.8 < miles < 7.0
    assert nearest(point, stations, 30, lambda st: st["id"] == "far") == (None, None)


def test_committed_index_matches_station_files():
    index = json.loads((REPO_ROOT / "data" / "weather_history" / "index.json").read_text())
    files = {p.stem for p in (REPO_ROOT / "data" / "weather_history" / "stations").glob("*.json")}
    assert files == set(index["stations"])
    for p in index["projects"]:
        assert p["rain_station"] in files and p["rain_distance_mi"] <= index["selection"]["rain_max_mi"]
        assert p["wind_station"] is None or p["wind_distance_mi"] <= index["selection"]["wind_max_mi"]
    first = index["projects"][0]["rain_station"]
    sample = json.loads((REPO_ROOT / "data" / "weather_history" / "stations" / f"{first}.json").read_text())
    assert len(sample["prcp_in"]) == len(sample["tmax_f"]) == len(sample["wsf2_mph"]) == 3653
    assert sample["source"]["url"].startswith("https://www.ncei.noaa.gov/")
