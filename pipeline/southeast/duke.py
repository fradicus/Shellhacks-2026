"""Duke Energy's transmission-project map (FL, NC, SC, KY): official project points plus project-page schedules.

From pipeline/:
  uv run python -m southeast.duke fetch --cache <dir>   # network: the map's data.json + one page per project
  uv run python -m southeast.duke build --cache <dir> [--check]
Each point is Duke's own map coordinate for the project (C45 `official` tier); placement precision is unstated.
A page's stated expected-completion year is a planned milestone at year precision, never a completion.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin

from common import load_json, write_json
from greatlakes.aep import page_text
from greatlakes.shared import fetch_into, utc_now, verify_cache

from .dense import SE_STATES, official_center, slug, write_batch

BATCH = "duke"
SOURCE_ID = "southeast:duke-transmission-map"
SITE = "https://www.duke-energy.com"
DATA_URL = f"{SITE}/-/media/json/maps/transmission-projects/data.json"
LANDING = f"{SITE}/our-company/about-us/electric-transmission-projects"
PUBLISHER = "Duke Energy"
ACCESS = "Public Duke Energy website; no login."
FIPS = {"FL": "12", "NC": "37", "SC": "45", "KY": "21", "OH": "39", "IN": "18"}
MAX_PAGES = 120
MONTHS = ("January February March April May June July August September October November December").split()
_MONTH = "(" + "|".join(MONTHS) + r")\s+"
_QUAL = r"(?:(?:early|mid|late|spring|summer|fall|autumn|winter|the end of)(?:[- ]to[- ](?:early|mid|late))?[- ]?(?:of )?)?"
# Planned completion as the page labels or states it: "Expected Completion : 2026", "Project completion – Late 2025",
# "In-service Date December 2025", "expected to be completed by mid-2026", "Completion is expected in October 2025".
PLANNED = re.compile(
    r"(?:expected completion|projected project completion date|anticipated completion|project completion expected"
    r"|project completion(?: (?:&|and) restoration)?|project complete|in-service date"
    r"|(?:expected|planned|scheduled|anticipated|targeted) to be (?:completed|complete|in service|energized)"
    r"|completion is expected|completion expected|targeted for)"
    r"\s*[:–—-]?\s*(?:in |by |for )?" + _QUAL + "(?:" + _MONTH + r")?(20\d\d)\b", re.I)
DONE = re.compile(r"\b(?:this|the) project (?:was|has been) completed in " + "(?:" + _MONTH + r")?(20\d\d)\b", re.I)


def states_of(raw: str) -> list[str]:
    return sorted({FIPS[s] for s in raw.split("/") if s in FIPS})


def page_file(url: str) -> str:
    return "page--" + slug(url)[:120] + ".html"


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest: dict = {}
    fetch_into(cache, "data.json", DATA_URL, manifest)
    rows = json.loads((cache / "data.json").read_bytes())["locations"]
    pages = [r["relatedLinks"]["url"] for r in rows
             if set(states_of(r["details"]["state"])) & set(SE_STATES.values()) and r.get("relatedLinks")]
    if len(pages) > MAX_PAGES:
        raise SystemExit(f"more than {MAX_PAGES} project pages; review before raising the limit")
    for path in sorted(set(pages)):
        url = urljoin(SITE, path)
        try:
            fetch_into(cache, page_file(path), url, manifest)
        except HTTPError as error:
            manifest[page_file(path)] = {"url": url, "http_status": error.code, "retrieved_at": utc_now()}
    write_json(cache / "manifest.json", manifest)


def _when(match: re.Match) -> tuple[str, str]:
    month, year = match.group(1), match.group(2)
    return (f"{year}-{MONTHS.index(month.title()) + 1:02d}", "month") if month else (year, "year")


def schedule(text: str | None) -> dict | None:
    """The page's one planned (or past-tense completed) date; None when absent or when phases state several."""
    done = {(*_when(m), m.group(0).strip()) for m in DONE.finditer(text or "")}
    if len({d[0] for d in done}) == 1:
        value, precision, phrase = sorted(done)[0]
        return {"kind": "completion", "value": value, "precision": precision, "phrase": phrase}
    planned = {(*_when(m), m.group(0).strip()) for m in PLANNED.finditer(text or "")}
    if done or len({p[0][:4] for p in planned}) != 1:
        return None
    # Several phrasings of the same year: keep the most precise one.
    value, precision, phrase = sorted(planned, key=lambda p: (p[1] != "month", p[0], p[2]))[0]
    return {"kind": "planned_milestone", "value": value, "precision": precision, "phrase": phrase}


