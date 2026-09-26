from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from common.io import REPO_ROOT, load_json, write_json
from common.schema import validate
from locations.boundaries import StateBoundaries, ensure_boundary_cache
from locations.build import build_locations, review_endpoint
from locations.core import AUTO_REVIEW_VERSION, candidate_index, canonical_json_sha256, grade_candidates, location_id


def _candidate(**changes: object) -> dict[str, object]:
    candidate: dict[str, object] = {
        "coordinate_method": "node_coordinates",
        "decision": "rejected",
        "match_type": "exact",
        "operator_status": "match",
        "osm_id": "node/1",
        "power": "substation",
        "state_evidence": "home_state_only",
        "voltage_status": "match",
    }
    candidate.update(changes)
    return candidate


def test_grading_requires_context_and_never_uses_candidate_order() -> None:
    candidate = _candidate()
    confidence, selected, limitations = grade_candidates([candidate], fine_area_verified=False)
    assert confidence == "medium"
    assert selected == candidate
    assert limitations == ["project_area_unverified"]

    confidence, selected, limitations = grade_candidates([candidate], fine_area_verified=True)
    assert confidence == "high"
    assert selected == candidate
    assert limitations == []

    conflict = _candidate(osm_id="node/2", voltage_status="conflict")
    for candidates in ([conflict, candidate], [candidate, conflict]):
        confidence, selected, _ = grade_candidates(candidates, fine_area_verified=False)
        assert confidence == "medium"
        assert selected == candidate

    tied = _candidate(osm_id="node/3")
    confidence, selected, reasons = grade_candidates([candidate, tied], fine_area_verified=True)
    assert confidence == "rejected"
    assert selected is None
    assert reasons == ["multiple_contextually_viable_candidates"]


def test_fuzzy_requires_fine_area_evidence_and_none_stays_rejected() -> None:
    fuzzy = _candidate(match_type="fuzzy", similarity=0.91)
    confidence, selected, reasons = grade_candidates([fuzzy], fine_area_verified=False)
    assert confidence == "rejected"
    assert selected is None
    assert reasons == ["fuzzy_name_without_fine_area_evidence"]

    confidence, selected, _ = grade_candidates([fuzzy], fine_area_verified=True)
    assert confidence == "low"
    assert selected == fuzzy

    confidence, selected, reasons = grade_candidates([])
    assert confidence == "rejected"
    assert selected is None
    assert reasons == ["no_named_osm_candidate"]


def test_location_identity_binds_versioned_endpoint_and_selected_evidence() -> None:
    expected = location_id("GPC:20010@gpc-2025", 0, "ANTHONY SHOALS", "way/171540506")
    assert expected == location_id("GPC:20010@gpc-2025", 0, "ANTHONY SHOALS", "way/171540506")
    assert expected != location_id("GPC:20010@gpc-2024", 0, "ANTHONY SHOALS", "way/171540506")
    assert expected != location_id("GPC:20010@gpc-2025", 1, "ANTHONY SHOALS", "way/171540506")
    assert expected != location_id("GPC:20010@gpc-2025", 0, "ANTHONY SHOALS", "way/999")


def test_canonical_input_fingerprint_ignores_json_formatting() -> None:
    left = json.loads('{"b": 2, "a": [1]}')
    right = json.loads('{\r\n  "a": [1],\r\n  "b": 2\r\n}')
    assert canonical_json_sha256(left) == canonical_json_sha256(right)


def test_boundary_cache_is_query_bound_hash_verified_and_axis_safe(tmp_path: Path) -> None:
    source = REPO_ROOT / "data/locations/boundaries"
    target = tmp_path / "boundaries"
    shutil.copytree(source, target)
    manifest = ensure_boundary_cache(target)
    raw = target / manifest["raw_geojson_path"]
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == manifest["raw_geojson_sha256"]

    boundaries = StateBoundaries.load(target)
    assert boundaries.state_for(-84.388, 33.749) == "GA"
    assert boundaries.state_for(33.749, -84.388) is None
    threshold_point = (-81.965, 33.69194063469767)
    assert boundaries.state_for(*threshold_point) == "SC"
    assert boundaries.distance_to_state_miles(*threshold_point, "GA") == pytest.approx(10.0087473281, abs=1e-6)

    raw.write_bytes(raw.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="cached Census bytes changed"):
        ensure_boundary_cache(target)


