"""F50 Interior West (WY, NV, UT, ID, MT): TPPL Wyoming rows and 2026 WECC progress reports, C33/C38 candidates (C50).

Part 1 reads the TPPL workbook F45 pins (same artifact and hash) and keeps the Wyoming rows F45 excluded by scope.
Origin and Termination name the endpoints, parsed and matched exactly as F45 does; a substation row whose endpoints
say only "Cheyenne, WY" is placed from its ProjectName with F46's name parser. Part 2 adds page-verified rows from
the 2026 WECC Annual Progress Reports (interiorwest.apr). No point is independently reviewed.

From pipeline/:
  uv run python -m interiorwest.build fetch --cache /tmp/interiorwest-f50
  uv run python -m interiorwest.build build --cache /tmp/interiorwest-f50 [--check]
OSM data (c) OpenStreetMap contributors, ODbL 1.0.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from california.caiso import match
from common import REPO_ROOT, load_json, write_json
from greatlakes.match import candidate_center, facility_key, voltages_kv
from greatlakes.shared import fetch_into, fetch_osm, osm_extract, verify_cache
from midwest.build import named
from southwest import build as sw

from . import apr

OUT = REPO_ROOT / "data" / "interiorwest"
STATES = {"WY": "56", "NV": "32", "UT": "49", "ID": "16", "MT": "30"}
TPPL_STATES = {"Wyoming": "WY"}
TPPL = "westconnect-tppl-2026-02-wy"
OPERATOR_KEYS = sw.OPERATOR_KEYS | {"Cheyenne Light Fuel and Power": ["CHEYENNE LIGHT", "BLACK HILLS"]}


def endpoints(row: dict) -> tuple[str | None, list[str | None], str]:
    """(kind, names, from): F45's Origin/Termination reading, then the ProjectName of a site row that names none."""
    names = [sw.endpoint(row["Origin"]), sw.endpoint(row["Termination"])]
    if any(names):
        same = names[0] and names[1] and facility_key(names[0]) == facility_key(names[1])
        if same or None in names:
            return "site", [n for n in names if n][:1], "origin_termination"
        return "line", names, "origin_termination"
    got = named(" ".join(str(row["ProjectName"]).split()))
    if got["kind"] == "site" and all(got["names"]):
        return "site", got["names"], "project_name"
    return None, [], "origin_termination"


def locate(row: dict, usps: str, facilities: list[dict]) -> tuple[dict | None, dict]:
    kind, names, source = endpoints(row)
    keys = OPERATOR_KEYS.get(row["Sponsor"], [])
    kv = voltages_kv(row["Voltage"], str(row["ProjectName"] or ""), str(row["Origin"] or ""),
                     str(row["Termination"] or ""))
    matches = [match(n, facilities, keys, kv) for n in names]
    center = candidate_center(kind, matches) if kind else None
    found = [m for m in matches if m["status"] == "matched"]
    tier = None
    if center:
        tier = "candidate" if all(m["corroboration"] != ["unique_in_state"] for m in found) else "candidate_unique_name"
        center["evidence"] = center["evidence"].replace("corroborated by unique_in_state",
                                                        "the only facility with that name in the state (C33 name-only)")
    fields = ("id", "name", "operator", "voltage", "lat", "lon")
    ends = [{k: v for k, v in m.items() if k not in ("facility", "facility_ids")}
            | ({"facility": {f: m["facility"].get(f) for f in fields}} if m["status"] == "matched" else {})
            for m in matches]
    return center, {"rule": "C33", "tier": tier, "independent_review": False, "kind": kind,
                    "reason": None if kind else "no_named_endpoint", "names_from": source, "voltages_kv": sorted(kv),
                    "operator_keys": keys, "endpoints": ends, "dataset": f"OpenStreetMap power=substation, {usps} (ODbL)"}