def build(cache: Path) -> dict:
    manifest = load_json(cache / "manifest.json")
    verify_cache(cache, [name for name, row in manifest.items() if "sha256" in row])
    data = manifest["data.json"]
    rows = json.loads((cache / "data.json").read_bytes())["locations"]
    projects, dispositions, seen = [], [], set()
    for index, row in enumerate(rows):
        locator = f"data.json#locations[{index}] (id {row['id']})"
        where = {"source_id": SOURCE_ID, "locator": locator, "name": row["name"]}
        states = states_of(row["details"]["state"])
        if not set(states) & set(SE_STATES.values()):
            dispositions.append(where | {"disposition": "excluded", "reason": f"outside F39 states "
                                         f"({row['details']['state']})"})
            continue
        if row["id"] in seen:
            dispositions.append(where | {"disposition": "duplicate", "project_id": f"{SOURCE_ID}:{row['id']}",
                                         "reason": "same map id listed twice"})
            continue
        seen.add(row["id"])
        pid = f"{SOURCE_ID}:{row['id']}"
        path = (row.get("relatedLinks") or {}).get("url")
        page = manifest.get(page_file(path)) if path else None
        text = page_text((cache / page_file(path)).read_bytes().decode("utf-8", "replace")) \
            if page and "sha256" in page else None
        stated = schedule(text)
        events = []
        if stated:
            done = stated["kind"] == "completion"
            events.append({
                "id": f"{pid}:{'completed' if done else 'expected-completion'}", "type": stated["kind"],
                "date": stated["value"], "precision": stated["precision"], "native_project_link": row["id"],
                "description": f"Duke's project page states “{stated['phrase']}”."
                               + ("" if done else " A planned date, not a completion."),
                "evidence": [{"publisher": PUBLISHER, "url": page["url"], "artifact_sha256": page["sha256"],
                              "locator": "project page schedule text", "source_date": None,
                              "retrieved_at": page["retrieved_at"], "access_review": ACCESS,
                              "facts": stated["phrase"]}]})
        lat, lon = row["coords"]["latitude"], row["coords"]["longitude"]
        projects.append({
            "_id": pid, "source_id": SOURCE_ID, "native_id": row["id"], "name": row["name"],
            "description": "; ".join(row.get("categories") or []) or None, "owner": PUBLISHER, "other_owners": [],
            "planning_region": None, "states": states, "counties": [], "geography_basis": "source_state",
            "status": stated["phrase"] if stated else None,
            "status_group": "in_service" if stated and stated["kind"] == "completion" else "unknown",
            "in_service": ({"raw": stated["phrase"], "value": stated["value"], "precision": stated["precision"]}
                           if stated else {"raw": None, "value": None, "precision": "unknown"}),
            "center": official_center(lat, lon, f"Duke Energy transmission-project map point, {locator}"),
            "location_review": "unreviewed",
            "location_candidate": {"rule": "C45", "tier": "official", "independent_review": False, "kind": "site",
                                   "source_point": {"lat": round(lat, 6), "lon": round(lon, 6)},
                                   "area": row["details"].get("city")},
            "project_events": events,
            "evidence": {"page": None, "sheet": "data.json", "row": index + 1, "source_sha256": data["sha256"],
                         "raw": {**row, "project_url": page["url"] if page else None,
                                 "page_sha256": page.get("sha256") if page else None,
                                 "page_http_status": page.get("http_status") if page else None}},
        })
        dispositions.append(where | {"disposition": "accepted", "project_id": pid,
                                     "reason": "project listed on Duke's transmission-project map"})
    sources = [{
        "_id": SOURCE_ID, "title": "Duke Energy transmission projects map", "publisher": PUBLISHER,
        "authority": "utility", "role": "project_plan", "landing_url": LANDING, "download_url": DATA_URL,
        "publication_date": None, "vintage": None, "retrieved_at": data["retrieved_at"], "sha256": data["sha256"],
        "public_status": "verified_public", "import_status": "imported", "access_policy": "public_document",
        "planning_region": None, "states": sorted({s for p in projects for s in p["states"]}),
        "project_count": len(projects),
        "notes": ["F39 dense Southeast (C45). Points are Duke's own map coordinates (official tier), placement "
                  "precision unstated, not independently reviewed. The map lists no status; pages give schedules "
                  "in prose, read only from an expected-completion statement."]}]
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
