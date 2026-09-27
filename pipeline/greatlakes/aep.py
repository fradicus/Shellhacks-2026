"""AEP Transmission project maps (OH, IN, MI): utility-published project markers and project pages.

From pipeline/:
  uv run python -m greatlakes.aep fetch --cache /tmp/gl-cache-aep   # network: 3 map files + one page per project
  uv run python -m greatlakes.aep build --cache /tmp/gl-cache-aep [--check]
Each marker is AEP's own point for the project on its public map; placement precision is unstated, so the point is an
unverified candidate (basis source_point), never a confirmed location. Several projects can share one marker.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

from common import load_json, validate, write_json

from .shared import fetch_into, verify_cache, write_outputs

SOURCE_ID = "aep-transmission-projects"
BASE = "https://www.aeptransmission.com/{}/"
STATES = {"ohio": "39", "indiana": "18", "michigan": "26"}
MAX_PAGES = 250
LEGEND = {"yellow": ("Projects Pending Regulatory Approval", "proposed"),
          "green": ("Regulatory Approved & Additional Projects", "planned")}
UNDERWAY = re.compile(r"construction (?:is|remains) (?:currently |now )?(?:underway|ongoing|in progress)|construction "
                      r"continues|crews (?:have )?(?:began|begun)|began construction", re.I)
FINISHED = re.compile(r"construction is (?:now )?complete|completed construction|placed (?:it |the \w+ |them )?in(?:-| )"
                      r"service|(?:is|was) now in(?:-| )service", re.I)
FUTURE = re.compile(r"expect|will|anticipat|plan|schedul", re.I)
# Work not yet started elsewhere in the project: a partial completion does not make the project in service.
PENDING = re.compile(r"prepare for construction|construction (?:is )?(?:scheduled|expected|planned) to begin|will begin"
                     r"|begins in", re.I)
SEASON = re.compile(r"(Spring|Summer|Fall|Autumn|Winter|January|February|March|April|May|June|July|August|September|"
                    r"October|November|December|Early|Late|Mid)[- ]?(?:\w+ )?(20\d\d):", re.I)


def page_name(state: str, url: str) -> str:
    return f"{state}--{url.strip('/').replace('/', '_')}.html"


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest: dict = {}
    pages = 0
    for state in STATES:
        fetch_into(cache, f"{state}-map-setup.json", BASE.format(state) + "geojson/map-setup.json", manifest)
        setup = json.loads((cache / f"{state}-map-setup.json").read_bytes())
        for marker in setup["markers"].values():
            for project in marker["projects"]:
                pages += 1
                if pages > MAX_PAGES:
                    raise SystemExit(f"more than {MAX_PAGES} project pages; review before raising the limit")
                fetch_into(cache, page_name(state, project["url"]), BASE.format(state) + project["url"], manifest)
    write_json(cache / "manifest.json", manifest)


def page_text(raw: str) -> str:
    raw = re.sub(r"<!--.*?-->|<(script|style|nav|footer|header)\b.*?</\1>", " ", raw, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


def describe(text: str, name: str) -> tuple[str | None, str | None]:
    """The project's description paragraph and its newest dated update, as the page states them."""
    body = text[text.rfind(name) + len(name):] if name in text else text
    description = body.split("Project Updates")[0].split("Project Releases")[0].strip()[:1500] or None
    update = None
    if "Project Updates" in body:
        updates = body.split("Project Updates", 1)[1]
        first = SEASON.search(updates)
        if first:
            rest = updates[first.start():]
            nxt = SEASON.search(rest, first.end() - first.start())
            update = rest[: nxt.start() if nxt else 600].strip()[:600]
    return description, update


