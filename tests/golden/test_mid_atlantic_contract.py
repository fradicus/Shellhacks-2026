"""C28 structural boundaries; examples are synthetic, never publication approvals."""
from copy import deepcopy

import pytest

from common import validate
from common.schema import SchemaError


def southeast_example():
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


def mid_atlantic_example():
    # C28 intentionally shares C27 acquisition/review/event structures.
    result = southeast_example()
    result["schema_version"] = "mid-atlantic-release-v1"
    project = result["projects"][0]
    project.update(_id="mid-atlantic:fixture:1", source_id="mid-atlantic:fixture-source", states=["36"])
    result["sources"] = [{
        "_id": project["source_id"], "title": "Synthetic contract fixture", "publisher": "Fixture publisher",
        "authority": "state_government", "role": "project_plan", "landing_url": "https://example.com/fixture",
        "download_url": "https://example.com/fixture", "publication_date": None, "vintage": None,
        "retrieved_at": "2025-01-01T00:00:00Z", "sha256": "0" * 64, "public_status": "verified_public",
        "import_status": "imported", "access_policy": "public_document", "planning_region": None,
        "states": ["36"], "notes": ["Synthetic schema fixture; not approved source data."],
    }]
    result["dispositions"][0].update(source_id=project["source_id"], project_id=project["_id"])
    result["acquisition"][0]["source_id"] = project["source_id"]
    result["expected_counts"]["new_sources"] = 1
    return result


@pytest.mark.parametrize("state", ["10", "11", "24", "34", "36", "42"])
def test_each_mid_atlantic_state_and_evidenced_cross_border_records(state):
    example = mid_atlantic_example()
    example["projects"][0]["states"] = [state]
    validate(example, "mid-atlantic-release")
    example["projects"][0]["states"].append("51")
    validate(example, "mid-atlantic-release")
    # C27 retains its own namespace and state boundary.
    with pytest.raises(SchemaError):
        validate(example, "southeast-release")
    validate(southeast_example(), "southeast-release")


@pytest.mark.parametrize(("field", "value"), [
    ("_id", "southeast:fixture:1"), ("_id", "mid-atlantic:missing-native-id"),
    ("_id", "mid-atlantic::1"), ("states", ["51", "54"]), ("states", ["09"]), ("states", []),
    ("center", {"lat": 40, "lon": -75, "basis": "source_point", "evidence": "Synthetic example"}),
    ("location_review", "confirmed"), ("location_verification", {}), ("project_events", []),
])
def test_inputs_cannot_bypass_scope_identity_or_location_projection(field, value):
    example = mid_atlantic_example()
    example["projects"][0][field] = value
    with pytest.raises(SchemaError):
        validate(example, "mid-atlantic-release")


@pytest.mark.parametrize(("field", "value"), [
    ("_id", "southeast:fixture-source"), ("_id", "mid-atlantic:"),
    ("role", "existing_infrastructure_reference"), ("import_status", "reference_only"),
])
def test_sources_use_separate_namespace_and_imported_project_role(field, value):
    example = mid_atlantic_example()
    example["sources"][0][field] = value
    with pytest.raises(SchemaError):
        validate(example, "mid-atlantic-release")


def test_reused_acquisition_review_and_location_requirements():
    example = mid_atlantic_example()
    for field, value in [
        ("identity_review", None), ("location_verifications", [{}]), ("projects", []),
        ("acquisition", []), ("dispositions", []), ("unexpected", True),
        ("schema_version", "southeast-release-v1"),
    ]:
        bad = deepcopy(example)
        bad[field] = value
        with pytest.raises(SchemaError):
            validate(bad, "mid-atlantic-release")
    for mutation in ["missing-enumeration", "duplicate-row", "pending-review", "accepted-null", "excluded-project"]:
        bad = deepcopy(example)
        if mutation == "missing-enumeration":
            bad["acquisition"][0]["enumeration_evidence"] = []
        elif mutation == "duplicate-row":
            bad["acquisition"][0]["row_locators"] *= 2
        elif mutation == "pending-review":
            bad["identity_review"]["decision"] = "pending"
        elif mutation == "accepted-null":
            bad["dispositions"][0]["project_id"] = None
        else:
            bad["dispositions"][0]["disposition"] = "excluded"
        with pytest.raises(SchemaError):
            validate(bad, "mid-atlantic-release")


def test_partial_unknown_denominators_and_unlocated_history_remain_representable():
    example = mid_atlantic_example()
    acquisition = example["acquisition"][0]
    acquisition.update(expected_source_rows=None, completeness="bounded_partial")
    example["project_events"] = [{"project_id": example["projects"][0]["_id"], "events": [{
        "id": "fixture-certification", "type": "certification", "date": "2025", "precision": "year",
        "native_project_link": "fixture-1", "description": "Synthetic permit, not completion",
        "evidence": acquisition["enumeration_evidence"],
    }]}]
    validate(example, "mid-atlantic-release")
    assert example["projects"][0]["center"] is None
    assert example["projects"][0]["in_service"] == {"raw": None, "value": None, "precision": "unknown"}
