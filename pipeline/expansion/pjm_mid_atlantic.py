"""Normalize pinned PJM public upgrade rows; never infer or approve a location."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

STATES = {"NY": "36", "NJ": "34", "PA": "42", "DE": "10", "MD": "24", "DC": "11"}
STATUS_GROUPS = {"IS": "in_service", "EP": "planned", "PL": "planned", "UC": "under_construction",
                 "UC-ISP": "under_construction", "Active": "proposed", "Cancelled": "cancelled",
                 "W": "cancelled"}
SOURCE_ID = "mid-atlantic:pjm-construction"
FIELDS = set("UpgradeId SubRegion Description ProjectType Voltage CostEstimate RequiredDate TransmissionOwner "
             "ProposalIds Schedule12Location CostAllocationPercent CostAllocationPercentLRS State Location Equipment "
             "Task Status TEACCost Driver ProjectedInServiceDate ActualInServiceDate PJMBoardApprovalDate ImmediateNeed "
             "InitialTEACDate LatestTEACDate TEACDates PercentComplete ISAInServiceDate RevisedInServiceDate "
             "LastUpdated TEACMaterials".split())


def source_date(raw: str) -> dict:
    value = raw.strip()
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", value):
        return {"raw": raw, "value": datetime.strptime(value, "%m/%d/%Y").date().isoformat(), "precision": "day"}
    return {"raw": raw or None, "value": None, "precision": "unknown"}


def read_registry(path: Path, source: dict) -> list[dict]:
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != source["sha256"]:
        raise ValueError("PJM artifact hash changed")
    tree = ElementTree.fromstring(content)
    if tree.tag != "Upgrades" or any(child.tag != "Upgrade" for child in tree):
        raise ValueError("unexpected PJM registry root")
    rows = []
    ids = set()
    for number, element in enumerate(tree.findall("Upgrade"), 1):
        raw = {child.tag: (child.text or "").strip() for child in element}
        if set(raw) != FIELDS or len(element) != len(FIELDS):
            raise ValueError("PJM fields changed or repeated")
        native = raw["UpgradeId"]
        if not native or native in ids:
            raise ValueError("missing or duplicate PJM native ID")
        ids.add(native)
        rows.append({"native_id": native, "row": number,
                     "locator": f"/Upgrades/Upgrade[{number}] [UpgradeId={native}]", "raw": raw})
    if not rows:
        raise ValueError("empty PJM registry")
    return rows


def normalize(row: dict, source: dict) -> dict:
    raw, native = row["raw"], row["native_id"]
    states = [part.strip() for part in raw["State"].split(",") if part.strip()]
    if not states or any(state not in STATES for state in states):
        raise ValueError("row requires explicit in-scope state review")
    evidence = {"publisher": "PJM Interconnection", "url": source["download_url"],
                "artifact_sha256": source["sha256"], "locator": row["locator"], "source_date": None,
                "retrieved_at": source["retrieved_at"], "access_review": ("Public PJM construction register XML export; "
                                  "no authentication or restricted map used."),
                "facts": ("Native upgrade ID, description, transmission-owner code, states, status code "
                          "and separately named date fields from this exact row.")}
    field = "ActualInServiceDate" if raw["ActualInServiceDate"] else "ProjectedInServiceDate"
    return {"_id": f"mid-atlantic:pjm:{native}", "source_id": source["_id"], "native_id": native,
            "name": f"{raw['Location'] or 'PJM'} — {raw['Equipment'] or raw['ProjectType']} ({native})",
            "description": raw["Description"], "owner": raw["TransmissionOwner"] or None,
            "other_owners": [], "planning_region": "PJM", "states": sorted({STATES[s] for s in states}),
            "counties": [], "geography_basis": "PJM XML State field; no county inferred from a reference point.",
            "status": raw["Status"] or None, "status_group": STATUS_GROUPS.get(raw["Status"], "unknown"),
            "in_service": source_date(raw[field]), "center": None, "location_review": "unlocated",
            "evidence": {"page": None, "sheet": None, "row": row["row"], "source_sha256": source["sha256"],
                         "raw": {**raw, "in_service_selected_field": field, "source_evidence": [evidence],
                                 "identity_note": ("PJM upgrade/component ID; several upgrades can share a facility "
                                                   "or parent project. Owner code retained verbatim."),
                                 "date_note": ("Actual and projected dates remain distinct. LastUpdated dates the source row, "
                                               "not a construction transition.")}}}


def events(project: dict) -> list[dict]:
    raw = project["evidence"]["raw"]
    result = []
    for field, kind in [("ActualInServiceDate", "in_service"), ("ProjectedInServiceDate", "planned_milestone"),
                        ("RevisedInServiceDate", "planned_milestone"), ("RequiredDate", "planned_milestone"),
                        ("ISAInServiceDate", "planned_milestone")]:
        date = source_date(raw[field])
        if date["value"] is not None:
            result.append({"id": f"{project['_id']}:{field}", "type": kind, "date": date["value"],
                           "precision": date["precision"], "native_project_link": project["native_id"],
                           "evidence": [{**raw["source_evidence"][0],
                                         "facts": f"{field}={raw[field]}; field meaning preserved."}],
                           "description": f"PJM {field}: {raw[field]}."})
    return result


def main() -> None:
    """Check the published PJM facts against the exact locally supplied source bytes."""
    import argparse

    from common import REPO_ROOT, load_json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Pinned public projectCostUpgrades.xml")
    args = parser.parse_args()
    release = load_json(REPO_ROOT / "data/expansion/mid-atlantic/releases/active.json")
    source = next(s for s in release["sources"] if s["_id"] == SOURCE_ID)
    rows = read_registry(args.source, source)
    by_id = {r["native_id"]: r for r in rows}
    histories = {h["project_id"]: h["events"] for h in release["project_events"]}
    count = 0
    for project in release["projects"]:
        if project["source_id"] != SOURCE_ID:
            continue
        if normalize(by_id[project["native_id"]], source) != project:
            raise ValueError(f"normalized source facts differ: {project['_id']}")
        if events(project) != histories.get(project["_id"], []):
            raise ValueError(f"source event facts differ: {project['_id']}")
        count += 1
    ledger = next(a for a in release["acquisition"] if a["source_id"] == SOURCE_ID)
    if [r["locator"] for r in rows] != ledger["row_locators"]:
        raise ValueError("source enumeration differs")
    print(f"Verified {count} published PJM projects and all {len(rows)} acquired rows; no files or database changed.")


if __name__ == "__main__":
    main()
