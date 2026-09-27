import copy
import math
import random
from itertools import combinations

import pytest

from common import match_id
from matches.core import EARTH_RADIUS_MI, haversine_mi
from national.build import load_snapshot
from national_pairs.build import candidates, exclusion, generate, identities, owner_index, route_candidates

LEDGER = {"version": "test-only", "entries": [
    {"identities": ["a"], "aliases": ["Alpha", "A Inc"], "evidence": ["test fixture"]},
    {"identities": ["b"], "aliases": ["Beta"], "evidence": ["test fixture"]},
    {"identities": ["c"], "aliases": ["Gamma"], "evidence": ["test fixture"]},
]}


def project(key, lat=30, lon=-95, owner="Alpha", **patch):
    return {"_id": key, "owner": owner, "other_owners": [], "states": ["48"],
            "planning_region": "ERCOT", "status_group": "planned", "location_review": "confirmed",
            "center": {"lat": lat, "lon": lon, "basis": "source_point"},
            "in_service": {"value": "2028-01-01", "precision": "day"}, **patch}


def snapshot(rows):
    return {"projects": rows, "geography": {"states": [
        {"state_fips": "48", "census_region_code": "3"}, {"state_fips": "40", "census_region_code": "3"},
    ]}}


def run(rows):
    return candidates(snapshot(rows), LEDGER)


def route(pair, drive, status="ok", moved=False):
    a, b, _ = route_candidates([pair])[0]
    origin = {**a["center"], "lat": a["center"]["lat"] + (0.01 if moved else 0)}
    ok = status == "ok"
    return {"_id": match_id(pair["a"], pair["b"]), "a": pair["a"], "b": pair["b"], "origin": origin,
            "destination": b["center"], "status": status, "distance_m": drive * 1609.344 if ok else None,
            "drive_mi": drive if ok else None, "duration_s": 60 if ok else None, "polyline": "_p~iF~ps|U" if ok else None,
            "start": origin if ok else None, "end": b["center"] if ok else None, "snap_m": [0.0, 0.0] if ok else None,
            "provider": "test", "travel_mode": "DRIVE", "routing_preference": "test", "data_source": "test",
            "computed_at": "2026-09-27T00:00:00Z"}


def drive_run(rows, build):
    """generate() with routes built per prefilter pair: build(pair) -> route record or None (never fetched)."""
    found = run(rows)["pairs"]
    routes = {r["_id"]: r for r in (build(p) for p in found) if r}
    return generate(snapshot(rows), LEDGER, routes=routes)


def test_exact_cutoff_and_bands_are_unrounded():
    delta = math.degrees(25 / EARTH_RADIUS_MI)
    assert not run([project("a", 0, 0), project("b", delta + 1e-8, 0, "Beta")])["pairs"]
    assert run([project("a", 0, 0), project("b", delta - 1e-8, 0, "Beta")])["pairs"][0]["band"] == 1
    assert run([project("a"), project("b", owner="Beta")])["pairs"][0]["band"] == 0


def test_aliases_joint_owners_unknowns_and_ambiguous_ledger():
    assert not run([project("a"), project("b", owner=" a INC ")])["pairs"]
    assert not run([project("a"), project("b", owner="Beta", other_owners=["Alpha"])])["pairs"]
    assert run([project("a", owner=None)])["coverage"]["excluded"] == {"unresolved_owner": 1}
    assert identities(project("a", other_owners=["Unknown"]), owner_index(LEDGER)) is None
    ledger = copy.deepcopy(LEDGER)
    ledger["entries"][1]["aliases"].append("Alpha")
    with pytest.raises(ValueError, match="ambiguous"):
        owner_index(ledger)


def test_eligibility_and_duplicate_ids():
    for patch in ({"center": None}, {"location_review": "rejected"}, {"location_review": "needs_review"},
                  {"status_group": "in_service"}, {"status_group": "cancelled"},
                  {"location_candidate": {"tier": "county_reference"}},
                  {"center": {"lat": math.nan, "lon": 0}}, {"center": {"lat": 95, "lon": 0}}):
        assert exclusion(project("a", **patch))
    assert exclusion(project("legacy:a")) == "legacy"
    with pytest.raises(ValueError, match="duplicate"):
        run([project("a"), project("a")])


def test_dates_tiers_scope_and_stable_ids_without_mutation():
    a = project("a", states=["48", "40"])
    b = project("b", owner="Beta", states=["40"], location_review="unreviewed",
                in_service={"value": "2028-01", "precision": "month"})
    rows = [a, b]
    before = copy.deepcopy(rows)
    result = run(rows)["pairs"][0]
    assert result["time_gap_days"] is None and result["tier"] == "tentative"
    assert result["shared_states"] == ["40"] and result["shared_regions"] == ["3"]
    assert result["shared_plans"] == ["ercot"]
    assert run(list(reversed(rows)))["pairs"][0] == result
    assert rows == before
    b["in_service"] = {"value": "2028-01-03", "precision": "day"}
    assert run(rows)["pairs"][0]["time_gap_days"] == 2


