"""Frozen empirical models with separate temporal calibration and evaluation windows."""

import json
import math
from datetime import date, datetime, timedelta
from statistics import mean, median

from outcomes.contracts import Artifact, Cutoffs, Observation, timestamp
from outcomes.importer import digest

MIN_TRAIN, MIN_CAL, MIN_TEST = 30, 20, 20


def cohort(row: Observation) -> str:
    return json.dumps([row.job_type, row.company_id, row.region], separators=(",", ":"), ensure_ascii=False)


def split(rows: list[Observation], cutoffs: Cutoffs) -> tuple[list, list, list]:
    train, calibration, holdout = [], [], []
    for row in rows:
        if row.available_at <= cutoffs.training:
            train.append(row)
        elif row.decision_at > cutoffs.training and row.available_at <= cutoffs.calibration:
            calibration.append(row)
        elif row.decision_at > cutoffs.calibration and row.available_at <= cutoffs.evaluation:
            holdout.append(row)
    return train, calibration, holdout


def quantile(values: list[float], probability: float) -> float:
    """Finite-sample conformal order statistic, never interpolation across residuals."""
    return sorted(values)[min(len(values) - 1, math.ceil((len(values) + 1) * probability) - 1)]


def exceedance(rows: list[Observation], baseline: float) -> float:
    return sum(row.duration_days > baseline for row in rows) / len(rows)


def validate_observations(rows: list[Observation], cutoffs: Cutoffs) -> None:
    if not cutoffs.training < cutoffs.calibration < cutoffs.evaluation:
        raise ValueError("cutoffs must be strictly chronological")
    ids, lineages = set(), set()
    for row in rows:
        if row.job_id in ids or row.project_lineage in lineages:
            raise ValueError("repeated identity/project lineage")
        ids.add(row.job_id)
        lineages.add(row.project_lineage)
        duration = (date.fromisoformat(row.actual_complete) - date.fromisoformat(row.actual_start)).days
        if duration != row.duration_days:
            raise ValueError("duration does not match exact actual anchors")
        if not row.features_available_at <= row.decision_at <= f"{row.actual_start}T00:00:00Z":
            raise ValueError("features/decision leak past actual construction start")
        if not f"{row.actual_complete}T00:00:00Z" <= row.available_at <= cutoffs.evaluation:
            raise ValueError("outcome availability contradicts actual completion/cutoff")
        if (row.planned_duration_days is None) != (row.planned_available_at is None):
            raise ValueError("incomplete planned baseline")
        if row.planned_available_at and row.planned_available_at > row.decision_at:
            raise ValueError("post-decision planned baseline")


