"""Acceptance of the source-reviewed F13 artifacts and their effective loader bindings."""

import copy
import hashlib
import json
import math
from collections import Counter
from datetime import date, datetime

import pytest

from common import REPO_ROOT, load_json, validate
from load.build import collect, join_projects, stage
from load.review_subjects import FINGERPRINT_VERSION, current_subjects, subject_hash


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


@pytest.fixture(scope="module")
def audit():
    records, errors, _ = collect(REPO_ROOT)
    assert not errors
    evidence = load_json(REPO_ROOT / "reports/audit/evidence.json")
    reviews = load_json(REPO_ROOT / "data/review/audit/audit.json")
    return records, evidence, reviews


def test_verdicts_are_schema_valid_current_and_complete(audit):
    records, evidence, reviews = audit
    ready = {**records, "projects": join_projects(records["projects"], records["locations"])}
    subjects = current_subjects(ready)
    assert len(reviews) == len({r["_id"] for r in reviews}) == len({(r["subject_type"], r["record_id"]) for r in reviews})
    assert set(Counter(r["subject_type"] for r in reviews)) == {"pair", "endpoint"}
    assert {r["verdict"] for r in reviews} == {"downgraded"}
    for review in reviews:
        validate(review, "review")
        assert review["reason"] and "unverified" in review["reason"]
        assert datetime.fromisoformat(review["at"]).utcoffset().total_seconds() == 0
        assert review["at"] == (evidence["rebinding"]["at"] if review["subject_type"] == "pair" else evidence["bound_at"])
        subject = subjects[(review["subject_type"], review["record_id"])]
        assert review["fingerprint_version"] == FINGERPRINT_VERSION
        assert review["subject_snapshot"] == subject
        assert review["subject_hash"] == canonical(subject) == subject_hash(subject)


def test_top_fifteen_and_exact_supporting_endpoint_union(audit):
    records, evidence, reviews = audit
    top = sorted(records["matches"], key=lambda m: m["rank"])[:15]
    pairs = [r for r in reviews if r["subject_type"] == "pair"]
    unaudited = {u["record_id"] for u in evidence["rebinding"]["unaudited_top_pairs"]}
    assert {r["record_id"] for r in pairs} | unaudited == {m["_id"] for m in top}
    assert not unaudited & {r["record_id"] for r in pairs}
    endpoint_ids = {e["record_id"] for r in pairs for e in r["subject_snapshot"]["endpoints"]}
    endpoints = evidence["supporting_endpoints"]
    reviewed = {r["record_id"] for r in reviews if r["subject_type"] == "endpoint"}
    assert endpoint_ids <= reviewed == {e["record_id"] for e in endpoints}
    assert len({e["osm_id"] for e in endpoints}) == 9
    assert len({e["project_id"] for e in endpoints}) == 10
    for endpoint in endpoints:
        assert endpoint["confidence"] == "medium"
        assert endpoint["coordinate_method"] == "overpass_bbox_center"
        assert endpoint["coordinates_equal_raw"] and endpoint["states_independent"]
        assert endpoint["raw_county"] is None
        assert endpoint["confirmation_eligible"] is False
        assert "project_area_unverified" in endpoint["producer_limitations"]


def test_evidence_is_pinned_to_the_actual_corpus(audit):
    _, evidence, _ = audit
    values = {
        "projects": load_json(REPO_ROOT / "data/projects/desc.json") + load_json(REPO_ROOT / "data/projects/gpc.json"),
        "locations": load_json(REPO_ROOT / "data/locations/locations.json"),
        "matches": load_json(REPO_ROOT / "data/matches/matches.json"),
    }
    assert evidence["input_hashes"] == {key: canonical(value) for key, value in values.items()}
    assert evidence["input_kind"] == "canonical_F10_output"
    assert len(evidence["math_checks"]) == 2 + len(values["matches"])
    assert all(check["passed"] for check in evidence["math_checks"])
    # Reproduce the independent numerical expectations; use no production math.
    by_id = {match["_id"]: match for match in values["matches"]}
    for check in evidence["math_checks"]:
        if "expected" in check:
            expected = check["expected"]
            actual = by_id[expected["_id"]]
            assert math.isclose(actual["distance_mi"], expected["distance_mi"], rel_tol=0, abs_tol=1e-10)
            for field in ("drive_mi", "time_gap_days", "band", "rank"):
                assert actual[field] == expected[field]


