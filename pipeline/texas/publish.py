"""Validate the fixed C29 Texas candidate release before national assembly."""

from __future__ import annotations

import hashlib
import math
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from common import load_json, validate
from texas.tpit import GIS_URL, SOURCE_ID, _facility

ACTIVE = Path("data/texas/releases/active.json")
FILES = {
    "source": "publication-source.json",
    "projects": "publication-candidates.json",
    "planned": "planned-observations.json",
    "future": "future-observations.json",
    "completed": "completed-observations.json",
    "source_audit": "source-audit.json",
    "geo_audit": "geo-source.json",
    "planned_summary": "planned-summary.json",
    "more_summary": "more-summary.json",
    "facilities": "facility-ledger.json",
}
ALLOWED_IDS = {"80546B", "92629", "80546C", "85973", "109790", "109814", "110120", "110122"}
SHEETS = {"planned": "PlannedTPIT071326NoCost", "future": "FutureTPIT071326NoCost"}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _time(value: str | None) -> None:
    if not value or datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() is None:
        raise ValueError("release requires observed UTC retrieval time")


def _unique(rows: list[dict], key: str) -> dict:
    result = {item[key] for item in rows}
    if len(result) != len(rows):
        raise ValueError(f"duplicate {key}")
    return {item[key]: item for item in rows}


def _close(a: float, b: float) -> bool:
    return math.isfinite(a) and math.isfinite(b) and abs(a - b) < 1e-9


def _check_project(project: dict, row: dict, entry: dict, release: dict, facilities: dict) -> None:
    validate(project, "national-project")
    native = project["native_id"]
    evidence = project["evidence"]
    raw = evidence["raw"]
    candidate = project["location_candidate"]
    center = project["center"]
    if (project["_id"] != f"ercot-tpit:{native}" or project["source_id"] != SOURCE_ID
            or project["location_review"] != "unreviewed" or candidate["tier"] != "candidate"
            or candidate["independent_review"] is not False or project["status_group"] != "planned"
            or project["status"] != row["status_raw"] or project["status"] != "Planned"
            or project["owner"] != row["owner_raw"] or project["name"] != row["title"]
            or project["states"] != ["48"] or project["counties"] != ["48491"]):
        raise ValueError(f"candidate identity/status changed: {native}")
    if (evidence["sheet"] != row["sheet"] or evidence["row"] != row["row"]
            or evidence["source_sha256"] != release["source_sha256"]
            or row["source_sha256"] != release["source_sha256"]
            or entry["sheet"] != row["sheet"] or entry["row"] != row["row"]
            or entry["id"] != project["_id"]):
        raise ValueError(f"source row or hash changed: {native}")
    fields = {
        "ERCOT Project Number": "native_id", "Project Title": "title",
        "Terminal from": "terminal_from", "Terminal to": "terminal_to",
        "Transmission Status": "status_raw", "Transmission Owner": "owner_raw",
        "County from": "county_from_raw", "County to": "county_to_raw",
        "Service Level kV": "voltage_kv_raw",
    }
    if any(raw[field] != row[key] for field, key in fields.items()):
        raise ValueError(f"source facts changed: {native}")
    milestone = row["projected_in_service"]
    if (project["in_service"] != milestone or milestone["precision"] != "month"
            or raw["Projected In-Service Date"] != milestone["raw"]):
        raise ValueError(f"month milestone changed: {native}")
    if (candidate != row["candidate_location"] or candidate["gis_url"] != GIS_URL
            or candidate["gis_sha256"] != release["gis_sha256"]
            or candidate["gis_crs"] != "EPSG:4326"):
        raise ValueError(f"candidate geometry evidence changed: {native}")

    if row["sheet"] == SHEETS["planned"]:
        if len(entry["endpoints"]) != 1:
            raise ValueError("planned candidate requires one located endpoint")
        side = entry["endpoints"][0]["side"]
        points = [{
            "side": side, "name": candidate["facility_name"],
            "global_id": candidate["facility_global_id"],
            "lat": candidate["lat"], "lon": candidate["lon"],
        }]
        if row[f"county_{side}_raw"] != "Williamson":
            raise ValueError(f"candidate county changed: {native}")
    else:
        points = [{k: item[k] for k in ("side", "name", "global_id", "lat", "lon")}
                  for item in candidate["endpoints"]]
        for point in points:
            county = row[f"county_{point['side']}_raw"]
            if county != "Williamson" and not (
                native == "109814" and point["side"] == "to" and county is None
                and candidate["owner_relation_url"] == "https://www.lcra.org/energy/electric-transmission/"
            ):
                raise ValueError(f"candidate county/owner link changed: {native}")
    if len(points) not in (1, 2) or points != entry["endpoints"]:
        raise ValueError(f"terminal/GIS link changed: {native}")
    for point in points:
        terminal = row[f"terminal_{point['side']}"]
        feature = facilities.get(_facility(terminal))
        if (_facility(terminal) != _facility(point["name"])
                or feature is None or feature["global_id"] != point["global_id"]
                or not _close(feature["lat"], point["lat"])
                or not _close(feature["lon"], point["lon"])
                or not (-106 <= point["lon"] <= -93 and 25 <= point["lat"] <= 37)
                or not all(math.isfinite(point[key]) for key in ("lat", "lon"))):
            raise ValueError(f"candidate terminal or Texas coordinates changed: {native}")
        if native == "109814" and feature["owner"] != "LCRA":
            raise ValueError("Glasscock owner corroboration changed")
    basis = "two" if len(points) == 2 else "one"
    lat = sum(point["lat"] for point in points) / len(points)
    lon = sum(point["lon"] for point in points) / len(points)
    if (center["basis"] != basis or candidate["basis"] != basis
            or not all(_close(lat, v) for v in (center["lat"], candidate["lat"], entry["center"]["lat"]))
            or not all(_close(lon, v) for v in (center["lon"], candidate["lon"], entry["center"]["lon"]))):
        raise ValueError(f"candidate center changed: {native}")


