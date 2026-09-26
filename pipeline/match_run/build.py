"""F10 full-corpus adapter. Spatial and ranking rules stay exclusively in ``matches.core``."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from common import REPO_ROOT, load_json, validate, write_json
from locations.core import SOURCE_BLOCKING_FLAGS, canonical_json_sha256
from matches import core

CONFIDENCE_RANK = {"high": 0, "medium": 1, "low": 2}
KNOWN_UTILITIES = set(core.KNOWN_UTILITIES)
F09_INPUT_KEYS = ("desc_projects", "gpc_projects", "osm_substations")


def _coordinate(value: Any, *, low: float, high: float, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number")
    number = float(value)
    if not math.isfinite(number) or not low <= number <= high:
        raise ValueError(f"{label} must be finite and within [{low}, {high}]")
    return number


def _active_projects(projects: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    active: dict[str, dict[str, Any]] = {}
    keys: dict[str, str] = {}
    for project in projects:
        if not project.get("active"):
            continue
        project_id = project.get("_id")
        project_key = project.get("project_key")
        if not isinstance(project_id, str) or not isinstance(project_key, str):
            raise ValueError("active projects require string _id and project_key")
        if project_id in active:
            raise ValueError(f"duplicate active project id: {project_id!r}")
        if project_key in keys:
            raise ValueError(
                f"multiple active versions for project_key {project_key!r}: {keys[project_key]!r}, {project_id!r}"
            )
        source_id = (project.get("source") or {}).get("source_id")
        if not isinstance(source_id, str) or project_id != f"{project_key}@{source_id}":
            raise ValueError(f"active project identity/source mismatch: {project_id!r}")
        active[project_id] = project
        keys[project_key] = project_id
    return active


def _slot(location: dict[str, Any], project: dict[str, Any]) -> tuple[str, int]:
    location_id = location.get("_id")
    if not isinstance(location_id, str):
        raise ValueError("location requires string _id")
    index = location.get("endpoint_index")
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise ValueError(f"location {location_id!r} has invalid endpoint_index {index!r}")
    endpoints = project.get("endpoints")
    if not isinstance(endpoints, list) or index >= len(endpoints):
        raise ValueError(f"location {location_id!r} endpoint_index {index!r} is outside the filed endpoints")
    return project["_id"], index


def _verify_location(location: dict[str, Any], project: dict[str, Any], index: int) -> None:
    location_id = location["_id"]
    source_id = project["source"]["source_id"]
    expected = {
        "project_id": project["_id"],
        "project_key": project["project_key"],
        "source_id": source_id,
        "project_utility": project.get("utility"),
    }
    for field, value in expected.items():
        if location.get(field) != value:
            raise ValueError(
                f"location {location_id!r} has stale {field} {location.get(field)!r}; expected {value!r}"
            )
    endpoint = project["endpoints"][index]
    if location.get("norm") != endpoint.get("norm"):
        raise ValueError(
            f"location {location_id!r} norm {location.get('norm')!r} contradicts filed endpoint {endpoint.get('norm')!r}"
        )
    if location.get("source_quality_flags") != project.get("quality_flags", []):
        raise ValueError(f"location {location_id!r} has stale source_quality_flags")
    project_source = location.get("project_source")
    if not isinstance(project_source, dict) or project_source.get("source_id") != source_id:
        raise ValueError(f"location {location_id!r} has stale project_source")
    identity = location.get("endpoint_identity")
    if not isinstance(identity, dict) or any(
        identity.get(field) != value
        for field, value in {
            "project_id": project["_id"],
            "endpoint_index": index,
            "endpoint_norm": endpoint.get("norm"),
        }.items()
    ):
        raise ValueError(f"location {location_id!r} has contradictory endpoint_identity")
    confidence = location.get("confidence")
    if confidence == "rejected":
        return
    if confidence not in CONFIDENCE_RANK:
        raise ValueError(f"location {location_id!r} has invalid accepted confidence {confidence!r}")
    _coordinate(location.get("lat"), low=-90.0, high=90.0, label=f"location {location_id!r} lat")
    _coordinate(location.get("lon"), low=-180.0, high=180.0, label=f"location {location_id!r} lon")
    if SOURCE_BLOCKING_FLAGS & set(project.get("quality_flags", [])):
        raise ValueError(f"source-gated project {project['_id']!r} cannot have an accepted location")


def _bind_locations(
    projects: list[dict[str, Any]], locations: list[dict[str, Any]]
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    active = _active_projects(projects)
    expected_slots = {
        (project_id, index)
        for project_id, project in active.items()
        for index, _ in enumerate(project.get("endpoints", []))
    }
    by_slot: dict[tuple[str, int], dict[str, Any]] = {}
    seen_ids: set[str] = set()
    for location in locations:
        location_id = location.get("_id")
        if not isinstance(location_id, str):
            raise ValueError("location requires string _id")
        if location_id in seen_ids:
            raise ValueError(f"duplicate location _id: {location_id!r}")
        seen_ids.add(location_id)
        project_id = location.get("project_id")
        project = active.get(project_id)
        if project is None:
            raise ValueError(f"location {location.get('_id')!r} is not bound to an active project version: {project_id!r}")
        slot = _slot(location, project)
        if slot in by_slot:
            raise ValueError(
                f"duplicate location records for {slot[0]!r} endpoint {slot[1]}: "
                f"{by_slot[slot]['_id']!r}, {location.get('_id')!r}"
            )
        _verify_location(location, project, slot[1])
        by_slot[slot] = location
    missing = sorted(expected_slots - set(by_slot))
    extra = sorted(set(by_slot) - expected_slots)
    if missing or extra:
        raise ValueError(f"location corpus does not cover the active filed slots; missing={missing[:5]!r}, extra={extra[:5]!r}")
    by_project: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (project_id, _), location in sorted(by_slot.items()):
        by_project[project_id].append(location)
    return active, dict(by_project)


def _prepared_projects(
    active: dict[str, dict[str, Any]], by_project: dict[str, list[dict[str, Any]]]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, int]]:
    prepared: list[dict[str, Any]] = []
    bindings: dict[str, dict[str, Any]] = {}
    excluded = Counter()
    for project in sorted(active.values(), key=lambda item: item["_id"]):
        utility = project.get("utility")
        accepted = [location for location in by_project.get(project["_id"], []) if location["confidence"] != "rejected"]
        computed_center = core.center(accepted)
        bindings[project["project_key"]] = {
            "center": computed_center,
            "location_ids": [location["_id"] for location in accepted],
            "project_id": project["_id"],
            "source_id": project["source"]["source_id"],
        }
        if utility not in KNOWN_UTILITIES:
            excluded["unknown_owner"] += 1
            continue
        if SOURCE_BLOCKING_FLAGS & set(project.get("quality_flags", [])):
            excluded["source_gated"] += 1
            continue
        if computed_center is None:
            excluded["no_accepted_location"] += 1
            continue
        confidences = [location["confidence"] for location in accepted]
        prepared.append(
            {
                "center": computed_center,
                "in_service": project.get("in_service"),
                "location_confidence": max(confidences, key=CONFIDENCE_RANK.__getitem__),
                "project_key": project["project_key"],
                "utility": utility,
            }
        )
    return prepared, bindings, dict(sorted(excluded.items()))


def _counts(values: list[dict[str, Any]], field: str, keys: tuple[Any, ...]) -> dict[str, int]:
    counts = Counter(value[field] for value in values)
    return {str(key): counts.get(key, 0) for key in keys}


def run_match_adapter(
    projects: list[dict[str, Any]],
    locations: list[dict[str, Any]],
    *,
    analysis_date: str,
    input_identity: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Bind the complete endpoint corpus, recompute centers, and delegate every match rule to frozen core."""
    date.fromisoformat(analysis_date)
    active, by_project = _bind_locations(projects, locations)
    prepared, bindings, excluded = _prepared_projects(active, by_project)
    prepared_by_key = {project["project_key"]: project for project in prepared}
    raw_matches = core.overlaps(prepared, analysis_date)
    enriched = []
    for match in raw_matches:
        a_binding, b_binding = bindings[match["a"]], bindings[match["b"]]
        record = {
            **match,
            "bindings": {"a": a_binding, "b": b_binding},
            "location_confidence": {
                "a": prepared_by_key[match["a"]]["location_confidence"],
                "b": prepared_by_key[match["b"]]["location_confidence"],
            },
            "review_state": "needs_review",
        }
        validate(record, "match")
        enriched.append(record)
    matches = core.priority_sort(enriched)

    active_values = list(active.values())
    active_by_utility = Counter(project.get("utility") for project in active_values)
    centered_by_utility = Counter(project["utility"] for project in prepared)
    all_known_pairs = active_by_utility["DESC"] * active_by_utility["GPC"]
    centered_pairs = centered_by_utility["DESC"] * centered_by_utility["GPC"]
    summary = {
        "analysis_date": analysis_date,
        "input_identity": input_identity or {},
        "projects": {
            "active": len(active),
            "active_by_utility": {
                "DESC": active_by_utility["DESC"],
                "GPC": active_by_utility["GPC"],
                "unknown": len(active) - active_by_utility["DESC"] - active_by_utility["GPC"],
            },
            "centered_known_owner": len(prepared),
            "centered_known_owner_by_utility": {
                "DESC": centered_by_utility["DESC"],
                "GPC": centered_by_utility["GPC"],
            },
            "centered_including_unknown_owner": sum(
                core.center(
                    [location for location in by_project.get(project_id, []) if location["confidence"] != "rejected"]
                )
                is not None
                for project_id in active
            ),
            "excluded": excluded,
        },
        "pairs": {
            "all_known_cross_utility_combinations": all_known_pairs,
            "centered_cross_utility_pairs_evaluated": centered_pairs,
            "excluded_before_distance": all_known_pairs - centered_pairs,
            "overlaps": len(matches),
            "spatial_nonmatches": centered_pairs - len(matches),
        },
        "overlaps_by_band": _counts(matches, "band", (0, 1)),
        "overlaps_by_view": _counts(matches, "view", ("historical", "future", "tentative")),
        "review_state": {"needs_review": len(matches)},
        "rules": {
            "center": "matches.core.center",
            "rank_version": core.RANK_VERSION,
            "rule_version": core.RULE_VERSION,
        },
        "top_10": [
            {
                "_id": match["_id"],
                "a": match["a"],
                "b": match["b"],
                "band": match["band"],
                "distance_mi": match["distance_mi"],
                "rank": match["rank"],
                "time_gap_days": match["time_gap_days"],
                "view": match["view"],
            }
            for match in matches[:10]
        ],
    }
    return matches, summary