def evaluate(rows: list[Observation], cutoffs: Cutoffs) -> dict:
    validate_observations(rows, cutoffs)
    all_train, all_cal, all_test = split(rows, cutoffs)
    evaluations = {}
    for key in sorted({cohort(row) for row in rows}):
        training = [row for row in all_train if cohort(row) == key]
        calibration = [row for row in all_cal if cohort(row) == key]
        holdout = [row for row in all_test if cohort(row) == key]
        entry = {
            "training": len(training),
            "calibration": len(calibration),
            "holdout": len(holdout),
            "passed": False,
            "reasons": [],
            "interval": None,
            "metrics": None,
            "probability": None,
        }
        evaluations[key] = entry
        if len(training) < MIN_TRAIN or len(calibration) < MIN_CAL or len(holdout) < MIN_TEST:
            entry["reasons"].append("insufficient temporally separated cohort support")
            continue
        center = float(median(row.duration_days for row in training))
        residuals = [abs(row.duration_days - center) for row in calibration]
        radius = quantile(residuals, 0.8)
        lower, upper = max(1.0, center - radius), center + radius
        baseline_rows = [row for row in all_train if row.job_type == training[0].job_type]
        baseline_center = float(median(row.duration_days for row in baseline_rows))
        mae = mean(abs(row.duration_days - center) for row in holdout)
        baseline_mae = mean(abs(row.duration_days - baseline_center) for row in holdout)
        coverage = mean(lower <= row.duration_days <= upper for row in holdout)
        entry["interval"] = {"lower": lower, "median": center, "upper": upper}
        entry["metrics"] = {"mae_days": mae, "baseline_mae_days": baseline_mae, "interval_coverage": coverage}
        if mae > baseline_mae + 1e-9 or mae > 30 or mae > center * 0.35:
            entry["reasons"].append("held-out duration error gate failed")
        if coverage < 0.75 or upper - lower > 120 or upper - lower > 2 * center:
            entry["reasons"].append("held-out interval coverage/width gate failed")
        entry["passed"] = not entry["reasons"]
        plans = [row.planned_duration_days for row in training if row.planned_duration_days is not None]
        if len(plans) < MIN_TRAIN:
            continue
        # The supported range is fixed from training; evaluation cannot enlarge it.
        domain = {"lower": min(plans), "upper": max(plans)}
        prob_cal = [
            r
            for r in calibration
            if r.planned_duration_days is not None and domain["lower"] <= r.planned_duration_days <= domain["upper"]
        ]
        prob_test = [
            r
            for r in holdout
            if r.planned_duration_days is not None and domain["lower"] <= r.planned_duration_days <= domain["upper"]
        ]
        if len(prob_cal) < MIN_CAL or len(prob_test) < MIN_TEST:
            continue

        def brier(observations, distribution):
            return mean(
                (exceedance(distribution, r.planned_duration_days) - int(r.duration_days > r.planned_duration_days)) ** 2
                for r in observations
            )

        cal_brier, test_brier = brier(prob_cal, training), brier(prob_test, training)
        cal_base, test_base = brier(prob_cal, baseline_rows), brier(prob_test, baseline_rows)
        # Require evaluated thresholds to cover the training-defined domain too.
        covered = all(
            min(r.planned_duration_days for r in sample) <= domain["lower"]
            and max(r.planned_duration_days for r in sample) >= domain["upper"]
            for sample in [prob_cal, prob_test]
        )
        entry["probability"] = {
            "passed": covered and cal_brier <= min(0.2, cal_base + 1e-9) and test_brier <= min(0.2, test_base + 1e-9),
            "domain": domain,
            "calibration": len(prob_cal),
            "holdout": len(prob_test),
            "calibration_brier": cal_brier,
            "holdout_brier": test_brier,
            "calibration_baseline_brier": cal_base,
            "holdout_baseline_brier": test_base,
        }
    return evaluations


def build_artifact(rows: list[Observation], cutoffs: Cutoffs, *, purpose: str) -> Artifact:
    ordered = sorted(rows, key=lambda row: row.job_id)
    return Artifact(
        schema_version="outcomes-model-v1",
        purpose=purpose,
        policy_version="empirical-cohort-v1",
        target="physical_construction_start_to_complete_calendar_days",
        dataset_hash=digest([r.model_dump() for r in ordered]),
        cutoffs=cutoffs,
        observations=ordered,
        evaluation=evaluate(ordered, cutoffs),
    )


def validate_artifact(artifact: Artifact, *, now: str, allow_test: bool = False) -> None:
    timestamp(now)
    if artifact.purpose != "authorized_actual_history" and not allow_test:
        raise ValueError("synthetic test model is not operational evidence")
    if artifact.cutoffs.evaluation > now:
        raise ValueError("future model evaluation")
    expires = datetime.strptime(artifact.cutoffs.evaluation, "%Y-%m-%dT%H:%M:%SZ") + timedelta(days=180)
    if datetime.strptime(now, "%Y-%m-%dT%H:%M:%SZ") > expires:
        raise ValueError("model evaluation expired")
    if artifact.dataset_hash != digest([row.model_dump() for row in artifact.observations]):
        raise ValueError("observation digest mismatch")
    if canonical_metrics(artifact.evaluation) != canonical_metrics(evaluate(artifact.observations, artifact.cutoffs)):
        raise ValueError("claimed support/evaluation differs from reproducible evaluation")


def canonical_metrics(value):
    if isinstance(value, dict):
        return {key: canonical_metrics(item) for key, item in value.items()}
    if isinstance(value, list):
        return [canonical_metrics(item) for item in value]
    return round(value, 9) if isinstance(value, float) else value
