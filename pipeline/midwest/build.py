"""F46 Midwest (IA, MO, KS, NE, ND, SD): SPP and MISO projects with C33/C38 loose, labeled candidate locations.

SPP's Quarterly Project Tracking workbook lists every upgrade SPP has approved, its owner, status and the owner's
expected in-service date; each upgrade is one record. MISO's projects-under-evaluation workbook (pinned by F40, which
kept only Great Lakes rows) adds the rows listing only these states. Locations are candidates from named OSM
substations in the row's own states; none is independently reviewed (C43).

From pipeline/:
  uv run python -m midwest.build fetch --cache /tmp/midwest-f46    # SPP zip, MISO workbook, OSM substations (6 states)
  uv run python -m midwest.build build --cache /tmp/midwest-f46 [--check]
OSM data (c) OpenStreetMap contributors, ODbL 1.0.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import warnings
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from openpyxl import load_workbook

from california.caiso import match
from common import REPO_ROOT, load_json, write_json
from greatlakes import miso
from greatlakes.match import candidate_center, facilities_named, voltages_kv
from greatlakes.shared import fetch_into, fetch_osm, osm_extract, verify_cache
from southeast import misospp  # F39's MTEP25 Appendix A workbook helpers, by import

OUT = REPO_ROOT / "data" / "midwest"
STATES = {"IA": "19", "MO": "29", "KS": "20", "NE": "31", "ND": "38", "SD": "46"}
SOURCE_ID = "spp-qpt-2026q3"
ZIP = "spp-qpt-2026q3.zip"
URL = "https://www.spp.org/Documents/77416/" + quote("3Q 2026 Quarterly Project Tracking Report Appendix 1&2.zip")
LANDING = "https://www.spp.org/engineering/project-tracking-ntcs/"
MEMBER = "3Q 2026 Quarterly Project Tracking Report Appendix 1&2/Q3 2026 Quarterly Project Tracking Appendix 1.xlsm"
HEADER_ROW = 2  # row 1 is the report title
STATUS = {
    "planned": {"on schedule < 4", "on schedule > 4", "delay - mitigation", "delay - mitigation window"},
    "proposed": {"ntc - commitment window", "ntc-c project estimate window", "re-evaluation", "identified"},
    "in_service": {"complete", "in service", "closed out"},
    "cancelled": {"withdrawn"},
}
# OSM operator-name fragments for the SPP owner codes in these states. Owners without an entry get no operator
# corroboration and no operator guard.
OPERATOR_KEYS = {
    "BEPC": ["BASIN ELECTRIC"], "EREC": ["EAST RIVER"], "NPPD": ["NEBRASKA PUBLIC POWER", "NPPD"],
    "EKC": ["EVERGY", "WESTAR"], "EM": ["EVERGY", "KANSAS CITY POWER", "KCP&L"],
    "EMW": ["EVERGY", "KCP&L", "GREATER MISSOURI"], "WAPA": ["WESTERN AREA", "WAPA"], "EDE": ["EMPIRE", "LIBERTY"],
    "OPPD": ["OMAHA PUBLIC POWER", "OPPD"], "MIDW": ["MIDWEST ENERGY"], "MRES": ["MISSOURI RIVER"],
    "SEPC": ["SUNFLOWER"], "LES": ["LINCOLN ELECTRIC"], "TSGT": ["TRI-STATE"], "OGE": ["OKLAHOMA GAS", "OG&E"],
    "SPS": ["SOUTHWESTERN PUBLIC", "XCEL"], "CBPC": ["CORN BELT"], "ITCGP": ["ITC"], "NIPCO": ["NORTHWEST IOWA POWER"],
    "NEET": ["NEXTERA"],
}
MISO_SOURCE_ID = "miso-mtep26-eval-midwest"
# FIX-F46: MISO's MTEP25 Appendix A workbook (approved App. A and App. B rows); F39 pins the same file for its states.
MISO_A_SOURCE_ID = "miso-mtep25-appendix-a-midwest"
MISO_A_FILE = "miso-mtep25-appendix-a.xlsx"
MISO_A_URL = misospp.MISO_FILES[misospp.MISO_A][0]
MISO_A_SHEETS = ("MTEP25 Data Pull - App. A", "MTEP25 Data Pull - App. B")
# MTEP IDs other rollouts already publish: F40's MISO list and F39's MISO/SPP batch.
MISO_PUBLISHED = ("data/greatlakes/miso/projects.json", "data/southeast/dense/misospp/projects.json")
# MISO submitters F40's key list does not name, checked before it. OSM tags Montana-Dakota both ways.
MISO_KEYS = [("MIDAMERICAN", ["MIDAMERICAN"]), ("MONTANA-DAKOTA", ["MONTANA-DAKOTA", "MDU"]),
             ("CITIZENS ELECTRIC", ["CITIZENS ELECTRIC"]), ("CEDAR FALLS", ["CEDAR FALLS"])]
# SPP name forms: "Craig 161 kV Ckt 2 Terminal Upgrade toward Midway 161 kV" is work at Craig; "toward" names the
# far end. "Wolf Creek 345kV Terminal Equipment", "Sweetwater 345kV GEN-2016-074 Interconnection" are sites.
TOWARD = re.compile(r"\s+toward\s+.*$", re.I)
SITE = re.compile(r"^(?P<name>.+?)\s*\d+(?:/\d+)*\s?kV?\b(?P<tail>.*)$", re.I)
# MISO forms: "Black Hawk: Install 345 kV 100 MVAR Capacitor" names the site before the colon.
COLON_SITE = re.compile(r"^(?P<name>[A-Z][\w .'’]*?):\s+(?P<tail>.*)$")
SITE_WORK = re.compile(r"\b(Terminal|Interconnection|Substation|Sub|Transformer|Relay|Bus Tie|Shunt|Equipment|"
                       r"Reactors?|Capacitor)\b", re.I)
# Bus numbers, generator queue positions and border points are not facilities.
NOT_A_NAME = re.compile(r"^(?:S\s?\d+|Sub \d+|GEN-\d{4}-\d+|DISIS-\d{4}-\d+)$|\bBorder\b", re.I)
QUEUE = re.compile(r"^(?:GEN|DISIS)-\d{4}-\d+$", re.I)


def clean(value) -> str:
    return value.date().isoformat() if isinstance(value, datetime) else " ".join(str(value).split())


def status_group(status: str) -> str:
    text = " ".join(status.lower().split())
    return next((group for group, words in STATUS.items() if text in words), "unknown")


def row_states(cell) -> list[str]:
    return sorted({s.strip().upper() for s in re.split(r"[,/]", str(cell or "")) if s.strip()})


def named(upgrade: str, description: str | None = None) -> dict:
    """Facilities an SPP upgrade name states: F40's parser after SPP's own forms, then non-facility names dropped."""
    text = re.sub(r"(?<=[A-Za-z])(?=\d+\s?kV)", " ", upgrade)  # "Spring Creek345 kV"
    text = re.sub(r"\s+-\s+(?=\d+\s?kV)", " ", TOWARD.sub("", text))  # "Leland Olds - Finstad - 345 kV New Line"
    text = re.sub(r"^(?:Replace|Repair|Upgrade|Apply|Expand)\s+", "", text)  # MISO: "Replace Labadie 345 kV …"
    text = re.sub(r"(\d+)-(\d+)(?=\s?kV)", r"\1/\2", text)  # "Plymouth 161-69 kV Transformer"
    text = re.sub(r"\s+N\d{1,3}(?=\s)", "", text)  # ITC Midwest line numbers: "Leland to Forest City N43 69 kV"
    text = re.sub(r"(?<=[A-Za-z])-\d(?=\s)", "", text)  # circuit numbers: "Baumgartner-Watson-1 138 kV"
    got = facilities_named(text, description)
    if got["reason"] == "no_named_facility" and (m := COLON_SITE.match(text)) and SITE_WORK.search(m["tail"]):
        got = {"kind": "site", "names": [m["name"].strip()], "from": "name", "reason": None}
    elif got["reason"] == "no_named_facility" and (m := SITE.match(text)) and SITE_WORK.search(m["tail"]):
        got = {"kind": "site", "names": [m["name"].strip()], "from": "name", "reason": None}
    names = [None if n is None or NOT_A_NAME.search(n.strip()) else n for n in got["names"]]
    if got["kind"] and not any(names):
        return {"kind": None, "names": [], "from": "name", "reason": "not_a_facility"}
    if got["kind"] == "line" and any(n and QUEUE.match(n.strip()) for n in got["names"]):
        # "Holt County 345kV - GEN-2015-023 Addition": a generator's work at one site, not a line to a queue number.
        return got | {"kind": "site", "names": [n for n in names if n]}
    return got | {"names": names}


def locate(name: str, kv: set[int], states: list[str], facilities: dict[str, list[dict]], keys: list[str],
           description: str | None = None) -> tuple[dict | None, dict]:
    return place(named(name, description), kv, states, facilities, keys)


def place(got: dict, kv: set[int], states: list[str], facilities: dict[str, list[dict]], keys: list[str]
          ) -> tuple[dict | None, dict]:
    """C33 candidate for facility names already parsed ({'kind', 'names', 'reason'}) in the row's own states."""
    pool = [f for s in states for f in facilities.get(s, [])]
    matches = [match(n, pool, keys, kv) if n else {"status": "not_a_facility", "name": None} for n in got["names"]]
    center = candidate_center(got["kind"], matches) if got["kind"] else None
    fields = ("id", "name", "operator", "voltage", "state", "lat", "lon")
    endpoints = [{k: v for k, v in m.items() if k not in ("facility", "facility_ids")}
                 | ({"facility": {f: m["facility"].get(f) for f in fields}} if m["status"] == "matched" else {})
                 for m in matches]
    found = [m for m in matches if m["status"] == "matched"]
    tier = None
    if center:
        tier = "candidate" if all(m["corroboration"] != ["unique_in_state"] for m in found) else "candidate_unique_name"
    return center, {"rule": "C33", "tier": tier, "independent_review": False, "kind": got["kind"],
                    "reason": got["reason"], "voltages_kv": sorted(kv), "operator_keys": keys,
                    "endpoints": endpoints,
                    "dataset": f"OpenStreetMap power=substation, {'/'.join(states)} (ODbL)"}


