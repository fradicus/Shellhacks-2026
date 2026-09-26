"""SYNTHETIC TEST ONLY. These records and metrics are never production evidence."""

import copy
import hashlib
import json
from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from outcomes.__main__ import external_path
from outcomes.contracts import Bundle, Cutoffs, Observation, Provenance
from outcomes.importer import digest, provenance_for, strict_json, validate_bundle
from outcomes.model import build_artifact as build_candidate
from outcomes.model import evaluate, validate_artifact


def build_artifact(rows, cutoffs, *, purpose):
    """Synthetic authorization metadata, isolated to this test fixture."""
    provenance = Provenance.model_validate(
        {
            "import_sha256": "c" * 64,
            "sources": [
                {
                    "id": "synthetic-source",
                    "publisher": "synthetic-publisher",
                    "lineage": "synthetic-source-lineage",
                    "sha256": "a" * 64,
                    "published_at": "2020-01-01T00:00:00Z",
                    "received_at": "2020-01-01T00:00:00Z",
                    "reviewed_at": "2020-01-01T00:00:00Z",
                    "authorization_ref": "synthetic-only",
                    "reviewer": "test",
                }
            ],
            "reviews": [
                {
                    "job_id": row.job_id,
                    "decision": "accepted",
                    "reviewed_at": row.available_at,
                    "reviewer": "test",
                    "reason": "Synthetic fixture only",
                    "start_semantics": "physical_construction_start",
                    "completion_semantics": "physical_construction_complete",
                }
                for row in sorted(rows, key=lambda r: r.job_id)
            ],
        }
    )
    return build_candidate(rows, cutoffs, purpose=purpose, provenance=provenance)


def synthetic_observations():
    rows = []
    for year, count in [(2021, 30), (2022, 20), (2023, 20)]:
        for i in range(count):
            actual_start = date(year, 1, 2)
            duration = 30 + (i % 3 - 1) * 2
            rows.append(
                Observation(
                    job_id=f"synthetic-only-{year}-{i}",
                    project_lineage=f"synthetic-lineage-{year}-{i}",
                    component_id="test-component",
                    job_type="synthetic-type",
                    company_id="synthetic-company",
                    region="synthetic-region",
                    decision_at=f"{year}-01-01T00:00:00Z",
                    features_available_at=f"{year}-01-01T00:00:00Z",
                    actual_start=actual_start.isoformat(),
                    actual_complete=(actual_start + timedelta(days=duration)).isoformat(),
                    available_at=f"{year}-03-01T00:00:00Z",
                    duration_days=duration,
                    planned_duration_days=40,
                    planned_available_at=f"{year}-01-01T00:00:00Z",
                    evidence_hashes=["a" * 64],
                )
            )
    return rows


def synthetic_cutoffs():
    return Cutoffs(training="2021-06-01T00:00:00Z", calibration="2022-06-01T00:00:00Z", evaluation="2023-06-01T00:00:00Z")


def test_synthetic_temporal_fit_and_probability_support():
    model = build_artifact(synthetic_observations(), synthetic_cutoffs(), purpose="synthetic_test_only")
    validate_artifact(model, now="2023-06-02T00:00:00Z", allow_test=True)
    entry = next(iter(model.evaluation.values()))
    assert (entry["training"], entry["calibration"], entry["holdout"]) == (30, 20, 20)
    assert entry["passed"] and entry["interval"] == {"lower": 28, "median": 30, "upper": 32}
    assert entry["probability"]["passed"] and entry["probability"]["domain"] == {"lower": 40, "upper": 40}
    with pytest.raises(ValueError, match="synthetic"):
        validate_artifact(model, now="2023-06-02T00:00:00Z")


@pytest.mark.parametrize(
    "field,value",
    [
        ("duration_days", 123),
        ("features_available_at", "2023-01-01T00:00:00Z"),
        ("decision_at", "2021-01-03T00:00:00Z"),
        ("available_at", "2024-01-01T00:00:00Z"),
        ("planned_available_at", "2021-02-01T00:00:00Z"),
    ],
)
def test_synthetic_leakage_and_actual_anchor_mismatch_rejected(field, value):
    rows = synthetic_observations()
    rows[0] = rows[0].model_copy(update={field: value})
    with pytest.raises(ValueError):
        evaluate(rows, synthetic_cutoffs())


