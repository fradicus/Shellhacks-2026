"""Build reviewed endpoint locations from versioned projects and the cached OSM inventory."""

from __future__ import annotations

import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from common.io import REPO_ROOT, load_json, write_json
from common.schema import validate

from .boundaries import StateBoundaries
from .core import (
    MATCHER_VERSION,
    PROJECT_SOURCE_GATES,
    SOURCE_BLOCKING_FLAGS,
    candidate_index,
    canonical_json_sha256,
    find_candidates,
    grade_candidates,
    location_id,
    review_id,
)

DEFAULT_REVIEW_AT = f"{os.getenv('ANALYSIS_DATE', '2026-09-26')}T00:00:00Z"


def _source_gate(project: dict[str, Any]) -> list[str]:
    gates = sorted(SOURCE_BLOCKING_FLAGS & set(project.get("quality_flags", [])))
    if project["_id"] in PROJECT_SOURCE_GATES:
        gates.append(PROJECT_SOURCE_GATES[project["_id"]])
    return gates


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
    f09_scope_reviews = [
        {
            "project_id": project["_id"],
            "project_key": project["project_key"],
            "reason": PROJECT_SOURCE_GATES[project["_id"]],
            "utility": _utility_key(project),
        }
        for project in projects
        if project["_id"] in PROJECT_SOURCE_GATES
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
            "f09_endpoint_scope_review": f09_scope_reviews,
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


def build_locations(
    *,
    repo_root: Path = REPO_ROOT,
    live_boundaries: bool = False,
    review_at: str = DEFAULT_REVIEW_AT,
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

    reviews = []
    for location in locations:
        verdict = "accepted_by_f09_rules" if location["confidence"] != "rejected" else "unresolved"
        review = {
            "_id": review_id(location["_id"], verdict),
            "at": review_at,
            "reason": location["evidence"],
            "record_id": location["_id"],
            "reviewer": "f09-deterministic-rules-v1",
            "verdict": verdict,
        }
        validate(review, "review")
        reviews.append(review)

    coverage = _coverage(projects, locations, boundaries.manifest)
    coverage["sanity_checks"] = _sanity(locations, inventory)
    coverage["semantic_input_sha256"] = {
        "desc_projects": canonical_json_sha256(desc),
        "gpc_projects": canonical_json_sha256(gpc),
        "osm_substations": canonical_json_sha256(inventory),
    }
    write_json(repo_root / "data/locations/locations.json", locations)
    write_json(repo_root / "data/locations/coverage.json", coverage)
    write_json(repo_root / "data/review/locations/geo.json", reviews)
    return coverage
