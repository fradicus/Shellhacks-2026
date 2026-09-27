"""Apply the fixed, independently reviewed location release to the national snapshot.

No network or database writes. F30 invokes this after validating its original snapshot.
"""

from __future__ import annotations

import math
from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from common import load_json, validate
from expansion.new_england import facts_hash

ACTIVE_RELEASE = Path("data/expansion/releases/active.json")
ROLES = {"site": {"site"}, "line": {"a", "b"}}


def record_hash(record: dict) -> str:
    return facts_hash({key: value for key, value in record.items() if key != "reviews"})


def utc(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None or result.utcoffset().total_seconds() != 0:
        raise ValueError("review and release times must be UTC")
    if result > datetime.now(UTC):
        raise ValueError("review or release time is in the future")
    return result


def check_point(point: dict) -> None:
    original = point["original_geometry"]
    x, y = original["coordinates"]
    if original["crs"] in {"EPSG:3857", "EPSG:102100"}:
        expected = [math.degrees(x / 6378137), math.degrees(math.atan(math.sinh(y / 6378137)))]
        if abs(point["lon"] - expected[0]) > 1e-7 or abs(point["lat"] - expected[1]) > 1e-7:
            raise ValueError("Web Mercator transformation does not reproduce the location")
    elif original["crs"] == "EPSG:4326":
        if abs(point["lon"] - x) > 1e-9 or abs(point["lat"] - y) > 1e-9:
            raise ValueError("WGS84 source point differs from the published location")
    elif original["crs"] == "EPSG:32145":
        # Independent reviewers recompute the specific datum operation and bind its exact output.
        # No unsupported runtime transformation is substituted for that reviewed operation.
        if "independently" not in original["transform"].lower():
            raise ValueError("Vermont transformation requires documented independent recomputation")
    else:
        raise ValueError("unreviewed source CRS")
    if not (-74 < point["lon"] < -66 and 40 < point["lat"] < 48):
        raise ValueError("this release is bounded to New England, or coordinate axes were reversed")
    for evidence in point["geometry_evidence"] + point["identity_evidence"]:
        if not evidence["facts"].strip() or not evidence["access_review"].strip():
            raise ValueError("evidence requires supported facts and source access review")
        utc(evidence["retrieved_at"])


def check_record(record: dict, project: dict) -> str:
    if record["project_facts_sha256"] != facts_hash(project):
        raise ValueError(f"{record['project_id']}: original project facts changed")
    if project["center"] is not None or project.get("location_verification") is not None:
        raise ValueError("initial expansion cannot overwrite an already located/reviewed project")
    roles = [point["role"] for point in record["points"]]
    if len(roles) != len(set(roles)) or not set(roles) <= ROLES[record["location_kind"]]:
        raise ValueError("duplicate or invalid site/endpoint role")
    if record["location_kind"] == "site" and roles != ["site"]:
        raise ValueError("a standalone site requires exactly one site point")
    facilities = [point["facility_id"] for point in record["points"]]
    if len(facilities) != len(set(facilities)):
        raise ValueError("two endpoints cannot reuse one facility")
    for point in record["points"]:
        check_point(point)
    seen_reviews = set()
    last_time = None
    for review in record["reviews"]:
        if review["reviewer"] == record["producer"]:
            raise ValueError("producer cannot approve its own location")
        if review["id"] in seen_reviews:
            raise ValueError("duplicate review id")
        seen_reviews.add(review["id"])
        reviewed_at = utc(review["reviewed_at"])
        if last_time and reviewed_at < last_time:
            raise ValueError("reviews must retain append order")
        last_time = reviewed_at
    for event in record["events"]:
        date, precision = event["date"], event["precision"]
        if precision == "unknown":
            if date is not None:
                raise ValueError("unknown event dates must remain null")
        elif not isinstance(date, str) or len(date) != {"day": 10, "month": 7, "year": 4}[precision]:
            raise ValueError("event date does not preserve declared precision")
        else:
            datetime.fromisoformat(date + {"year": "-01-01", "month": "-01", "day": ""}[precision])
        if event["native_project_link"] != project["native_id"]:
            raise ValueError("event is not explicitly linked to the native project")
    if not record["reviews"]:
        return "no_review"
    last = record["reviews"][-1]
    if last["facts_sha256"] != record_hash(record):
        return "stale_review"
    return last["decision"]


def center(record: dict) -> dict:
    points = record["points"]
    basis = "source_point" if record["location_kind"] == "site" else "two" if len(points) == 2 else "one"
    return {
        "lat": sum(point["lat"] for point in points) / len(points),
        "lon": sum(point["lon"] for point in points) / len(points),
        "basis": basis,
        "evidence": "Independently reviewed " + ("site" if basis == "source_point" else
                     "two endpoints" if basis == "two" else "partial location: one endpoint")
        + "; see location_verification for source precision, identity evidence and review.",
    }


def apply_release(snapshot: dict, root: Path) -> dict:
    path = root / ACTIVE_RELEASE
    if not path.exists():
        return snapshot
    release = load_json(path)
    validate(release, "expansion-release")
    utc(release["created_at"])
    by_id = {project["_id"]: project for project in snapshot["projects"]}
    decisions = {}
    for record in release["records"]:
        project_id = record["project_id"]
        if project_id in decisions:
            raise ValueError("duplicate project in location release")
        if project_id not in by_id:
            raise ValueError("location release cannot introduce an unknown project id")
        decisions[project_id] = check_record(record, by_id[project_id])
    result = deepcopy(snapshot)
    projected = {project["_id"]: project for project in result["projects"]}
    accepted = []
    for record in release["records"]:
        project_id = record["project_id"]
        project = projected[project_id]
        project["location_verification"] = record
        if decisions[project_id] == "confirmed":
            project["center"] = center(record)
            project["location_review"] = "confirmed"
            accepted.append(record)
        else:
            project["location_review"] = "rejected" if decisions[project_id] == "rejected" else "needs_review"
    result["coverage"]["expansion"] = {
        "release_id": release["release_id"],
        "confirmed_projects": len(accepted),
        "distinct_facility_sites": len({point["facility_id"] for row in accepted for point in row["points"]}),
        "standalone_site_projects": sum(row["location_kind"] == "site" for row in accepted),
        "complete_endpoint_projects": sum(row["location_kind"] == "line" and len(row["points"]) == 2 for row in accepted),
        "partial_endpoint_projects": sum(row["location_kind"] == "line" and len(row["points"]) == 1 for row in accepted),
        "unconfirmed_records": len(release["records"]) - len(accepted),
        "review_counts": dict(Counter(decisions.values())),
        "state_counts": dict(Counter(state for row in accepted for state in by_id[row["project_id"]]["states"])),
        "status_counts": dict(Counter(by_id[row["project_id"]]["status_group"] for row in accepted)),
        "notes": release["coverage_notes"],
    }
    return result
