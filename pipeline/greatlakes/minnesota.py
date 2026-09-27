"""Minnesota: 2025 Biennial Transmission Projects Report zone tables -> national-project records with C26 candidates.

From pipeline/:
  uv run python -m greatlakes.minnesota fetch --cache /tmp/gl-cache   # network: 6 report pages + 1 Overpass query
  uv run python -m greatlakes.minnesota build --cache /tmp/gl-cache   # offline; add --check to compare committed output
Raw pages stay in the cache outside the checkout. A changed page hash fails the build until sources.json is reviewed.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from common import REPO_ROOT, load_json, validate, write_json
from common.names import norm_name

from .match import candidate_center, facilities_named, match_facility, voltages_kv

SOURCE_ID = "mn-btpr-2025"
STATE_FIPS = "27"
BASE = "https://www.minnelectrans.com/documents/2025_Biennial_Report/html/"
PAGES = [f"Ch_6_Needs-6.{n}.htm" for n in range(3, 9)]
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_QUERY = '[out:json][timeout:170];area["ISO3166-2"="US-MN"]->.a;nwr["power"="substation"](area.a);out center tags;'
USER_AGENT = "GridBridge/0.1 (https://github.com/fradicus/Shellhacks-2026)"
MAX_BYTES = 8 * 1024 * 1024
OUT = REPO_ROOT / "data" / "greatlakes"
OSM_EXTRACT = OUT / "osm" / "mn-substations.json"

ID = re.compile(r"20\d\d-[A-Z]{2}-N\d+")
# Operator-name fragments for the utility codes the report uses; matched against the OSM operator tag.
OPERATOR_KEYS = {
    "XEL": ["XCEL", "NORTHERN STATES"], "XCEL": ["XCEL", "NORTHERN STATES"], "GRE": ["GREAT RIVER"],
    "OTP": ["OTTER TAIL"], "MP": ["MINNESOTA POWER", "ALLETE"], "MPC": ["MINNKOTA"], "MRES": ["MISSOURI RIVER"],
    "ITCM": ["ITC"], "ITC": ["ITC"], "DPC": ["DAIRYLAND"], "SMP": ["SOUTHERN MINNESOTA MUNICIPAL", "SMMPA"],
    "SMMPA": ["SOUTHERN MINNESOTA MUNICIPAL", "SMMPA"], "RPU": ["ROCHESTER PUBLIC"],
    "CMPAS": ["CENTRAL MINNESOTA MUNICIPAL", "CMMPA"], "ATC": ["AMERICAN TRANSMISSION"],
}
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
     "december"], 1)}


def _get(url: str, data: bytes | None = None, timeout: int = 180) -> bytes:
    request = Request(url, data=data, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS URLs only
        body = response.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        raise RuntimeError(f"{url}: exceeds {MAX_BYTES} bytes")
    return body


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for page in PAGES:
        body = _get(BASE + page)
        (cache / page).write_bytes(body)
        manifest[page] = {"url": BASE + page, "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body),
                          "retrieved_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}
        time.sleep(1)
    body = _get(OVERPASS_URL, urlencode({"data": OVERPASS_QUERY}).encode())
    (cache / "osm-mn.json").write_bytes(body)
    manifest["osm-mn.json"] = {"url": OVERPASS_URL, "query": OVERPASS_QUERY, "sha256": hashlib.sha256(body).hexdigest(),
                               "bytes": len(body), "retrieved_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}
    write_json(cache / "manifest.json", manifest)


def osm_extract(raw: dict) -> list[dict]:
    """Named substations only, with the fields matching reads. OSM data (c) OpenStreetMap contributors, ODbL."""
    out = []
    for e in raw["elements"]:
        tags = e.get("tags", {})
        if not tags.get("name"):
            continue
        point = e if "lat" in e else e.get("center")
        if not point:
            continue
        out.append({"id": f"{e['type']}/{e['id']}", "name": tags["name"], "norm": norm_name(tags["name"]),
                    "operator": tags.get("operator"), "voltage": tags.get("voltage"),
                    "lat": round(point["lat"], 7), "lon": round(point["lon"], 7)})
    return sorted(out, key=lambda f: f["id"])


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
    manifest = load_json(cache / "manifest.json")
    osm = osm_extract(json.loads((cache / "osm-mn.json").read_bytes()))
    geography = load_json(REPO_ROOT / "data" / "national" / "geography.json")
    counties = {c["name"]: c["county_geoid"] for c in geography["counties"] if c["county_geoid"].startswith(STATE_FIPS)}

    pages = {page: (cache / page).read_text(encoding="utf-8", errors="replace") for page in PAGES}
    for name in [*PAGES, "osm-mn.json"]:
        if hashlib.sha256((cache / name).read_bytes()).hexdigest() != manifest[name]["sha256"]:
            raise SystemExit(f"{name}: cache bytes do not match the fetch manifest")
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
            named = facilities_named(name, detail.get("description"))
            kv = voltages_kv(name, detail.get("description"))
            keys = [k for c in codes for k in OPERATOR_KEYS.get(c, [])]
            matches = [match_facility(n, osm, keys, kv) for n in named["names"]]
            center = candidate_center(named["kind"], matches) if named["kind"] else None
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
                "location_candidate": {
                    "rule": "C26", "kind": named["kind"], "names_from": named["from"], "reason": named["reason"],
                    "voltages_kv": sorted(kv), "operator_keys": keys,
                    "endpoints": [{k: v for k, v in m.items() if k != "facility"} | (
                        {"facility": {f: m["facility"][f] for f in ("id", "name", "operator", "voltage", "lat", "lon")}}
                        if m["status"] == "matched" else {}) for m in matches],
                    "dataset": "OpenStreetMap (ODbL), data/greatlakes/osm/mn-substations.json",
                },
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
                "artifacts": [{"page": p} | manifest[p] for p in PAGES]},
               {"_id": "osm-mn-substations", "publisher": "OpenStreetMap contributors",
                "rights": "ODbL 1.0; attribution required",
                "role": "candidate facility geometry only (C26)", "artifacts": [manifest["osm-mn.json"]]}]
    return {"projects": projects, "dispositions": dispositions, "sources": sources, "osm": osm}


def summary(projects: list[dict]) -> dict:
    located = [p for p in projects if p["center"]]
    reasons = Counter(
        p["location_candidate"]["reason"] or ",".join(sorted({e["status"] for e in p["location_candidate"]["endpoints"]}))
        for p in projects if not p["center"])
    return {"projects": len(projects), "candidate_located": len(located),
            "by_basis": dict(Counter(p["center"]["basis"] for p in located)),
            "by_status": dict(Counter(p["status_group"] for p in projects)),
            "located_by_status": dict(Counter(p["status_group"] for p in located)),
            "unlocated_reasons": dict(reasons), "verified": 0}


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
    outputs = {OUT / "mn" / "projects.json": result["projects"], OUT / "mn" / "dispositions.json": result["dispositions"],
               OUT / "mn" / "sources.json": result["sources"], OSM_EXTRACT: result["osm"],
               OUT / "mn" / "summary.json": summary(result["projects"]),
               # Fixed publication path (C26); later states append their projects here.
               OUT / "projects.json": result["projects"]}
    if args.check:
        stale = [str(p) for p, v in outputs.items() if not p.exists() or load_json(p) != v]
        print("stale: " + ", ".join(stale) if stale else "ok")
        return 1 if stale else 0
    for path, value in outputs.items():
        write_json(path, value)
    print(json.dumps(summary(result["projects"]), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