def test_pair_math_recomputed_without_production_math(audit):
    records, _, _ = audit
    projects = {p["project_key"]: p for p in records["projects"] if p["active"]}
    for match in records["matches"]:
        coordinates = []
        dates = []
        for key in (match["a"], match["b"]):
            project = projects[key]
            endpoints = [e for e in records["locations"]
                         if e["project_id"] == project["_id"] and e["confidence"] != "rejected"]
            assert 1 <= len(endpoints) <= 2
            coordinates.append(tuple(sum(e[axis] for e in endpoints) / len(endpoints) for axis in ("lat", "lon")))
            filed = project["in_service"]
            dates.append(date.fromisoformat(filed["date"]) if filed["precision"] == "day" else None)
        (a, x), (b, y) = coordinates
        a, b = math.radians(a), math.radians(b)
        h = math.sin((b - a) / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(math.radians(y - x) / 2) ** 2
        distance = 7917.6 * math.atan2(math.sqrt(h), math.sqrt(1 - h))
        gap = abs((dates[0] - dates[1]).days) if all(dates) else None
        assert distance <= match["drive_mi"] <= 25
        assert math.isclose(match["distance_mi"], distance, rel_tol=0, abs_tol=1e-10)
        assert match["time_gap_days"] == gap
        assert match["band"] == (0 if match["drive_mi"] < 10 else 1)


def test_source_spot_checks_are_not_model_accuracy(audit):
    records, evidence, _ = audit
    sources = {s["_id"]: s for s in records["sources"]}
    projects = {p["_id"]: p for p in records["projects"]}
    georgia = evidence["source_review"]["georgia"]
    desc = evidence["source_review"]["desc"]
    assert len(georgia) == 8 and len(desc["observations"]) == 2
    for row in georgia:
        assert all(row[f"{field}_matches"] for field in ("name", "date", "owner"))
        assert row["source_sha256"] == sources["gpc-2025"]["sha256"]
        assert row["page"] == projects[row["project_id"]]["source"]["page"]
    spot = evidence["extraction_spot_check"]
    assert spot["sample_count"] == len(spot["observations"]) == 12
    assert spot["field_group_count"] == 9
    assert spot["agreements"] == 108 and spot["mismatches"] == 0
    assert sum(sum(o["non_location_checks"].values()) for o in spot["observations"]) == 108
    assert evidence["gemini_real_records"] == spot["gemini_comparison"]["real_records"] == 0
    assert evidence["gemini_accuracy"] is None and spot["gemini_comparison"]["accuracy"] is None
    for observation in spot["observations"]:
        assert observation["source_sha256"] == sources[observation["source_id"]]["sha256"]
    # The superseded triage and workstation paths must not enter published evidence.
    serialized = json.dumps(evidence)
    assert "manual_row_or_card_review_required" not in serialized
    assert "C:\\Users\\" not in serialized.replace("\\\\", "\\")


def test_effective_review_states_are_downgraded_without_changing_producer_data(audit):
    records, _, reviews = audit
    before = copy.deepcopy(records)
    staged = stage(records, "f13-test")
    rejected = {m["id"] for m in staged["matches"] if m["review_state"] == "rejected"}
    assert rejected == {r["record_id"] for r in reviews if r["subject_type"] == "pair"}
    assert Counter(m["review_state"] for m in staged["matches"]) == {
        "rejected": len(rejected), "needs_review": len(staged["matches"]) - len(rejected)}
    assert records == before


@pytest.mark.parametrize("changed", ["source", "endpoint", "match"])
def test_old_audit_cannot_apply_after_a_reviewed_fact_changes(audit, changed):
    records, _, reviews = audit
    modified = copy.deepcopy(records)
    pair = next(r for r in reviews if r["subject_type"] == "pair")
    snapshot = pair["subject_snapshot"]
    if changed == "source":
        source_id = snapshot["projects"][0]["source"]["source_id"]
        next(s for s in modified["sources"] if s["_id"] == source_id)["sha256"] = "a" * 64
    elif changed == "endpoint":
        endpoint_id = snapshot["endpoints"][0]["record_id"]
        next(e for e in modified["locations"] if e["_id"] == endpoint_id)["lat"] += 0.001
    else:
        next(m for m in modified["matches"] if m["_id"] == pair["record_id"])["distance_mi"] += 0.001
    staged = stage(modified, "f13-mutated")
    assert next(m for m in staged["matches"] if m["id"] == pair["record_id"])["review_state"] == "needs_review"
