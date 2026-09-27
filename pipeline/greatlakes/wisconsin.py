"""Wisconsin: ATC's 2025 10-Year Assessment network project list -> national-project records with C26 candidates.

From pipeline/:
  uv run python -m greatlakes.wisconsin fetch --cache /tmp/gl-cache-wi   # network: 1 PDF, 5 zone pages (OSM: greatlakes.osm)
  uv run python -m greatlakes.wisconsin build --cache /tmp/gl-cache-wi   # offline; add --check to compare
States come from ATC's own zone pages ("Zone N includes the counties of: ..., Wis. ..., Mich."), not inference.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from collections import Counter
from pathlib import Path

import pdfplumber

from common import REPO_ROOT, load_json, validate, write_json

from . import osm as osm_data
from .match import voltages_kv
from .shared import OPERATOR_KEYS, fetch_into, locate, verify_cache, write_outputs

SOURCE_ID = "atc-tya-2025"
PDF = "TYA-2025-Network-Project-List.pdf"
PDF_URL = "https://www.atc10yearplan.com/wp-content/uploads/2025/11/" + PDF
ZONES = [f"zone-{n}.html" for n in range(1, 6)]
ZONE_URL = "https://www.atc10yearplan.com/blog/zones-directory/{}/"
STATE_ABBREV = {"Wis.": "WI", "Mich.": "MI", "Ill.": "IL", "Minn.": "MN"}
FIPS = {"WI": "55", "MI": "26", "IL": "17", "MN": "27"}
OWNER = "American Transmission Company"  # the document is "ATC's 2025 10-Year Assessment Project List"
DATASET = "OpenStreetMap (ODbL), data/greatlakes/osm/{wi,mi,il}-substations.json"
ISD = re.compile(r"([A-Z][a-z]{2})-(\d\d)")
MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
STATUS = {"Planned": "planned", "Proposed": "proposed", "Provisional": "proposed"}
HEADER = ["Project Name", "ISD", "Zone", "Need Category", "Status", "MTEP Appendix", "MTEP PRJID", "Cost", "Explanation"]


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest: dict = {}
    fetch_into(cache, PDF, PDF_URL, manifest)
    for zone in ZONES:
        fetch_into(cache, zone, ZONE_URL.format(zone.removesuffix(".html")), manifest)
    write_json(cache / "manifest.json", manifest)


def zone_states(text: str) -> list[str]:
    """States named in the page's 'includes the counties of:' list."""
    flat = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style).*?</\1>", "", text,
                                                                            flags=re.S))))
    m = re.search(r"includes the counties of:(.*?)(?:Zone \d (?:Planned|Proposed|Provisional)|$)", flat)
    return sorted({STATE_ABBREV[a] for a in re.findall(r"(Wis\.|Mich\.|Ill\.|Minn\.)", m[1] if m else "")})


def parse_pdf(path: Path) -> list[dict]:
    rows = []
    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            for table in page.extract_tables():
                for index, row in enumerate(table, start=1):
                    if len(row) == 9 and row[1] and ISD.fullmatch(row[1].strip()):
                        rows.append({"page": page_number, "row": index, "cells": dict(zip(HEADER, row, strict=True))})
    return rows


def cost(raw: str | None) -> dict:
    digits = re.sub(r"\D", "", raw or "")
    return {"raw": raw, "usd": int(digits) if digits else None}


def build(cache: Path) -> dict:
    manifest = verify_cache(cache, [PDF, *ZONES])
    zones = {str(n): zone_states((cache / z).read_text(encoding="utf-8")) for n, z in enumerate(ZONES, start=1)}
    mn_mtep = {str(p["evidence"]["raw"].get("MTEP Project Number")): p["_id"]
               for p in load_json(REPO_ROOT / "data" / "greatlakes" / "mn" / "projects.json")
               if str(p["evidence"]["raw"].get("MTEP Project Number")).isdigit()}
    rows = parse_pdf(cache / PDF)
    occurrences = Counter(r["cells"]["MTEP PRJID"] for r in rows)
    seen: Counter = Counter()
    projects, dispositions = [], []
    for row in rows:
        c = {k: (v or "").strip() or None for k, v in row["cells"].items()}
        prjid = c["MTEP PRJID"] or "none"
        seen[prjid] += 1
        native = prjid if occurrences[row["cells"]["MTEP PRJID"]] == 1 else f"{prjid}-{seen[prjid]}"
        locator = f"{PDF}#page-{row['page']}-row-{row['row']}"
        if not c["Project Name"]:
            dispositions.append({"native_id": native, "locator": locator, "disposition": "rejected",
                                 "reason": "row has no project name"})
            continue
        if prjid in mn_mtep:
            dispositions.append({"native_id": native, "locator": locator, "disposition": "duplicate",
                                 "reason": f"same MTEP project number as {mn_mtep[prjid]}"})
            continue
        name = re.sub(r"\s*--\s*Project Withdrawn$", "", c["Project Name"].replace("\n", " "))
        zone_list = re.findall(r"\d", c["Zone"] or "")
        states = sorted({s for z in zone_list for s in zones.get(z, [])})
        explanation = c["Explanation"] or ""
        if "withdrawn" in (c["Project Name"] + explanation).lower():
            group = "cancelled"
        elif "in-service" in explanation.lower():
            group = "in_service"
        else:
            group = STATUS.get(c["Status"] or "", "unknown")
        m = ISD.fullmatch(c["ISD"])
        in_service = {"raw": c["ISD"], "value": f"20{m[2]}-{MONTHS[m[1]]:02d}", "precision": "month"}
        facilities = osm_data.load(states)  # no source state ("Various" zone): nothing to match against
        # Text after the first comma describes the work; "LRTP Tranche N Project NN:" prefixes the endpoints.
        facility_text = re.sub(r"^LRTP Tranche \d+ Project \d+:\s*", "", name.split(",")[0])
        center, candidate = locate(facility_text, None, facilities, OPERATOR_KEYS["ATC"], voltages_kv(name), DATASET)
        if not states:
            candidate["reason"] = "no_source_state"
        project = {
            "_id": f"{SOURCE_ID}:{native}", "source_id": SOURCE_ID, "native_id": native, "name": name,
            "description": None, "owner": OWNER, "other_owners": [], "planning_region": "atc-tya",
            "states": [FIPS[s] for s in states], "counties": [],
            "geography_basis": "source_zone" if states else None,
            "status": f"{c['Status']} ({explanation})" if explanation else c["Status"], "status_group": group,
            "in_service": in_service, "center": center, "location_review": "unreviewed" if center else "unlocated",
            "location_candidate": candidate, "estimated_cost": cost(c["Cost"]),
            "evidence": {"page": row["page"], "sheet": locator, "row": row["row"],
                         "raw": c | {"source_url": PDF_URL, "source_sha256": manifest[PDF]["sha256"]}},
        }
        validate(project, "national-project")
        projects.append(project)
        dispositions.append({"native_id": native, "locator": locator, "disposition": "accepted",
                             "reason": "row in ATC's 2025 network project list"})
    projects.sort(key=lambda p: p["_id"])
    sources = [{"_id": SOURCE_ID, "publisher": "American Transmission Company",
                "title": "ATC's 2025 10-Year Assessment Project List (network projects) and zone pages",
                "vintage": "2025-11", "rights": "Published openly on atc10yearplan.com",
                "zone_states": zones, "artifacts": [{"file": f} | manifest[f] for f in [PDF, *ZONES]]}]
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
    return write_outputs("wi", build(args.cache), args.check)


if __name__ == "__main__":
    sys.exit(main())
