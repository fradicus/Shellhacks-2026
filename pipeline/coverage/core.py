"""Build the coverage ledger from committed canonical records. No network or database access."""

from collections import Counter
from typing import Any

from load.build import stage

CONFIDENCES = ("high", "medium", "low", "rejected")
STATES = ("confirmed", "rejected", "needs_review")


def _counts(values) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _gemini(summary: dict | None) -> dict | None:
    if summary is None:
        return None
    return {key: summary.get(key) for key in (
        "status", "reason", "measurement", "model", "live_calls", "corpus_pages", "pages_processed",
        "qa_checked", "per_field",
    )}


def _audit(evidence: dict | None) -> tuple[dict | None, dict | None]:
    if evidence is None:
        return None, None
    reviews = evidence.get("review_counts")
    spot = evidence.get("extraction_spot_check")
    if not isinstance(reviews, dict) or not isinstance(spot, dict):
        return None, None
    source_audit = {key: spot.get(key) for key in (
        "sample_count", "field_group_count", "agreements", "mismatches", "gemini_comparison",
    )}
    return reviews, source_audit


def summarize(records: dict[str, list[dict]], gemini_summary: dict | None = None,
              audit_evidence: dict | None = None) -> list[dict]:
    """Return one coverage record per source.

    Project counts use filing versions, never utility totals. Match attribution uses F10's explicit project/source
    bindings. Review state is F06's effective staged state, so a producer value cannot be mistaken for audit outcome.
    """
    sources = records.get("sources", [])
    projects = records.get("projects", [])
    locations = records.get("locations", [])
    matches = records.get("matches", [])
    source_ids = [source["_id"] for source in sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("duplicate source id")

    project_by_id = {project["_id"]: project for project in projects}
    if len(project_by_id) != len(projects):
        raise ValueError("duplicate project id")
    by_source = {source_id: [] for source_id in source_ids}
    for project in projects:
        source_id = project["source"]["source_id"]
        if source_id not in by_source:
            raise ValueError(f"project references unknown source {source_id!r}")
        by_source[source_id].append(project)

    locations_by_source: dict[str, list[dict]] = {source_id: [] for source_id in source_ids}
    for location in locations:
        project = project_by_id.get(location.get("project_id"))
        if project is None:
            raise ValueError(f"location references unknown project {location.get('project_id')!r}")
        locations_by_source[project["source"]["source_id"]].append(location)

    matched_ids: dict[str, set[str]] = {source_id: set() for source_id in source_ids}
    matches_by_source: dict[str, list[dict]] = {source_id: [] for source_id in source_ids}
    for match in matches:
        involved: set[str] = set()
        bindings = match.get("bindings")
        if not isinstance(bindings, dict):
            raise ValueError(f"match {match['_id']!r} has no explicit bindings")
        for side in ("a", "b"):
            binding = bindings.get(side)
            project = project_by_id.get(binding.get("project_id") if isinstance(binding, dict) else None)
            if project is None or binding.get("source_id") != project["source"]["source_id"]:
                raise ValueError(f"match {match['_id']!r} has an invalid {side} binding")
            source_id = project["source"]["source_id"]
            matched_ids[source_id].add(project["_id"])
            involved.add(source_id)
        for source_id in involved:
            matches_by_source[source_id].append(match)

    # Reuse the loader's current-binding policy. This does not mutate producer records.
    effective = {match["id"]: match for match in stage(records, "coverage-ledger")["matches"]}
    audit_counts, source_audit = _audit(audit_evidence)
    gemini = _gemini(gemini_summary)
    global_counts: dict[str, Any] = {
        "project_versions": len(projects),
        "active_projects": sum(project.get("active") is True for project in projects),
        "location_records": len(locations),
        "located_endpoints": sum(location["confidence"] != "rejected" for location in locations),
        "located_project_versions": len({location["project_id"] for location in locations
                                         if location["confidence"] != "rejected"}),
        "matches": len(matches),
        "distinct_matched_project_versions": len(set().union(*matched_ids.values()) if matched_ids else set()),
        "raw_match_states": _counts(match.get("review_state", "needs_review") for match in matches),
        "effective_match_states": _counts(match["review_state"] for match in effective.values()),
        "audit_review_counts": audit_counts,
        "manual_source_audit": source_audit,
        "gemini": gemini,
    }

    output = []
    for source in sources:
        source_id = source["_id"]
        versions = by_source[source_id]
        active = [project for project in versions if project.get("active") is True]
        location_rows = locations_by_source[source_id]
        accepted = [location for location in location_rows if location["confidence"] != "rejected"]
        located_ids = {location["project_id"] for location in accepted}
        unlocated = [project for project in active if project["_id"] not in located_ids]
        source_matches = matches_by_source[source_id]
        if source_id == "sample":
            coverage_scope = "fixture_reference_only"
        else:
            coverage_scope = "canonical_projects" if versions else "not_ingested"
        counts = {
            "contract_version": "coverage-v1",
            "coverage_scope": coverage_scope,
            "rows_seen": len(versions),
            "rows_parsed": len(versions),
            "project_versions": len(versions),
            "distinct_project_keys": len({project["project_key"] for project in versions}),
            "active_projects": len(active),
            "inactive_projects": len(versions) - len(active),
            "active_by_utility": _counts(project["utility"] for project in active),
            "filed_endpoint_projects_all_versions": _counts(str(len(project.get("endpoints", []))) for project in versions),
            "filed_endpoint_projects_active": _counts(str(len(project.get("endpoints", []))) for project in active),
            "filed_endpoints_all_versions": sum(len(project.get("endpoints", [])) for project in versions),
            "location_records": len(location_rows),
            "endpoint_confidence": {confidence: sum(row["confidence"] == confidence for row in location_rows)
                                    for confidence in CONFIDENCES},
            "located_endpoints": len(accepted),
            "located_active_projects": len({project_id for project_id in located_ids
                                             if project_by_id[project_id].get("active") is True}),
            "unlocated_active_projects": len(unlocated),
            "unlocated_active": [{"project_id": project["_id"], "project_key": project["project_key"],
                                   "name": project["name"]} for project in unlocated],
            "flagged_versions": sum(bool(project.get("quality_flags")) for project in versions),
            "flagged_active_projects": sum(bool(project.get("quality_flags")) for project in active),
            "quality_flags": _counts(flag for project in versions for flag in project.get("quality_flags", [])),
            "distinct_matched_project_versions": len(matched_ids[source_id]),
            "matches_involving_source": len(source_matches),
            "match_views": _counts(match["view"] for match in source_matches),
            "raw_match_states": _counts(match.get("review_state", "needs_review") for match in source_matches),
            "effective_match_states": _counts(effective[match["_id"]]["review_state"] for match in source_matches),
            "global": global_counts,
        }
        if not versions:
            # The sponsor sample is a fixture reference, not an ingested parser scope. Null avoids turning the absence
            # of canonical records into a claim of zero projects, locations, flags, or matches.
            for key in (
                "rows_seen", "rows_parsed", "project_versions", "distinct_project_keys", "active_projects",
                "inactive_projects", "filed_endpoint_projects_all_versions", "filed_endpoint_projects_active",
                "filed_endpoints_all_versions", "location_records", "endpoint_confidence", "located_endpoints",
                "located_active_projects", "unlocated_active_projects", "flagged_versions", "flagged_active_projects",
                "quality_flags", "distinct_matched_project_versions", "matches_involving_source", "match_views",
                "raw_match_states", "effective_match_states",
            ):
                counts[key] = None
        output.append({"_id": source_id, "counts": counts})
    return output