def read_rows(zip_bytes: bytes) -> list[dict]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        book = load_workbook(io.BytesIO(archive.read(MEMBER)), read_only=True, data_only=True)
    sheet = book.worksheets[0]
    table = list(sheet.iter_rows(values_only=True))
    header = [clean(h) if h is not None else "" for h in table[HEADER_ROW - 1]]
    rows = []
    for number, row in enumerate(table[HEADER_ROW:], start=HEADER_ROW + 1):
        cells = dict(zip(header, list(row) + [None] * (len(header) - len(row)), strict=True))
        if cells["UID"] is not None:
            rows.append(cells | {"_sheet": sheet.title, "_row": number})
    return rows


def day(cell) -> str | None:
    return cell.date().isoformat() if isinstance(cell, datetime) and cell.year >= 2000 else None


def dated_events(pid: str, native: str, status: str, group: str, value: str | None, artifact: dict, evidence: dict,
                 label: str, slug: str, cited: str, column: str) -> list[dict]:
    """An in-service status is dated only by a date on or before retrieval; any other stated date is a milestone."""
    if group == "in_service":
        reported = value if value and value <= artifact["retrieved_at"][:10] else None
        return [{"id": f"{pid}:status-in-service", "type": "in_service", "date": reported,
                 "precision": "day" if reported else "unknown", "native_project_link": native,
                 "description": (f"Project status “{status}”; {label[0].lower() + label[1:]} {reported}."
                                 if reported else f"Project status “{status}”; the workbook gives no "
                                 "in-service date on or before retrieval."),
                 "evidence": [evidence | {"facts": f"Project Status = {status}"}]}]
    if not value:
        return []
    return [{"id": f"{pid}:{slug}", "type": "planned_milestone", "date": value, "precision": "day",
             "native_project_link": native, "description": f"{label} {value} ({cited}).",
             "evidence": [evidence | {"facts": f"{column} = {value}"}]}]