def test_revisions_never_cross_temporal_folds():
    rows = synthetic_observations()
    rows[-1] = rows[-1].model_copy(update={"project_lineage": rows[0].project_lineage})
    with pytest.raises(ValueError, match="lineage"):
        evaluate(rows, synthetic_cutoffs())


def test_temporal_embargo_does_not_promote_long_running_jobs_into_holdout():
    rows = synthetic_observations()
    rows[30] = rows[30].model_copy(update={"available_at": "2023-03-01T00:00:00Z"})
    entry = next(iter(evaluate(rows, synthetic_cutoffs()).values()))
    assert entry["calibration"] == 19 and entry["holdout"] == 20 and not entry["passed"]


def test_poor_future_error_and_coverage_abstain():
    rows = synthetic_observations()
    for i in range(50, 70):
        rows[i] = rows[i].model_copy(
            update={"duration_days": 90, "actual_complete": "2023-04-02", "available_at": "2023-05-01T00:00:00Z"}
        )
    entry = next(iter(evaluate(rows, synthetic_cutoffs()).values()))
    assert not entry["passed"] and len(entry["reasons"]) == 2


def test_claimed_metrics_hash_freshness_and_counts_do_not_self_validate():
    model = build_artifact(synthetic_observations(), synthetic_cutoffs(), purpose="synthetic_test_only")
    for field, value in [("training", 9999), ("passed", False), ("metrics", {})]:
        altered = model.model_copy(deep=True)
        next(iter(altered.evaluation.values()))[field] = value
        with pytest.raises(ValueError, match="evaluation"):
            validate_artifact(altered, now="2023-06-02T00:00:00Z", allow_test=True)
    with pytest.raises(ValueError, match="digest"):
        validate_artifact(model.model_copy(update={"dataset_hash": "b" * 64}), now="2023-06-02T00:00:00Z", allow_test=True)
    with pytest.raises(ValueError, match="expired"):
        validate_artifact(model, now="2024-06-02T00:00:00Z", allow_test=True)
    with pytest.raises(ValueError, match="future"):
        validate_artifact(model, now="2022-06-02T00:00:00Z", allow_test=True)


@pytest.fixture
def synthetic_bundle(tmp_path):
    job = {
        "id": "synthetic-job",
        "project_lineage": "synthetic-project",
        "component_id": "synthetic-component",
        "job_type": "synthetic-type",
        "company_id": "synthetic-company",
        "region": "synthetic-region",
        "decision_at": "2023-01-02T00:00:00Z",
        "features_known_at": "2023-01-01T00:00:00Z",
    }
    events = [
        {
            "id": f"synthetic-event-{kind}",
            "job_id": job["id"],
            "component_id": job["component_id"],
            "kind": kind,
            "actuality": "actual",
            "date": when,
            "precision": "day",
            "known_at": "2023-03-01T00:00:00Z",
        }
        for kind, when in [("construction_start", "2023-01-03"), ("construction_complete", "2023-02-03")]
    ]
    documents = [("features", {"job": job}, "2023-01-01T00:00:00Z"), ("actuals", {"events": events}, "2023-03-01T00:00:00Z")]
    sources = []
    for identity, document, published in documents:
        path = tmp_path / f"synthetic-only-{identity}.json"
        raw = json.dumps(document).encode()
        path.write_bytes(raw)
        sources.append(
            {
                "id": identity,
                "publisher": "synthetic-publisher",
                "lineage": "synthetic-lineage",
                "local_path": str(path),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "published_at": published,
                "received_at": published,
                "reviewed_at": published,
                "reviewer": "synthetic-reviewer",
                "authorization_ref": "synthetic-test-only",
            }
        )
    return {
        "schema_version": "outcomes-import-v1",
        "purpose": "synthetic_test_only",
        "sources": sources,
        "jobs": [{**job, "evidence": {"source_id": "features", "pointer": "/job"}}],
        "events": [{**e, "evidence": {"source_id": "actuals", "pointer": f"/events/{i}"}} for i, e in enumerate(events)],
        "reviews": [
            {
                "job_id": job["id"],
                "decision": "accepted",
                "reviewed_at": "2023-03-02T00:00:00Z",
                "reviewer": "synthetic-reviewer",
                "reason": "Synthetic fixture only, not measured evidence",
                "start_semantics": "physical_construction_start",
                "completion_semantics": "physical_construction_complete",
            }
        ],
    }