def test_other_state_candidate_requires_filed_tie_evidence() -> None:
    class CrossBorderBoundary:
        def state_for(self, lon: float, lat: float) -> str:
            return "SC"

        def distance_to_state_miles(self, lon: float, lat: float, state: str) -> float:
            return 5.0

    project = {
        "_id": "GPC:QA@gpc-qa",
        "active": True,
        "endpoints": [{"name": "Alpha", "norm": "ALPHA", "raw": "Alpha"}],
        "field_evidence": {"name": {"page": 1, "quote": "Alpha substation equipment replacement"}},
        "name": "Alpha substation equipment replacement",
        "project_key": "GPC:QA",
        "quality_flags": [],
        "source": {"page": 1, "source_id": "gpc-qa"},
        "utility": "GPC",
        "voltages_kv": [115],
    }
    osm = {
        "coordinate_method": "node_coordinates",
        "lat": 33.5,
        "lon": -81.965,
        "name": "Alpha",
        "norm": "ALPHA",
        "operator": "Georgia Power",
        "osm_id": "node/900000001",
        "osm_url": "https://www.openstreetmap.org/node/900000001",
        "power": "substation",
        "voltage": "115000",
    }
    index = candidate_index([osm])
    rejected = review_endpoint(project, project["endpoints"][0], 0, index, CrossBorderBoundary())
    assert rejected["confidence"] == "rejected" and "lat" not in rejected
    assert "cross_border_tie_evidence_missing" in rejected["candidates"][0]["reasons"]

    tied = {
        **project,
        "field_evidence": {"name": {"page": 1, "quote": "Alpha - Beta 115 kV Tie Line"}},
        "name": "Alpha - Beta 115 kV Tie Line",
    }
    accepted = review_endpoint(tied, tied["endpoints"][0], 0, index, CrossBorderBoundary())
    assert accepted["confidence"] == "medium" and accepted["osm_id"] == osm["osm_id"]
    evidence = accepted["candidates"][0]["cross_border_tie_evidence"]
    assert evidence == {"field": "name", "page": 1, "quote": tied["name"], "source_id": "gpc-qa"}


def _minimal_repo(root: Path) -> dict[str, object]:
    project: dict[str, object] = {
        "_id": "GPC:QA@gpc-qa",
        "active": True,
        "endpoints": [{"name": "Alpha", "norm": "ALPHA", "raw": "Alpha"}],
        "name": "Alpha equipment replacement",
        "project_key": "GPC:QA",
        "quality_flags": [],
        "source": {"page": 1, "source_id": "gpc-qa"},
        "utility": "GPC",
        "voltages_kv": [115],
    }
    write_json(root / "data/projects/desc.json", [])
    write_json(root / "data/projects/gpc.json", [project])
    write_json(root / "data/osm/substations.json", [])
    shutil.copytree(REPO_ROOT / "data/locations/boundaries", root / "data/locations/boundaries")
    return project


def test_review_history_is_append_only_latest_replay_safe_and_a_b_a_safe(tmp_path: Path) -> None:
    project = _minimal_repo(tmp_path)
    review_path = tmp_path / "data/review/locations/geo.json"
    build_locations(repo_root=tmp_path, review_at="2026-09-26T12:00:00Z")
    first = load_json(review_path)
    assert len(first) == 1 and first[0]["decision_version"] == AUTO_REVIEW_VERSION

    build_locations(repo_root=tmp_path, review_at="2026-09-26T13:00:00Z")
    assert load_json(review_path) == first

    changed = {**project, "quality_flags": ["source_status_conflict"]}
    write_json(tmp_path / "data/projects/gpc.json", [changed])
    build_locations(repo_root=tmp_path, review_at="2026-09-26T13:00:00Z")
    second = load_json(review_path)
    assert len(second) == 2 and second[-1]["supersedes"] == first[-1]["_id"]
    assert second[-1]["reason"] != first[-1]["reason"]

    write_json(tmp_path / "data/projects/gpc.json", [project])
    build_locations(repo_root=tmp_path, review_at="2026-09-26T14:00:00Z")
    third = load_json(review_path)
    assert len(third) == 3 and len({review["_id"] for review in third}) == 3
    assert third[-1]["reason"] == first[-1]["reason"]
    assert third[-1]["supersedes"] == second[-1]["_id"]
    assert datetime.fromisoformat(third[-1]["at"]).astimezone(UTC) > datetime.fromisoformat(second[-1]["at"]).astimezone(UTC)

    build_locations(repo_root=tmp_path, review_at="2026-09-26T15:00:00Z")
    assert load_json(review_path) == third


