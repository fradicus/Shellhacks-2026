"""Build and validate the committed national snapshot from reviewed cached inputs."""

from __future__ import annotations

import hashlib
from collections import Counter
from importlib import import_module
from pathlib import Path
from typing import Any

from common import REPO_ROOT, SchemaError, load_json, validate, write_json
from national.geography import build_geography
from national.iso_ne import SOURCE_ID as ISO_SOURCE_ID
from national.iso_ne import parse as parse_iso_ne
from national.legacy import normalize as normalize_legacy
from national.registry import cache_path, manifest
from national.sources import build_sources

OUTPUTS = {
    "sources": "national-source",
    "projects": "national-project",
    "geography": "national-geography",
    "coverage": "national-coverage",
}
EXPECTED_ISO_PROJECTS = 1_024
EXPECTED_LEGACY_PROJECTS = 262


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def validate_cache(root: Path, entries: list[dict[str, Any]]) -> None:
    for entry in entries:
        path = cache_path(entry, root)
        if not path.is_file():
            raise ValueError(f"cached source missing: {entry['id']} ({path.name})")
        if path.stat().st_size != entry["bytes"]:
            raise ValueError(f"cached source size changed: {entry['id']}")
        digest = _sha256(path)
        if digest != entry["sha256"]:
            raise ValueError(f"cached source SHA-256 changed: {entry['id']} ({digest})")


def _coverage(projects: list[dict[str, Any]], imported_source_ids: set[str]) -> dict[str, Any]:
    source_rows = []
    for source_id in sorted(imported_source_ids):
        rows = [project for project in projects if project["source_id"] == source_id]
        statuses = Counter(project["status_group"] for project in rows)
        source_rows.append({
            "source_id": source_id,
            "project_count": len(rows),
            "located_count": sum(project["center"] is not None for project in rows),
            "active_status_count": sum(project["status_group"] in {"planned", "proposed", "under_construction"}
                                       for project in rows),
            "unknown_state_count": sum(not project["states"] for project in rows),
            "unknown_county_count": sum(not project["counties"] for project in rows),
            "status_counts": dict(sorted(statuses.items())),
        })
    return {
        "schema_version": "national-coverage-v1",
        "projects_total": len(projects),
        "located_count": sum(project["center"] is not None for project in projects),
        "location_counts": {
            "confirmed_centers": sum(p["center"] is not None and p["location_review"] == "confirmed"
                                     for p in projects),
            "candidate_centers": sum(p["center"] is not None and p["location_review"] != "confirmed"
                                     for p in projects),
            "approximate_only": sum(p["center"] is None and bool((p.get("approximate_location") or {}).get("anchors"))
                                    for p in projects),
            "no_display_location": sum(p["center"] is None and not (p.get("approximate_location") or {}).get("anchors")
                                       for p in projects),
            "rejected_projects": sum(p["location_review"] == "rejected" for p in projects),
        },
        "sources": source_rows,
        "failures": [],
        "notes": [
            "Counts cover imported records only and do not claim nationwide project completeness.",
            "ISO-NE supplies no counties or coordinates; independently reviewed expansion evidence may locate projects.",
            "Legacy state membership uses eligible endpoint containment in pinned Census boundaries; "
            "it retains candidate review status and does not establish full route extent. Other unknown geography stays unknown.",
            "Located counts require a project center. Approximate-only county references remain outside that count; "
            "confirmed centers, candidate centers, approximate-only records and no-display-location records partition projects. "
            "Rejected projects are an overlapping review count, not an additional location category.",
            "Legacy discovery includes current filing versions only; superseded versions remain in the filing-change view.",
            "Census bounds and representative points frame reference geography and never become project locations.",
            "EIA-861 remains a reference-only catalog entry; no utility identity or service-area match is inferred.",
        ],
    }


def validate_records(name: str, value: Any) -> list[str]:
    schema = OUTPUTS[name]
    values = value if isinstance(value, list) else [value]
    errors = []
    for index, record in enumerate(values):
        try:
            validate(record, schema)
        except SchemaError as exc:
            errors.append(f"{name}[{index}]: {exc}")
    return errors


