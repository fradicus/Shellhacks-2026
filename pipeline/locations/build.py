"""Build reviewed endpoint locations from versioned projects and the cached OSM inventory."""

from __future__ import annotations

import os
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from common.io import REPO_ROOT, load_json, write_json
from common.schema import validate

from .boundaries import StateBoundaries
from .core import (
    AUTO_REVIEW_VERSION,
    AUTO_REVIEWER,
    MATCHER_VERSION,
    SOURCE_BLOCKING_FLAGS,
    automatic_decision_hash,
    candidate_index,
    canonical_json_sha256,
    find_candidates,
    grade_candidates,
    location_id,
    review_event_id,
)


def _source_gate(project: dict[str, Any]) -> list[str]:
    return sorted(SOURCE_BLOCKING_FLAGS & set(project.get("quality_flags", [])))


def _evidence_text(confidence: str, selected: dict[str, Any] | None, reasons: list[str]) -> str:
    if selected is None:
        return f"Unlocated by {MATCHER_VERSION}: {', '.join(reasons)}."
    facts = [
        f"{selected['match_type']} normalized-name match to {selected['osm_id']}",
        f"state evidence {selected['state_evidence']}",
        f"operator evidence {selected['operator_status']}",
        f"voltage evidence {selected['voltage_status']}",
        f"coordinate method {selected['coordinate_method']}",
    ]
    if reasons:
        facts.append(f"limitations {', '.join(reasons)}")
    return f"{confidence.capitalize()} by {MATCHER_VERSION}: " + "; ".join(facts) + "."


def review_endpoint(
    project: dict[str, Any],
    endpoint: dict[str, Any],
    endpoint_index: int,
    index: dict[str, list[dict[str, Any]]],
    boundaries: StateBoundaries,
) -> dict[str, Any]:
    source_gate = _source_gate(project)
    candidates = find_candidates(project, endpoint["norm"], index, boundaries)
    if source_gate:
        confidence, selected, reasons = "rejected", None, [f"source_gate:{flag}" for flag in source_gate]
    else:
        # Neither numeric GPC zone nor state membership is accepted as positive fine-area proof.
        confidence, selected, reasons = grade_candidates(candidates, fine_area_verified=False)
    selected_id = selected["osm_id"] if selected else None
    record_id = location_id(project["_id"], endpoint_index, endpoint["norm"], selected_id)
    for candidate in candidates:
        if selected and candidate["osm_id"] == selected["osm_id"]:
            candidate["decision"] = "accepted"
            candidate["reasons"] = reasons

    record: dict[str, Any] = {
        "_id": record_id,
        "candidates": candidates,
        "confidence": confidence,
        "endpoint_identity": {
            "endpoint_index": endpoint_index,
            "endpoint_norm": endpoint["norm"],
            "evidence_id": selected_id,
            "project_id": project["_id"],
            "version": "v1",
        },
        "endpoint_index": endpoint_index,
        "evidence": _evidence_text(confidence, selected, reasons),
        "limitations": reasons,
        "matcher_version": MATCHER_VERSION,
        "name": endpoint["name"],
        "norm": endpoint["norm"],
        "project_id": project["_id"],
        "project_key": project["project_key"],
        "project_source": project.get("source"),
        "project_utility": project.get("utility"),
        "source_id": (project.get("source") or {}).get("source_id"),
        "source_quality_flags": project.get("quality_flags", []),
    }
    if selected:
        record.update(
            {
                "coordinate_method": selected["coordinate_method"],
                "lat": selected["lat"],
                "lon": selected["lon"],
                "osm_id": selected["osm_id"],
                "osm_url": selected["osm_url"],
            }
        )
    validate(record, "location")
    return record


def _utility_key(project: dict[str, Any]) -> str:
    return project.get("utility") if project.get("utility") in {"DESC", "GPC"} else "unknown"


