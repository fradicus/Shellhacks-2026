"""F10 adapter tests: full-corpus identity guards and sponsor golden through one run path."""

from __future__ import annotations

import copy

import pytest

from common import REPO_ROOT, load_json, validate
from match_run.build import _verify_f09_identity, run_match_adapter
from matches import core
from matches.routes import load_routes

ANALYSIS_DATE = "2026-09-26"


def _project(
    key: str,
    utility: str,
    *,
    source_id: str = "synthetic-source",
    active: bool = True,
    flags: list[str] | None = None,
) -> dict:
    return {
        "_id": f"{key}@{source_id}",
        "active": active,
        "center": {"lat": -80.0, "lon": 170.0, "basis": "two"},
        "endpoints": [{"name": f"{key} endpoint", "norm": f"{key} ENDPOINT", "raw": key}],
        "in_service": {"date": "2027-01-01", "precision": "day", "raw": "1/1/2027"},
        "project_key": key,
        "quality_flags": flags or [],
        "source": {"page": 1, "source_id": source_id},
        "utility": utility,
    }


def _location(project: dict, *, confidence: str = "high", lat: float = 33.0, lon: float = -81.0) -> dict:
    endpoint = project["endpoints"][0]
    location = {
        "_id": f"location:{project['_id']}",
        "confidence": confidence,
        "endpoint_identity": {
            "endpoint_index": 0,
            "endpoint_norm": endpoint["norm"],
            "evidence_id": "synthetic-evidence" if confidence != "rejected" else None,
            "project_id": project["_id"],
            "version": "v1",
        },
        "endpoint_index": 0,
        "evidence": "synthetic test evidence",
        "name": endpoint["name"],
        "norm": endpoint["norm"],
        "project_id": project["_id"],
        "project_key": project["project_key"],
        "project_source": project["source"],
        "project_utility": project["utility"],
        "source_id": project["source"]["source_id"],
        "source_quality_flags": project["quality_flags"],
    }
    if confidence != "rejected":
        location |= {"lat": lat, "lon": lon}
    return location


def _synthetic_pair() -> tuple[list[dict], list[dict]]:
    projects = [_project("DESC:SYNTH-A", "DESC"), _project("GPC:SYNTH-B", "GPC")]
    return projects, [_location(projects[0]), _location(projects[1], lat=33.01)]


def _golden_adapter_input() -> tuple[list[dict], list[dict], dict[str, str]]:
    projects, locations, labels = [], [], {}
    for source in load_json(REPO_ROOT / "data/fixtures/golden/projects.json"):
        key = f"{source['utility']}:{source['project_id']}"
        project = {
            "_id": f"{key}@sperry-sample",
            "active": True,
            "endpoints": [
                {"name": endpoint["name"], "norm": endpoint["name"].upper(), "raw": endpoint["name"]}
                for endpoint in source["endpoints"]
            ],
            "in_service": {
                "date": source["in_service_date"],
                "precision": "day",
                "raw": source["in_service_raw"],
            },
            "project_key": key,
            "quality_flags": [],
            "source": {"page": source["row"], "source_id": "sperry-sample"},
            "utility": source["utility"],
        }
        projects.append(project)
        for index, endpoint in enumerate(source["endpoints"]):
            confidence = "high" if endpoint["lat"] is not None and endpoint["lon"] is not None else "rejected"
            location = _location(project, confidence=confidence)
            location |= {
                "_id": f"golden:{key}:{index}",
                "endpoint_index": index,
                "name": endpoint["name"],
                "norm": endpoint["name"].upper(),
                "endpoint_identity": {
                    "endpoint_index": index,
                    "endpoint_norm": endpoint["name"].upper(),
                    "evidence_id": "sponsor-workbook" if confidence == "high" else None,
                    "project_id": project["_id"],
                    "version": "v1",
                },
            }
            if confidence == "high":
                location |= {"lat": endpoint["lat"], "lon": endpoint["lon"]}
            locations.append(location)
        labels[key] = source["project_id"]
    return projects, locations, labels