def project(row: dict, artifact: dict, facilities: dict[str, list[dict]]) -> dict:
    native = str(row["UID"])
    pid = f"{SOURCE_ID}:{native}"
    status = clean(row["Project Status"] or "Not stated")
    group = status_group(status)
    states = row_states(row["State(s)"])
    locator = f"{MEMBER.split('/')[-1]}, sheet {row['_sheet']}, row {row['_row']}"
    evidence = {"publisher": "Southwest Power Pool", "url": artifact["url"], "artifact_sha256": artifact["sha256"],
                "locator": locator, "source_date": None, "retrieved_at": artifact["retrieved_at"],
                "access_review": "Public SPP workbook; no login.", "facts": ""}
    cell = row["Project Owner Indicated In-Service Date"]
    value = day(cell)
    precision = "day" if value else "unknown"
    events = dated_events(pid, native, status, group, value, artifact, evidence, "Owner-indicated in-service date",
                          "owner-in-service", "SPP Q3 2026 project tracking",
                          "Project Owner Indicated In-Service Date")
    owner = clean(row["ProjectOwner"])
    kv = voltages_kv(row["Upgrade Name"]) | {int(v) for v in re.findall(r"\d+", str(row["Voltages (kV)"] or "")) if int(v) > 0}
    center, candidate = locate(clean(row["Upgrade Name"]), kv, states, facilities, OPERATOR_KEYS.get(owner, []))
    text = row["Project Description/ Comments"]
    raw_keys = ("NTC ID", "PID", "UID", "ProjectOwner", "State(s)", "Project Name", "Upgrade Name", "Project Type",
                "Project Owner Indicated In-Service Date", "Project Status", "Current Cost Estimate", "Voltages (kV)",
                "From Bus Name", "To Bus Name")
    return {
        "_id": pid, "source_id": SOURCE_ID, "native_id": native, "name": clean(row["Upgrade Name"]),
        "major_project": clean(row["Project Name"]) if row["Project Name"] else None, "part": clean(row["Upgrade Name"]),
        "description": clean(text)[:500] if text else None, "owner": owner, "other_owners": [], "planning_region": "spp",
        "states": [STATES[s] for s in states], "counties": [], "geography_basis": "source_state",
        "status": status, "status_group": group,
        "in_service": {"raw": clean(cell) if cell is not None else None, "value": value, "precision": precision},
        "center": center, "location_review": "unreviewed" if center else "unlocated",
        "location_candidate": candidate, "project_events": events,
        "evidence": {"page": None, "sheet": row["_sheet"], "row": row["_row"], "source_sha256": artifact["sha256"],
                     "raw": {k: clean(row[k]) if row[k] is not None else None for k in raw_keys}},
    }


