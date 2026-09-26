from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from common.io import REPO_ROOT, load_json
from common.schema import validate
from locations.boundaries import StateBoundaries, ensure_boundary_cache
from locations.core import canonical_json_sha256, grade_candidates, location_id


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

    raw.write_bytes(raw.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="cached Census bytes changed"):
        ensure_boundary_cache(target)


def test_generated_full_corpus_is_schema_valid_version_bound_and_single_acceptance() -> None:
    locations = load_json(REPO_ROOT / "data/locations/locations.json")
    reviews = load_json(REPO_ROOT / "data/review/locations/geo.json")
    coverage = load_json(REPO_ROOT / "data/locations/coverage.json")

    assert len(locations) == 402
    assert len(reviews) == 402
    assert coverage["totals"]["active_projects"] == 262
    assert coverage["totals"]["filed_endpoints"] == 402
    assert coverage["totals"]["zero_endpoint_projects"] == 23
    assert coverage["coverage_scope"] == "full"
    assert coverage["confidence_policy"]["state_membership_is_fine_area_evidence"] is False
    assert len(coverage["source_gates"]["endpoint_ambiguous"]) == 23
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

    assert {review["record_id"] for review in reviews} == ids
    for review in reviews:
        validate(review, "review")


def test_source_conflicts_and_okatie_sanity_remain_unlocated() -> None:
    locations = load_json(REPO_ROOT / "data/locations/locations.json")
    coverage = load_json(REPO_ROOT / "data/locations/coverage.json")

    west_point = [record for record in locations if record["project_id"] == "GPC:20482@gpc-2025"]
    assert len(west_point) == 2
    assert all(record["confidence"] == "rejected" for record in west_point)
    assert all("source_gate:source_status_conflict" in record["limitations"] for record in west_point)

    scope_conflict = [record for record in locations if record["project_id"] == "DESC:6238 H@desc-2025"]
    assert len(scope_conflict) == 2
    assert all(record["confidence"] == "rejected" for record in scope_conflict)
    assert all(
        "source_gate:filed_title_and_description_endpoint_scope_conflict" in record["limitations"]
        for record in scope_conflict
    )

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
