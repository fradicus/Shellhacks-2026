"""Minnesota: 2025 Biennial Transmission Projects Report zone tables -> national-project records with C26 candidates.

From pipeline/:
  uv run python -m greatlakes.minnesota fetch --cache /tmp/gl-cache   # network: 6 report pages (OSM: greatlakes.osm)
  uv run python -m greatlakes.minnesota build --cache /tmp/gl-cache   # offline; add --check to compare committed output
Raw pages stay in the cache outside the checkout. A changed page hash fails the build until sources.json is reviewed.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

from common import REPO_ROOT, load_json, validate, write_json

from . import osm as osm_data
from .match import voltages_kv
from .shared import OPERATOR_KEYS, fetch_into, locate, verify_cache, write_outputs

SOURCE_ID = "mn-btpr-2025"
STATE_FIPS = "27"
BASE = "https://www.minnelectrans.com/documents/2025_Biennial_Report/html/"
PAGES = [f"Ch_6_Needs-6.{n}.htm" for n in range(3, 9)]
DATASET = "OpenStreetMap (ODbL), data/greatlakes/osm/mn-substations.json"
ID = re.compile(r"20\d\d-[A-Z]{2}-N\d+")
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
     "december"], 1)}


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest: dict = {}
    for page in PAGES:
        fetch_into(cache, page, BASE + page, manifest)
    write_json(cache / "manifest.json", manifest)


def _flat(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def parse_page(text: str) -> tuple[list[dict], dict[str, dict]]:
    """Table rows (needed / completed) and per-project detail sections, keyed by MPUC tracking number."""
    rows = []
    for table in re.findall(r"<table.*?</table>", text, re.S):
        trs = re.findall(r"<tr.*?</tr>", table, re.S)
        cells = [[_flat(c) for c in re.findall(r"<t[dh][ >].*?</t[dh]>", tr, re.S)] for tr in trs]
        if not cells or not cells[0] or cells[0][0] != "MPUC Tracking Number":
            continue
        header = cells[0]
        kind = "needed" if "MTEP Project Number" in header else "completed"
        for index, row in enumerate(cells[1:], start=2):
            if row and ID.fullmatch(row[0]):
                rows.append({"table": kind, "row": index, "cells": dict(zip(header, row, strict=False))})
    body = _flat(re.sub(r"<(script|style).*?</\1>", "", text, flags=re.S))
    sections = {}
    pieces = re.split(r"MPUC Tracking Number:\s*(20\d\d-[A-Z]{2}-N\d+)", body)
    for tracking, segment in zip(pieces[1::2], pieces[2::2], strict=True):
        sections.setdefault(tracking, {
            "utility": _field(segment, "Utility", ["Project Description"]),
            "description": _field(segment, "Project Description", ["Need Driver", "Alternatives", "Analysis", "Schedule"]),
            "schedule": _field(segment, "Schedule", ["General Impacts", "Other Impacts", "Analysis"], 600),
        })
    return rows, sections


def _field(segment: str, label: str, stops: list[str], limit: int = 2000) -> str | None:
    m = re.search(rf"{label}:\s*(.*?)\s*(?:{'|'.join(s + ':' for s in stops)}|$)", segment)
    return m.group(1)[:limit] if m and m.group(1) else None


def _codes(cell: str) -> list[str]:
    return list(dict.fromkeys(c.upper() for c in re.findall(r"[A-Za-z&]{2,}", cell)))


def completed_status(text: str) -> tuple[str, dict]:
    low = text.lower()
    unknown = {"raw": text, "value": None, "precision": "unknown"}
    if "withdrawn" in low or "cancel" in low:
        return "cancelled", unknown
    if "study" in low or "hold" in low:
        return "unknown", unknown
    if m := re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text):
        return "in_service", {"raw": text, "value": f"{m[3]}-{int(m[1]):02d}-{int(m[2]):02d}", "precision": "day"}
    if m := re.fullmatch(r"([A-Za-z]+),? (\d{4})", text):
        if m[1].lower() in MONTHS:
            return "in_service", {"raw": text, "value": f"{m[2]}-{MONTHS[m[1].lower()]:02d}", "precision": "month"}
    if m := re.fullmatch(r"(?:Completed in )?(\d{4})", text):
        return "in_service", {"raw": text, "value": m[1], "precision": "year"}
    return "unknown", unknown


def planned_in_service(schedule: str | None) -> dict:
    """A single stated in-service month/year from the schedule text; anything less clear stays unknown."""
    found = set()
    for m in re.finditer(r"in[- ]service[^.]{0,40}?\b(?:(" + "|".join(MONTHS) + r"),? )?(20\d\d)\b", schedule or "", re.I):
        found.add((m[2], MONTHS[m[1].lower()] if m[1] else None))
    if len(found) != 1:
        return {"raw": schedule, "value": None, "precision": "unknown"}
    year, month = found.pop()
    if month:
        return {"raw": schedule, "value": f"{year}-{month:02d}", "precision": "month"}
    return {"raw": schedule, "value": year, "precision": "year"}


def county_fips(description: str | None, counties: dict[str, str]) -> list[str]:
    found = re.findall(r"((?:St\.? )?[A-Z][a-z]+(?: [A-Z][a-z]+)?) County", description or "")
    return sorted({counties[n.replace("St ", "St. ")] for n in found if n.replace("St ", "St. ") in counties})


def build(cache: Path) -> dict:
    manifest = verify_cache(cache, PAGES)
    osm = osm_data.load(["MN"])
    geography = load_json(REPO_ROOT / "data" / "national" / "geography.json")
    counties = {c["name"]: c["county_geoid"] for c in geography["counties"] if c["county_geoid"].startswith(STATE_FIPS)}

    pages = {page: (cache / page).read_text(encoding="utf-8", errors="replace") for page in PAGES}
    parsed = {page: parse_page(text) for page, text in pages.items()}
    owner_names = {}
    for _, sections in parsed.values():
        for s in sections.values():
            for name, code in re.findall(r"([A-Z][\w .&]+?) \(([A-Z&]+)\)", s["utility"] or ""):
                owner_names.setdefault(code, name.strip())

    projects, dispositions = [], []
    seen: dict[str, str] = {}
    for page, (rows, sections) in parsed.items():
        for row in rows:
            cells = row["cells"]
            tracking = cells["MPUC Tracking Number"]
            locator = f"{page}#{row['table']}-row-{row['row']}"
            if tracking in seen:
                dispositions.append({"native_id": tracking, "locator": locator, "disposition": "duplicate",
                                     "reason": f"same tracking number already accepted at {seen[tracking]}"})
                continue
            seen[tracking] = locator
            detail = sections.get(tracking, {})
            name = cells.get("MISO Project Name") or cells.get("Description")
            codes = _codes(cells.get("Utility", ""))
            if row["table"] == "needed":
                status, group = "Needed project (2025 Biennial Report)", "planned"
                in_service = planned_in_service(detail.get("schedule"))
            else:
                group, in_service = completed_status(cells.get("Date Completed", ""))
                status = cells.get("Date Completed") or None
            kv = voltages_kv(name, detail.get("description"))
            keys = [k for c in codes for k in OPERATOR_KEYS.get(c, [])]
            center, candidate = locate(name, detail.get("description"), osm, keys, kv, DATASET)
            full_owners = [owner_names.get(c, c) for c in codes]
            project = {
                "_id": f"{SOURCE_ID}:{tracking}", "source_id": SOURCE_ID, "native_id": tracking, "name": name,
                "description": detail.get("description"),
                "owner": full_owners[0] if len(full_owners) == 1 else None,
                "other_owners": full_owners if len(full_owners) > 1 else [],
                "planning_region": "mn-biennial", "states": [STATE_FIPS],
                "counties": county_fips(detail.get("description"), counties),
                "geography_basis": "source_state", "status": status, "status_group": group,
                "in_service": in_service, "center": center,
                "location_review": "unreviewed" if center else "unlocated",
                "location_candidate": candidate,
                "evidence": {"page": None, "sheet": locator, "row": row["row"],
                             "raw": cells | {"source_url": BASE + page, "source_sha256": manifest[page]["sha256"]}},
            }
            validate(project, "national-project")
            projects.append(project)
            dispositions.append({"native_id": tracking, "locator": locator, "disposition": "accepted",
                                 "reason": "listed in the report's needed or completed/withdrawn project table"})
    projects.sort(key=lambda p: p["_id"])
    sources = [{"_id": SOURCE_ID, "publisher": "Minnesota Transmission Owners (MPUC Docket E999/M-25-99)",
                "title": "2025 Minnesota Biennial Transmission Projects Report, Chapter 6 zone pages",
                "vintage": "2025-10-31", "rights": "Public regulatory filing, published openly on minnelectrans.com",
                "artifacts": [{"page": p} | manifest[p] for p in PAGES]}]
    return {"projects": projects, "dispositions": dispositions, "sources": sources}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["fetch", "build"])
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "fetch":
        fetch(args.cache)
        return 0
    return write_outputs("mn", build(args.cache), args.check)


if __name__ == "__main__":
    sys.exit(main())