def _coverage(
    projects: list[dict[str, Any]], locations: list[dict[str, Any]], boundary_manifest: dict[str, Any]
) -> dict[str, Any]:
    project_lookup = {project["_id"]: project for project in projects}
    per_utility: dict[str, Counter[str]] = defaultdict(Counter)
    for project in projects:
        utility = _utility_key(project)
        per_utility[utility]["active_projects"] += 1
        endpoints = project.get("endpoints", [])
        per_utility[utility]["filed_endpoints"] += len(endpoints)
        if not endpoints:
            per_utility[utility]["zero_endpoint_projects"] += 1
    for location in locations:
        utility = _utility_key(project_lookup[location["project_id"]])
        per_utility[utility][location["confidence"]] += 1
        if location["confidence"] != "rejected":
            per_utility[utility]["located"] += 1

    source_ambiguities = [
        {
            "project_id": project["_id"],
            "project_key": project["project_key"],
            "quality_flags": project.get("quality_flags", []),
            "utility": _utility_key(project),
        }
        for project in projects
        if "endpoint_ambiguous" in project.get("quality_flags", [])
    ]
    status_conflicts = [
        {
            "project_id": project["_id"],
            "project_key": project["project_key"],
            "quality_flags": project.get("quality_flags", []),
            "utility": _utility_key(project),
        }
        for project in projects
        if "source_status_conflict" in project.get("quality_flags", [])
    ]
    located = [location for location in locations if location["confidence"] != "rejected"]
    sample = sorted(
        located,
        key=lambda item: canonical_json_sha256(["f09-sample-v1", item["_id"]]),
    )[:5]
    totals = Counter()
    for counts in per_utility.values():
        totals.update(counts)
    return {
        "analysis_date": os.getenv("ANALYSIS_DATE", "2026-09-26"),
        "boundary_source": {
            "query_url": boundary_manifest["query_url"],
            "raw_geojson_sha256": boundary_manifest["raw_geojson_sha256"],
            "retrieved_at": boundary_manifest["retrieved_at"],
            "source": boundary_manifest["source"],
            "source_vintage": boundary_manifest["source_vintage"],
        },
        "confidence_policy": {
            "high_requires_positive_fine_area_evidence": True,
            "numeric_gpc_zone_is_geography": False,
            "state_membership_is_fine_area_evidence": False,
            "unique_exact_fallback": "medium with project_area_unverified",
        },
        "coverage_scope": "full",
        "matcher_version": MATCHER_VERSION,
        "per_utility": {key: dict(sorted(value.items())) for key, value in sorted(per_utility.items())},
        "sampled_locations": [
            {
                "_id": item["_id"],
                "confidence": item["confidence"],
                "name": item["name"],
                "osm_url": item["osm_url"],
                "project_id": item["project_id"],
            }
            for item in sample
        ],
        "source_gates": {
            "endpoint_ambiguous": source_ambiguities,
            "source_status_conflict": status_conflicts,
        },
        "totals": dict(sorted(totals.items())),
    }


def _sanity(locations: list[dict[str, Any]], inventory: list[dict[str, Any]]) -> dict[str, Any]:
    desc_6888 = [item for item in locations if item["project_key"] == "DESC:6888"]
    okatie = next((item for item in desc_6888 if item["norm"] == "OKATIE"), None)
    mcintosh = next((item for item in desc_6888 if item["norm"] == "MCINTOSH"), None)
    unnamed = next((item for item in inventory if item["osm_id"] == "way/1064022697"), None)
    return {
        "DESC:6888": {
            "mcintosh": {
                "confidence": mcintosh["confidence"] if mcintosh else "missing_endpoint",
                "candidate_ids": [item["osm_id"] for item in mcintosh["candidates"]] if mcintosh else [],
                "note": "Exact name exists, but Georgia Power/230 kV conflicts require review for the filed 115 kV DESC tie.",
            },
            "okatie": {
                "confidence": okatie["confidence"] if okatie else "missing_endpoint",
                "named_candidate_count": len(okatie["candidates"]) if okatie else 0,
                "note": "No named OSM identity; sponsor workbook coordinates were not used.",
                "unnamed_diagnostic": {
                    "coordinate_method": unnamed.get("coordinate_method") if unnamed else None,
                    "name": unnamed.get("name") if unnamed else None,
                    "osm_id": unnamed.get("osm_id") if unnamed else None,
                    "operator": unnamed.get("operator") if unnamed else None,
                    "status": "candidate_only_not_asserted_as_okatie" if unnamed else "not_in_inventory",
                    "voltage": unnamed.get("voltage") if unnamed else None,
                },
            },
            "status": "partial",
        }
    }


def _parse_utc_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC)


def _format_utc_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _review_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    value = load_json(path)
    history = value if isinstance(value, list) else [value]
    ids = set()
    for review in history:
        validate(review, "review")
        if review["_id"] in ids:
            raise ValueError(f"duplicate append-only review id: {review['_id']}")
        ids.add(review["_id"])
    return history


