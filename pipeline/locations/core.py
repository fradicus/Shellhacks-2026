"""Candidate generation, evidence comparison, and conservative confidence grading."""

from __future__ import annotations

import difflib
import hashlib
import json
from collections import defaultdict
from typing import Any

from .boundaries import StateBoundaries

MATCHER_VERSION = "location-review-v1"
DESC_OPERATOR_ALIASES = {
    "dominion energy south carolina",
    "south carolina electric & gas",
    "south carolina electric & gas company",
}
GPC_OPERATOR_ALIASES = {"georgia power", "georgia power company"}
SOURCE_BLOCKING_FLAGS = {"endpoint_ambiguous", "source_status_conflict"}
PROJECT_SOURCE_GATES = {
    "DESC:6238 H@desc-2025": "filed_title_and_description_endpoint_scope_conflict",
}


def canonical_json_sha256(value: Any) -> str:
    content = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def location_id(project_id: str, endpoint_index: int, endpoint_norm: str, evidence_id: str | None) -> str:
    """Identity binds source-version endpoint identity and selected evidence, never array position elsewhere."""
    identity = f"v1\0{project_id}\0{endpoint_index}\0{endpoint_norm}\0{evidence_id or 'unlocated'}"
    return f"location:v1:{hashlib.sha256(identity.encode()).hexdigest()[:24]}"


def review_id(record_id: str, verdict: str) -> str:
    identity = f"v1\0{record_id}\0{verdict}\0f09-deterministic-rules-v1"
    return f"review:v1:{hashlib.sha256(identity.encode()).hexdigest()[:24]}"


def parse_voltage_kv(value: Any) -> list[float]:
    if not isinstance(value, str):
        return []
    parsed = []
    for item in value.split(";"):
        item = item.strip()
        if item.isdigit():
            parsed.append(int(item) / 1000)
    return sorted(set(parsed))


def _operator_status(project: dict[str, Any], candidate: dict[str, Any]) -> str:
    operator = candidate.get("operator")
    if not operator:
        return "missing"
    normalized = operator.casefold().strip()
    utility = project.get("utility")
    if utility == "DESC":
        return "match" if normalized in DESC_OPERATOR_ALIASES else "conflict"
    if utility == "GPC":
        return "match" if normalized in GPC_OPERATOR_ALIASES else "conflict"
    return "unverifiable_owner"


def _voltage_status(project: dict[str, Any], candidate: dict[str, Any]) -> str:
    project_values = {float(value) for value in project.get("voltages_kv", []) if isinstance(value, (int, float))}
    candidate_values = set(parse_voltage_kv(candidate.get("voltage")))
    if not project_values or not candidate_values:
        return "missing"
    return "match" if project_values & candidate_values else "conflict"


def _home_state(project: dict[str, Any]) -> str:
    return "SC" if project.get("utility") == "DESC" else "GA"


def _candidate_record(
    project: dict[str, Any],
    osm: dict[str, Any],
    *,
    match_type: str,
    similarity: float,
    boundaries: StateBoundaries,
) -> dict[str, Any]:
    lat, lon = osm.get("lat"), osm.get("lon")
    state = boundaries.state_for(lon, lat) if isinstance(lat, (int, float)) and isinstance(lon, (int, float)) else None
    home_state = _home_state(project)
    border_distance = None
    geography_status = "outside_ga_sc"
    if state == home_state:
        geography_status = "home_state_only"
    elif state in {"GA", "SC"} and isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        border_distance = boundaries.distance_to_state_miles(lon, lat, home_state)
        geography_status = "other_state_within_10_mi" if border_distance <= 10.0 else "other_state_over_10_mi"

    reasons = []
    if osm.get("power") != "substation":
        reasons.append("not_substation")
    if osm.get("coordinate_method") == "overpass_bbox_center":
        reasons.append("coordinate_is_overpass_bbox_center")
    if geography_status == "home_state_only":
        reasons.append("state_is_coarse_context_only")
    elif geography_status == "other_state_within_10_mi":
        reasons.append("cross_border_candidate_requires_tie_evidence")
    elif geography_status == "other_state_over_10_mi":
        reasons.append("outside_allowed_border_distance")
    else:
        reasons.append("outside_ga_sc")

    operator_status = _operator_status(project, osm)
    voltage_status = _voltage_status(project, osm)
    if operator_status == "conflict":
        reasons.append("operator_conflict")
    elif operator_status == "unverifiable_owner":
        reasons.append("owner_mapping_unverified")
    elif operator_status == "missing":
        reasons.append("operator_missing")
    if voltage_status == "conflict":
        reasons.append("voltage_conflict")
    elif voltage_status == "missing":
        reasons.append("voltage_missing")

    return {
        "border_distance_mi": border_distance,
        "coordinate_method": osm.get("coordinate_method"),
        "decision": "rejected",
        "lat": lat,
        "lon": lon,
        "match_type": match_type,
        "name": osm.get("name"),
        "norm": osm.get("norm"),
        "operator": osm.get("operator"),
        "operator_status": operator_status,
        "osm_id": osm["osm_id"],
        "osm_url": osm["osm_url"],
        "power": osm.get("power"),
        "raw_cache_paths": osm.get("raw_cache_paths", []),
        "reasons": reasons,
        "similarity": similarity,
        "state": state,
        "state_evidence": geography_status,
        "voltage": osm.get("voltage"),
        "voltage_kv": parse_voltage_kv(osm.get("voltage")),
        "voltage_status": voltage_status,
    }


