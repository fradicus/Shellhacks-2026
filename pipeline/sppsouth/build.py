"""F47 SPP South (OK, NM, non-ERCOT TX): SPP-approved upgrades with C33/C38 loose, labeled candidate locations.

The rows of SPP's Q3 2026 Quarterly Project Tracking workbook (the artifact F46 pins) that list only Oklahoma, New
Mexico or Texas. Records, statuses, dates and locations follow C43 part 1 through F46's code by import; only the scope,
source identity and owner operator fragments are new (C47). No point is independently reviewed.

From pipeline/:
  uv run python -m sppsouth.build fetch --cache /tmp/sppsouth-f47    # SPP zip, OSM substations (OK, NM, TX)
  uv run python -m sppsouth.build build --cache /tmp/sppsouth-f47 [--check]
OSM data (c) OpenStreetMap contributors, ODbL 1.0.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from common import REPO_ROOT, load_json, write_json
from greatlakes.match import voltages_kv
from greatlakes.shared import fetch_into, fetch_osm, osm_extract, verify_cache
from midwest import build as spp

OUT = REPO_ROOT / "data" / "sppsouth"
STATES = {"OK": "40", "NM": "35", "TX": "48"}
SOURCE_ID = "spp-qpt-2026q3-south"
# SPP rows other rollouts already publish, by native UID (F46 Midwest, F39 dense Southeast).
PUBLISHED = (("data/midwest/projects.json", "spp-qpt-2026q3"), ("data/southeast/dense/misospp/projects.json", "spp-qpt"))
# OSM operator-name fragments for the SPP owner codes in these states; F46's list answers the rest. Owners without an
# entry get no operator corroboration and no operator guard.
OPERATOR_KEYS = spp.OPERATOR_KEYS | {
    "OGE": ["OKLAHOMA GAS", "OG&E"],
    "AEP": ["AMERICAN ELECTRIC POWER", "AEP", "PUBLIC SERVICE COMPANY OF OKLAHOMA", "SOUTHWESTERN ELECTRIC POWER",
            "SWEPCO"],
    "WFEC": ["WESTERN FARMERS"], "GRDA": ["GRAND RIVER DAM"], "SPS": ["SOUTHWESTERN PUBLIC", "XCEL"],
    "ETEC": ["EAST TEXAS ELECTRIC"], "LEA": ["LEA COUNTY"], "SWPA": ["SOUTHWESTERN POWER ADMIN"],
}


# Xcel names its SPS sites "Potter County Interchange", "TUCO Interchange"; SPP's workbook says "Potter County", "TUCO".
# Aliases come only from the OSM name itself and only where OSM names SPS/Xcel as operator.
SPS_SUFFIX = re.compile(r"^(.+?) (?:Interchange|Switching Station|Switchyard)$", re.I)


def with_aliases(facilities: list[dict]) -> list[dict]:
    return facilities + [f | {"name": m[1], "norm": m[1].upper(), "osm_name": f["name"]} for f in facilities
                         if (m := SPS_SUFFIX.match(f["name"]))
                         and any(k in (f.get("operator") or "").upper() for k in OPERATOR_KEYS["SPS"])]


def published_uids(root: Path = REPO_ROOT) -> set[str]:
    return {p["native_id"] for path, fragment in PUBLISHED if (root / path).exists()
            for p in load_json(root / path) if fragment in p["source_id"]}


def project(row: dict, artifact: dict, facilities: dict[str, list[dict]]) -> dict:
    """F46's SPP record (C43 part 1) under this rollout's source ID and state codes."""
    native = str(row["UID"])
    pid = f"{SOURCE_ID}:{native}"
    status = spp.clean(row["Project Status"] or "Not stated")
    group = spp.status_group(status)
    states = spp.row_states(row["State(s)"])
    locator = f"{spp.MEMBER.split('/')[-1]}, sheet {row['_sheet']}, row {row['_row']}"
    evidence = {"publisher": "Southwest Power Pool", "url": artifact["url"], "artifact_sha256": artifact["sha256"],
                "locator": locator, "source_date": None, "retrieved_at": artifact["retrieved_at"],
                "access_review": "Public SPP workbook; no login.", "facts": ""}
    cell = row["Project Owner Indicated In-Service Date"]
    value = spp.day(cell)
    events = spp.dated_events(pid, native, status, group, value, artifact, evidence, "Owner-indicated in-service date",
                              "owner-in-service", "SPP Q3 2026 project tracking",
                              "Project Owner Indicated In-Service Date")
    owner = spp.clean(row["ProjectOwner"])
    kv = voltages_kv(row["Upgrade Name"]) | {int(v) for v in re.findall(r"\d+", str(row["Voltages (kV)"] or ""))
                                             if int(v) > 0}
    center, candidate = spp.locate(spp.clean(row["Upgrade Name"]), kv, states, facilities, OPERATOR_KEYS.get(owner, []))
    text = row["Project Description/ Comments"]
    raw_keys = ("NTC ID", "PID", "UID", "ProjectOwner", "State(s)", "Project Name", "Upgrade Name", "Project Type",
                "Project Owner Indicated In-Service Date", "Project Status", "Current Cost Estimate", "Voltages (kV)",
                "From Bus Name", "To Bus Name")
    return {
        "_id": pid, "source_id": SOURCE_ID, "native_id": native, "name": spp.clean(row["Upgrade Name"]),
        "major_project": spp.clean(row["Project Name"]) if row["Project Name"] else None,
        "part": spp.clean(row["Upgrade Name"]),
        "description": spp.clean(text)[:500] if text else None, "owner": owner, "other_owners": [],
        "planning_region": "spp", "states": [STATES[s] for s in states], "counties": [],
        "geography_basis": "source_state", "status": status, "status_group": group,
        "in_service": {"raw": spp.clean(cell) if cell is not None else None, "value": value,
                       "precision": "day" if value else "unknown"},
        "center": center, "location_review": "unreviewed" if center else "unlocated",
        "location_candidate": candidate, "project_events": events,
        "evidence": {"page": None, "sheet": row["_sheet"], "row": row["_row"], "source_sha256": artifact["sha256"],
                     "raw": {k: spp.clean(row[k]) if row[k] is not None else None for k in raw_keys}},
    }


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest = load_json(cache / "manifest.json") if (cache / "manifest.json").exists() else {}
    if spp.ZIP not in manifest:
        fetch_into(cache, spp.ZIP, spp.URL, manifest)
        write_json(cache / "manifest.json", manifest)
    for state in STATES:
        if f"osm-{state.lower()}.json" not in manifest:
            fetch_osm(cache, state, manifest)
            write_json(cache / "manifest.json", manifest)


def build(cache: Path) -> dict[Path, object]:
    osm_files = [f"osm-{s.lower()}.json" for s in STATES]
    manifest = verify_cache(cache, [spp.ZIP, *osm_files])
    facilities = {s: with_aliases(osm_extract(json.loads((cache / f"osm-{s.lower()}.json").read_bytes()), s))
                  for s in STATES}
    osm_names = {(f["id"], f["name"]): f["osm_name"] for fs in facilities.values() for f in fs if "osm_name" in f}
    artifact = manifest[spp.ZIP]
    taken = published_uids()
    projects, dispositions = [], []
    for row in spp.read_rows((cache / spp.ZIP).read_bytes()):
        states = spp.row_states(row["State(s)"])
        where = {"source_id": SOURCE_ID, "sheet": row["_sheet"], "row": row["_row"], "uid": str(row["UID"]),
                 "name": spp.clean(row["Upgrade Name"] or "")}
        reason = ("no state listed" if not states
                  else f"outside F47 states ({','.join(states)})" if not set(states) <= STATES.keys()
                  else "UID published by another rollout" if str(row["UID"]) in taken else None)
        if reason:
            dispositions.append(where | {"disposition": "excluded", "reason": reason})
            continue
        record = project(row, artifact, facilities)
        for e in record["location_candidate"]["endpoints"]:  # an alias match still cites the OSM feature's own name
            if (f := e.get("facility")) and (f["id"], f["name"]) in osm_names:
                f["osm_name"] = osm_names[(f["id"], f["name"])]
                record["center"]["evidence"] += f" OSM {f['id']} is named “{f['osm_name']}”; “{f['name']}” is its alias."
        projects.append(record)
        dispositions.append(where | {"disposition": "accepted", "_id": record["_id"],
                                     "location": record["location_candidate"]["tier"] or "unlocated"})
    if len({p["_id"] for p in projects}) != len(projects):
        raise SystemExit("project ID repeated within the workbook")
    projects.sort(key=lambda p: p["_id"])
    source = {
        "_id": SOURCE_ID, "publisher": "Southwest Power Pool",
        "title": "SPP Q3 2026 Quarterly Project Tracking Report, Appendix 1", "authority": "regional_planning_organization",
        "role": "project_plan", "landing_url": spp.LANDING, "download_url": artifact["url"], "publication_date": None,
        "vintage": "2026 Q3", "retrieved_at": artifact["retrieved_at"], "sha256": artifact["sha256"],
        "public_status": "verified_public", "import_status": "imported", "access_policy": "public_document",
        "planning_region": "spp", "states": sorted({s for p in projects for s in p["states"]}),
        "project_count": len(projects),
        "notes": ["F47 SPP South release (C47): SPP upgrades whose listed states are all OK, NM or TX; the same "
                  "artifact and hash as F46's spp-qpt-2026q3. Locations are unreviewed C33 candidates from named OSM "
                  "substations; none is independently confirmed. Source-bounded, not statewide coverage.",
                  f"sha256 is of the appendix zip; rows are read from its member “{spp.MEMBER.split('/')[-1]}”."],
    }
    return {OUT / "projects.json": projects, OUT / "sources.json": [source],
            OUT / "dispositions.json": dispositions,
            OUT / "osm-sources.json": {"publisher": "OpenStreetMap contributors", "rights": "ODbL 1.0; attribution "
                                       "required", "role": "candidate facility geometry only (C33)",
                                       "named_substations": {s: len(f) for s, f in facilities.items()},
                                       "extracts": {name: manifest[name] for name in osm_files}},
            OUT / "summary.json": summary(projects)}


def summary(projects: list[dict]) -> dict:
    located = [p for p in projects if p["center"]]
    by_state = Counter(s for p in projects for s in p["states"])
    located_by_state = Counter(s for p in located for s in p["states"])
    return {"projects": len(projects), "located": len(located), "verified": 0,
            "distinct_points": len({(p["center"]["lat"], p["center"]["lon"]) for p in located}),
            "by_state": {s: {"projects": by_state[f], "located": located_by_state[f]} for s, f in STATES.items()},
            "by_owner": dict(sorted(Counter(p["owner"] for p in projects).items())),
            "by_tier": dict(sorted(Counter(p["location_candidate"]["tier"] for p in located).items())),
            "by_basis": dict(sorted(Counter(p["center"]["basis"] for p in located).items())),
            "by_status": dict(sorted(Counter(p["status_group"] for p in projects).items())),
            "located_by_status": dict(sorted(Counter(p["status_group"] for p in located).items())),
            "unlocated_reasons": dict(sorted(Counter(
                p["location_candidate"]["reason"] or ",".join(sorted({e["status"] for e in
                                                                      p["location_candidate"]["endpoints"]}))
                for p in projects if not p["center"]).items()))}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["fetch", "build"])
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "fetch":
        fetch(args.cache)
        return 0
    from .publish import release

    outputs = build(args.cache)
    outputs |= release(outputs)
    if args.check:
        stale = [str(p) for p, v in outputs.items() if not p.exists() or load_json(p) != v]
        print("stale: " + ", ".join(stale) if stale else "ok")
        return 1 if stale else 0
    for path, value in outputs.items():
        write_json(path, value)
    print(json.dumps(outputs[OUT / "summary.json"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
