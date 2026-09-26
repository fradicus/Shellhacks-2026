import json
from collections import Counter
from copy import deepcopy

import pytest

from common import REPO_ROOT
from national.build import load_snapshot, validate_snapshot_values


def test_committed_snapshot_has_measured_not_national_claims():
    snapshot = load_snapshot(REPO_ROOT)
    projects, coverage = snapshot["projects"], snapshot["coverage"]
    assert len(projects) == coverage["projects_total"] == 1_286
    assert coverage["located_count"] == 69
    iso = [project for project in projects if project["source_id"] == "iso-ne-rsp-2026-06"]
    legacy = [project for project in projects if project["_id"].startswith("legacy:")]
    assert len(iso) == 1_024
    assert len(legacy) == 262
    assert Counter(project["status_group"] for project in iso) == {
        "planned": 37,
        "under_construction": 7,
        "proposed": 2,
        "in_service": 643,
        "cancelled": 335,
    }
    assert Counter(project["location_review"] for project in projects) == {
        "unlocated": 1_207,
        "needs_review": 69,
        "rejected": 10,
    }
    assert all(project["center"] is None for project in iso)
    assert all(project["counties"] == [] for project in projects)
    assert "nationwide project completeness" in coverage["notes"][0]


def test_iso_rows_preserve_source_precision_and_row_evidence():
    projects = {project["_id"]: project for project in load_snapshot(REPO_ROOT)["projects"]}
    assert projects["iso-ne:1926"]["in_service"] == {
        "raw": "2026-06-01T00:00:00",
        "value": "2026-06",
        "precision": "month",
    }
    assert projects["iso-ne:1917"]["in_service"]["value"] == "2028-12"
    assert projects["iso-ne:1917"]["evidence"]["raw"]["Projected In-Service Month/Year"].startswith("2028-12-31")
    assert projects["iso-ne:1535"]["in_service"] == {"raw": "2016", "value": "2016", "precision": "year"}
    assert projects["iso-ne:1397"]["in_service"] == {"raw": "TBD", "value": None, "precision": "unknown"}
    unknown = projects["iso-ne:1161"]
    assert unknown["states"] == [] and unknown["center"] is None and unknown["geography_basis"] is None
    assert unknown["evidence"]["sheet"] == "RSP_sortable" and unknown["evidence"]["row"] == 777


def test_catalog_entries_do_not_invent_counts_or_state_footprints():
    sources = load_snapshot(REPO_ROOT)["sources"]
    catalog = [source for source in sources if source["import_status"] == "catalogued"]
    assert len(catalog) == 11
    assert all(source["project_count"] is None and source["states"] == [] for source in catalog)
    assert all(source["access_policy"] == "catalog_only" and source["sha256"] is None for source in catalog)
    westconnect = next(source for source in catalog if source["planning_region"] == "westconnect")
    assert "not yet been updated" in westconnect["notes"][0]
    scrtp = next(source for source in catalog if source["planning_region"] == "scrtp")
    assert "no completed transition" in scrtp["notes"][0]


def test_snapshot_json_is_canonical_utf8():
    for name in ("sources", "projects", "geography", "coverage"):
        path = REPO_ROOT / "data" / "national" / f"{name}.json"
        parsed = json.loads(path.read_text(encoding="utf-8"))
        assert path.read_text(encoding="utf-8") == json.dumps(
            parsed, indent=2, sort_keys=True, ensure_ascii=False
        ) + "\n"


def invalid_unknown_state(snapshot):
    snapshot["projects"][0]["states"] = ["99"]


def invalid_unknown_county(snapshot):
    snapshot["projects"][0]["counties"] = ["99999"]


def invalid_cross_state_county(snapshot):
    snapshot["projects"][0]["states"] = ["25"]
    snapshot["projects"][0]["counties"] = ["06001"]


def invalid_evidence_hash(snapshot):
    snapshot["projects"][0]["evidence"]["source_sha256"] = "0" * 64


def invalid_duplicate_source(snapshot):
    snapshot["sources"].append(deepcopy(snapshot["sources"][0]))


def invalid_coverage_count(snapshot):
    snapshot["coverage"]["sources"][0]["project_count"] = 999_999


def invalid_catalog_source(snapshot):
    catalog = next(source for source in snapshot["sources"] if source["import_status"] == "catalogued")
    snapshot["projects"][0]["source_id"] = catalog["_id"]


@pytest.mark.parametrize(
    "mutation",
    [
        invalid_unknown_state,
        invalid_unknown_county,
        invalid_cross_state_county,
        invalid_evidence_hash,
        invalid_duplicate_source,
        invalid_coverage_count,
        invalid_catalog_source,
    ],
)
def test_cross_record_validator_rejects_invalid_bindings(mutation):
    snapshot = deepcopy(load_snapshot(REPO_ROOT))
    mutation(snapshot)
    assert validate_snapshot_values(snapshot)