def _verify_f09_identity(
    desc: list[dict[str, Any]],
    gpc: list[dict[str, Any]],
    osm: list[dict[str, Any]],
    locations: list[dict[str, Any]],
    coverage: dict[str, Any],
    analysis_date: str,
) -> dict[str, str]:
    current = {
        "desc_projects": canonical_json_sha256(desc),
        "gpc_projects": canonical_json_sha256(gpc),
        "osm_substations": canonical_json_sha256(osm),
    }
    expected = coverage.get("semantic_input_sha256")
    if not isinstance(expected, dict):
        raise ValueError("F09 coverage lacks semantic_input_sha256")
    for key in F09_INPUT_KEYS:
        if expected.get(key) != current[key]:
            raise ValueError(f"F09 semantic input fingerprint mismatch for {key}")
    if coverage.get("analysis_date") != analysis_date:
        raise ValueError(
            f"F09 analysis_date {coverage.get('analysis_date')!r} does not match match run {analysis_date!r}"
        )
    if (coverage.get("totals") or {}).get("filed_endpoints") != len(locations):
        raise ValueError("F09 coverage filed-endpoint count does not match locations corpus")
    return {**current, "f09_locations": canonical_json_sha256(locations)}


def build_matches(*, repo_root: Path = REPO_ROOT, analysis_date: str = "2026-09-26") -> dict[str, Any]:
    desc = load_json(repo_root / "data/projects/desc.json")
    gpc = load_json(repo_root / "data/projects/gpc.json")
    locations = load_json(repo_root / "data/locations/locations.json")
    coverage = load_json(repo_root / "data/locations/coverage.json")
    osm = load_json(repo_root / "data/osm/substations.json")
    identity = _verify_f09_identity(desc, gpc, osm, locations, coverage, analysis_date)
    matches, summary = run_match_adapter(
        [*desc, *gpc], locations, analysis_date=analysis_date, input_identity=identity
    )
    write_json(repo_root / "data/matches/matches.json", matches)
    write_json(repo_root / "data/matches/summary.json", summary)
    return summary
