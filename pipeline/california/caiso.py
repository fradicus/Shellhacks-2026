"""F43 California: CAISO-approved transmission projects with C33 loose, labeled candidate locations.

The Transmission Development Forum workbook lists every project the CAISO transmission plan approved, its status and
every expected in-service date each forum reported. The newest edition supplies current projects; older editions
only add projects they report as in service that the newer one dropped. Locations are C26/C33 candidates from
named OSM substations in California; none is independently reviewed.

From pipeline/:
  uv run python -m california.caiso fetch --cache /tmp/ca-f43    # three workbooks + OSM CA substations
  uv run python -m california.caiso build --cache /tmp/ca-f43 [--check]
OSM data (c) OpenStreetMap contributors, ODbL 1.0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

from common import REPO_ROOT, load_json, write_json
from greatlakes.match import DUPLICATE_METERS, _meters, candidate_center, facilities_named, facility_key, match_facility
from greatlakes.shared import fetch_into, fetch_osm, osm_extract, verify_cache

OUT = REPO_ROOT / "data" / "california"
TP_URL = "https://www.caiso.com/documents/approved-projects-transmission-planning-process-{}.xlsx"
NU_URL = "https://www.caiso.com/documents/network-upgrades-generator-interconnection-{}.xlsx"
LANDING = "https://www.caiso.com/library/transmission-development-forum"
# Newest approved-projects edition first; older editions contribute only in-service projects the newer ones no
# longer list. The network-upgrade register (newest public edition: July 2025) is its own list.
SOURCES = {
    "caiso-tdf-2026-07": ("jul-2026", TP_URL, "Approved Projects - Transmission Planning Process"),
    "caiso-tdf-2025-07": ("jul-2025", TP_URL, "Approved Projects - Transmission Planning Process"),
    "caiso-tdf-2025-01": ("jan-2025", TP_URL, "Approved Projects - Transmission Planning Process"),
    "caiso-nu-2025-07": ("jul-2025", NU_URL, "Network Upgrades - Generator Interconnection"),
}
NEWEST = "caiso-tdf-2026-07"
# Network-upgrade rows the register itself says are not being built.
NOT_BUILDING = {"removed", "replaced", "not triggered", "none", "not stated"}
OPERATOR_KEYS = {"PG&E": ["PACIFIC GAS"], "SCE": ["SOUTHERN CALIFORNIA EDISON"], "SDG&E": ["SAN DIEGO GAS"]}
STATUS = {
    "in_service": {"in-service", "in service", "completed", "complete", "construction complete", "close-out",
                   "closeout", "operational"},
    "under_construction": {"construction", "execution"},
    "cancelled": {"cancelled"},
    "planned": {"in-flight", "in flight", "engineering", "design", "final engineering", "engineering design",
                "preliminary engineering", "permitting", "permitting, engineering and design"},
    "proposed": {"initiating", "initiation", "planning", "initial development activities", "in development",
                 "plan/analyze"},
}
# California name forms the F40 parser does not read: a site named only before its voltage, a site stated in
# parentheses, and leading line codes or work phrases before the facility names.
EXPLICIT_SITE = re.compile(r"\(([A-Z][\w.'’ ]*?) Substation\)")
LEAD = re.compile(r"^(?:TL\s?\d+[A-Z]?\s+|Reconductor(?: of)?\s+|Upgrade\s+|Series Compensation on\s+|"
                  r"3 Ohm Series Reactor on\s+|Short Circuit Mitigation for\s+|Method of Service for\s+|"
                  r"Equipment Upgrade at CCSF Owned\s+)+")
PAREN_LINE = re.compile(r"\bLine \(([A-Z][\w.' ]*?) [–-] ([A-Z][\w.' ]*?)\)$")  # "…HVDC 500 kV Line (Metcalf – San Jose)"
KV_SITE = re.compile(r"^([A-Z][\w.'’]*(?: [A-Z][\w.'’]*){0,3}) \d+(?:/\d+)*\s?kV\b")
GENERIC = {"NORTH", "SOUTH", "EAST", "WEST"}  # "IV-North of Songs": a direction, never a facility name


def named(project: str, description: str | None = None) -> dict:
    if m := EXPLICIT_SITE.search(project):
        return {"kind": "site", "names": [m[1]], "from": "name", "reason": None}
    if m := PAREN_LINE.search(project):
        return {"kind": "line", "names": [m[1], m[2]], "from": "name", "reason": None}
    text = LEAD.sub("", re.sub(r"\s+Conversion to BAAH\b", "", project))
    got = facilities_named(text, description)
    if got["reason"] == "no_named_facility" and not re.search(r"\blines?\b", text, re.I) and (m := KV_SITE.match(text)):
        got = {"kind": "site", "names": [m[1]], "from": "name", "reason": None}
    names = [None if n and n.upper() in GENERIC else n for n in got["names"]]
    if got["kind"] and not any(names):
        return {"kind": None, "names": [], "from": "name", "reason": "generic_name"}
    return got | {"names": names}


def conflicts(facility: dict, keys: list[str]) -> bool:
    """Another utility's facility with the same name is counter-evidence, whatever else corroborates it."""
    operator = (facility.get("operator") or "").upper()
    return bool(keys and operator and not any(k in operator for k in keys))