def test_source_pointer_and_actual_elapsed_duration(synthetic_bundle):
    bundle = Bundle.model_validate(synthetic_bundle)
    rows, quarantine = validate_bundle(bundle, as_of="2023-06-01T00:00:00Z", allow_test=True)
    assert not quarantine and rows[0].duration_days == 31 and rows[0].planned_duration_days is None
    with pytest.raises(ValueError, match="synthetic"):
        validate_bundle(bundle, as_of="2023-06-01T00:00:00Z")


@pytest.mark.parametrize(
    "mutation", ["invented_date", "coarse", "planned_only", "duplicate", "late_features", "unreviewed", "component"]
)
def test_ineligible_imports_are_quarantined(synthetic_bundle, mutation):
    data = copy.deepcopy(synthetic_bundle)
    if mutation == "invented_date":
        data["events"][0]["date"] = "2023-01-01"
    elif mutation == "coarse":
        data["events"][0]["precision"] = "month"
    elif mutation == "planned_only":
        data["events"][0]["actuality"] = "planned"
    elif mutation == "duplicate":
        data["jobs"].append(copy.deepcopy(data["jobs"][0]))
    elif mutation == "late_features":
        data["sources"][0]["reviewed_at"] = "2023-04-01T00:00:00Z"
    elif mutation == "unreviewed":
        data["reviews"][0]["decision"] = "unresolved"
    else:
        data["events"][0]["component_id"] = "different-component"
    rows, quarantine = validate_bundle(Bundle.model_validate(data), as_of="2023-06-01T00:00:00Z", allow_test=True)
    assert not rows and quarantine


def test_wrong_hash_future_source_strict_keys_and_json(synthetic_bundle):
    data = copy.deepcopy(synthetic_bundle)
    data["sources"][0]["sha256"] = "a" * 64
    with pytest.raises(ValueError, match="hash"):
        validate_bundle(Bundle.model_validate(data), as_of="2023-06-01T00:00:00Z", allow_test=True)
    with pytest.raises(ValidationError):
        Bundle.model_validate({**synthetic_bundle, "fake_accuracy": 0.99})
    for raw in [b'{"same":1,"same":2}', b'{"value":NaN}']:
        with pytest.raises(ValueError):
            strict_json(raw)


def test_private_output_cannot_enter_repository():
    from pathlib import Path

    with pytest.raises(ValueError, match="outside"):
        external_path(str(Path(__file__).resolve().parents[2] / "data/private-model.json"))
    with pytest.raises(ValueError, match="absolute"):
        external_path("model.json")


def test_observation_digest_is_ordered_and_reproducible():
    rows = synthetic_observations()
    first = build_artifact(rows, synthetic_cutoffs(), purpose="synthetic_test_only")
    second = build_artifact(list(reversed(rows)), synthetic_cutoffs(), purpose="synthetic_test_only")
    assert first == second
    assert first.dataset_hash == digest([r.model_dump() for r in first.observations])


def test_authorization_and_review_changes_are_bound_without_local_paths(synthetic_bundle):
    bundle = Bundle.model_validate(synthetic_bundle)
    rows, _ = validate_bundle(bundle, as_of="2023-06-01T00:00:00Z", allow_test=True)
    original = provenance_for(bundle, rows)
    changed = bundle.model_copy(deep=True)
    changed.sources[0].authorization_ref = "authorization-changed"
    assert digest(original.model_dump()) != digest(provenance_for(changed, rows).model_dump())
    changed = bundle.model_copy(deep=True)
    changed.reviews[0].reason = "review changed"
    assert digest(original.model_dump()) != digest(provenance_for(changed, rows).model_dump())
    assert "local_path" not in original.model_dump_json()


@pytest.mark.parametrize("identifier", ["a\u0301", "a\u203f", "é"])
def test_identifier_keys_use_the_same_explicit_ascii_contract_as_web(identifier):
    data = synthetic_observations()[0].model_dump()
    data["company_id"] = identifier
    with pytest.raises(ValidationError):
        Observation.model_validate(data)
