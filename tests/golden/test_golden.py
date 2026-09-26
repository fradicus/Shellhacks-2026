"""Golden test: the sponsor sample must yield exactly OVL_1..OVL_6 and exclude the other 19 cross-utility pairs."""

from datetime import date

import pytest

from common import REPO_ROOT, load_json, match_id
from matches.core import center, haversine_mi, is_overlap, overlaps, priority_sort, time_gap_days

GOLDEN = REPO_ROOT / "data/fixtures/golden"
ANALYSIS = date(2026, 9, 26)

EXPECTED = {  # overlap_id: (project a, project b, distance 2dp, gap days)
    "OVL_1": ("DESC_2", "GPC_1", 4.09, 3074),
    "OVL_2": ("DESC_3", "GPC_2", 5.65, 152),
    "OVL_3": ("DESC_3", "GPC_3", 7.55, 517),
    "OVL_4": ("DESC_1", "GPC_1", 8.01, 3074),
    "OVL_5": ("DESC_5", "GPC_2", 14.34, 365),
    "OVL_6": ("DESC_5", "GPC_3", 14.81, 730),
}
PRIORITY = ["OVL_2", "OVL_3", "OVL_1", "OVL_4", "OVL_5", "OVL_6"]


def key(pid: str) -> str:
    return f"{pid.split('_')[0]}:{pid}"


def golden_projects():
    return [
        {
            "project_key": key(g["project_id"]),
            "utility": g["utility"],
            "center": center(g["endpoints"]),
            "in_service": {"raw": g["in_service_raw"], "date": g["in_service_date"], "precision": "day"},
        }
        for g in load_json(GOLDEN / "projects.json")
    ]


@pytest.fixture(scope="module")
def result():
    return {m["_id"]: m for m in overlaps(golden_projects(), ANALYSIS)}


def test_exactly_six(result):
    expected_ids = {match_id(key(a), key(b)) for a, b, _, _ in EXPECTED.values()}
    assert set(result) == expected_ids


@pytest.mark.parametrize("ovl", sorted(EXPECTED))
def test_distance_and_gap(result, ovl):
    a, b, dist, gap = EXPECTED[ovl]
    m = result[match_id(key(a), key(b))]
    assert round(m["distance_mi"], 2) == dist
    assert m["time_gap_days"] == gap
    assert m["band"] == (0 if dist < 10 else 1)
    assert m["view"] == "historical"


def test_other_nineteen_excluded(result):
    ps = golden_projects()
    cross = [(p, q) for p in ps for q in ps if p["utility"] == "DESC" and q["utility"] == "GPC"]
    assert len(cross) == 25
    excluded = [(p, q) for p, q in cross if match_id(p["project_key"], q["project_key"]) not in result]
    assert len(excluded) == 19
    for p, q in excluded:
        assert not is_overlap(p, q)[0]


def test_matches_workbook_overlap_sheet(result):
    sheet = load_json(GOLDEN / "overlaps.json")
    assert [r["overlap_id"] for r in sheet] == sorted(EXPECTED)
    for r in sheet:
        m = result[match_id(key(r["project_id_a"]), key(r["project_id_b"]))]
        assert round(m["distance_mi"], 2) == r["distance_mi"]
        assert m["time_gap_days"] == r["time_gap_days"]


def test_priority_order(result):
    ranked = priority_sort(result.values())
    by_id = {match_id(key(a), key(b)): ovl for ovl, (a, b, _, _) in EXPECTED.items()}
    assert [by_id[m["_id"]] for m in ranked] == PRIORITY
    assert [m["rank"] for m in ranked] == [1, 2, 3, 4, 5, 6]


# --- boundaries -------------------------------------------------------------------------------------------------

def proj(k, utility, lat, lon, d="2027-01-01", precision="day"):
    return {
        "project_key": k,
        "utility": utility,
        "center": None if lat is None else {"lat": lat, "lon": lon, "basis": "two"},
        "in_service": {"raw": d, "date": d, "precision": precision},
    }


