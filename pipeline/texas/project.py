"""Stage the four source-linked Georgetown transmission projects for national review."""

from __future__ import annotations

import json
from pathlib import Path

from common import validate
from texas.tpit import GIS_URL, SOURCE_ID

SOURCE_URL = "https://www.ercot.com/files/docs/2022/03/02/ERCOT-July-Ad-Hoc-TPIT-No-Cost-071326-UPDATE.xlsx"


def stage(rows: list[dict], summary: dict, future_rows: list[dict] | None = None) -> tuple[dict, list[dict]]:
    source = {
        "_id": SOURCE_ID,
        "title": "July 2026 Transmission Project Information Tracking",
        "publisher": "ERCOT",
        "authority": "regional_planning_organization",
        "role": "project_plan",
        "landing_url": "https://www.ercot.com/gridinfo/sysplan",
        "download_url": SOURCE_URL,
        "publication_date": "2026-07-17",
        "vintage": "2026-07-13",
        "retrieved_at": None,
        "sha256": summary["source_sha256"],
        "public_status": "verified_public",
        "access_policy": "public_document",
        "import_status": "imported",
        "planning_region": "ercot",
        "states": ["48"],
        "project_count": 4,
        "notes": [
            "Four scope-reviewed transmission projects staged; 354 planned-sheet rows remain research observations.",
            "All four points are labeled candidate locations from City of Georgetown facility geometry.",
            "The workbook's Month/Yr date headers determine milestone precision.",
        ],
    }
    validate(source, "national-source")
    projects = []
    for row in rows:
        candidate = row["candidate_location"]
        if candidate is None:
            continue
        if row["status_raw"] != "Planned" or not row["title"] or row["county_from_raw"] != "Williamson":
            raise ValueError(f"project {row['native_id']} needs manual scope/status review")
        if row["native_id"] not in {"80546B", "92629", "80546C", "85973"}:
            raise ValueError("unreviewed project entered staged set")
        project = {
            "_id": f"ercot-tpit:{row['native_id']}",
            "source_id": SOURCE_ID,
            "native_id": row["native_id"],
            "name": row["title"],
            "description": None,
            "owner": row["owner_raw"],
            "other_owners": [],
            "planning_region": "ercot",
            "states": ["48"],
            "counties": ["48491"],
            "geography_basis": "ERCOT Williamson County terminal; Census coordinate county check",
            "status": row["status_raw"],
            "status_group": "planned",
            "in_service": row["projected_in_service"],
            "center": {
                "lat": candidate["lat"], "lon": candidate["lon"], "basis": "one",
                "evidence": f"Unverified candidate: ERCOT row {row['row']} terminal matched City of Georgetown "
                            f"facility {candidate['facility_global_id']} ({GIS_URL})",
            },
            "location_review": "unreviewed",
            "location_candidate": candidate,
            "evidence": {
                "page": None,
                "sheet": row["sheet"],
                "row": row["row"],
                "source_sha256": row["source_sha256"],
                "raw": {
                    "ERCOT Project Number": row["native_id"],
                    "Project Title": row["title"],
                    "Terminal from": row["terminal_from"],
                    "Terminal to": row["terminal_to"],
                    "Transmission Status": row["status_raw"],
                    "Transmission Owner": row["owner_raw"],
                    "Projected In-Service Date": row["projected_in_service"]["raw"],
                    "County from": row["county_from_raw"],
                    "County to": row["county_to_raw"],
                    "Service Level kV": row["voltage_kv_raw"],
                },
            },
        }
        validate(project, "national-project")
        projects.append(project)
    if len(projects) != 4 or len({p["_id"] for p in projects}) != 4:
        raise ValueError("staged project count/identity changed")
    if summary["source_sha256"] != rows[0]["source_sha256"]:
        raise ValueError("source hash mismatch")
    if future_rows is not None:
        from texas.more import stage_future

        projects.extend(stage_future(future_rows, summary["source_sha256"]))
        projects.sort(key=lambda item: item["_id"])
        if len(projects) != 8 or len({item["_id"] for item in projects}) != 8:
            raise ValueError("staged project count/identity changed")
        source["project_count"] = 8
        source["notes"] = [
            "Eight manually scoped transmission projects staged from July 2026 TPIT; other rows remain research observations.",
            "All eight point candidates use City of Georgetown facility geometry and carry unreviewed labels.",
            "The workbook's Month/Yr headers determine milestone precision; source cohort and row statuses remain separate.",
        ]
        validate(source, "national-source")
    return source, projects


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    folder = root / "data" / "texas"
    rows = json.loads((folder / "planned-observations.json").read_text())
    summary = json.loads((folder / "planned-summary.json").read_text())
    future = folder / "future-observations.json"
    future_rows = json.loads(future.read_text()) if future.exists() else None
    source, projects = stage(rows, summary, future_rows)
    (folder / "publication-source.json").write_text(json.dumps(source, indent=2) + "\n")
    (folder / "publication-candidates.json").write_text(json.dumps(projects, indent=2) + "\n")


if __name__ == "__main__":
    main()