def apply_release(snapshot: dict, root: Path) -> dict:
    path = root / ACTIVE
    if not path.exists():
        return snapshot
    release = load_json(path)
    if (release["policy"] != "C25" or release["source_id"] != SOURCE_ID
            or release["release_id"] != "texas-ercot-2026-07-candidates-1"
            or set(release["files"]) != set(FILES)
            or set(release["expected_counts"]) != {"projects", "centers", "observations"}
            or release["expected_counts"] != {"projects": 8, "centers": 5, "observations": 2049}):
        raise ValueError("Texas release manifest changed")
    folder = root / "data" / "texas"
    for key, filename in FILES.items():
        if _sha(folder / filename) != release["files"][key]:
            raise ValueError(f"Texas release file hash changed: {key}")
    data = {key: load_json(folder / filename) for key, filename in FILES.items()}
    source = data["source"]
    validate(source, "national-source")
    source_audit, geo_audit = data["source_audit"], data["geo_audit"]
    ledger = data["facilities"]
    _time(release["workbook_retrieved_at"])
    _time(release["gis_retrieved_at"])
    if (release["source_sha256"] != source["sha256"] or source["sha256"] != source_audit["sha256"]
            or source_audit["reacquired_sha256"] != source["sha256"]
            or release["workbook_retrieved_at"] != source["retrieved_at"]
            or source["retrieved_at"] != source_audit["reacquired_at"]
            or release["gis_sha256"] != geo_audit["sha256"]
            or geo_audit["reacquired_sha256"] != geo_audit["sha256"]
            or release["gis_retrieved_at"] != geo_audit["reacquired_at"]
            or geo_audit["crs"] != "EPSG:4326"
            or ledger["source_sha256"] != geo_audit["sha256"]
            or ledger["crs"] != "EPSG:4326"
            or len(ledger["facilities"]) != geo_audit["feature_count"]
            or source["_id"] != SOURCE_ID or source["project_count"] != 8
            or source["import_status"] != "imported" or source["role"] != "project_plan"):
        raise ValueError("Texas source acquisition or identity changed")
    rows = data["planned"] + data["future"]
    if (len(data["planned"]) != 358 or len(data["future"]) != 1429
            or len(data["completed"]) != 262 or len(rows) + len(data["completed"]) != 2049
            or data["planned_summary"]["source_sha256"] != source["sha256"]
            or data["more_summary"]["source_sha256"] != source["sha256"]
            or data["more_summary"]["gis_sha256"] != geo_audit["sha256"]):
        raise ValueError("Texas observation reconciliation changed")
    observations = {(row["sheet"], row["row"]): row for row in rows}
    if len(observations) != len(rows):
        raise ValueError("duplicate source row")
    facilities = _unique(ledger["facilities"], "global_id")
    by_name = {_facility(item["name"]): item for item in facilities.values()}
    if len(by_name) != len(facilities):
        raise ValueError("ambiguous normalized facility name")
    projects = _unique(data["projects"], "_id")
    entries = _unique(release["entries"], "id")
    if (len(projects) != 8 or projects.keys() != entries.keys()
            or {project["native_id"] for project in projects.values()} != ALLOWED_IDS):
        raise ValueError("Texas accepted project identity changed")
    if any(project["source_id"] == SOURCE_ID for project in snapshot["projects"]):
        raise ValueError("Texas source already present")
    if source["_id"] in {item["_id"] for item in snapshot["sources"]} or projects.keys() & {
        item["_id"] for item in snapshot["projects"]
    }:
        raise ValueError("Texas release conflicts with active identity")
    for project_id, project in projects.items():
        entry = entries[project_id]
        row = observations.get((entry["sheet"], entry["row"]))
        if row is None or row["native_id"] != project["native_id"]:
            raise ValueError(f"Texas source locator changed: {project_id}")
        _check_project(project, row, entry, release, by_name)
    centers = {(project["center"]["lat"], project["center"]["lon"]) for project in projects.values()}
    if len(centers) != 5:
        raise ValueError("Texas distinct center count changed")
    result = deepcopy(snapshot)
    result["sources"].append(deepcopy(source))
    result["projects"].extend(deepcopy(list(projects.values())))
    result["coverage"]["texas"] = {
        "release_id": release["release_id"], "source_id": SOURCE_ID,
        "source_observations": 2049, "candidate_projects": 8,
        "distinct_centers": 5, "complete_endpoint_projects": 1,
        "partial_endpoint_projects": 7, "independently_confirmed_projects": 0,
        "source_sha256": source["sha256"], "gis_sha256": geo_audit["sha256"],
        "notes": "Williamson County candidate locations only; no Texas-wide coverage claim.",
    }
    return result