def match(name: str | None, facilities: list[dict], keys: list[str], kv: set[int]) -> dict:
    """F40's exact-name match, then C33's loosening: an uncorroborated name held by one California facility."""
    hit = match_facility(name, facilities, keys, kv)
    if hit["status"] == "matched" and conflicts(hit["facility"], keys):
        return {k: v for k, v in hit.items() if k != "facility"} | {"status": "operator_conflict"}
    if hit["status"] != "not_corroborated":
        return hit
    same = [f for f in facilities if facility_key(f["name"]) == hit["norm"]]
    if any(_meters(a, b) > DUPLICATE_METERS for a in same for b in same):
        return hit | {"status": "ambiguous"}
    facility = sorted(same, key=lambda f: (f["id"].startswith("node"), f["id"]))[0]
    if conflicts(facility, keys):
        return hit | {"status": "operator_conflict"}
    return {"status": "matched", "name": name, "norm": hit["norm"], "facility": facility,
            "corroboration": ["unique_in_state"]}


def locate(project: str, description: str | None, facilities: list[dict], keys: list[str]
           ) -> tuple[dict | None, dict]:
    got = named(project, description)
    kv = {round(float(v)) for group in re.findall(r"([\d.]+(?:/[\d.]+)*)\s?kV", project, re.I)
          for v in group.split("/") if v.replace(".", "", 1).isdigit()}
    matches = [match(n, facilities, keys, kv) if n else {"status": "not_a_facility", "name": None}
               for n in got["names"]]
    center = candidate_center(got["kind"], matches) if got["kind"] else None
    fields = ("id", "name", "osm_name", "operator", "voltage", "lat", "lon")
    endpoints = [{k: v for k, v in m.items() if k not in ("facility", "facility_ids")}
                 | ({"facility": {f: m["facility"].get(f) for f in fields}} if m["status"] == "matched" else {})
                 for m in matches]
    found = [m for m in matches if m["status"] == "matched"]
    tier = None
    if center:
        tier = "candidate" if all(m["corroboration"] != ["unique_in_state"] for m in found) else "candidate_unique_name"
    return center, {"rule": "C33", "tier": tier, "independent_review": False, "kind": got["kind"],
                    "reason": got["reason"], "voltages_kv": sorted(kv), "operator_keys": keys,
                    "endpoints": endpoints, "dataset": "OpenStreetMap power=substation, California (ODbL)"}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def clean(value) -> str:
    return value.date().isoformat() if isinstance(value, datetime) else " ".join(str(value).split())


def date_of(value) -> tuple[str | None, str]:
    """(value, precision) for a workbook cell. Pre-2000 days are typos in the source (1933 for 2033): unknown."""
    if isinstance(value, datetime):
        return (value.date().isoformat(), "day") if value.year >= 2000 else (None, "unknown")
    if isinstance(value, int) and 2000 <= value <= 2100:
        return str(value), "year"
    return None, "unknown"


def status_group(status: str) -> str:
    text = status.lower().strip()
    return next((group for group, words in STATUS.items() if text in words), "unknown")


def pick(col: dict[str, int], *names: str) -> int | None:
    return next((col[n] for n in names if n in col), None)


