"""Strict, versioned import and private-model contracts."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, with_config
from typing_extensions import TypedDict


def timestamp(value: str) -> str:
    if len(value) != 20 or not value.endswith("Z"):
        raise ValueError("UTC timestamp must be YYYY-MM-DDTHH:MM:SSZ")
    datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    return value


def day(value: str) -> str:
    if len(value) != 10 or date.fromisoformat(value).isoformat() != value:
        raise ValueError("date must be an exact ISO calendar day")
    return value


Stamp = Annotated[str, AfterValidator(timestamp)]
Day = Annotated[str, AfterValidator(day)]
Identifier = Annotated[str, Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_ .:/-]+$")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class Source(Strict):
    id: Identifier
    publisher: Identifier
    lineage: Identifier
    local_path: Annotated[str, Field(min_length=1, max_length=1000)]
    sha256: Digest
    published_at: Stamp
    received_at: Stamp
    reviewed_at: Stamp
    authorization_ref: Identifier
    reviewer: Identifier


class Evidence(Strict):
    source_id: Identifier
    pointer: Annotated[str, Field(min_length=1, max_length=1000, pattern=r"^/")]


class Job(Strict):
    id: Identifier
    project_lineage: Identifier
    component_id: Identifier
    job_type: Identifier
    company_id: Identifier
    region: Identifier
    decision_at: Stamp
    features_known_at: Stamp
    evidence: Evidence


class Event(Strict):
    id: Identifier
    job_id: Identifier
    component_id: Identifier
    kind: Literal["construction_start", "construction_complete"]
    actuality: Literal["actual", "planned"]
    date: str | None
    precision: Literal["day", "month", "year", "unknown"]
    known_at: Stamp
    evidence: Evidence


class Review(Strict):
    job_id: Identifier
    decision: Literal["accepted", "rejected", "unresolved"]
    reviewed_at: Stamp
    reviewer: Identifier
    reason: Annotated[str, Field(min_length=1, max_length=1000)]
    start_semantics: Literal["physical_construction_start"]
    completion_semantics: Literal["physical_construction_complete"]


class Bundle(Strict):
    schema_version: Literal["outcomes-import-v1"]
    purpose: Literal["authorized_actual_history", "synthetic_test_only"]
    sources: Annotated[list[Source], Field(max_length=1000)]
    jobs: Annotated[list[Job], Field(max_length=10000)]
    events: Annotated[list[Event], Field(max_length=50000)]
    reviews: Annotated[list[Review], Field(max_length=10000)]


class Observation(Strict):
    job_id: Identifier
    project_lineage: Identifier
    component_id: Identifier
    job_type: Identifier
    company_id: Identifier
    region: Identifier
    decision_at: Stamp
    features_available_at: Stamp
    actual_start: Day
    actual_complete: Day
    available_at: Stamp
    duration_days: Annotated[int, Field(gt=0, le=3650)]
    planned_duration_days: Annotated[int, Field(gt=0, le=3650)] | None
    planned_available_at: Stamp | None
    evidence_hashes: Annotated[list[Digest], Field(min_length=1, max_length=10)]


class Cutoffs(Strict):
    training: Stamp
    calibration: Stamp
    evaluation: Stamp


class AuditSource(Strict):
    id: Identifier
    publisher: Identifier
    lineage: Identifier
    sha256: Digest
    published_at: Stamp
    received_at: Stamp
    reviewed_at: Stamp
    authorization_ref: Identifier
    reviewer: Identifier


class Provenance(Strict):
    import_sha256: Digest
    sources: Annotated[list[AuditSource], Field(max_length=1000)]
    reviews: Annotated[list[Review], Field(max_length=10000)]


@with_config(ConfigDict(extra="forbid", strict=True))
class Interval(TypedDict):
    lower: float
    median: float
    upper: float


@with_config(ConfigDict(extra="forbid", strict=True))
class Metrics(TypedDict):
    mae_days: float
    baseline_mae_days: float
    interval_coverage: Annotated[float, Field(ge=0, le=1)]


@with_config(ConfigDict(extra="forbid", strict=True))
class Domain(TypedDict):
    lower: Annotated[int, Field(gt=0, le=3650)]
    upper: Annotated[int, Field(gt=0, le=3650)]


@with_config(ConfigDict(extra="forbid", strict=True))
class ProbabilityEvaluation(TypedDict):
    passed: bool
    domain: Domain
    calibration: Annotated[int, Field(ge=0)]
    holdout: Annotated[int, Field(ge=0)]
    calibration_brier: Annotated[float, Field(ge=0, le=1)]
    holdout_brier: Annotated[float, Field(ge=0, le=1)]
    calibration_baseline_brier: Annotated[float, Field(ge=0, le=1)]
    holdout_baseline_brier: Annotated[float, Field(ge=0, le=1)]


@with_config(ConfigDict(extra="forbid", strict=True))
class Evaluation(TypedDict):
    training: Annotated[int, Field(ge=0)]
    calibration: Annotated[int, Field(ge=0)]
    holdout: Annotated[int, Field(ge=0)]
    passed: bool
    reasons: list[str]
    interval: Interval | None
    metrics: Metrics | None
    probability: ProbabilityEvaluation | None


class Artifact(Strict):
    schema_version: Literal["outcomes-model-v1"]
    purpose: Literal["authorized_actual_history", "synthetic_test_only"]
    policy_version: Literal["empirical-cohort-v1"]
    target: Literal["physical_construction_start_to_complete_calendar_days"]
    dataset_hash: Digest
    provenance: Provenance
    provenance_hash: Digest
    cutoffs: Cutoffs
    observations: Annotated[list[Observation], Field(max_length=10000)]
    evaluation: dict[str, Evaluation]