def candidate_index(inventory: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in inventory:
        if item.get("norm") and item.get("lat") is not None and item.get("lon") is not None:
            grouped[item["norm"]].append(item)
    return {norm: sorted(items, key=lambda item: item["osm_id"]) for norm, items in grouped.items()}


def find_candidates(
    project: dict[str, Any],
    endpoint_norm: str,
    index: dict[str, list[dict[str, Any]]],
    boundaries: StateBoundaries,
) -> list[dict[str, Any]]:
    exact = index.get(endpoint_norm, [])
    if exact:
        matches = [(endpoint_norm, 1.0, item) for item in exact]
    else:
        norms = difflib.get_close_matches(endpoint_norm, sorted(index), n=5, cutoff=0.85)
        matches = [
            (norm, difflib.SequenceMatcher(None, endpoint_norm, norm).ratio(), item)
            for norm in norms
            for item in index[norm]
        ]
    candidates = [
        _candidate_record(project, item, match_type="exact" if exact else "fuzzy", similarity=similarity, boundaries=boundaries)
        for _, similarity, item in matches
    ]
    candidates.sort(key=lambda item: (-item["similarity"], item["norm"], item["osm_id"]))
    for rank, item in enumerate(candidates, start=1):
        item["rank"] = rank
    return candidates


def _context_viable(candidate: dict[str, Any]) -> bool:
    if candidate["power"] != "substation":
        return False
    if candidate["state_evidence"] not in {"home_state_only", "other_state_within_10_mi"}:
        return False
    if candidate["operator_status"] == "conflict":
        return False
    if candidate["voltage_status"] == "conflict":
        return False
    return True


def grade_candidates(
    candidates: list[dict[str, Any]],
    *,
    fine_area_verified: bool = False,
) -> tuple[str, dict[str, Any] | None, list[str]]:
    """Choose only when public context leaves exactly one viable feature."""
    if not candidates:
        return "rejected", None, ["no_named_osm_candidate"]
    viable = [candidate for candidate in candidates if _context_viable(candidate)]
    if not viable:
        return "rejected", None, ["no_candidate_passed_type_geography_operator_voltage_review"]
    if len(viable) > 1:
        return "rejected", None, ["multiple_contextually_viable_candidates"]
    selected = viable[0]
    if selected["match_type"] == "fuzzy" and not fine_area_verified:
        return "rejected", None, ["fuzzy_name_without_fine_area_evidence"]
    limitations = []
    if not fine_area_verified:
        limitations.append("project_area_unverified")
    if selected["operator_status"] == "missing":
        limitations.append("operator_missing")
    if selected["operator_status"] == "unverifiable_owner":
        limitations.append("owner_mapping_unverified")
    if selected["voltage_status"] == "missing":
        limitations.append("voltage_missing")
    if selected["state_evidence"] == "other_state_within_10_mi":
        limitations.append("cross_border_tie_not_independently_verified")
    if selected["match_type"] == "fuzzy":
        confidence = "low"
    elif fine_area_verified and selected["operator_status"] in {"match", "missing"}:
        confidence = "high"
    else:
        confidence = "medium"
    return confidence, selected, limitations
