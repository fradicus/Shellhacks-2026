"""F51 California municipal utilities (C51): 2026 WECC progress reports of LADWP, IID, SMUD, TANC, TID and MID.

Rows are transcribed with a page and verbatim quote into data/camunis/transcriptions/ and read through F50's
progress-report reader (interiorwest.apr), which re-verifies each one against the pinned PDF and places it under C33
with C38's operator guard. None of these utilities files in CAISO's Transmission Development Forum (F44).

From pipeline/:
  uv run python -m camunis.build fetch --cache /tmp/camunis-f51
  uv run python -m camunis.build build --cache /tmp/camunis-f51 [--check]
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
from greatlakes.shared import fetch_into, fetch_osm, osm_extract, verify_cache
from interiorwest import apr

OUT = REPO_ROOT / "data" / "camunis"
STATES = {"CA": "06", "UT": "49", "NV": "32"}
LADWP, IID, SMUD = ("Los Angeles Department of Water and Power", "Imperial Irrigation District",
                    "Sacramento Municipal Utility District")
TANC, TID, MID = "Transmission Agency of Northern California", "Turlock Irrigation District", "Modesto Irrigation District"
REPORTS = {f"apr_{org.lower()}_2026": (f"{org}_2026_APR.pdf", f"{apr.BASE}{org}%202026%20APR.pdf",
                                       f"wecc-apr-2026-{org.lower()}", owner)
           for org, owner in (("LADWP", LADWP), ("IID", IID), ("SMUD", SMUD), ("TANC", TANC), ("TID", TID),
                              ("MID", MID))}
TERRITORY = {LADWP: ["CA", "UT", "NV"], IID: ["CA"], SMUD: ["CA"], TANC: ["CA"], TID: ["CA"], MID: ["CA"]}
OPERATOR_KEYS = {LADWP: ["LOS ANGELES DEPARTMENT OF WATER", "LADWP"], IID: ["IMPERIAL IRRIGATION"],
                 SMUD: ["SACRAMENTO MUNICIPAL", "SMUD"], TANC: ["TRANSMISSION AGENCY OF NORTHERN", "TANC"],
                 TID: ["TURLOCK"], MID: ["MODESTO"]}
# Rollouts whose projects a transcribed row may point to with published_as.
PUBLISHED = ("data/california/projects.json", "data/southwest/projects.json", "data/interiorwest/projects.json")


# LADWP's OSM facilities are named "Rinaldi Receiving Station", "Receiving Station E - Toluca", "Barren Ridge Switching
# Station"; its reports say "Rinaldi", "Toluca", "RS-E", "Barren Ridge". Aliases come only from the OSM name itself.
LETTERED = re.compile(r"^(?:LADWP )?Receiving Station ([A-Z])\b(?:\s*-\s*([^/]+?))?(?:\s*/.*)?$")
SUFFIXED = re.compile(r"^(?:LADWP )?(.+?) (?:Receiving|Switching|Converter) Station$")


def aliases(facility: dict) -> list[str]:
    """Report-style names an LADWP-operated OSM facility also answers to."""
    if not any(k in (facility.get("operator") or "").upper() for k in OPERATOR_KEYS[LADWP]):
        return []
    if m := LETTERED.match(facility["name"]):
        return [f"RS-{m[1]}", *([m[2].strip()] if m[2] else [])]
    return [m[1]] if (m := SUFFIXED.match(facility["name"])) else []


def with_aliases(facilities: list[dict]) -> list[dict]:
    return facilities + [f | {"name": a, "norm": a.upper(), "osm_name": f["name"]} for f in facilities for a in aliases(f)]


def published_ids(root: Path = REPO_ROOT) -> set[str]:
    return {p["_id"] for path in PUBLISHED for p in load_json(root / path)}


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest = load_json(cache / "manifest.json") if (cache / "manifest.json").exists() else {}
    for name, url, _, _ in REPORTS.values():
        if name not in manifest:
            fetch_into(cache, name, url, manifest)
            write_json(cache / "manifest.json", manifest)
    for usps in STATES:
        if f"osm-{usps.lower()}.json" not in manifest:
            fetch_osm(cache, usps, manifest)
            write_json(cache / "manifest.json", manifest)


def build(cache: Path) -> dict[Path, object]:
    osm_files = [f"osm-{s.lower()}.json" for s in STATES]
    manifest = verify_cache(cache, [*(r[0] for r in REPORTS.values()), *osm_files])
    facilities = {s: with_aliases(osm_extract(json.loads((cache / f"osm-{s.lower()}.json").read_bytes()), s))
                  for s in STATES}
    osm_names = {(f["id"], f["name"]): f["osm_name"] for fs in facilities.values() for f in fs if "osm_name" in f}
    projects, dispositions = apr.projects(cache, manifest, facilities, STATES, reports=REPORTS, territory=TERRITORY,
                                          operator_keys=OPERATOR_KEYS, transcriptions=OUT / "transcriptions",
                                          published=published_ids(), scope="C51")
    for p in projects:  # an alias match still cites the OSM feature's own name
        for e in p["location_candidate"]["endpoints"]:
            if (f := e.get("facility")) and (f["id"], f["name"]) in osm_names:
                f["osm_name"] = osm_names[(f["id"], f["name"])]
                p["center"]["evidence"] += f" OSM {f['id']} is named “{f['osm_name']}”; “{f['name']}” is its LADWP alias."
    if len({p["_id"] for p in projects}) != len(projects):
        raise SystemExit("project ID repeated within a source")
    projects.sort(key=lambda p: p["_id"])
    sources = []
    for name, url, source_id, publisher in REPORTS.values():
        artifact = manifest[name]
        sources.append({
            "_id": source_id, "publisher": publisher, "title": f"{publisher} 2026 WECC Annual Progress Report",
            "authority": "utility", "role": "project_plan", "landing_url": url, "download_url": artifact["url"],
            "publication_date": None, "vintage": "2026", "retrieved_at": artifact["retrieved_at"],
            "sha256": artifact["sha256"], "public_status": "verified_public", "import_status": "imported",
            "access_policy": "public_document", "planning_region": "WECC",
            "states": sorted({s for p in projects if p["source_id"] == source_id for s in p["states"]}),
            "project_count": sum(p["source_id"] == source_id for p in projects),
            "notes": ["F51 California municipal-utility release (C51): transmission rows transcribed with a page and "
                      "verbatim quote the build re-finds in the PDF; rows F44, F45 or F50 publish are excluded.",
                      "Candidate points are unreviewed C33 exact-name OSM matches with C38's operator guard; a row "
                      "whose text names no place is placed only by a corroborated facility in the owner's territory."]})
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
