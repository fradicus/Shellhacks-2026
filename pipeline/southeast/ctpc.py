"""Carolinas Transmission Planning Collaborative (CTPC, formerly NCTPC): Duke Energy Carolinas and Progress projects.

Each annual Collaborative Transmission Plan (and mid-year update) lists the major DEC/DEP projects with an ID,
name, owner, status, projected in-service date and cost. The newest edition supplies current projects; older
editions add one planned_milestone per changed projected date, and in-service projects the newer editions no
longer list. Locations are C45 OSM name candidates over NC and SC substations combined (the DEC/DEP footprint);
none is independently reviewed.

From pipeline/:
  uv run python -m southeast.ctpc fetch --cache <dir>   # network: 12 report PDFs + OSM NC/SC substations
  uv run python -m southeast.ctpc build --cache <dir> [--check]
OSM data (c) OpenStreetMap contributors, ODbL 1.0.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pdfplumber

from california.caiso import match
from common import load_json, write_json
from common.names import norm_name
from greatlakes.match import candidate_center, voltages_kv
from greatlakes.shared import fetch_into, fetch_osm, osm_extract, verify_cache

from .dense import SE_STATES, locate, write_batch

BATCH = "ctpc"
PREFIX = "southeast:ctpc"
PUBLISHER = "Carolinas Transmission Planning Collaborative"
LANDING = "https://carolinastpc.org/reference/"
BASE = "https://carolinastpc.org/media/reference/"
ACCESS = "Public CTPC reference library (https://carolinastpc.org/reference/); no login, not marked CEII."
# Oldest first: (report date stated in the file name, path under BASE, title).
EDITIONS = {
    "2016": ("2017-01-13", "2017/01/13/2016-2026_NCTPC_Report___01_13_2017_FINAL.pdf", "2016-2026 NCTPC Report"),
    "2017": ("2018-01-16", "2018/01/16/2017-2027_NCTPC_Report_01_16_2018_FINAL.pdf", "2017-2027 NCTPC Report"),
    "2018": ("2019-01-17", "2024/06/24/2018-2028_NCTPC_Report_1_17_2019_FINAL.pdf", "2018-2028 NCTPC Report"),
    "2019": ("2020-01-22", "2024/06/24/2019-2029_NCTPC_Report_1_22_2020_FINAL.pdf", "2019-2029 NCTPC Report"),
    "2020": ("2021-01-15", "2024/06/24/2020-2030_NCTPC_Report_01_15_2021_FINAL_REPORT.pdf",
             "2020-2030 NCTPC Report"),
    "2021": ("2022-01-24", "2024/06/24/2021-2031_NCTPC_Report_01_24_2022_FINAL_REPORT.pdf",
             "2021-2031 NCTPC Report"),
    "2022": ("2023-02-21", "2024/06/24/2022_NCTPC_Report_02_21_2023_FINAL.pdf", "2022 NCTPC Report"),
    "2023": ("2024-02-22", "2024/06/24/2023_NCTPC_Collaborative_Transmission_Plan_Report_02222024_FINAL.pdf",
             "2023 NCTPC Collaborative Transmission Plan Report"),
    "2024": ("2025-02-28", "2025/02/28/2024_CTPC_Collaborative_Transmission_Plan_FINAL_Report_02-28-2025.pdf",
             "2024 CTPC Collaborative Transmission Plan"),
    "2024-myu": ("2025-07-24", "2025/07/24/2025_Mid-Year_Update_to_2024_CTPC_Transmission_Plan__FINAL_07242025.pdf",
                 "2025 Mid-Year Update to the 2024 CTPC Transmission Plan"),
    "2025": ("2026-04-16", "2026/04/22/2025_CTPC_Collaborative_Transmission_Plan_Report_FINAL_04-16-2026.pdf",
             "2025 CTPC Collaborative Transmission Plan"),
    "2025-myu": ("2026-08-13", "2026/08/14/2025_Collaborative_Transmission_Plan_MidYear_Update_08-13-26.pdf",
                 "2025 Collaborative Transmission Plan Mid-Year Update"),
}
NEWEST = "2025-myu"
# Through the 2023 plan, projects carry NCTPC reference numbers ("0086"); from the 2024 plan on, the owners' own
# project IDs ("W200126", "E190092", "CTPCDEC01"). The source gives no crosswalk, so the two schemes stay apart.
UTILITY_ERA = ("2024", "2024-myu", "2025", "2025-myu")
PROJECT_ID = re.compile(r"(?:CTPC(?:DEC|DEP)\d+|[A-Z]{1,4}\d{5,6}[A-Z]?|\d{4})")
STATUS = {"conceptual": "proposed", "planned": "planned", "underway": "under_construction",
          "in-service": "in_service", "in service": "in_service", "removed": "cancelled", "cancelled": "cancelled",
          "deferred": "unknown"}
OWNERS = {"DEC": ("Duke Energy Carolinas", ["DUKE"]), "DEP": ("Duke Energy Progress", ["DUKE", "PROGRESS"])}
# "DUKE" also matches the sister company's facilities; an OSM operator naming the other one is a conflict (C38).
SISTER = {"DEC": "PROGRESS", "DEP": "DUKE ENERGY CAROLINAS"}
DATE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})")  # the 2023 plan writes "6/1/24"
COST = re.compile(r"\$?\d+(?:\.\d+)?")
# A line terminal owned by another utility is named with its prefix ("Greenville-VEPCO Everetts"). OSM names omit
# the prefix, so such a terminal is matched separately and only when its OSM operator is that utility.
FOREIGN = {"VEPCO": ["DOMINION", "VIRGINIA ELECTRIC"], "SCEG": ["DOMINION", "SOUTH CAROLINA ELECTRIC"]}

def artifact(edition: str) -> str:
    return f"ctpc-{edition}.pdf"


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest = load_json(cache / "manifest.json") if (cache / "manifest.json").exists() else {}
    for edition, (_, path, _) in EDITIONS.items():
        if artifact(edition) not in manifest:
            fetch_into(cache, artifact(edition), BASE + path, manifest)
            write_json(cache / "manifest.json", manifest)
    for state in ("NC", "SC"):
        if f"osm-{state.lower()}.json" not in manifest:
            fetch_osm(cache, state, manifest)
            write_json(cache / "manifest.json", manifest)


def text(cell: str | None) -> str:
    return " ".join((cell or "").split())


def parse_row(cells: list[str | None]) -> dict | None:
    """One listing row: ID, name, owner, status, projected in-service date, cost; None if not a listing row.

    Listing layouts differ by edition (extra issue/study columns, merged cells), so fields are read by value in
    order: the name is the first text after the ID, the date and cost follow the status.
    """
    values = [text(c) for c in cells if text(c)]
    if len(values) < 4 or not PROJECT_ID.fullmatch(values[0]):
        return None
    status_at = next((i for i, v in enumerate(values) if v.lower() in STATUS), None)
    owner = next((v for v in values if v in OWNERS), None)
    if status_at is None or owner is None or status_at < 2:
        return None
    after = [v for v in values[status_at + 1:] if v not in OWNERS]
    date = after[0] if after and (DATE.fullmatch(after[0]) or after[0].upper() in ("TBD", "-", "–", "_")) else None
    cost = after[1] if date and len(after) > 1 and COST.fullmatch(after[1]) else None
    return {"id": values[0], "name": values[1], "owner": owner, "status": values[status_at], "date": date,
            "cost_musd": cost}


def read_edition(path: Path) -> list[dict]:
    """Every project-listing row with its page. Plan-comparison tables ("Update on ...") hold two editions' values
    side by side and are skipped; each edition is read from its own listing."""
    rows = []
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            for table in page.extract_tables():
                if "Update on" in " ".join(text(c) for c in table[0]):
                    continue
                for cells in table:
                    if row := parse_row(cells):
                        rows.append(row | {"page": number, "raw": [text(c) for c in cells]})
    return rows


def day(value: str | None) -> str | None:
    m = DATE.fullmatch(value or "")
    return f"{m[3] if len(m[3]) == 4 else '20' + m[3]}-{int(m[1]):02d}-{int(m[2]):02d}" if m else None


def clean_name(name: str, tie: bool = False) -> str:
    """The facility part of a CTPC name ("<facility>, <work>") in the form the shared name parser reads.

    A line section stated in parentheses with two terminals ("Cokesbury 100 kV Line (Coronaca–Hodges)") gives the
    endpoints of the work; any other parenthetical (a tap, a three-point section, an alias) is dropped. DEC names
    its tie stations "X Tie", OSM both "X" and "X Tie": with `tie`, a "Tie" the source writes after the voltage joins
    the name ("Shelby 230/100/44 kV Tie" reads "Shelby Tie"). A "Tie" is never added to a bare terminal name.
    """
    facility = re.split(r"[,;]", name)[0].strip()
    section = re.search(r"\(([^()]*)\)", facility)
    parts = [p.strip() for p in re.split(r"\s*[–—-]\s*", section[1])] if section else []
    if len(parts) == 2 and all(parts) and re.search(r"\bLines?\b", facility, re.I):
        kv = re.search(r"[\d./]+\s*kV", facility)
        facility = f"{parts[0]} – {parts[1]} {kv[0] + ' ' if kv else ''}Line"
    facility = re.sub(r"\([^()]*\)", " ", facility)
    facility = re.sub(r"\bBanks?\s+#?\d+(?:\s*&\s*#?\d+)*", "Bank", facility)  # "Banks #1 & #2", "Banks 1 & 2"
    facility = re.sub(r"(?<=[a-z])(?=\d+\s*kV)", " ", facility)  # "Folkstone115 kV"
    if tie:
        facility = re.sub(r"^(.+?)(?<!Tie)\s+([\d./]+\s*kV)\s+Tie\b", r"\1 Tie \2", facility)
    facility = re.sub(r"\bSwitching Station\b", "Station", facility)
    facility = re.sub(r"\bTie$", "Tie Station", facility.strip())  # "Madison Tie", "at Oakvale Tie"
    return " ".join(facility.split())


def place(name: str, owner: str, facilities: list[dict], state_of: dict[str, str]) -> tuple[dict | None, dict, list]:
    """C45 candidate over NC+SC facilities; the project's states are the matched facilities' states."""
    facility = clean_name(name)
    center, candidate = locate(facility, None, facilities, OWNERS[owner][1])
    if center is None and clean_name(name, tie=True) != facility:
        facility = clean_name(name, tie=True)
        center, candidate = locate(facility, None, facilities, OWNERS[owner][1])
    for endpoint in candidate["endpoints"]:
        utility = (endpoint.get("name") or "").split(" ")[0].upper()
        if endpoint["status"] == "no_facility" and utility in FOREIGN:
            bare = endpoint["name"].split(" ", 1)[1]
            hit = match(bare, facilities, FOREIGN[utility], voltages_kv(facility))
            if hit["status"] == "matched" and "operator" in hit["corroboration"]:
                keep = ("id", "name", "operator", "voltage", "lat", "lon")
                endpoint.update({k: v for k, v in hit.items() if k != "facility"}
                                | {"facility": {k: hit["facility"].get(k) for k in keep}, "utility": utility})
        if endpoint["status"] == "matched" and SISTER[owner] in (endpoint["facility"].get("operator") or "").upper():
            for key in ("facility", "corroboration"):
                endpoint.pop(key)
            endpoint["status"] = "operator_conflict"
        if endpoint.get("corroboration") == ["unique_in_state"] and voltage_conflict(endpoint, facility):
            # A name-only match whose tagged voltages exclude the project's (a 230 kV "Wateree" for a 100 kV line)
            # is another facility with the same name, e.g. Dominion's Wateree Station for Duke's Wateree Hydro.
            for key in ("facility", "corroboration"):
                endpoint.pop(key)
            endpoint["status"] = "voltage_conflict"
    found =[e for e in candidate["endpoints"] if e["status"] == "matched"]
    center = candidate_center(candidate["kind"], candidate["endpoints"]) if candidate["kind"] and found else None
    tier = None
    if center:
        tier = "candidate" if all(e["corroboration"] != ["unique_in_state"] for e in found) else "candidate_unique_name"
    states = sorted({SE_STATES[state_of[e["facility"]["id"]]] for e in found})
    return center, candidate | {"tier": tier, "names_from": facility}, states


def voltage_conflict(endpoint: dict, facility: str) -> bool:
    tagged = {round(int(v) / 1000) for v in re.findall(r"\d+", endpoint["facility"].get("voltage") or "")
              if int(v) >= 1000}
    stated = voltages_kv(facility)
    return bool(stated and tagged and not stated & tagged)


def evidence(edition: str, row: dict, manifest: dict, facts: str) -> dict:
    item = manifest[artifact(edition)]
    return {"publisher": PUBLISHER, "url": item["url"], "artifact_sha256": item["sha256"],
            "locator": f"{EDITIONS[edition][2]}, page {row['page']}, project {row['id']}",
            "source_date": EDITIONS[edition][0], "retrieved_at": item["retrieved_at"], "access_review": ACCESS,
            "facts": facts}


def group_of(row: dict) -> str:
    return STATUS[row["status"].lower()]


def events(pid: str, listings: list[tuple[str, dict]], manifest: dict) -> list[dict]:
    """One planned_milestone per changed projected date, oldest edition first; in-service only as the source dates it.

    Dates print as m/d/yyyy (the plans state them "±6 months"); they are kept at the printed day precision.
    """
    native = listings[0][1]["id"]
    out, last = [], None
    for edition, row in listings:
        value, facts = day(row["date"]), f"Status = {row['status']}; Projected In-Service Date = {row['date']}"
        if group_of(row) == "in_service":
            # A newer edition's in-service date supersedes an older one (the mid-year updates correct them).
            if value and value <= EDITIONS[edition][0]:
                out = [e for e in out if e["type"] != "in_service"]
                out.append({"id": f"{pid}:in-service", "type": "in_service", "date": value, "precision": "day",
                            "native_project_link": native, "evidence": [evidence(edition, row, manifest, facts)],
                            "description": f"{EDITIONS[edition][2]} reports the project In-Service, dated {value}."})
            continue
        if value is None or group_of(row) == "cancelled":
            continue
        if last and last["date"] == value:
            last["description"] = last["description"].split(" Unchanged")[0] + f" Unchanged through the {edition} edition."
            continue
        last = {"id": f"{pid}:planned-{edition}", "type": "planned_milestone", "date": value, "precision": "day",
                "native_project_link": native, "evidence": [evidence(edition, row, manifest, facts)],
                "description": f"Projected in-service {value}, first reported in {EDITIONS[edition][2]}. A planned "
                               "date, not a completion."}
        out.append(last)
    edition, row = listings[-1]
    if group_of(row) == "in_service" and not any(e["type"] == "in_service" for e in out):
        out.append({"id": f"{pid}:in-service", "type": "in_service", "date": None, "precision": "unknown",
                    "native_project_link": native, "evidence": [evidence(edition, row, manifest, f"Status = "
                                                                         f"{row['status']}")],
                    "description": f"{EDITIONS[edition][2]} reports the project In-Service without a usable date."})
    return out


GENERIC_WORDS = {"line", "lines", "substation", "upgrade", "rebuild", "construct", "station", "reconductor",
                 "switching", "with", "and", "the", "replace", "install", "section", "tie", "retail", "mile", "north",
                 "south", "east", "west"}


def name_words(name: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}", name.lower())) - GENERIC_WORDS


def same_name(name: str) -> str:
    """Whole project name, dashes and spacing normalized: the only cross-scheme identity this batch accepts."""
    return norm_name(re.sub(r"\s*[–—-]\s*", " - ", name))


def era(edition: str) -> str:
    return "owner-id" if edition in UTILITY_ERA else "nctpc"


def source_id(edition: str) -> str:
    return f"southeast:ctpc-plan-{edition}"


def build(cache: Path) -> dict:
    manifest = verify_cache(cache, [artifact(e) for e in EDITIONS] + ["osm-nc.json", "osm-sc.json"])
    facilities, state_of = [], {}
    for state in ("NC", "SC"):
        for f in osm_extract(json.loads((cache / f"osm-{state.lower()}.json").read_bytes()), state):
            if f["id"] not in state_of:  # a border facility in both extracts is kept once
                state_of[f["id"]] = state
                facilities.append(f)
    listed: dict[str, list[dict]] = {e: read_edition(cache / artifact(e)) for e in EDITIONS}
    listings: dict[tuple[str, str], list[tuple[str, dict]]] = {}
    for edition, rows in listed.items():
        for row in rows:
            history = listings.setdefault((era(edition), row["id"]), [])
            if not history or history[-1][0] != edition:
                history.append((edition, row))
    # An ID is stable across editions only while the name agrees: one mid-year update prints E220378 (Durham–RTP
    # elsewhere) on the Asheboro–Siler City row. A listing sharing no name word with the newest one is not linked.
    unlinked = set()
    for key, history in listings.items():
        newest = name_words(history[-1][1]["name"])
        unlinked |= {(edition, key[1]) for edition, row in history if not name_words(row["name"]) & newest}
        listings[key] = [(edition, row) for edition, row in history if (edition, key[1]) not in unlinked]
    owner_names = {same_name(r["name"]): r["id"] for e in UTILITY_ERA for r in listed[e]}
    projects, dispositions, sources, decided = [], [], [], {}
    for edition in reversed(EDITIONS):  # newest first: a project's newest listing decides
        kept, here = 0, set()
        for row in listed[edition]:
            key = (era(edition), row["id"])
            where = {"source_id": source_id(edition), "locator": f"page {row['page']}", "native_id": row["id"],
                     "name": row["name"]}
            reason = None
            if row["id"] in here:
                dispositions.append(where | {"disposition": "duplicate", "project_id": decided.get(key),
                                             "reason": "same project ID listed again in this edition"})
                continue
            here.add(row["id"])
            if (edition, row["id"]) in unlinked:
                reason = (f"same ID as a newer listing named “{listings[key][-1][1]['name']}” but no shared name "
                          "word: not linked, and not reported in service")
                if group_of(row) == "in_service":
                    raise SystemExit(f"{edition} {row['id']}: in-service row with a conflicting ID; review it")
            elif key in decided:
                reason = ("listed in a newer edition; its dates here become that project's events" if decided[key]
                          else "a newer edition's listing of this ID decided it (excluded there)")
            elif edition != NEWEST and group_of(row) != "in_service":
                reason = "not in the newest edition and not reported in service" + (
                    "; from the 2024 plan on projects carry owner IDs and the plans give no crosswalk, so a "
                    "continuing project is listed under its owner ID" if era(edition) == "nctpc" else "")
            elif era(edition) == "nctpc" and (same := owner_names.get(same_name(row["name"]))):
                reason = (f"same name as owner-ID project {same} (2024+ plans); the plans give no crosswalk from "
                          "NCTPC reference numbers, so it is kept once under the owner ID")
            if reason:
                if (edition, row["id"]) not in unlinked:
                    decided.setdefault(key, None)
                dispositions.append(where | {"disposition": "excluded", "reason": reason})
                continue
            pid = f"{PREFIX}:{row['id']}"
            decided[key] = pid
            projects.append(record(pid, edition, row, listings[key], manifest, facilities, state_of))
            kept += 1
            dispositions.append(where | {"disposition": "accepted", "project_id": pid})
        item = manifest[artifact(edition)]
        mine = [p for p in projects if p["source_id"] == source_id(edition)]
        sources.append({
            "_id": source_id(edition), "title": f"CTPC {EDITIONS[edition][2]} (Duke Energy Carolinas/Progress)",
            "publisher": PUBLISHER, "authority": "regional_planning_organization", "role": "project_plan",
            "landing_url": LANDING, "download_url": item["url"], "publication_date": EDITIONS[edition][0],
            "vintage": edition, "retrieved_at": item["retrieved_at"], "sha256": item["sha256"],
            "public_status": "verified_public", "import_status": "imported", "access_policy": "public_document",
            "planning_region": "ctpc", "states": sorted({s for p in mine for s in p["states"]}), "project_count": kept,
            "notes": ["F39 dense Southeast (C45). Locations are unreviewed OSM name candidates over NC and SC "
                      "substations; none is independently confirmed. Source-bounded major-project listing, not "
                      "statewide coverage."]
            + ([] if edition == NEWEST else ["Only in-service projects no newer edition lists are imported; other "
                                             "rows supply dated events for the newer listing."])})
    return {"projects": projects, "sources": sources[::-1], "dispositions": dispositions}


def record(pid: str, edition: str, row: dict, listings: list, manifest: dict, facilities: list[dict],
           state_of: dict[str, str]) -> dict:
    center, candidate, states = place(row["name"], row["owner"], facilities, state_of)
    value = day(row["date"])
    return {
        "_id": pid, "source_id": source_id(edition), "native_id": row["id"], "name": row["name"], "description": None,
        "owner": f"{OWNERS[row['owner']][0]} ({row['owner']})", "other_owners": [], "planning_region": "ctpc",
        "states": states, "counties": [], "geography_basis": "candidate_facility_state" if center else None,
        "status": row["status"], "status_group": group_of(row),
        "in_service": {"raw": row["date"], "value": value, "precision": "day" if value else "unknown"},
        "center": center, "location_review": "unreviewed" if center else "unlocated",
        "location_candidate": candidate, "project_events": events(pid, listings, manifest),
        "evidence": {"page": row["page"], "sheet": None, "row": None,
                     "source_sha256": manifest[artifact(edition)]["sha256"],
                     "raw": {"edition": edition, "cells": row["raw"], "cost_musd": row["cost_musd"],
                             "listed_in": [e for e, _ in listings]}},
    }

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["fetch", "build"])
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "fetch":
        fetch(args.cache)
        return 0
    result = build(args.cache)
    return write_batch(BATCH, result["projects"], result["sources"], result["dispositions"], args.check)


if __name__ == "__main__":
    sys.exit(main())
