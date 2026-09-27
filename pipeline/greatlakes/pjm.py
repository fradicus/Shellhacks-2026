"""Pennsylvania rows from the browser-downloaded public PJM construction register.

Run `python -m greatlakes.pjm --source ~/Downloads/projectCostUpgrades.xml [--check]`.
Native upgrade IDs are components; several can share a facility or parent project.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from common import validate
from expansion.pjm_mid_atlantic import events, normalize, read_registry
from national.build import load_snapshot

from . import osm
from .match import voltages_kv
from .shared import locate, write_outputs

SOURCE_ID = "greatlakes-pjm-pa"
URL = "https://www.pjm.com/pjmfiles/media/planning/projectConstruction-data/projectCostUpgrades.xml"
SHA256 = "cb96605a3dd65cc62111df5ef58ba54075116e53b60b965b198d4b86d764f002"
RETRIEVED = "2026-09-27T12:31:06.802585+00:00"
# Source descriptions explicitly identify distribution-only work, outside the transmission scope.
EXCLUDED = {"b0012": "distribution capacitors in an area, not a named transmission facility",
            "n6890": "tap and recloser on explicitly described distribution circuit 00517-63",
            "n8207.1": "SCADA switch on explicitly described distribution circuit 00519-51"}
DATASET = "OpenStreetMap PA substations (ODbL); HIFLD fallback data/greatlakes/hifld/sources.json"


def project(row: dict, source: dict, facilities: list[dict]) -> dict:
    p = normalize(row, source)
    p["_id"] = f"{SOURCE_ID}:{row['native_id']}"
    raw = row["raw"]
    # Location, voltage and equipment are verbatim fields, title-cased only for the existing name parser.
    title = " ".join(s for s in (raw["Location"].title(),
                                f"{raw['Voltage']} kV" if raw["Voltage"] else "",
                                raw["Equipment"].title()) if s)
    sites = re.findall(r"\bat (?:the )?([A-Z][\w.'’]*(?: [A-Z][\w.'’]*){0,3}) (?:[Ss]ubstation|[Ss]tation)\b",
                     raw["Description"])
    site_equipment = raw["Equipment"] in {"Circuit Breaker", "Transformer", "Capacitor", "Bus", "Substation",
                                                   "Substation equipment", "Disconnect Switch", "Relay",
                                                   "Communication Equipment", "Reactive Device"}
    if len(sites) == 1 and site_equipment:
        # A breaker at Elroy is at that site even when Location names the entire Elroy–Hosensack circuit.
        title = f"{sites[0]} Substation"
    center, candidate = locate(title, raw["Description"], facilities, [],
                               voltages_kv(title, f"{raw['Voltage']} kV"), DATASET)
    if site_equipment and candidate["kind"] == "line":
        # A circuit label does not tell us which terminal contains the site equipment.
        center = None
        candidate["reason"] = "site_equipment_work_site_unresolved"
    p["center"] = center
    p["location_review"] = "unreviewed" if center else "unlocated"
    p["location_candidate"] = candidate
    p["project_events"] = events(p)
    p["evidence"]["raw"]["source_sha256"] = source["sha256"]
    p["evidence"]["raw"]["location_note"] = (
        "Candidate from the explicit PJM Location, Voltage and Equipment fields, with Description as parser fallback. "
        "Owner code is not expanded or used as operator corroboration. No location is independently reviewed.")
    validate(p, "national-project")
    return p


def build(path: Path) -> dict:
    source = {"_id": SOURCE_ID, "sha256": SHA256, "download_url": URL, "retrieved_at": RETRIEVED}
    rows = read_registry(path, source)
    snapshot = load_snapshot()
    existing = {p["native_id"]: p["_id"] for p in snapshot["projects"]
                if "pjm" in p["source_id"].lower() and p["source_id"] != SOURCE_ID}
    facilities = osm.load(["PA"])
    projects, dispositions = [], []
    for row in rows:
        entry = {"native_id": row["native_id"], "locator": row["locator"]}
        if row["native_id"] in existing:
            dispositions.append(entry | {"disposition": "duplicate", "project_id": existing[row["native_id"]],
                                         "reason": "same PJM native upgrade ID already published"})
        elif row["raw"]["State"] != "PA":
            dispositions.append(entry | {"disposition": "excluded", "reason": "not an explicitly PA-only row"})
        elif row["native_id"] in EXCLUDED:
            dispositions.append(entry | {"disposition": "excluded", "reason": EXCLUDED[row["native_id"]]})
        else:
            p = project(row, source, facilities)
            projects.append(p)
            dispositions.append(entry | {"disposition": "accepted", "project_id": p["_id"],
                                         "reason": "explicit PA state, new PJM upgrade/component ID"})
    return {"projects": projects, "dispositions": dispositions, "sources": [{
        "_id": SOURCE_ID, "artifacts": [{"file": "projectCostUpgrades.xml", "url": URL, "sha256": SHA256,
                                          "retrieved_at": RETRIEVED,
                                          "access_review": "Public XML saved through Brave; no login or warning bypass."}],
        "project_count": len(projects), "notes": [
            "PJM upgrade/component IDs, not a count of distinct construction sites. Owner codes retained verbatim.",
            "Actual, projected and revised service dates remain separate source events. No completion inferred."]}]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    raise SystemExit(write_outputs("pjm", build(args.source), args.check))
