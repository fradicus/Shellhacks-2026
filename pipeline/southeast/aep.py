"""AEP Transmission state project maps for the Southeast (KY, VA, WV, TN, LA, AR): official project markers.

From pipeline/:
  uv run python -m southeast.aep fetch --cache <dir>   # network: 6 map files + one page per project
  uv run python -m southeast.aep build --cache <dir> [--check]
Each marker is AEP's own point for the project on its public map (C40 `official` tier); placement precision is
unstated, so it is never a confirmed location. Page parsing is F40's `greatlakes.aep`, reused by import.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin

from common import load_json, write_json
from greatlakes.aep import FINISHED, FUTURE, PENDING, SEASON, UNDERWAY, describe, page_name, page_text
from greatlakes.shared import fetch_into, utc_now, verify_cache

from .dense import official_center, write_batch

BATCH = "aep"
PREFIX = "southeast:aep"
BASE = "https://www.aeptransmission.com/{}/"
STATES = {"kentucky": "21", "virginia": "51", "westvirginia": "54", "tennessee": "47", "louisiana": "22",
          "arkansas": "05"}
MAX_PAGES = 250
PUBLISHER = "AEP Transmission (American Electric Power)"
ACCESS = "Public AEP Transmission website; no login."


def legend_status(label: str | None) -> str:
    """Each state map labels its own legend colors ("Projects Pending Approval", "Approved Projects", ...)."""
    text = (label or "").lower()
    return "proposed" if "pending" in text else "planned" if "approved" in text or "current" in text else "unknown"


def skip_reason(project: dict, marker: dict) -> str | None:
    if project["name"].strip() == "Projects Overview":
        return "program overview page, not a single project"
    if project["name"].strip().lower().startswith("no active projects") or not -90 <= marker["center"]["lat"] <= 90 \
            or marker["center"]["lat"] < 20:
        return "placeholder marker: no active project"
    return None


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest: dict = {}
    pages = 0
    for state in STATES:
        fetch_into(cache, f"{state}-map-setup.json", BASE.format(state) + "geojson/map-setup.json", manifest)
        setup = json.loads((cache / f"{state}-map-setup.json").read_bytes())
        for marker in setup["markers"].values():
            for project in marker["projects"]:
                if skip_reason(project, marker):
                    continue
                pages += 1
                if pages > MAX_PAGES:
                    raise SystemExit(f"more than {MAX_PAGES} project pages; review before raising the limit")
                url = urljoin(BASE.format(state), project["url"])
                try:
                    fetch_into(cache, page_name(state, project["url"]), url, manifest)
                except HTTPError as error:  # a map entry whose page is gone: keep the map facts, record the miss
                    manifest[page_name(state, project["url"])] = {"url": url, "http_status": error.code,
                                                                  "retrieved_at": utc_now()}
    write_json(cache / "manifest.json", manifest)


def update_event(pid: str, native: str, update: str | None, evidence: dict) -> list[dict]:
    """The newest dated project update as a source_status observation, dated only to the year it names."""
    head = SEASON.match(update or "")
    if not head:
        return []
    return [{"id": f"{pid}:latest-update", "type": "source_status", "date": head[2], "precision": "year",
             "native_project_link": native,
             "description": f"AEP project update headed “{head[0].rstrip(':')}”: {update[head.end():].strip()[:400]}",
             "evidence": [evidence | {"facts": f"Project Updates entry “{head[0].rstrip(':')}”; the page states no "
                                               "exact date."}]}]


def build(cache: Path) -> dict:
    manifest = load_json(cache / "manifest.json")
    verify_cache(cache, [name for name, row in manifest.items() if "sha256" in row])
    projects, dispositions, sources = [], [], []
    by_url: dict[str, dict] = {}
    for state, fips in STATES.items():
        setup_name = f"{state}-map-setup.json"
        artifact = manifest[setup_name]
        setup = json.loads((cache / setup_name).read_bytes())
        legend = {row["toggle"]: row["label"] for row in setup.get("legend", [])}
        source_id = f"{PREFIX}:{state}"
        kept = 0
        for marker_id, marker in sorted(setup["markers"].items(), key=lambda kv: int(kv[0])):
            for project in marker["projects"]:
                locator = f"{setup_name}#markers.{marker_id}"
                name = html.unescape(project["name"]).strip()
                where = {"source_id": source_id, "locator": locator, "name": name}
                if reason := skip_reason(project, marker):
                    dispositions.append(where | {"disposition": "excluded", "reason": reason})
                    continue
                url = urljoin(BASE.format(state), project["url"])
                if url in by_url:  # one project page listed on two state maps: one project, both states
                    first = by_url[url]
                    first["states"] = sorted({*first["states"], fips})
                    dispositions.append(where | {"disposition": "duplicate", "project_id": first["_id"],
                                                 "reason": "same project page listed on another state map"})
                    continue
                native = url.removeprefix("https://www.aeptransmission.com/").strip("/")
                pid = f"{PREFIX}:{native}"
                page = page_name(state, project["url"])
                fetched = "sha256" in manifest[page]
                description, update = describe(page_text((cache / page).read_bytes().decode("utf-8", "replace")),
                                               name) if fetched else (None, None)
                label = legend.get(project.get("fillColor") or marker.get("fillColor"))
                group = legend_status(label)
                sentences = re.split(r"(?<=[.!?])\s+", update or "")
                if any(FINISHED.search(s) and not FUTURE.search(s) for s in sentences) and not PENDING.search(update):
                    group = "in_service"
                elif any(UNDERWAY.search(s) for s in sentences):
                    group = "under_construction"
                lat, lon = marker["center"]["lat"], marker["center"]["lng"]
                page_evidence = {"publisher": PUBLISHER, "url": url, "artifact_sha256": manifest[page].get("sha256"),
                                 "locator": "Project Updates", "source_date": None,
                                 "retrieved_at": manifest[page]["retrieved_at"], "access_review": ACCESS, "facts": "-"}
                record = {
                    "_id": pid, "source_id": source_id, "native_id": native, "name": name,
                    "description": description, "owner": "AEP Transmission", "other_owners": [],
                    "planning_region": None, "states": [fips], "counties": [], "geography_basis": "source_state",
                    "status": "; ".join(x for x in (label, update) if x) or None, "status_group": group,
                    "in_service": {"raw": None, "value": None, "precision": "unknown"},
                    "center": official_center(lat, lon, f"AEP Transmission project-map marker {marker_id} "
                                                         f"({BASE.format(state)}geojson/map-setup.json)"),
                    "location_review": "unreviewed",
                    "location_candidate": {"rule": "C40", "tier": "official", "independent_review": False,
                                           "kind": "site", "marker_id": marker_id,
                                           "source_point": {"lat": round(lat, 6), "lon": round(lon, 6)},
                                           "shared_marker": len(marker["projects"]) > 1, "legend": label},
                    "project_events": update_event(pid, native, update, page_evidence),
                    "evidence": {"page": None, "sheet": setup_name, "row": None, "source_sha256": artifact["sha256"],
                                 "raw": {"marker": marker_id, "project": project, "marker_center": marker["center"],
                                         "project_url": url, "page_sha256": manifest[page].get("sha256"),
                                         "page_http_status": manifest[page].get("http_status"),
                                         "latest_update": update}},
                }
                projects.append(record)
                by_url[url] = record
                kept += 1
                dispositions.append(where | {"disposition": "accepted", "project_id": pid,
                                             "reason": "project listed on AEP's state project map"})
        sources.append({
            "_id": source_id, "title": f"AEP Transmission {state.title()} project map", "publisher": PUBLISHER,
            "authority": "utility", "role": "project_plan", "landing_url": BASE.format(state),
            "download_url": artifact["url"], "publication_date": None, "vintage": None,
            "retrieved_at": artifact["retrieved_at"], "sha256": artifact["sha256"], "public_status": "verified_public",
            "import_status": "imported", "access_policy": "public_document", "planning_region": None,
            "states": [fips], "project_count": kept,
            "notes": ["F39 dense Southeast (C40). Markers are AEP's own project points (official tier), placement "
                      "precision unstated, not independently reviewed. Legend colors are the map's own labels."]})
    return {"projects": projects, "sources": sources, "dispositions": dispositions}


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
