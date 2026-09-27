"""Read-only projection of current legacy filing versions into the national contract."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from common import load_json
from load.build import bind_locations, collect, decide, join_projects
from load.review_subjects import current_subjects
from locations.boundaries import STATE_CODES, StateBoundaries
from matches.core import center

STATUS_GROUPS = {"planned": "planned", "in progress": "under_construction"}


def _milestone(value: dict[str, Any] | None) -> dict[str, str | None]:
    value = value or {}
    precision = value.get("precision", "unknown")
    date_value = value.get("date")
    if precision not in {"day", "month", "year", "unknown"}:
        precision = "unknown"
    if precision == "unknown":
        date_value = None
    return {"raw": value.get("raw"), "value": date_value, "precision": precision}


def normalize(root: Path) -> list[dict[str, Any]]:
    records, errors, _ = collect(root)
    if errors:
        raise ValueError("legacy inputs failed validation:\n" + "\n".join(errors))
    joined = join_projects(records["projects"], records["locations"])
    ready = {**records, "projects": joined}
    decisions = decide(records["reviews"], current_subjects(ready))
    endpoint_decisions = {record_id: state for (kind, record_id), state in decisions.items() if kind == "endpoint"}
    bound_locations, bind_errors = bind_locations(records["projects"], records["locations"])
    if bind_errors:
        raise ValueError("legacy location binding failed:\n" + "\n".join(bind_errors))
    accepted: dict[str, list[dict[str, Any]]] = defaultdict(list)
    usable: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for location in bound_locations:
        if location["confidence"] == "rejected":
            continue
        accepted[location["project_id"]].append(location)
        if endpoint_decisions.get(location["_id"]) != "rejected":
            usable[location["project_id"]].append(location)

    source_hashes = {
        source["_id"]: source["sha256"] for source in load_json(root / "data" / "sources" / "sources.json")
    }
    boundaries = StateBoundaries.load(root / "data/locations/boundaries")
    state_fips = {name: code for code, name in STATE_CODES.items()}

    projects = []
    for project in records["projects"]:
        if not project["active"]:
            continue
        endpoints = sorted(usable.get(project["_id"], []), key=lambda row: (row["endpoint_index"], row["_id"]))
        located = center(endpoints)
        if located:
            reviews = [endpoint_decisions.get(endpoint["_id"]) for endpoint in endpoints]
            location_review = "confirmed" if reviews and all(review == "confirmed" for review in reviews) else "needs_review"
            located = {
                **located,
                "evidence": "Legacy endpoint records: " + ", ".join(endpoint["_id"] for endpoint in endpoints),
            }
        elif accepted.get(project["_id"]):
            location_review = "rejected"
        else:
            location_review = "unlocated"
        # State membership follows eligible endpoints, never the utility name or a line's mean point.
        endpoint_states = [
            {"endpoint_id": endpoint["_id"], "state_fips": state_fips[state]}
            for endpoint in endpoints
            if endpoint.get("lat") is not None and endpoint.get("lon") is not None
            if (state := boundaries.state_for(endpoint["lon"], endpoint["lat"])) is not None
        ]
        states = sorted({entry["state_fips"] for entry in endpoint_states})
        source = project["source"]
        status = project.get("status")
        projects.append({
            "_id": f"legacy:{project['_id']}",
            "source_id": source["source_id"],
            "native_id": str(project["native_id"]),
            "name": project["name"],
            "description": project.get("description"),
            "owner": project.get("owner_code"),
            "other_owners": [],
            "planning_region": None,
            "states": states,
            "counties": [],
            "geography_basis": (
                "Census containment of eligible legacy endpoints; candidate location review retained; "
                "endpoint membership does not establish the full route or county."
                if states else "reviewed_legacy_endpoints" if located else None
            ),
            "status": status,
            "status_group": STATUS_GROUPS.get((status or "").strip().lower(), "unknown"),
            "in_service": _milestone(project.get("in_service")),
            "center": located,
            "location_review": location_review,
            "legacy_project_key": project["project_key"],
            "legacy_utility": project["utility"],
            "evidence": {
                "page": source.get("page"),
                "sheet": None,
                "row": source.get("row_top") if type(source.get("row_top")) is int else None,
                "source_sha256": source_hashes[source["source_id"]],
                "raw": {
                    "project_id": project["_id"],
                    "project_key": project["project_key"],
                    "active": project["active"],
                    "owner_code": project.get("owner_code"),
                    "status": status,
                    "in_service": project.get("in_service"),
                    "row_top": source.get("row_top"),
                    "endpoint_reviews": {
                        endpoint["_id"]: endpoint_decisions.get(endpoint["_id"], "needs_review")
                        for endpoint in accepted.get(project["_id"], [])
                    },
                    "state_assignment": {
                        "method": "eligible_endpoint_containment",
                        "boundary_url": boundaries.manifest["query_url"],
                        "boundary_sha256": boundaries.manifest["raw_geojson_sha256"],
                        "boundary_vintage": boundaries.manifest["source_vintage"],
                        "endpoints": endpoint_states,
                    } if states else None,
                },
            },
        })
    return sorted(projects, key=lambda project: project["_id"])