def validate_snapshot_values(snapshot: dict[str, Any]) -> list[str]:
    errors = []
    for name in OUTPUTS:
        errors.extend(validate_records(name, snapshot[name]))
    source_ids = [source["_id"] for source in snapshot["sources"]]
    if len(set(source_ids)) != len(source_ids):
        errors.append("sources: duplicate _id")
    source_by_id = {source["_id"]: source for source in snapshot["sources"]}
    project_ids: set[str] = set()
    for project in snapshot["projects"]:
        if project["_id"] in project_ids:
            errors.append(f"projects: duplicate _id {project['_id']!r}")
        project_ids.add(project["_id"])
        source = source_by_id.get(project["source_id"])
        if source is None:
            errors.append(f"projects: {project['_id']!r} references unknown source {project['source_id']!r}")
        elif source["import_status"] != "imported" or source["role"] != "project_plan":
            errors.append(f"projects: {project['_id']!r} references a non-imported project source")
        elif project["evidence"].get("source_sha256") != source.get("sha256"):
            errors.append(f"projects: {project['_id']!r} evidence hash does not match its source")
        if project["center"] is not None and project["location_review"] in {"rejected", "unlocated"}:
            errors.append(f"projects: {project['_id']!r} exposes a center with {project['location_review']} review")
    states = snapshot["geography"]["states"]
    counties = snapshot["geography"]["counties"]
    if len({state["state_fips"] for state in states}) != len(states):
        errors.append("geography: duplicate state_fips")
    if len({county["county_geoid"] for county in counties}) != len(counties):
        errors.append("geography: duplicate county_geoid")
    state_ids = {state["state_fips"] for state in states}
    county_by_id = {county["county_geoid"]: county for county in counties}
    if any(county["state_fips"] not in state_ids for county in counties):
        errors.append("geography: county references an unknown state")
    for project in snapshot["projects"]:
        unknown_states = sorted(set(project["states"]) - state_ids)
        unknown_counties = sorted(set(project["counties"]) - set(county_by_id))
        if unknown_states:
            errors.append(f"projects: {project['_id']!r} references unknown states {unknown_states}")
        if unknown_counties:
            errors.append(f"projects: {project['_id']!r} references unknown counties {unknown_counties}")
        for county_id in set(project["counties"]) - set(unknown_counties):
            if county_by_id[county_id]["state_fips"] not in project["states"]:
                errors.append(f"projects: {project['_id']!r} county {county_id} is outside its states")
    if snapshot["coverage"]["projects_total"] != len(snapshot["projects"]):
        errors.append("coverage: projects_total does not match projects")
    if snapshot["coverage"]["located_count"] != sum(p["center"] is not None for p in snapshot["projects"]):
        errors.append("coverage: located_count does not match projects")
    imported_source_ids = {
        source["_id"] for source in snapshot["sources"] if source["import_status"] == "imported"
    }
    expected_coverage = _coverage(snapshot["projects"], imported_source_ids)
    if snapshot["coverage"].get("sources") != expected_coverage["sources"]:
        errors.append("coverage: per-source counts do not match projects")
    if ("location_counts" in snapshot["coverage"]
            and snapshot["coverage"]["location_counts"] != expected_coverage["location_counts"]):
        errors.append("coverage: location counts do not match projects")
    actual_counts = Counter(project["source_id"] for project in snapshot["projects"])
    for source_id in imported_source_ids:
        if source_by_id[source_id].get("project_count") != actual_counts[source_id]:
            errors.append(f"sources: {source_id!r} project_count does not match projects")
    return errors