def miso_keys(submitter: str) -> list[str]:
    up = submitter.upper()
    return next((keys for fragment, keys in MISO_KEYS if fragment in up), None) or miso.operator_keys(submitter)


def miso_rows(path: Path) -> list[dict]:
    """Every data row of F40's pinned MISO workbook, with its sheet row number."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # openpyxl: unsupported data-validation extension
        book = load_workbook(path, read_only=True)
        table = list(book[miso.SHEET].iter_rows(values_only=True))  # read-only sheets parse (and warn) here
    header = [str(h) for h in table[1]]
    return [dict(zip(header, values, strict=True)) | {"_row": number}
            for number, values in enumerate(table[2:], start=3)]


def miso_states(cell) -> list[str]:
    return sorted({s.strip() for s in str(cell or "").split(";") if s.strip()})


def miso_project(row: dict, artifact: dict, facilities: dict[str, list[dict]]) -> dict:
    native = str(row["MTEP Project ID"])
    pid = f"{MISO_SOURCE_ID}:{native}"
    status = clean(row["Planning Status"] or "Not stated")
    group = miso.STATUS.get(status[:2], "unknown")
    states = miso_states(row["State(s)"])
    evidence = {"publisher": "Midcontinent Independent System Operator (MISO)", "url": artifact["url"],
                "artifact_sha256": artifact["sha256"], "locator": f"{miso.FILE}#{miso.SHEET}!row-{row['_row']}",
                "source_date": None, "retrieved_at": artifact["retrieved_at"],
                "access_review": "Public MISO CDN workbook; no login.", "facts": ""}
    value = day(row["Expected ISD"])
    events = dated_events(pid, native, status, group, value, artifact, evidence, "Expected in-service date",
                          "expected-isd", "MISO MTEP26 projects under evaluation", "Expected ISD")
    name, text = clean(row["Project Name"]), row["Project Description"]
    kv = {int(v) for v in (row["Max kV"], row["Min kV"]) if isinstance(v, int | float) and v > 0} | voltages_kv(name, text)
    owner = clean(row["Submitting TO"])
    center, candidate = locate(name, kv, states, facilities, miso_keys(owner), clean(text) if text else None)
    raw_keys = ("Target MTEP Cycle", "Target Appendix", "Submitting TO", "Planning Region", "State(s)", "MTEP Project ID",
                "Project Name", "Project Type", "Expected ISD", "Current Cost", "Planning Status", "Max kV", "Min kV")
    return {
        "_id": pid, "source_id": MISO_SOURCE_ID, "native_id": native, "name": name,
        "description": clean(text)[:500] if text else None, "owner": owner, "other_owners": [], "planning_region": "miso",
        "states": [STATES[s] for s in states], "counties": [], "geography_basis": "source_state",
        "status": status, "status_group": group,
        "in_service": {"raw": value, "value": value, "precision": "day" if value else "unknown"},
        "center": center, "location_review": "unreviewed" if center else "unlocated",
        "location_candidate": candidate, "project_events": events,
        "evidence": {"page": None, "sheet": miso.SHEET, "row": row["_row"], "source_sha256": artifact["sha256"],
                     "raw": {k: clean(row[k]) if row[k] is not None else None for k in raw_keys}},
    }


def miso_a_rows(path: Path) -> tuple[str, list[dict]]:
    """Appendix A/B project rows with their Facility-sheet rows, and the workbook's "as of" date."""
    sheets = {ws.title: ws for ws in misospp.workbook(path).worksheets}
    title = next(sheets[MISO_A_SHEETS[0]].iter_rows(values_only=True, max_row=1))[0]
    as_of = datetime.strptime(re.search(r"as of (\d+/\d+/\d{4})", title)[1], "%m/%d/%Y").date().isoformat()
    facilities: dict[str, list[dict]] = {}
    for n, f in misospp.sheet_rows(sheets["MTEP25 Data Pull - Facility"], 1):
        facilities.setdefault(misospp.mtep_id(f["MTEP Project ID (Project) (Project)"]), []).append(f | {"_row": n})
    rows = []
    for sheet in MISO_A_SHEETS:
        for n, c in misospp.sheet_rows(sheets[sheet], 1):
            native = misospp.mtep_id(c["MTEP Project ID"])
            rows.append(c | {"_sheet": sheet, "_row": n, "_native": native, "_facilities": facilities.get(native, [])})
    return as_of, rows