def test_sponsor_golden_uses_the_same_adapter_and_keeps_drives_within_25() -> None:
    projects, locations, _ = _golden_adapter_input()
    routes = load_routes(REPO_ROOT / "data/fixtures/golden/routes.json")
    matches, summary = run_match_adapter(projects, locations, analysis_date=ANALYSIS_DATE, routes=routes)
    sheet = load_json(REPO_ROOT / "data/fixtures/golden/overlaps.json")
    expected = {
        core.match_id(f"DESC:{row['project_id_a']}", f"GPC:{row['project_id_b']}"): row for row in sheet
    }
    within = {mid for mid in expected if routes[mid]["drive_mi"] <= core.OVERLAP_MI}
    assert summary["pairs"] == {
        "all_known_cross_utility_combinations": 25,
        "centered_cross_utility_pairs_evaluated": 25,
        "excluded_before_distance": 0,
        "within_straight_line_prefilter": len(expected),
        "route_states": {"ok": len(expected), "no_route": 0, "missing": 0, "stale": 0},
        "overlaps": len(within),
        "drive_over_limit": len(expected) - len(within),
        "spatial_nonmatches": 25 - len(within),
    }
    assert set(match["_id"] for match in matches) == within
    for match in matches:
        assert round(match["distance_mi"], 2) == expected[match["_id"]]["distance_mi"]
        assert match["drive_mi"] == routes[match["_id"]]["drive_mi"]
        assert match["time_gap_days"] == expected[match["_id"]]["time_gap_days"]
    assert [match["rank"] for match in matches] == list(range(1, len(within) + 1))


def test_no_stored_routes_means_no_overlaps() -> None:
    projects, locations, _ = _golden_adapter_input()
    matches, summary = run_match_adapter(projects, locations, analysis_date=ANALYSIS_DATE)
    assert matches == [] and summary["pairs"]["route_states"]["missing"] == 6


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda ps, ls: ls[0].__setitem__("lat", True), "finite number"),
        (lambda ps, ls: ls[0].__setitem__("lon", float("nan")), "finite and within"),
        (lambda ps, ls: ls[0].__setitem__("lat", 91.0), "finite and within"),
        (lambda ps, ls: ls[0].__setitem__("endpoint_index", False), "invalid endpoint_index"),
        (lambda ps, ls: ls[0].__setitem__("endpoint_index", -1), "invalid endpoint_index"),
        (lambda ps, ls: ls[0].__setitem__("endpoint_index", 1), "outside the filed endpoints"),
        (lambda ps, ls: ls[0].__setitem__("project_key", "DESC:OTHER"), "stale project_key"),
        (lambda ps, ls: ls[0].__setitem__("source_id", "old-source"), "stale source_id"),
        (lambda ps, ls: ls[0].__setitem__("norm", "OTHER"), "contradicts filed endpoint"),
    ],
)
def test_binding_and_coordinate_mutations_fail_closed(change, message: str) -> None:
    projects, locations = _synthetic_pair()
    change(projects, locations)
    with pytest.raises(ValueError, match=message):
        run_match_adapter(projects, locations, analysis_date=ANALYSIS_DATE)


def test_inactive_source_gated_and_duplicate_slots_fail_closed() -> None:
    projects, locations = _synthetic_pair()
    projects[0]["active"] = False
    with pytest.raises(ValueError, match="not bound to an active project version"):
        run_match_adapter(projects, locations, analysis_date=ANALYSIS_DATE)

    projects, locations = _synthetic_pair()
    projects[0]["quality_flags"] = ["source_status_conflict"]
    locations[0]["source_quality_flags"] = ["source_status_conflict"]
    with pytest.raises(ValueError, match="cannot have an accepted location"):
        run_match_adapter(projects, locations, analysis_date=ANALYSIS_DATE)

    projects, locations = _synthetic_pair()
    duplicate = _location(projects[0], confidence="rejected") | {"_id": "location:duplicate-rejected"}
    with pytest.raises(ValueError, match="duplicate location records"):
        run_match_adapter(projects, [*locations, duplicate], analysis_date=ANALYSIS_DATE)

    projects, locations = _synthetic_pair()
    locations[1]["_id"] = locations[0]["_id"]
    with pytest.raises(ValueError, match="duplicate location _id"):
        run_match_adapter(projects, locations, analysis_date=ANALYSIS_DATE)


