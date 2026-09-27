"""F15 coverage ledger denominators and unavailable metrics."""

import copy

from common import REPO_ROOT, load_json, validate
from coverage.core import summarize
from load.build import collect


def current():
    records, errors, _ = collect(REPO_ROOT)
    assert errors == []
    return records


def test_current_source_counts_and_effective_review_states():
    rows = {row["_id"]: row["counts"] for row in summarize(
        current(), load_json(REPO_ROOT / "data/extraction/eval.json"),
        load_json(REPO_ROOT / "reports/audit/evidence.json"),
    )}
    assert set(rows) == {"desc-2024", "desc-2025", "gpc-2025", "sample"}
    assert (rows["desc-2024"]["project_versions"], rows["desc-2024"]["active_projects"]) == (44, 7)
    assert rows["desc-2024"]["filed_endpoint_projects_all_versions"] == {"0": 4, "1": 13, "2": 27}
    assert (rows["desc-2025"]["located_endpoints"], rows["desc-2025"]["unlocated_active_projects"]) == (16, 31)
    assert (rows["gpc-2025"]["project_versions"], rows["gpc-2025"]["located_endpoints"]) == (208, 73)
    assert rows["gpc-2025"]["endpoint_confidence"] == {"high": 0, "medium": 73, "low": 0, "rejected": 264}
    assert rows["gpc-2025"]["active_by_utility"] == {"GPC": 138, "unknown": 70}
    assert rows["sample"]["coverage_scope"] == "fixture_reference_only"
    assert rows["sample"]["project_versions"] is None
    assert rows["desc-2025"]["effective_match_states"] == {"needs_review": 3, "rejected": 2}
    assert rows["desc-2025"]["global"] == rows["gpc-2025"]["global"]
    assert rows["desc-2025"]["global"]["audit_review_counts"] == {
        "pairs": 15, "endpoints": 14, "confirmed": 0, "downgraded": 29,
    }
    assert rows["desc-2025"]["global"]["gemini"]["status"] == "unavailable"
    assert all("gemini" not in row for row in rows.values())  # one global DESC evaluation, not per-source accuracy


def test_all_location_records_and_project_denominators_reconcile():
    rows = [row["counts"] for row in summarize(current())]
    assert sum(row["project_versions"] or 0 for row in rows) == 299
    assert sum(row["active_projects"] or 0 for row in rows) == 262
    assert sum(row["location_records"] or 0 for row in rows) == 400
    assert sum(row["located_endpoints"] or 0 for row in rows) == 89
    confidence = {key: sum((row["endpoint_confidence"] or {}).get(key, 0) for row in rows)
                  for key in ("high", "medium", "low", "rejected")}
    assert confidence == {"high": 0, "medium": 89, "low": 0, "rejected": 311}


def test_missing_optional_inputs_are_null_and_inputs_are_not_mutated():
    records = current()
    before = copy.deepcopy(records)
    rows = summarize(records)
    assert records == before
    assert rows[0]["counts"]["global"]["gemini"] is None
    assert rows[0]["counts"]["global"]["audit_review_counts"] is None
    assert rows[0]["counts"]["global"]["manual_source_audit"] is None
    for row in rows:
        validate(row, "coverage")


def test_empty_real_source_is_not_mislabeled_as_fixture():
    source = load_json(REPO_ROOT / "data/sources/sources.json")[0]
    [row] = summarize({"sources": [source], "projects": [], "locations": [], "matches": [], "reviews": [],
                       "briefs": [], "extractions": [], "coverage": [], "version_changes": []})
    assert row["counts"]["coverage_scope"] == "not_ingested"
    assert row["counts"]["project_versions"] is None