def miso_a_project(row: dict, artifact: dict, as_of: str, facilities: dict[str, list[dict]]) -> dict:
    native = row["_native"]
    pid = f"{MISO_A_SOURCE_ID}:{native}"
    status = clean(row["Planning Status"] or "Not stated")
    group = miso.STATUS.get(status[:2], "unknown")
    states = miso_states(row["State(s)"])
    locator = f"{MISO_A_FILE}#{row['_sheet']}!row-{row['_row']}"
    evidence = {"publisher": "Midcontinent Independent System Operator (MISO)", "url": artifact["url"],
                "artifact_sha256": artifact["sha256"], "locator": locator, "source_date": as_of,
                "retrieved_at": artifact["retrieved_at"], "access_review": "Public MISO CDN workbook; no login.",
                "facts": ""}
    value = day(row["Expected ISD"])
    events = dated_events(pid, native, status, group, value, artifact, evidence, "Expected in-service date",
                          "expected-isd", f"MISO MTEP25 Appendix A, as of {as_of}", "Expected ISD")
    name, text = clean(row["Project Name"]), row["Project Description"]
    rows = row["_facilities"]
    kv = ({int(v) for v in (row.get("Max kV"), row.get("Min kV")) if isinstance(v, int | float) and v > 0}
          | {int(f["Max kV"]) for f in rows if isinstance(f["Max kV"], int | float) and f["Max kV"] > 0}
          | voltages_kv(name, text))
    owner = clean(row["Submitting TO"])
    # The Facility sheet's From/To substations, when they name one site or one line (F39's rule); else the title.
    subs = None if misospp.PROGRAM.search(name) else misospp.facility_names(rows)
    if subs:
        center, candidate = place({"kind": subs[0], "names": subs[1], "from": "facility_from_to", "reason": None},
                                  kv, states, facilities, miso_keys(owner))
    else:
        center, candidate = locate(name, kv, states, facilities, miso_keys(owner), clean(text) if text else None)
    raw_keys = ("MTEP Project ID", "Target Appendix", "Submitting TO", "State(s)", "Project Name", "Project Type",
                "Expected ISD", "Current Cost", "Planning Status", "Max kV", "Min kV")
    return {
        "_id": pid, "source_id": MISO_A_SOURCE_ID, "native_id": native, "name": name,
        "description": clean(text)[:500] if text else None, "owner": owner, "other_owners": [], "planning_region": "miso",
        "states": [STATES[s] for s in states], "counties": [], "geography_basis": "source_state",
        "status": status, "status_group": group,
        "in_service": {"raw": value, "value": value, "precision": "day" if value else "unknown"},
        "center": center, "location_review": "unreviewed" if center else "unlocated",
        "location_candidate": candidate | {"names_from": "facility_from_to" if subs else "name"},
        "project_events": events,
        "evidence": {"page": None, "sheet": row["_sheet"], "row": row["_row"], "source_sha256": artifact["sha256"],
                     "raw": {k: clean(row[k]) if row.get(k) is not None else None for k in raw_keys}
                     | {"facilities": [{k: clean(v) for k, v in f.items() if k and not k.startswith("_") and v is not None}
                                       for f in rows]}},
    }


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest = load_json(cache / "manifest.json") if (cache / "manifest.json").exists() else {}
    if ZIP not in manifest:
        fetch_into(cache, ZIP, URL, manifest)
        write_json(cache / "manifest.json", manifest)
    if miso.FILE not in manifest:
        fetch_into(cache, miso.FILE, miso.URL, manifest)
        write_json(cache / "manifest.json", manifest)
    if MISO_A_FILE not in manifest:
        fetch_into(cache, MISO_A_FILE, MISO_A_URL, manifest)
        write_json(cache / "manifest.json", manifest)
    from sppsouth.history import files

    for name, url in files().items():
        if name not in manifest:
            fetch_into(cache, name, url, manifest)
            write_json(cache / "manifest.json", manifest)
    for state in STATES:
        if f"osm-{state.lower()}.json" not in manifest:
            fetch_osm(cache, state, manifest)
            write_json(cache / "manifest.json", manifest)