def build(cache: Path) -> dict:
    manifest = load_json(cache / "manifest.json")
    verify_cache(cache, list(manifest))
    projects, dispositions = [], []
    by_url: dict[str, dict] = {}
    for state, fips in STATES.items():
        setup_name = f"{state}-map-setup.json"
        setup = json.loads((cache / setup_name).read_bytes())
        for marker_id, marker in sorted(setup["markers"].items(), key=lambda kv: int(kv[0])):
            for project in marker["projects"]:
                url = urljoin(BASE.format(state), project["url"])
                if url in by_url:  # the same project page listed on another state's map: one project, both states
                    first = by_url[url]
                    first["states"] = sorted({*first["states"], fips})
                    dispositions.append({"native_id": first["native_id"], "locator": f"{setup_name}#markers.{marker_id}",
                                         "disposition": "duplicate", "reason": f"same project page as {first['_id']}"})
                    continue
                native = url.removeprefix("https://www.aeptransmission.com/").strip("/")
                page = page_name(state, project["url"])
                name = html.unescape(project["name"]).strip()
                description, update = describe(page_text((cache / page).read_bytes().decode("utf-8", "replace")), name)
                legend, group = LEGEND.get(project.get("fillColor") or marker.get("fillColor"), (None, "unknown"))
                # Only a plain past/present statement in the newest update changes the legend's status.
                sentences = re.split(r"(?<=[.!?])\s+", update or "")
                if any(FINISHED.search(s) and not FUTURE.search(s) for s in sentences) and not PENDING.search(update):
                    group = "in_service"
                elif any(UNDERWAY.search(s) for s in sentences):
                    group = "under_construction"
                lat, lon = marker["center"]["lat"], marker["center"]["lng"]
                center = {"lat": round(lat, 6), "lon": round(lon, 6), "basis": "source_point",
                          "evidence": f"Official source: AEP Transmission project-map marker {marker_id} "
                                      f"({BASE.format(state)}geojson/map-setup.json); placement precision unstated; "
                                      "not independently reviewed."}
                record = {
                    "_id": f"{SOURCE_ID}:{native}", "source_id": SOURCE_ID, "native_id": native, "name": name,
                    "description": description, "owner": "AEP Transmission", "other_owners": [],
                    "planning_region": None, "states": [fips],
                    "counties": [], "geography_basis": "source_state",
                    "status": "; ".join(x for x in (legend, update) if x) or None, "status_group": group,
                    "in_service": {"raw": None, "value": None, "precision": "unknown"},
                    "center": center, "location_review": "unreviewed",
                    "location_candidate": {"rule": "C25 official source", "kind": "site",
                                           "marker_id": marker_id, "shared_marker": len(marker["projects"]) > 1,
                                           "latest_update": update, "legend": legend},
                    "evidence": {"page": None, "sheet": setup_name, "row": None,
                                 "raw": {"marker": marker_id, "project": project, "marker_center": marker["center"],
                                         "project_url": url,
                                         "map_sha256": manifest[setup_name]["sha256"],
                                         "page_sha256": manifest[page]["sha256"]}},
                }
                validate(record, "national-project")
                projects.append(record)
                by_url[url] = record
                dispositions.append({"native_id": native, "locator": f"{setup_name}#markers.{marker_id}",
                                     "disposition": "accepted", "reason": "project listed on AEP's state project map"})
    projects.sort(key=lambda p: p["_id"])
    sources = [{"_id": SOURCE_ID, "publisher": "AEP Transmission (American Electric Power)",
                "title": "AEP Transmission state project maps and project pages (Ohio, Indiana, Michigan)",
                "vintage": "live site, retrieved date", "rights": "Public website; AEP terms of use",
                "note": "Legend colors: yellow = pending regulatory approval, green = regulatory approved & additional "
                        "projects. Marker coordinates are AEP's; their placement method is not stated.",
                "artifacts": [{"file": k} | v for k, v in sorted(manifest.items()) if k.endswith("map-setup.json")],
                "project_pages": len([k for k in manifest if k.endswith(".html")])}]
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
    return write_outputs("aep", build(args.cache), args.check)


if __name__ == "__main__":
    sys.exit(main())