def tppl_project(row: dict, artifact: dict, facilities: list[dict]) -> dict:
    """F45's TPPL record (C42) under this rollout's source ID and state."""
    native = str(row["projectid"])
    pid = f"{TPPL}:{native}"
    usps = TPPL_STATES[row["StateTraversed"]]
    status = row["Development"] or "Not stated"
    group = sw.STATUS.get(status.lower(), "unknown")
    isd = sw.in_service(row["InService"])
    center, candidate = locate(row, usps, facilities)
    evidence = {"publisher": "WestConnect", "url": artifact["url"], "artifact_sha256": artifact["sha256"],
                "locator": f"sheet All Projects, row {row['_row']} (projectid {native})", "source_date": None,
                "retrieved_at": artifact["retrieved_at"],
                "access_review": "Public WestConnect TPPL workbook linked from the TPPL page; no login.", "facts": ""}
    events = []
    if group == "in_service":
        events.append({"id": f"{pid}:in-service", "type": "in_service", "date": isd["value"],
                       "precision": isd["precision"], "native_project_link": native,
                       "description": f"Development “{status}”; InService "
                                      + (f"{isd['value']}." if isd["value"] else "gives no year."),
                       "evidence": [evidence | {"facts": f"Development = {status}; InService = {isd['raw']}"}]})
    elif isd["value"]:
        events.append({"id": f"{pid}:planned-in-service", "type": "planned_milestone", "date": isd["value"],
                       "precision": "year", "native_project_link": native,
                       "description": f"Expected in service {isd['value']} (development status “{status}”).",
                       "evidence": [evidence | {"facts": f"InService = {isd['value']}"}]})
    modified = row.get("modifieddate")
    raw = {k: row.get(k) for k in ("projectid", "Sponsor", "ProjectName", "FacilityType", "Voltage", "Development",
                                   "Origin", "Termination", "InService", "SubRegionalID_Name", "StateTraversed")}
    return {
        "_id": pid, "source_id": TPPL, "native_id": native, "name": " ".join(str(row["ProjectName"]).split()),
        "description": (" ".join(str(row["Description"] or "").split())[:500] or None),
        "owner": row["Sponsor"], "other_owners": [], "planning_region": "westconnect", "states": [STATES[usps]],
        "counties": [], "geography_basis": "source_state", "status": status, "status_group": group,
        "in_service": isd, "center": center, "location_review": "unreviewed" if center else "unlocated",
        "location_candidate": candidate, "project_events": events,
        "evidence": {"page": None, "sheet": "All Projects", "row": row["_row"], "source_sha256": artifact["sha256"],
                     "raw": raw | {"modifieddate": modified.date().isoformat() if modified else None}},
    }


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest = load_json(cache / "manifest.json") if (cache / "manifest.json").exists() else {}
    if "tppl.xlsx" not in manifest:
        fetch_into(cache, "tppl.xlsx", sw.TPPL_URL, manifest)
        write_json(cache / "manifest.json", manifest)
    for name, url, _, _ in apr.REPORTS.values():
        if name not in manifest:
            fetch_into(cache, name, url, manifest)
            write_json(cache / "manifest.json", manifest)
    for usps in STATES:
        if f"osm-{usps.lower()}.json" not in manifest:
            fetch_osm(cache, usps, manifest)
            write_json(cache / "manifest.json", manifest)