def test_provisional_midnight_review_is_preserved_and_superseded(tmp_path: Path) -> None:
    _minimal_repo(tmp_path)
    review_path = tmp_path / "data/review/locations/geo.json"
    build_locations(repo_root=tmp_path, review_at="2026-09-26T12:00:00Z")
    current = load_json(review_path)[0]
    legacy = {
        "_id": "review:v1:provisional",
        "at": "2026-09-26T00:00:00Z",
        "reason": current["reason"],
        "record_id": current["record_id"],
        "reviewer": "f09-deterministic-rules-v1",
        "verdict": current["verdict"],
    }
    write_json(review_path, [legacy])
    build_locations(repo_root=tmp_path, review_at="2026-09-26T12:00:00Z")
    repaired = load_json(review_path)
    assert repaired[0] == legacy
    assert repaired[1]["supersedes"] == legacy["_id"]
    assert repaired[1]["supersession_reason"] == "supersedes_provisional_midnight_v1"


def test_generated_full_corpus_is_schema_valid_version_bound_and_single_acceptance() -> None:
    locations = load_json(REPO_ROOT / "data/locations/locations.json")
    reviews = load_json(REPO_ROOT / "data/review/locations/geo.json")
    coverage = load_json(REPO_ROOT / "data/locations/coverage.json")

    assert len(locations) == 400
    assert len(reviews) == 802
    assert coverage["totals"]["active_projects"] == 262
    assert coverage["totals"]["filed_endpoints"] == 400
    assert coverage["totals"]["zero_endpoint_projects"] == 24
    assert coverage["coverage_scope"] == "full"
    assert coverage["confidence_policy"]["state_membership_is_fine_area_evidence"] is False
    assert len(coverage["source_gates"]["endpoint_ambiguous"]) == 24
    assert [item["project_id"] for item in coverage["source_gates"]["source_status_conflict"]] == [
        "GPC:20482@gpc-2025"
    ]

    ids = set()
    for record in locations:
        validate(record, "location")
        assert record["_id"] not in ids
        ids.add(record["_id"])
        assert record["project_id"].endswith("@" + record["source_id"])
        accepted = [candidate for candidate in record["candidates"] if candidate["decision"] == "accepted"]
        assert len(accepted) <= 1
        if record["confidence"] == "rejected":
            assert not accepted
            assert "lat" not in record and "lon" not in record and "osm_id" not in record
        else:
            assert len(accepted) == 1
            assert record["osm_id"] == accepted[0]["osm_id"]
            assert record["_id"] == location_id(
                record["project_id"], record["endpoint_index"], record["norm"], record["osm_id"]
            )

    assert len({review["_id"] for review in reviews}) == len(reviews)
    current_reviews = [review for review in reviews if review.get("decision_version") == AUTO_REVIEW_VERSION]
    assert len(current_reviews) == 400
    assert {review["record_id"] for review in current_reviews} == ids
    assert all(review["at"] != "2026-09-26T00:00:00Z" for review in current_reviews)
    for review in reviews:
        validate(review, "review")


def test_source_conflicts_and_okatie_sanity_remain_unlocated() -> None:
    locations = load_json(REPO_ROOT / "data/locations/locations.json")
    coverage = load_json(REPO_ROOT / "data/locations/coverage.json")

    west_point = [record for record in locations if record["project_id"] == "GPC:20482@gpc-2025"]
    assert len(west_point) == 2
    assert all(record["confidence"] == "rejected" for record in west_point)
    assert all("source_gate:source_status_conflict" in record["limitations"] for record in west_point)

    assert not [record for record in locations if record["project_id"] == "DESC:6238 H@desc-2025"]
    scope_conflict = next(
        item
        for item in coverage["source_gates"]["endpoint_ambiguous"]
        if item["project_id"] == "DESC:6238 H@desc-2025"
    )
    assert "endpoint_scope_ambiguous" in scope_conflict["quality_flags"]

    project = coverage["sanity_checks"]["DESC:6888"]
    assert project["status"] == "partial"
    assert project["okatie"]["confidence"] == "rejected"
    assert project["okatie"]["named_candidate_count"] == 0
    assert project["okatie"]["unnamed_diagnostic"] == {
        "coordinate_method": "overpass_bbox_center",
        "name": None,
        "operator": None,
        "osm_id": "way/1064022697",
        "status": "candidate_only_not_asserted_as_okatie",
        "voltage": "230000",
    }
    assert project["mcintosh"]["confidence"] == "rejected"
    assert project["mcintosh"]["candidate_ids"] == ["way/121624352"]