def lat_at_miles(miles: float, lat0: float = 33.0) -> float:
    """Latitude due north of (lat0, -81) at exactly `miles` along the meridian (haversine with R = 3958.8)."""
    from math import degrees

    return lat0 + degrees(miles / 3958.8)


@pytest.mark.parametrize("miles,hit", [(24.999, True), (25.001, False)])
def test_25_mile_boundary(miles, hit):
    a = proj("DESC:A", "DESC", 33.0, -81.0)
    b = proj("GPC:B", "GPC", lat_at_miles(miles), -81.0)
    assert abs(haversine_mi(33.0, -81.0, lat_at_miles(miles), -81.0) - miles) < 1e-9
    assert is_overlap(a, b)[0] is hit


def test_exactly_25_excluded_by_strict_less_than():
    # Float geometry can't land on exactly 25.000, so pin the distance and check the comparison itself.
    from matches import core

    orig = core.haversine_mi
    core.haversine_mi = lambda *a: 25.0
    try:
        assert core.is_overlap(proj("DESC:A", "DESC", 33, -81), proj("GPC:B", "GPC", 33, -81))[0] is False
    finally:
        core.haversine_mi = orig


def test_same_utility_excluded():
    assert overlaps([proj("DESC:A", "DESC", 33, -81), proj("DESC:B", "DESC", 33, -81)], ANALYSIS) == []


def test_unknown_utility_excluded():
    assert overlaps([proj("DESC:A", "DESC", 33, -81), proj("UNKNOWN:B", "unknown", 33, -81)], ANALYSIS) == []


def test_missing_center_excluded():
    assert overlaps([proj("DESC:A", "DESC", 33, -81), proj("GPC:B", "GPC", None, None)], ANALYSIS) == []


def test_month_precision_gap_is_null():
    a = {"raw": "2027-06", "date": "2027-06-01", "precision": "month"}
    b = {"raw": "6/1/2027", "date": "2027-06-01", "precision": "day"}
    assert time_gap_days(a, b) is None
    [m] = overlaps([proj("DESC:A", "DESC", 33, -81), proj("GPC:B", "GPC", 33.01, -81, "2027-06-01", "month")], ANALYSIS)
    assert m["time_gap_days"] is None


def test_unknown_gap_sorts_last_within_band():
    ps = [proj("DESC:A", "DESC", 33, -81), proj("GPC:B", "GPC", 33.01, -81, precision="year"),
          proj("GPC:C", "GPC", 33.05, -81, d="2027-02-01")]
    ranked = priority_sort(overlaps(ps, ANALYSIS))
    assert [m["b"] for m in ranked] == ["GPC:C", "GPC:B"]


def test_center_rules():
    assert center([{"lat": 1.0, "lon": 2.0}, {"lat": 3.0, "lon": 4.0}]) == {"lat": 2.0, "lon": 3.0, "basis": "two"}
    assert center([{"lat": 1.0, "lon": 2.0}, {"lat": None, "lon": None}]) == {"lat": 1.0, "lon": 2.0, "basis": "one"}
    assert center([{"lat": 1.0, "lon": 2.0, "confidence": "rejected"}]) is None
    assert center([]) is None


def test_views():
    fut = [proj("DESC:A", "DESC", 33, -81, "2027-01-01"), proj("GPC:B", "GPC", 33.01, -81, "2028-01-01")]
    for p in fut:
        p["location_confidence"] = "high"
    assert overlaps(fut, ANALYSIS)[0]["view"] == "future"
    fut[1]["location_confidence"] = "low"
    assert overlaps(fut, ANALYSIS)[0]["view"] == "tentative"
    fut[1]["in_service"]["date"] = "2020-01-01"
    assert overlaps(fut, ANALYSIS)[0]["view"] == "historical"