def read_edition(path: Path) -> list[dict]:
    """Every project row of every PTO sheet, with its dated in-service columns in workbook order."""
    rows = []
    for sheet in load_workbook(path, read_only=True, data_only=True).worksheets:
        table = list(sheet.iter_rows(values_only=True))
        header = [clean(h) if h is not None else "" for h in table[0]] if table else []
        col = {h: i for i, h in reversed(list(enumerate(header)))}
        # Approved-project and network-upgrade workbooks name the same columns differently.
        name_i, status_i = pick(col, "Project", "Network Upgrades"), pick(col, "Project Status", "Status")
        id_i, approved_i, text_i = pick(col, "TP Project ID", "ID"), pick(col, "Transmission Plan Approved"), \
            pick(col, "Description")
        if name_i is None or status_i is None:
            continue
        dated = [i for i, h in enumerate(header) if "in-service" in h.lower() and "status" not in h.lower()]
        for number, row in enumerate(table[1:], start=2):
            cells = list(row) + [None] * (len(header) - len(row))
            name, pto = cells[name_i], cells[col["PTO"]]
            if not name or not pto:
                continue
            def text(i: int | None, cells: list = cells) -> str | None:
                return clean(cells[i]) if i is not None and cells[i] is not None else None

            rows.append({
                "sheet": sheet.title, "row": number, "name": clean(name), "pto": clean(pto), "tp_id": text(id_i),
                "approved": text(approved_i), "description": (text(text_i) or "")[:500] or None,
                "status": text(status_i) or "Not stated", "notes": (text(col.get("Notes")) or "")[:500] or None,
                "dates": [(header[i], cells[i]) for i in dated],
            })
    return rows


def project(row: dict, source_id: str, artifact: dict, facilities: list[dict]) -> dict:
    native = row["tp_id"] if row["tp_id"] and row["tp_id"] != "#N/A" else slug(row["name"])[:80]
    pid = f"{source_id}:{native}"
    locator = f"sheet {row['sheet']}, row {row['row']}"
    evidence = {"publisher": "California ISO", "url": artifact["url"], "artifact_sha256": artifact["sha256"],
                "locator": locator, "source_date": None, "retrieved_at": artifact["retrieved_at"],
                "access_review": "Public CAISO workbook; no login.",
                "facts": ""}
    group = status_group(row["status"])
    # One event per revision: a forum repeating the previous expected date adds no new fact.
    events, last = [], None
    for header, cell in row["dates"]:
        value, precision = date_of(cell)
        if value is None:
            continue
        if last and last["date"] == value:
            last["description"] = last["description"].split(" Unchanged")[0] + f" Unchanged through “{header}”."
            continue
        last = {"id": f"{pid}:{slug(header)}", "type": "planned_milestone", "date": value,
                "precision": precision, "native_project_link": native,
                "description": f"Expected in-service {value}, first reported in “{header}”.",
                "evidence": [evidence | {"facts": f"{header} = {value}"}]}
        events.append(last)
    current_header, current = row["dates"][-1] if row["dates"] else ("", None)
    value, precision = date_of(current)
    if group == "in_service":
        # The current column still holding a date on or before retrieval is the date the in-service report lists.
        reported = value if value and value <= artifact["retrieved_at"][:10] else None
        if reported:
            events = [e for e in events if e["id"] != f"{pid}:{slug(current_header)}"]
        events.append({
            "id": f"{pid}:status-in-service", "type": "in_service", "date": reported,
            "precision": precision if reported else "unknown", "native_project_link": native,
            "description": (f"Project status “{row['status']}”; “{current_header}” lists {reported}." if reported else
                            f"Project status “{row['status']}”; the workbook gives no in-service date for it."),
            "evidence": [evidence | {"facts": f"Project Status = {row['status']}"}]})
    keys = OPERATOR_KEYS.get(row["pto"], [])
    center, candidate = locate(row["name"], row["description"], facilities, keys)
    return {
        "_id": pid, "source_id": source_id, "native_id": native, "name": row["name"], "description": row["description"],
        "owner": row["pto"], "other_owners": [], "planning_region": "caiso",
        "states": ["06"] if center else [], "counties": [],
        "geography_basis": "candidate_facility_state" if center else None,
        "status": row["status"], "status_group": group,
        "in_service": {"raw": clean(current) if current is not None else None, "value": value, "precision": precision},
        "center": center, "location_review": "unreviewed" if center else "unlocated",
        "location_candidate": candidate, "project_events": events,
        "evidence": {"page": None, "sheet": row["sheet"], "row": row["row"], "source_sha256": artifact["sha256"],
                     "raw": {"ID": row["tp_id"], "Project": row["name"], "PTO": row["pto"],
                             "Transmission Plan Approved": row["approved"], "Project Status": row["status"],
                             current_header or "Current In-Service": clean(current) if current is not None else None,
                             "Notes": row["notes"]}},
    }


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest = load_json(cache / "manifest.json") if (cache / "manifest.json").exists() else {}
    for source_id, (edition, url, _) in SOURCES.items():
        if f"{source_id}.xlsx" not in manifest:
            fetch_into(cache, f"{source_id}.xlsx", url.format(edition), manifest)
            write_json(cache / "manifest.json", manifest)
    if "osm-ca.json" not in manifest:
        fetch_osm(cache, "CA", manifest)
        write_json(cache / "manifest.json", manifest)


