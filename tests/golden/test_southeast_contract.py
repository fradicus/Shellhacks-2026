"""Additive release schema boundary, using explicitly synthetic contract examples."""
from copy import deepcopy

import pytest

from common import validate
from common.schema import SchemaError


def release():
    return {
        "schema_version": "southeast-release-v1", "release_id": "fixture-only",
        "created_at": "2026-01-01T00:00:00Z", "producer": "fixture-producer",
        "sources": [], "projects": [{
            "_id": "southeast:fixture:1", "source_id": "fixture-source", "native_id": "fixture-1",
            "name": "Synthetic schema example", "owner": None, "other_owners": [], "planning_region": None,
            "states": ["12"], "counties": [], "geography_basis": "synthetic fixture",
            "status": None, "status_group": "unknown", "in_service": {"raw": None, "value": None, "precision": "unknown"},
            "center": None, "location_review": "unlocated", "evidence": {"page": None, "sheet": None, "row": None, "raw": {}},
        }], "location_verifications": [], "project_events": [],
        "dispositions": [{"source_id": "fixture-source", "locator": "fixture-row", "disposition": "accepted",
                          "project_id": "southeast:fixture:1", "reason": "synthetic fixture"}],
        "acquisition": [{"source_id": "fixture-source", "scope": "synthetic fixture", "row_locators": ["fixture-row"],
                         "expected_source_rows": 1, "completeness": "complete", "enumeration_evidence": [{
                             "publisher": "Fixture publisher", "url": "https://example.com/fixture", "artifact_sha256": "0" * 64,
                             "locator": "fixture-row", "source_date": None, "retrieved_at": "2025-01-01T00:00:00Z",
                             "access_review": "Synthetic fixture", "facts": "One synthetic row"}]}],
        "expected_counts": {"new_sources": 0, "new_projects": 1, "confirmed_projects": 0, "source_rows": 1},
        "coverage_notes": ["Schema fixture only: missing source references must fail producer semantic validation."],
        "identity_review": {"reviewer": "fixture-reviewer", "reviewed_at": "2026-01-01T00:00:00Z",
                            "facts_sha256": "0" * 64, "decision": "approved", "evidence": "Synthetic example"},
    }


def test_contract_requires_unlocated_input_and_preserves_national_schema():
    valid = release()
    validate(valid, "southeast-release")
    cases = [
        ("_id", "legacy:fixture:1"), ("states", ["09"]), ("location_review", "confirmed"),
        ("center", {"lat": 28, "lon": -81, "basis": "source_point", "evidence": "synthetic"}),
        ("location_verification", {}), ("project_events", []), ("in_service", {"raw": None, "value": "2026-01-01", "precision": "unknown"}),
    ]
    for field, value in cases:
        bad = deepcopy(valid)
        bad["projects"][0][field] = value
        with pytest.raises(SchemaError):
            validate(bad, "southeast-release")
    # Cross-border work is retained when the project has an evidenced Southeast state.
    valid["projects"][0]["states"] = ["51", "24"]
    validate(valid, "southeast-release")


def test_contract_requires_identity_approval_and_typed_location_records():
    for field, value in [("identity_review", None), ("location_verifications", [{}]), ("projects", [])]:
        bad = release()
        bad[field] = value
        with pytest.raises(SchemaError):
            validate(bad, "southeast-release")
    bad = release()
    bad["identity_review"]["decision"] = "pending"
    with pytest.raises(SchemaError):
        validate(bad, "southeast-release")


def test_unlocated_history_and_acquisition_binding_are_structural_requirements():
    valid = release()
    event = {"id": "fixture-event", "type": "certification", "date": "2025", "precision": "year",
             "native_project_link": "fixture-1", "description": "Synthetic permit event, not completion",
             "evidence": valid["acquisition"][0]["enumeration_evidence"]}
    valid["project_events"] = [{"project_id": "southeast:fixture:1", "events": [event]}]
    validate(valid, "southeast-release")
    project = deepcopy(valid["projects"][0])
    project["project_events"] = [event]
    validate(project, "national-project")
    assert project["center"] is None
    for change in ["missing-acquisition", "duplicate-row", "accepted-null", "excluded-project"]:
        bad = deepcopy(valid)
        if change == "missing-acquisition":
            del bad["acquisition"]
        elif change == "duplicate-row":
            bad["acquisition"][0]["row_locators"] *= 2
        elif change == "accepted-null":
            bad["dispositions"][0]["project_id"] = None
        else:
            bad["dispositions"][0]["disposition"] = "excluded"
        with pytest.raises(SchemaError):
            validate(bad, "southeast-release")
