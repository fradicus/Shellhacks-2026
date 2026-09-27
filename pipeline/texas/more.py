"""Research later ERCOT TPIT sheets and stage only manually scoped line candidates."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from common import validate
from texas.tpit import GIS_URL, SOURCE_ID, _facility, _month, _text

FUTURE = "FutureTPIT071326NoCost"
COMPLETED = "CompletedTPIT071326NoCost"
FUTURE_CANDIDATES = {940: ("from", "to"), 1140: ("to",), 1358: ("from",), 1366: ("from",)}
FUTURE_IDS = {940: "109790", 1140: "109814", 1358: "110122", 1366: "110120"}
OWNER_RELATION = "https://www.lcra.org/energy/electric-transmission/"


def extract_more(workbook: Path, gis: Path) -> tuple[dict[str, list[dict]], dict]:
    from openpyxl import load_workbook

    book = load_workbook(workbook, read_only=True, data_only=True)
    facilities: dict[str, list[dict]] = defaultdict(list)
    for feature in json.loads(gis.read_text())["features"]:
        facilities[_facility(feature["properties"].get("Name"))].append(feature)
    source_hash = hashlib.sha256(workbook.read_bytes()).hexdigest()
    gis_hash = hashlib.sha256(gis.read_bytes()).hexdigest()
    cohorts = {}
    summary = {"source_sha256": source_hash, "gis_sha256": gis_hash, "sheets": {}}
    for sheet_name, count in ((FUTURE, 1429), (COMPLETED, 262)):
        if sheet_name not in book.sheetnames:
            raise ValueError(f"missing sheet {sheet_name}")
        sheet = book[sheet_name]
        if "7/13/2026" not in str(sheet["A1"].value):
            raise ValueError(f"source vintage changed in {sheet_name}")
        headings = next(sheet.iter_rows(min_row=2, max_row=2, values_only=True))
        if headings[0] != "ERCOT Project Number" or headings[11] != "Projected In-Service Date (Month/Yr)":
            raise ValueError(f"columns changed in {sheet_name}")
        records = []
        for number, row in enumerate(sheet.iter_rows(min_row=3, values_only=True), start=3):
            if row[0] is None:
                continue
            item = {
                "source_id": SOURCE_ID, "native_id": _text(row[0]), "sheet": sheet_name,
                "row": number, "source_sha256": source_hash, "title": _text(row[1]),
                "terminal_from": _text(row[4]), "terminal_to": _text(row[5]),
                "status_raw": _text(row[6]), "sheet_cohort": "future" if sheet_name == FUTURE else "completed",
                "owner_raw": _text(row[8]), "projected_in_service": _month(row[11]),
                "actual_in_service": _month(row[12]), "voltage_kv_raw": _text(row[13]),
                "county_from_raw": _text(row[18]), "county_to_raw": _text(row[19]),
                "disposition": "needs_scope_review", "candidate_location": None,
            }
            if sheet_name == FUTURE and number in FUTURE_CANDIDATES:
                if (item["native_id"] != FUTURE_IDS[number] or item["status_raw"] != "Planned"
                        or item["owner_raw"] != "LCRATSC" or not item["title"]):
                    raise ValueError(f"candidate project facts changed at row {number}")
                endpoints = []
                for side in FUTURE_CANDIDATES[number]:
                    terminal = item[f"terminal_{side}"]
                    matches = facilities[_facility(terminal)]
                    if len(matches) != 1:
                        raise ValueError(f"candidate {number} has ambiguous facility {terminal}")
                    feature = matches[0]
                    lon, lat = feature["geometry"]["coordinates"]
                    if not (-106 <= lon <= -93 and 25 <= lat <= 37):
                        raise ValueError(f"candidate {number} is outside Texas bounds")
                    county = item[f"county_{side}_raw"]
                    if county != "Williamson" and not (
                        number == 1140 and side == "to" and county is None
                        and feature["properties"].get("OWNER") == "LCRA"
                    ):
                        raise ValueError(f"candidate {number} lacks county/owner corroboration")
                    endpoints.append({
                        "side": side, "name": feature["properties"]["Name"],
                        "global_id": feature["properties"]["GlobalID"],
                        "lat": lat, "lon": lon,
                        "county_check": "48491",
                    })
                item["candidate_location"] = {
                    "tier": "candidate", "basis": "two" if len(endpoints) == 2 else "one",
                    "lat": sum(e["lat"] for e in endpoints) / len(endpoints),
                    "lon": sum(e["lon"] for e in endpoints) / len(endpoints),
                    "endpoints": endpoints, "gis_url": GIS_URL, "gis_sha256": gis_hash,
                    "gis_crs": "EPSG:4326",
                    "owner_relation_url": OWNER_RELATION if number == 1140 else None,
                    "independent_review": False,
                }
            records.append(item)
        ids = Counter(item["native_id"] for item in records)
        if len(records) != count:
            raise ValueError(f"row count changed in {sheet_name}")
        duplicate_ids = sorted(key for key, value in ids.items() if value > 1)
        expected_duplicates = ["102795", "110733", "110749", "110751", "110753"] if sheet_name == FUTURE else []
        if duplicate_ids != expected_duplicates:
            raise ValueError(f"duplicate IDs changed in {sheet_name}")
        cohorts[sheet_name] = records
        summary["sheets"][sheet_name] = {
            "observations": len(records), "unique_ids": len(ids), "duplicate_ids": duplicate_ids,
            "statuses": dict(sorted(Counter(item["status_raw"] or "unknown" for item in records).items())),
            "candidate_projects": sum(item["candidate_location"] is not None for item in records),
            "publication_status": "research_only",
        }
    return cohorts, summary


def stage_future(records: list[dict], source_hash: str) -> list[dict]:
    projects = []
    for row in records:
        location = row["candidate_location"]
        if location is None:
            continue
        if (row["sheet"] != FUTURE or row["native_id"] != FUTURE_IDS.get(row["row"])
                or row["status_raw"] != "Planned" or row["owner_raw"] != "LCRATSC"
                or not row["title"]):
            raise ValueError("unreviewed project entered future staged set")
        if row["source_sha256"] != source_hash:
            raise ValueError("source hash mismatch")
        project = {
            "_id": f"ercot-tpit:{row['native_id']}", "source_id": SOURCE_ID,
            "native_id": row["native_id"], "name": row["title"], "description": None,
            "owner": row["owner_raw"], "other_owners": [], "planning_region": "ercot",
            "states": ["48"], "counties": ["48491"],
            "geography_basis": "ERCOT named terminal; city GIS; Census Williamson County check",
            "status": row["status_raw"], "status_group": "planned",
            "in_service": row["projected_in_service"],
            "center": {
                "lat": location["lat"], "lon": location["lon"], "basis": location["basis"],
                "evidence": f"Unverified candidate: ERCOT {row['sheet']} row {row['row']} terminals "
                            f"linked to City of Georgetown features ({GIS_URL})",
            },
            "location_review": "unreviewed", "location_candidate": location,
            "evidence": {
                "page": None, "sheet": row["sheet"], "row": row["row"],
                "source_sha256": source_hash,
                "raw": {
                    "ERCOT Project Number": row["native_id"], "Project Title": row["title"],
                    "Terminal from": row["terminal_from"], "Terminal to": row["terminal_to"],
                    "Transmission Status": row["status_raw"], "Transmission Owner": row["owner_raw"],
                    "Projected In-Service Date": row["projected_in_service"]["raw"],
                    "County from": row["county_from_raw"], "County to": row["county_to_raw"],
                    "Service Level kV": row["voltage_kv_raw"],
                },
            },
        }
        validate(project, "national-project")
        projects.append(project)
    if len(projects) != 4:
        raise ValueError("staged future count changed")
    return projects


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    folder = root / "data" / "texas"
    source_audit = json.loads((folder / "source-audit.json").read_text())
    geo_audit = json.loads((folder / "geo-source.json").read_text())
    workbook = Path(sys.argv[1])
    gis = Path(sys.argv[2])
    cohorts, summary = extract_more(workbook, gis)
    if summary["source_sha256"] != source_audit["sha256"] or summary["gis_sha256"] != geo_audit["sha256"]:
        raise ValueError("sources differ from pinned acquisition")
    for sheet_name, filename in ((FUTURE, "future-observations.json"), (COMPLETED, "completed-observations.json")):
        (folder / filename).write_text(json.dumps(cohorts[sheet_name], indent=2) + "\n")
    (folder / "more-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    features = json.loads(gis.read_text())["features"]
    ledger = {
        "source_sha256": summary["gis_sha256"], "crs": "EPSG:4326",
        "facilities": sorted(({
            "name": feature["properties"]["Name"],
            "owner": feature["properties"].get("OWNER"),
            "global_id": feature["properties"]["GlobalID"],
            "lat": feature["geometry"]["coordinates"][1],
            "lon": feature["geometry"]["coordinates"][0],
        } for feature in features), key=lambda item: item["global_id"]),
    }
    (folder / "facility-ledger.json").write_text(json.dumps(ledger, indent=2) + "\n")
    from texas.project import main as stage_projects

    stage_projects()


if __name__ == "__main__":
    main()