def build_snapshot(root: Path = REPO_ROOT) -> dict[str, Any]:
    source_manifest = manifest(root)
    validate_cache(root, source_manifest)
    geography = build_geography(root / "data" / "national" / "cache", source_manifest)
    iso_entry = next(entry for entry in source_manifest if entry["id"] == ISO_SOURCE_ID)
    iso_projects = parse_iso_ne(cache_path(iso_entry, root), geography, iso_entry["sha256"])
    legacy_projects = normalize_legacy(root)
    if len(iso_projects) != EXPECTED_ISO_PROJECTS:
        raise ValueError(f"expected {EXPECTED_ISO_PROJECTS} ISO-NE projects, found {len(iso_projects)}")
    if len(legacy_projects) != EXPECTED_LEGACY_PROJECTS:
        raise ValueError(f"expected {EXPECTED_LEGACY_PROJECTS} current legacy projects, found {len(legacy_projects)}")
    projects = sorted([*iso_projects, *legacy_projects], key=lambda project: project["_id"])
    project_counts = Counter(project["source_id"] for project in projects)
    sources = build_sources(root, source_manifest, dict(project_counts))
    imported_source_ids = {source["_id"] for source in sources if source["import_status"] == "imported"}
    coverage = _coverage(projects, imported_source_ids)
    snapshot = {"sources": sources, "projects": projects, "geography": geography, "coverage": coverage}
    errors = validate_snapshot_values(snapshot)
    if errors:
        raise ValueError("national snapshot validation failed:\n" + "\n".join(errors))
    for name in OUTPUTS:
        write_json(root / "data" / "national" / f"{name}.json", snapshot[name])
    return snapshot


def rebuild_legacy(root: Path = REPO_ROOT) -> dict[str, Any]:
    """Refresh the legacy projection without re-downloading or baking in regional overlays."""
    snapshot = {name: load_json(root / "data/national" / f"{name}.json") for name in OUTPUTS}
    errors = validate_snapshot_values(snapshot)
    if errors:
        raise ValueError("national base validation failed:\n" + "\n".join(errors))
    snapshot["projects"] = sorted(
        [p for p in snapshot["projects"] if not p["_id"].startswith("legacy:")] + normalize_legacy(root),
        key=lambda p: p["_id"],
    )
    counts = Counter(p["source_id"] for p in snapshot["projects"])
    imported = {s["_id"] for s in snapshot["sources"] if s["import_status"] == "imported"}
    for source in snapshot["sources"]:
        if source["_id"] in imported:
            source["project_count"] = counts[source["_id"]]
    snapshot["coverage"] = _coverage(snapshot["projects"], imported)
    errors = validate_snapshot_values(snapshot)
    if errors:
        raise ValueError("refreshed national base validation failed:\n" + "\n".join(errors))
    for name in ("projects", "sources", "coverage"):
        write_json(root / "data/national" / f"{name}.json", snapshot[name])
    return snapshot


def load_snapshot(root: Path = REPO_ROOT) -> dict[str, Any]:
    snapshot = {name: load_json(root / "data" / "national" / f"{name}.json") for name in OUTPUTS}
    errors = validate_snapshot_values(snapshot)
    if errors:
        raise ValueError("national snapshot validation failed:\n" + "\n".join(errors))
    # C32 replaces the C29 Texas slot; never append both representations of the same IDs.
    texas = ("texas/statewide", "texas.statewide_publish") if (
        root / "data/texas/statewide/releases/active.json"
    ).exists() else ("texas", "texas.publish")
    # Fixed producer order: C23 locations, C27 Southeast, C28 Mid-Atlantic, Texas, C26 Great Lakes, C38 California,
    # C33 PNW, C42 Southwest, C43 Midwest, C47 SPP South, C50 Interior West, then C51 California
    # municipal utilities.
    # Source/candidate folders are never scanned and cannot activate themselves.
    for directory, module in (
        ("expansion", "expansion.publish"),
        ("southeast", "southeast.publish"),
        ("expansion/mid-atlantic", "expansion.mid_atlantic"),
        texas,
        ("greatlakes", "greatlakes.publish"),
        ("california", "california.publish"),
        ("pnw", "pnw.publish"),
        ("southwest", "southwest.publish"),
        ("midwest", "midwest.publish"),
        ("sppsouth", "sppsouth.publish"),
        ("interiorwest", "interiorwest.publish"),
        ("camunis", "camunis.publish"),
    ):
        if not (root / "data" / directory / "releases" / "active.json").exists():
            continue
        snapshot = import_module(module).apply_release(snapshot, root)
        imported_source_ids = {
            source["_id"] for source in snapshot["sources"] if source["import_status"] == "imported"
        }
        measured = _coverage(snapshot["projects"], imported_source_ids)
        for name in ("projects_total", "located_count", "location_counts", "sources", "notes"):
            snapshot["coverage"][name] = measured[name]
        errors = validate_snapshot_values(snapshot)
        if errors:
            raise ValueError("assembled national snapshot validation failed:\n" + "\n".join(errors))
    return snapshot