def build(cache: Path) -> dict[Path, object]:
    osm_files = [f"osm-{s.lower()}.json" for s in STATES]
    from sppsouth import history as spp_history

    manifest = verify_cache(cache, [ZIP, miso.FILE, MISO_A_FILE, *spp_history.files(), *osm_files])
    facilities = {s: osm_extract(json.loads((cache / f"osm-{s.lower()}.json").read_bytes()), s) for s in STATES}
    artifact = manifest[ZIP]
    projects, dispositions = [], []
    spp_rows = read_rows((cache / ZIP).read_bytes())
    for row in spp_rows:
        states = row_states(row["State(s)"])
        where = {"source_id": SOURCE_ID, "sheet": row["_sheet"], "row": row["_row"], "uid": str(row["UID"]),
                 "name": clean(row["Upgrade Name"] or "")}
        if not states or not set(states) <= STATES.keys():
            reason = "no state listed" if not states else f"outside F46 states ({','.join(states)})"
            dispositions.append(where | {"disposition": "excluded", "reason": reason})
            continue
        record = project(row, artifact, facilities)
        projects.append(record)
        dispositions.append(where | {"disposition": "accepted", "_id": record["_id"],
                                     "location": record["location_candidate"]["tier"] or "unlocated"})
    spp_count = len(projects)
    great_lakes = set(miso.GREAT_LAKES)
    for row in miso_rows(cache / miso.FILE):
        states = miso_states(row["State(s)"])
        where = {"source_id": MISO_SOURCE_ID, "sheet": miso.SHEET, "row": row["_row"],
                 "native_id": str(row["MTEP Project ID"]), "name": clean(row["Project Name"] or "")}
        if set(states) & great_lakes:
            dispositions.append(where | {"disposition": "excluded", "reason": "F40 row (lists a Great Lakes state)"})
            continue
        if not states or not set(states) <= STATES.keys():
            reason = "no state listed" if not states else f"outside F46 states ({','.join(states)})"
            dispositions.append(where | {"disposition": "excluded", "reason": reason})
            continue
        record = miso_project(row, manifest[miso.FILE], facilities)
        projects.append(record)
        dispositions.append(where | {"disposition": "accepted", "_id": record["_id"],
                                     "location": record["location_candidate"]["tier"] or "unlocated"})
    miso_count = len(projects) - spp_count
    taken = {p["native_id"] for p in projects if p["source_id"] == MISO_SOURCE_ID} | {
        p["native_id"] for path in MISO_PUBLISHED for p in load_json(REPO_ROOT / path) if "miso" in p["source_id"]}
    as_of, a_rows = miso_a_rows(cache / MISO_A_FILE)
    for row in a_rows:
        states = miso_states(row["State(s)"])
        where = {"source_id": MISO_A_SOURCE_ID, "sheet": row["_sheet"], "row": row["_row"],
                 "native_id": row["_native"], "name": clean(row["Project Name"] or "")}
        reason = ("no state listed" if not states
                  else f"outside F46 states ({','.join(states)})" if not set(states) <= STATES.keys()
                  else "MTEP ID already published (F46 MTEP26 list, F40 or F39)" if row["_native"] in taken
                  else None)
        if reason:
            dispositions.append(where | {"disposition": "excluded", "reason": reason})
            continue
        taken.add(row["_native"])  # App. B repeats of an App. A ID stay out
        record = miso_a_project(row, manifest[MISO_A_FILE], as_of, facilities)
        projects.append(record)
        dispositions.append(where | {"disposition": "accepted", "_id": record["_id"],
                                     "location": record["location_candidate"]["tier"] or "unlocated"})
    # FIX-F46: completed SPP upgrades only the older Q4 editions list, through F47's reader (sppsouth.history).
    from sppsouth import history
    from sppsouth.build import published_uids as south_uids

    taken_spp = south_uids() | {p["native_id"] for p in load_json(REPO_ROOT / "data" / "sppsouth" / "projects.json")}
    past, more, used = history.projects(cache, manifest, {str(r["UID"]) for r in spp_rows}, taken_spp, facilities,
                                        STATES, OPERATOR_KEYS, "C43", suffix="midwest")
    projects += past
    dispositions += more
    if len({p["_id"] for p in projects}) != len(projects):
        raise SystemExit("project ID repeated within a workbook")
    projects.sort(key=lambda p: p["_id"])
    miso_artifact = manifest[miso.FILE]
    miso_source = {
        "_id": MISO_SOURCE_ID, "publisher": "Midcontinent Independent System Operator (MISO)",
        "title": "MTEP Projects Under Evaluation (MTEP26 cycle)", "authority": "regional_planning_organization",
        "role": "project_plan", "landing_url": "https://www.misoenergy.org/planning/transmission-planning/mtep/",
        "download_url": miso_artifact["url"], "publication_date": None, "vintage": "MTEP26 cycle, retrieved date",
        "retrieved_at": miso_artifact["retrieved_at"], "sha256": miso_artifact["sha256"],
        "public_status": "verified_public", "import_status": "imported", "access_policy": "public_document",
        "planning_region": "miso",
        "states": sorted({s for p in projects if p["source_id"] == MISO_SOURCE_ID for s in p["states"]}),
        "project_count": miso_count,
        "notes": ["F46 Midwest release (C43): rows listing only IA, MO, ND or SD from the workbook F40 pinned "
                  "(miso-mtep26-eval); F40 kept the Great Lakes rows. Same artifact and hash.",
                  "Under-evaluation projects are proposals; M2 rows are Appendix A approved. Locations are unreviewed "
                  "C33 candidates from named OSM substations; none is independently confirmed."],
    }
    source = {
        "_id": SOURCE_ID, "publisher": "Southwest Power Pool",
        "title": "SPP Q3 2026 Quarterly Project Tracking Report, Appendix 1", "authority": "regional_planning_organization",
        "role": "project_plan", "landing_url": LANDING, "download_url": artifact["url"], "publication_date": None,
        "vintage": "2026 Q3", "retrieved_at": artifact["retrieved_at"], "sha256": artifact["sha256"],
        "public_status": "verified_public", "import_status": "imported", "access_policy": "public_document",
        "planning_region": "spp",
        "states": sorted({s for p in projects if p["source_id"] == SOURCE_ID for s in p["states"]}),
        "project_count": spp_count,
        "notes": ["F46 Midwest release (C43): SPP upgrades whose listed states are all IA, MO, KS, NE, ND or SD. "
                  "Locations are unreviewed C33 candidates from named OSM substations; none is independently "
                  "confirmed. Source-bounded, not statewide coverage.",
                  f"sha256 is of the appendix zip; rows are read from its member “{MEMBER.split('/')[-1]}”."],
    }
    a_artifact = manifest[MISO_A_FILE]
    a_source = {
        "_id": MISO_A_SOURCE_ID, "publisher": "Midcontinent Independent System Operator (MISO)",
        "title": "MTEP25 Appendix A workbook (App. A approved and App. B rows)",
        "authority": "regional_planning_organization", "role": "project_plan",
        "landing_url": "https://www.misoenergy.org/planning/transmission-planning/mtep/",
        "download_url": a_artifact["url"], "publication_date": None, "vintage": f"MTEP25, as of {as_of}",
        "retrieved_at": a_artifact["retrieved_at"], "sha256": a_artifact["sha256"], "public_status": "verified_public",
        "import_status": "imported", "access_policy": "public_document", "planning_region": "miso",
        "states": sorted({s for p in projects if p["source_id"] == MISO_A_SOURCE_ID for s in p["states"]}),
        "project_count": sum(p["source_id"] == MISO_A_SOURCE_ID for p in projects),
        "notes": ["FIX-F46 (Midwest release): rows listing only IA, MO, ND or SD whose MTEP ID no rollout publishes; "
                  "F39 reads the same workbook for its own states.",
                  "Located from the Facility sheet's From/To substations when they name one site or line, else from "
                  "the title. Unreviewed C33 candidates; none is independently confirmed."]}
    past_sources = history.sources(used, projects, "F46 Midwest (FIX-F46): completed IA/MO/KS/NE/ND/SD upgrades "
                                   "absent from the 2026 Q3 edition.", suffix="midwest")
    return {OUT / "projects.json": projects, OUT / "sources.json": [source, miso_source, a_source, *past_sources],
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
            "by_source": {s: {"projects": n, "located": sum(p["source_id"] == s for p in located)}
                          for s, n in sorted(Counter(p["source_id"] for p in projects).items())},
            "distinct_points": len({(p["center"]["lat"], p["center"]["lon"]) for p in located}),
            "by_state": {s: {"projects": by_state[f], "located": located_by_state[f]} for s, f in STATES.items()},
            "by_tier": dict(sorted(Counter(p["location_candidate"]["tier"] for p in located).items())),
            "by_basis": dict(sorted(Counter(p["center"]["basis"] for p in located).items())),
            "by_status": dict(sorted(Counter(p["status_group"] for p in projects).items())),
            "located_by_status": dict(sorted(Counter(p["status_group"] for p in located).items())),
            "located_not_in_service": sum(p["status_group"] not in {"in_service", "cancelled"} for p in located),
            "located_with_dated_events": sum(any(e["date"] for e in p["project_events"]) for p in located),
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