def build(cache: Path) -> dict[Path, object]:
    manifest = verify_cache(cache, [f"{s}.xlsx" for s in SOURCES] + ["osm-ca.json"])
    # OSM names switching stations "X Switching Station"; the matcher already drops a bare "Station".
    facilities = [f | {"name": re.sub(r" Switching Station$", "", f["name"]), "osm_name": f["name"]}
                  for f in osm_extract(json.loads((cache / "osm-ca.json").read_bytes()), "CA")]
    projects, dispositions, sources, seen, seen_names = [], [], [], set(), set()
    for source_id, (edition, url, title) in SOURCES.items():
        artifact = manifest[f"{source_id}.xlsx"]
        older = url == TP_URL and source_id != NEWEST
        kept = []
        for row in read_edition(cache / f"{source_id}.xlsx"):
            where = {"source_id": source_id, "sheet": row["sheet"], "row": row["row"], "name": row["name"]}
            key = slug(row["name"])
            if url == NU_URL and row["status"].lower() in NOT_BUILDING:
                dispositions.append(where | {"disposition": "excluded", "reason": f"status {row['status']}"})
                continue
            if older and (key in seen_names or status_group(row["status"]) != "in_service"):
                dispositions.append(where | {"disposition": "excluded", "reason": "listed in a newer edition"
                                             if key in seen_names else "not in service; the newest edition governs"})
                continue
            record = project(row, source_id, artifact, facilities)
            if record["_id"] in seen:
                # A few TP IDs cover several rows; each row is its own named project.
                record = project(row | {"tp_id": f"{row['tp_id']}:{key[:60]}"}, source_id, artifact, facilities)
            if record["_id"] in seen:
                dispositions.append(where | {"disposition": "duplicate", "reason": "same project listed twice"})
                continue
            seen.add(record["_id"])
            seen_names.add(key)
            kept.append(record)
            dispositions.append(where | {"disposition": "accepted", "_id": record["_id"],
                                         "location": record["location_candidate"]["tier"] or "unlocated"})
        projects += kept
        sources.append({
            "_id": source_id, "publisher": "California ISO",
            "title": f"CAISO {title} ({edition.replace('-', ' ').title()} Transmission Development Forum)",
            "authority": "regional_planning_organization", "role": "project_plan", "landing_url": LANDING,
            "download_url": artifact["url"], "publication_date": None, "vintage": edition,
            "retrieved_at": artifact["retrieved_at"], "sha256": artifact["sha256"], "public_status": "verified_public",
            "import_status": "imported", "access_policy": "public_document", "planning_region": "caiso",
            "states": ["06"] if any(p["center"] for p in kept) else [], "project_count": len(kept),
            "notes": ["F43 California release (C35). Locations are unreviewed C33 candidates from named OSM "
                      "substations; none is independently confirmed. Source-bounded, not statewide coverage."]
            + (["Only in-service projects the newer edition no longer lists are imported."] if older else [])
            + (["Removed, replaced and not-triggered upgrades are excluded."] if url == NU_URL else []),
        })
    projects.sort(key=lambda p: p["_id"])
    osm = manifest["osm-ca.json"]
    return {OUT / "projects.json": projects, OUT / "sources.json": sources, OUT / "dispositions.json": dispositions,
            OUT / "osm-sources.json": {"publisher": "OpenStreetMap contributors", "rights": "ODbL 1.0; attribution "
                                       "required", "role": "candidate facility geometry only (C33)",
                                       "named_substations": len(facilities), **osm},
            OUT / "summary.json": summary(projects)}


def summary(projects: list[dict]) -> dict:
    located = [p for p in projects if p["center"]]
    return {"projects": len(projects), "located": len(located), "verified": 0,
            "distinct_points": len({(p["center"]["lat"], p["center"]["lon"]) for p in located}),
            "by_tier": dict(Counter(p["location_candidate"]["tier"] for p in located)),
            "by_basis": dict(Counter(p["center"]["basis"] for p in located)),
            "located_by_status": dict(sorted(Counter(p["status_group"] for p in located).items())),
            "by_status": dict(sorted(Counter(p["status_group"] for p in projects).items())),
            "located_not_in_service": sum(p["status_group"] != "in_service" for p in located),
            "located_with_events": sum(bool(p["project_events"]) for p in located),
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


def sha(value: object) -> str:
    """Byte-identical to common.write_json, so the release can pin committed file hashes."""
    return hashlib.sha256((json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()).hexdigest()


if __name__ == "__main__":
    sys.exit(main())
