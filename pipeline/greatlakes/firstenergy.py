"""FirstEnergy transmission project pages (Ohio, Pennsylvania) -> national-project records with C26 candidates.

From pipeline/:
  uv run python -m greatlakes.firstenergy fetch --cache /tmp/gl-cache-fe   # network: 2 index pages + one per project
  uv run python -m greatlakes.firstenergy build --cache /tmp/gl-cache-fe [--check]
Pages state the project, owning subsidiary, counties and often a siting-board case; no coordinates. Candidates come
from the endpoint/site names in the title, matched to OSM substations in the page's state.
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
from .shared import fetch_into, locate, verify_cache, write_outputs

SOURCE_ID = "firstenergy-transmission-projects"
SITE = "https://www.firstenergycorp.com"
STATES = {"ohio": ("OH", "39", "Ohio"), "pennsylvania": ("PA", "42", "Pennsylvania")}
MAX_PAGES = 120
DATASET = "OpenStreetMap (ODbL), data/greatlakes/osm/{oh,pa}-substations.json"
OWNERS = ["American Transmission Systems", "Mid-Atlantic Interstate Transmission", "Trans-Allegheny Interstate Line",
          "Pennsylvania Electric Company", "Metropolitan Edison", "West Penn Power", "Penelec", "Met-Ed",
          "FirstEnergy Pennsylvania Electric Company", "Ohio Edison", "Toledo Edison", "Cleveland Electric Illuminating"]
OPERATOR_KEYS = ["FIRSTENERGY", "FIRST ENERGY", "ATSI", "AMERICAN TRANSMISSION SYSTEMS", "OHIO EDISON", "TOLEDO EDISON",
                 "CLEVELAND ELECTRIC", "PENELEC", "PENNSYLVANIA ELECTRIC", "MET-ED", "METROPOLITAN EDISON",
                 "WEST PENN", "MID-ATLANTIC INTERSTATE", "MAIT", "ILLUMINATING"]


def page_name(path: str) -> str:
    return path.strip("/").replace("/", "--")


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest: dict = {}
    pages = 0
    for state in STATES:
        index = f"/about/transmission_projects/{state}.html"
        fetch_into(cache, page_name(index), SITE + index, manifest)
        text = (cache / page_name(index)).read_text(encoding="utf-8", errors="replace")
        for path in sorted(set(re.findall(rf'href="(/about/transmission_projects/{state}/[^"#?]+\.html)"', text))):
            pages += 1
            if pages > MAX_PAGES:
                raise SystemExit(f"more than {MAX_PAGES} project pages; review before raising the limit")
            fetch_into(cache, page_name(path), SITE + path, manifest)
    write_json(cache / "manifest.json", manifest)


def read_page(raw: str) -> tuple[str | None, str]:
    """The page's <title> and the body text between it and 'Project Documents'."""
    h1 = re.search(r"<title[^>]*>(.*?)</title>", raw, re.S)
    title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h1[1]))).strip() if h1 else None
    body = re.sub(r"<!--.*?-->|<(script|style|nav|footer|header)\b.*?</\1>", " ", raw, flags=re.S)
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body))).strip()
    if title and title in text:
        text = text[text.rfind(title) + len(title):]
    return title, text.split("Project Documents")[0].split("Last Modified")[0].strip()[:2000]


def status_of(text: str) -> str:
    if re.search(r"construction (?:is|was) (?:now )?complete|placed in(?:-| )service|energized", text, re.I):
        return "in_service"
    if re.search(r"construction (?:is|remains) (?:currently )?(?:underway|ongoing)|under construction", text, re.I):
        return "under_construction"
    return "proposed" if re.search(r"\bpropos", text, re.I) else "unknown"


def build(cache: Path) -> dict:
    manifest = load_json(cache / "manifest.json")
    verify_cache(cache, list(manifest))
    geography = load_json(REPO_ROOT / "data" / "national" / "geography.json")
    projects, dispositions = [], []
    for state, (abbrev, fips, state_name) in STATES.items():
        counties = {c["name"]: c["county_geoid"] for c in geography["counties"] if c["county_geoid"].startswith(fips)}
        facilities = osm_data.load([abbrev])
        prefix = page_name(f"/about/transmission_projects/{state}/") + "--"
        for name in sorted(k for k in manifest if k.startswith(prefix)):
            raw = (cache / name).read_bytes().decode("utf-8", "replace")
            title, text = read_page(raw)
            native = f"{abbrev}:{name.removeprefix(prefix).removesuffix('.html')}"
            locator = manifest[name]["url"]
            if not title:
                dispositions.append({"native_id": native, "locator": locator, "disposition": "rejected",
                                     "reason": "page has no project title"})
                continue
            case = re.search(r"Case No\.?\s*([0-9]{2}-[0-9]{4}-EL-[A-Z]{3})", f"{title} {text}")
            clean_title = re.sub(r"\s*[-–]\s*Case No\..*$", "", title)
            owner = next((o for o in OWNERS if o in text), None)
            named_counties = re.findall(rf"([A-Z][a-z]+(?: [A-Z][a-z]+)?) Count(?:y|ies),? {state_name}", text)
            center, candidate = locate(clean_title, text, facilities, OPERATOR_KEYS, voltages_kv(title, text), DATASET)
            project = {
                "_id": f"{SOURCE_ID}:{native}", "source_id": SOURCE_ID, "native_id": native, "name": clean_title,
                "description": text or None, "owner": owner, "other_owners": [], "planning_region": None,
                "states": [fips], "counties": sorted({counties[c] for c in named_counties if c in counties}),
                "geography_basis": "source_state", "status": None, "status_group": status_of(text),
                "in_service": {"raw": None, "value": None, "precision": "unknown"},
                "center": center, "location_review": "unreviewed" if center else "unlocated",
                "location_candidate": candidate, "siting_case": case[1] if case else None,
                "evidence": {"page": None, "sheet": locator, "row": None,
                             "raw": {"title": title, "source_url": locator, "source_sha256": manifest[name]["sha256"]}},
            }
            validate(project, "national-project")
            projects.append(project)
            dispositions.append({"native_id": native, "locator": locator, "disposition": "accepted",
                                 "reason": f"project page listed on FirstEnergy's {state_name} transmission projects"})
    projects.sort(key=lambda p: p["_id"])
    sources = [{"_id": SOURCE_ID, "publisher": "FirstEnergy Corp.",
                "title": "FirstEnergy transmission projects: Ohio and Pennsylvania pages",
                "vintage": "live site, retrieved date", "rights": "Public website; FirstEnergy terms of use",
                "artifacts": [{"file": k} | v for k, v in sorted(manifest.items())]}]
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
    return write_outputs("firstenergy", build(args.cache), args.check)


if __name__ == "__main__":
    sys.exit(main())