def test_centers_are_recomputed_unknown_owners_excluded_and_replay_is_deterministic() -> None:
    projects, locations = _synthetic_pair()
    unknown = _project("GPC:SYNTH-UNKNOWN", "unknown")
    projects.append(unknown)
    locations.append(_location(unknown, lat=33.005))
    mid = core.match_id("DESC:SYNTH-A", "GPC:SYNTH-B")
    routes = {mid: {"_id": mid, "origin": {"lat": 33.0, "lon": -81.0}, "destination": {"lat": 33.01, "lon": -81.0},
                    "status": "ok", "drive_mi": 1.2, "provider": "synthetic", "travel_mode": "DRIVE",
                    "computed_at": "2026-09-26T00:00:00Z", "polyline": None}}
    first = run_match_adapter(projects, locations, analysis_date=ANALYSIS_DATE, routes=routes)
    second = run_match_adapter(projects[::-1], locations[::-1], analysis_date=ANALYSIS_DATE, routes=routes)
    assert first == second
    matches, summary = first
    assert len(matches) == 1 and matches[0]["distance_mi"] == pytest.approx(core.haversine_mi(33.0, -81.0, 33.01, -81.0))
    assert matches[0]["bindings"]["a"]["center"] == {"lat": 33.0, "lon": -81.0, "basis": "one"}
    assert summary["projects"]["excluded"]["unknown_owner"] == 1


def test_f09_semantic_identity_refuses_stale_project_or_osm_input() -> None:
    desc = load_json(REPO_ROOT / "data/projects/desc.json")
    gpc = load_json(REPO_ROOT / "data/projects/gpc.json")
    osm = load_json(REPO_ROOT / "data/osm/substations.json")
    locations = load_json(REPO_ROOT / "data/locations/locations.json")
    coverage = load_json(REPO_ROOT / "data/locations/coverage.json")
    identity = _verify_f09_identity(desc, gpc, osm, locations, coverage, ANALYSIS_DATE)
    assert identity["f09_locations"]

    stale_desc = copy.deepcopy(desc)
    stale_desc[0]["name"] += " changed"
    with pytest.raises(ValueError, match="desc_projects"):
        _verify_f09_identity(stale_desc, gpc, osm, locations, coverage, ANALYSIS_DATE)
    stale_osm = [*osm, {"osm_id": "synthetic/stale"}]
    with pytest.raises(ValueError, match="osm_substations"):
        _verify_f09_identity(desc, gpc, stale_osm, locations, coverage, ANALYSIS_DATE)


def test_committed_full_corpus_is_reproducible_and_schema_valid() -> None:
    projects = [
        *load_json(REPO_ROOT / "data/projects/desc.json"),
        *load_json(REPO_ROOT / "data/projects/gpc.json"),
    ]
    locations = load_json(REPO_ROOT / "data/locations/locations.json")
    expected_matches = load_json(REPO_ROOT / "data/matches/matches.json")
    expected_summary = load_json(REPO_ROOT / "data/matches/summary.json")
    routes = load_routes(REPO_ROOT / "data/routes/routes.json")
    matches, summary = run_match_adapter(
        projects,
        locations,
        analysis_date=ANALYSIS_DATE,
        routes=routes,
        input_identity=expected_summary["input_identity"],
    )
    assert matches == expected_matches and summary == expected_summary
    pairs = summary["pairs"]
    assert pairs["route_states"]["missing"] == pairs["route_states"]["stale"] == 0, "fetch routes: match_run --fetch-routes"
    assert sum(pairs["route_states"].values()) == pairs["within_straight_line_prefilter"]
    assert pairs["overlaps"] == len(matches) == sum(summary["overlaps_by_band"].values())
    assert all(match["review_state"] == "needs_review" for match in matches)
    assert [match["rank"] for match in matches] == list(range(1, len(matches) + 1))
    for match in matches:
        validate(match, "match")
        assert match["distance_mi"] <= match["drive_mi"] <= core.OVERLAP_MI
        assert match["drive_mi"] == routes[match["_id"]]["drive_mi"] and match["route"]["polyline"]