def test_grid_equals_brute_force_including_poles_and_date_line():
    rng = random.Random(48)
    rows = [project(str(i), rng.uniform(-89, 89), rng.uniform(-180, 180),
                    ["Alpha", "Beta", "Gamma"][i % 3]) for i in range(500)]
    # Dense random neighborhoods plus pole/date-line cases exercise bucket boundaries.
    rows += [project(f"dense{i}", 30 + rng.uniform(-1, 1), -95 + rng.uniform(-1, 1),
                     ["Alpha", "Beta"][i % 2]) for i in range(200)]
    rows += [project("pole-a", 89.99, 0), project("pole-b", 89.99, 179, "Beta"),
             project("date-a", 0, 179.99), project("date-b", 0, -179.99, "Beta")]
    expected = {tuple(sorted((a["_id"], b["_id"]))) for a, b in combinations(rows, 2)
                if a["owner"] != b["owner"] and haversine_mi(
                    a["center"]["lat"], a["center"]["lon"], b["center"]["lat"], b["center"]["lon"]) <= 25}
    actual = run(rows)
    assert {(p["a"], p["b"]) for p in actual["pairs"]} == expected
    assert actual["coverage"]["distance_comparisons"] < len(rows) * (len(rows) - 1) / 4
    assert [p["rank"] for p in actual["pairs"]] == list(range(1, len(expected) + 1))


def test_same_owner_code_is_resolved_in_its_source_only():
    ledger = {"version": "test", "entries": [
        {"identities": ["brazos"], "aliases": ["BEPC"], "source_ids": ["ercot"], "evidence": ["test"]},
        {"identities": ["basin"], "aliases": ["BEPC"], "source_ids": ["spp"], "evidence": ["test"]},
    ]}
    owners = owner_index(ledger)
    assert identities(project("a", owner="BEPC", source_id="ercot"), owners) == {"brazos"}
    assert identities(project("b", owner="BEPC", source_id="spp"), owners) == {"basin"}
    assert identities(project("c", owner="BEPC", source_id="unmapped"), owners) is None
    ledger["entries"][1]["source_ids"].append("ercot")
    with pytest.raises(ValueError, match="ambiguous"):
        owner_index(ledger)


THREE = [project("a", 30, -95), project("b", 30.01, -95, "Beta"), project("c", 30.05, -95, "Gamma")]


def test_the_stored_drive_decides_and_ranks():
    drives = {("a", "b"): 20.0, ("a", "c"): 15.0, ("b", "c"): 25.0000001}
    result = drive_run(THREE, lambda p: route(p, drives[(p["a"], p["b"])]))
    assert [(p["a"], p["b"]) for p in result["pairs"]] == [("a", "c"), ("a", "b")]
    assert [p["rank"] for p in result["pairs"]] == [1, 2]
    first = result["pairs"][0]
    assert first["drive_mi"] == 15.0 and first["band"] == 1 and first["distance_mi"] < 10
    assert first["route"]["polyline"] == "_p~iF~ps|U" and first["rule_version"] == "national-drive-25mi-v1"
    cov = result["coverage"]
    assert cov["straight_line_candidates"] == 3 and cov["route_states"] == {"ok": 3}
    assert cov["drive_over_limit"] == 1 and cov["pairs"] == 2
    exact = drive_run(THREE[:2], lambda p: route(p, 25.0))["pairs"]
    assert exact[0]["drive_mi"] == 25.0 and exact[0]["band"] == 1
    near = drive_run(THREE[:2], lambda p: route(p, 9.99))["pairs"]
    assert near[0]["band"] == 0


def test_pairs_without_a_current_route_are_excluded_and_counted():
    build = {("a", "b"): lambda p: route(p, 5.0), ("a", "c"): lambda p: route(p, 0, status="no_route"),
             ("b", "c"): lambda p: route(p, 5.0, moved=True)}
    result = drive_run(THREE, lambda p: build[(p["a"], p["b"])](p))
    assert [(p["a"], p["b"], p["band"]) for p in result["pairs"]] == [("a", "b", 0)]
    assert result["coverage"]["route_states"] == {"no_route": 1, "ok": 1, "stale": 1}
    missing = drive_run(THREE, lambda p: None)
    assert not missing["pairs"] and missing["coverage"]["route_states"] == {"missing": 3}


def test_no_routes_file_publishes_no_pairs(tmp_path):
    result = generate(snapshot(THREE), LEDGER, root=tmp_path)
    assert not result["pairs"] and result["coverage"]["route_states"] == {"missing": 3}


def test_committed_routes_bind_to_the_published_candidates():
    result = generate(load_snapshot())
    pairs, cov = result["pairs"], result["coverage"]
    assert pairs, "the committed routes should keep at least one national pair"
    assert all(0 <= p["drive_mi"] <= 25 and p["route"]["polyline"] and p["band"] == (0 if p["drive_mi"] < 10 else 1)
               for p in pairs)
    assert [p["rank"] for p in pairs] == list(range(1, len(pairs) + 1))
    assert sum(cov["route_states"].values()) == cov["straight_line_candidates"]
    assert cov["pairs"] + cov["drive_over_limit"] == cov["route_states"].get("ok", 0)