def build(cache: Path) -> dict[Path, object]:
    osm_files = [f"osm-{s.lower()}.json" for s in STATES]
    manifest = verify_cache(cache, ["tppl.xlsx", *(r[0] for r in apr.REPORTS.values()), *osm_files])
    facilities = {s: osm_extract(json.loads((cache / f"osm-{s.lower()}.json").read_bytes()), s) for s in STATES}
    rows, stamp = sw.read_tppl(cache / "tppl.xlsx")
    projects, dispositions = [], []
    for row in rows:
        where = {"source_id": TPPL, "locator": f"All Projects row {row['_row']}", "name": row["ProjectName"]}
        state = row["StateTraversed"]
        if state not in TPPL_STATES:
            reason = f"state {state}; F45 or outside C50" if state in {*sw.TPPL_STATES, None} else f"state {state}"
            dispositions.append(where | {"disposition": "excluded", "reason": reason})
            continue
        project = tppl_project(row, manifest["tppl.xlsx"], facilities[TPPL_STATES[state]])
        projects.append(project)
        dispositions.append(where | {"disposition": "accepted", "_id": project["_id"],
                                     "location": project["location_candidate"]["tier"] or "unlocated"})
    reported, more = apr.projects(cache, manifest, facilities, STATES)
    projects += reported
    dispositions += more
    if len({p["_id"] for p in projects}) != len(projects):
        raise SystemExit("project ID repeated within a source")
    projects.sort(key=lambda p: p["_id"])
    tppl = manifest["tppl.xlsx"]
    sources = [
        {"_id": TPPL, "publisher": "WestConnect", "title": "WestConnect Transmission Plan Project List (TPPL) workbook",
         "authority": "regional_planning_organization", "role": "project_plan", "landing_url": sw.TPPL_LANDING,
         "download_url": tppl["url"], "publication_date": None, "vintage": None,
         "retrieved_at": tppl["retrieved_at"], "sha256": tppl["sha256"], "public_status": "verified_public",
         "import_status": "imported", "access_policy": "public_document", "planning_region": "westconnect",
         "states": sorted({s for p in projects if p["source_id"] == TPPL for s in p["states"]}),
         "project_count": sum(p["source_id"] == TPPL for p in projects),
         "notes": ["F50 Interior West release (C50): the workbook's Wyoming rows; the same artifact and hash as F45's "
                   "westconnect-tppl-2026-02. Candidate points are unreviewed C33 exact-name OSM matches with C38's "
                   "operator guard; none is independently confirmed. Source-bounded.",
                   f"The workbook's Control sheet TimeStamp reads {stamp}; its meaning (save or send) is not stated."]},
    ]
    for name, url, source_id, publisher in apr.REPORTS.values():
        artifact = manifest[name]
        sources.append({
            "_id": source_id, "publisher": publisher, "title": f"{publisher} 2026 WECC Annual Progress Report",
            "authority": "utility", "role": "project_plan", "landing_url": url, "download_url": artifact["url"],
            "publication_date": None, "vintage": "2026", "retrieved_at": artifact["retrieved_at"],
            "sha256": artifact["sha256"], "public_status": "verified_public", "import_status": "imported",
            "access_policy": "public_document", "planning_region": "WECC",
            "states": sorted({s for p in projects if p["source_id"] == source_id for s in p["states"]}),
            "project_count": sum(p["source_id"] == source_id for p in projects),
            "notes": ["F50 Interior West release (C50 part 2): transmission rows transcribed with a page and verbatim "
                      "quote the build re-finds in the PDF; rows another rollout publishes are excluded.",
                      "Candidate points are unreviewed C33 exact-name OSM matches with C38's operator guard; a row "
                      "whose text names no state is placed only by a corroborated facility in the owner's territory."]})
    return {OUT / "projects.json": projects, OUT / "sources.json": sources, OUT / "dispositions.json": dispositions,
            OUT / "osm-sources.json": {"publisher": "OpenStreetMap contributors", "rights": "ODbL 1.0; attribution "
                                       "required", "role": "candidate facility geometry only (C33)",
                                       "named_substations": {s: len(f) for s, f in facilities.items()},
                                       "extracts": {name: manifest[name] for name in osm_files}},
            OUT / "summary.json": summary(projects)}


def summary(projects: list[dict]) -> dict:
    located = [p for p in projects if p["center"]]
    return {"projects": len(projects), "located": len(located), "verified": 0,
            "distinct_points": len({(p["center"]["lat"], p["center"]["lon"]) for p in located}),
            "by_source": dict(sorted(Counter(p["source_id"] for p in projects).items())),
            "by_state": dict(sorted(Counter(s for p in projects for s in p["states"]).items())),
            "located_by_state": dict(sorted(Counter(s for p in located for s in p["states"]).items())),
            "by_tier": dict(sorted(Counter(p["location_candidate"]["tier"] for p in located).items())),
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