def _latest_review(history: list[dict[str, Any]], record_id: str) -> dict[str, Any] | None:
    candidates = [
        (timestamp, position, review)
        for position, review in enumerate(history)
        if review.get("record_id") == record_id
        and (timestamp := _parse_utc_timestamp(review.get("at"))) is not None
    ]
    return max(candidates, default=(None, -1, None), key=lambda item: (item[0], item[1]))[2]


def _append_automatic_reviews(
    path: Path,
    locations: list[dict[str, Any]],
    *,
    review_at: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Append changed automatic decisions; exact replay preserves the latest event byte-for-byte."""
    history = _review_history(path)
    existing_ids = {review["_id"] for review in history}
    requested_time = _parse_utc_timestamp(review_at) if review_at is not None else datetime.now(UTC)
    if requested_time is None:
        raise ValueError("review_at must be a timezone-aware ISO-8601 timestamp")
    appended = 0
    for location in locations:
        verdict = "accepted_by_f09_rules" if location["confidence"] != "rejected" else "unresolved"
        reason = location["evidence"]
        decision_hash = automatic_decision_hash(location, verdict, reason)
        previous = _latest_review(history, location["_id"])
        if (
            previous is not None
            and previous.get("reviewer") == AUTO_REVIEWER
            and previous.get("decision_version") == AUTO_REVIEW_VERSION
            and previous.get("decision_hash") == decision_hash
        ):
            continue
        previous_at = _parse_utc_timestamp(previous.get("at")) if previous else None
        event_time = requested_time
        if previous_at is not None and event_time <= previous_at:
            event_time = previous_at + timedelta(microseconds=1)
        at = _format_utc_timestamp(event_time)
        event_id = review_event_id(location["_id"], decision_hash, at, previous.get("_id") if previous else None)
        if event_id in existing_ids:
            raise ValueError(f"append-only review identity collision: {event_id}")
        review = {
            "_id": event_id,
            "at": at,
            "decision_hash": decision_hash,
            "decision_version": AUTO_REVIEW_VERSION,
            "matcher_version": MATCHER_VERSION,
            "reason": reason,
            "record_id": location["_id"],
            "reviewer": AUTO_REVIEWER,
            "verdict": verdict,
        }
        if previous is not None:
            review["supersedes"] = previous["_id"]
            review["supersession_reason"] = (
                "supersedes_provisional_midnight_v1"
                if previous.get("reviewer") == "f09-deterministic-rules-v1"
                and previous.get("at") == "2026-09-26T00:00:00Z"
                else "automatic_decision_changed"
            )
        validate(review, "review")
        history.append(review)
        existing_ids.add(event_id)
        appended += 1
    write_json(path, history)
    return history, appended


def build_locations(
    *,
    repo_root: Path = REPO_ROOT,
    live_boundaries: bool = False,
    review_at: str | None = None,
) -> dict[str, Any]:
    desc = load_json(repo_root / "data/projects/desc.json")
    gpc = load_json(repo_root / "data/projects/gpc.json")
    inventory = load_json(repo_root / "data/osm/substations.json")
    projects = [project for project in [*desc, *gpc] if project.get("active") is True]
    boundaries = StateBoundaries.load(repo_root / "data/locations/boundaries", live=live_boundaries)
    index = candidate_index(inventory)
    locations = [
        review_endpoint(project, endpoint, endpoint_index, index, boundaries)
        for project in projects
        for endpoint_index, endpoint in enumerate(project.get("endpoints", []))
    ]
    locations.sort(key=lambda item: (item["project_id"], item["endpoint_index"], item["_id"]))

    coverage = _coverage(projects, locations, boundaries.manifest)
    coverage["sanity_checks"] = _sanity(locations, inventory)
    coverage["semantic_input_sha256"] = {
        "desc_projects": canonical_json_sha256(desc),
        "gpc_projects": canonical_json_sha256(gpc),
        "osm_substations": canonical_json_sha256(inventory),
    }
    write_json(repo_root / "data/locations/locations.json", locations)
    reviews, _ = _append_automatic_reviews(
        repo_root / "data/review/locations/geo.json", locations, review_at=review_at
    )
    coverage["review_history"] = {
        "automatic_decision_version": AUTO_REVIEW_VERSION,
        "events": len(reviews),
        "latest_automatic_events": sum(review.get("decision_version") == AUTO_REVIEW_VERSION for review in reviews),
        "provisional_v1_events_preserved": sum(
            review.get("reviewer") == "f09-deterministic-rules-v1" for review in reviews
        ),
    }
    write_json(repo_root / "data/locations/coverage.json", coverage)
    return coverage
