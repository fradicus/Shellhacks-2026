"""South Carolina Regional Transmission Planning (SCRTP): DESC's $2M+ project list and Santee Cooper's committed
transmission facilities from every archived SCRTP meeting deck (2013 onward).

From pipeline/ (needs `pdftotext`):
  uv run python -m southeast.scrtp fetch --cache <dir>   # network: DESC list, archive page, decks, OSM SC
  uv run python -m southeast.scrtp build --cache <dir> [--check]
DESC rows whose project ID is already a legacy DESC register ID are duplicates of that record. Santee Cooper rows
carry no IDs: a project is its exact normalized title across decks. A project dropping out of a later deck is not
evidence it was built. Locations are C40 OSM name candidates, never reviewed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from common import REPO_ROOT, load_json, write_json
from greatlakes.shared import fetch_into, fetch_osm, osm_extract, verify_cache

from .dense import locate, slug, write_batch

BATCH = "scrtp"
SITE = "https://www.scrtp.com/"
DESC_URL = f"{SITE}assets/pdfs/home/2026-2030-2million-and-above-project-descriptions.pdf"
ARCHIVE_URL = f"{SITE}meeting-archives.html"
DECK = re.compile(r"assets/pdfs/meeting-archives/scrtp-meeting-(\d{4}-\d{2}-\d{2})-presentation\.pdf")
MAX_DECKS = 80
DESC_KEYS = ["DOMINION", "SOUTH CAROLINA ELECTRIC", "SCE&G", "SCANA"]
SANTEE_KEYS = ["SANTEE COOPER", "SOUTH CAROLINA PUBLIC SERVICE"]
ACCESS = "Public SCRTP website document; no login. SCRTP study reports behind the CEII NDA were not used."
DESC_STATUS = {"in progress": "under_construction", "planned": "planned", "complete": "in_service",
               "completed": "in_service", "in service": "in_service", "cancelled": "cancelled"}
ROW = re.compile(r"^\s*(\S.*?\S)\s{2,}(\d{1,2}/\d{1,2}/\d{2,4})\s*$")


def text_of(path: Path) -> str:
    return subprocess.run(["pdftotext", "-layout", str(path), "-"], check=True, capture_output=True,
                          text=True).stdout


def when(raw: str | None) -> dict:
    """m/d/yy or m/d/yyyy as a day; an impossible calendar date (the source's "04/31/26") stays unknown."""
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})", (raw or "").strip())
    if m:
        year = int(m[3]) + (2000 if len(m[3]) == 2 else 0)
        try:
            return {"raw": raw.strip(), "value": date(year, int(m[1]), int(m[2])).isoformat(), "precision": "day"}
        except ValueError:
            pass
    return {"raw": (raw or "").strip() or None, "value": None, "precision": "unknown"}


def desc_rows(text: str) -> list[dict]:
    """One project per page: title, then labeled Project ID / Description / Need / Status / Planned In-Service Date."""
    rows = []
    for page, block in enumerate(text.split("\f"), start=1):
        if "Project ID" not in block:
            continue
        lines = [line.strip() for line in block.splitlines()]
        head = lines.index("Project ID")
        # The title may wrap: every line between the page banner ("... 5 Year Budget") and "Project ID".
        start = max((i for i, line in enumerate(lines[:head]) if "Budget" in line), default=-1) + 1
        title = " ".join(line for line in lines[start:head] if line)

        def field(label: str, lines: list[str] = lines) -> str | None:
            if label not in lines:
                return None
            start = lines.index(label) + 1
            value = []
            for line in lines[start:]:
                if not line and value:
                    break
                if line:
                    value.append(line)
            return " ".join(value) or None

        rows.append({"page": page, "title": title, "id": field("Project ID"),
                     "description": field("Project Description"), "need": field("Project Need"),
                     "status": field("Project Status"), "date": field("Planned In-Service Date")})
    return rows


def santee_rows(text: str) -> list[dict]:
    """The "Committed Transmission Facilities" table: title and in-service date, until the table ends."""
    if "Santee Cooper" not in text:
        return []
    rows = []
    for page, block in enumerate(text.split("\f"), start=1):
        if "Committed Transmission Facilities" not in block:
            continue
        table = block.split("Committed Transmission Facilities", 1)[1]
        for line in table.splitlines():
            if m := ROW.match(line):
                rows.append({"page": page, "title": " ".join(m[1].split()), "date": m[2]})
    return rows


def site_name(title: str) -> str:
    """DESC titles end in ": <work>" ("Coit – Gills Creek 115kV: Construct"); the facility part precedes it."""
    return re.sub(r"\s*:\s*[^:]*$", "", title).strip() or title


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest: dict = {}
    fetch_into(cache, "desc-2026-2030.pdf", DESC_URL, manifest)
    fetch_into(cache, "meeting-archives.html", ARCHIVE_URL, manifest)
    decks = sorted(set(DECK.findall((cache / "meeting-archives.html").read_text("utf-8", "replace"))))
    if len(decks) > MAX_DECKS:
        raise SystemExit(f"more than {MAX_DECKS} decks; review before raising the limit")
    for day in decks:
        url = f"{SITE}assets/pdfs/meeting-archives/scrtp-meeting-{day}-presentation.pdf"
        try:
            fetch_into(cache, f"deck-{day}.pdf", url, manifest, meeting_date=day)
        except RuntimeError as error:  # over the bounded-fetch size: recorded as a gap, not read
            manifest[f"skipped-{day}"] = {"url": url, "reason": str(error), "meeting_date": day}
    fetch_osm(cache, "SC", manifest)
    write_json(cache / "manifest.json", manifest)


def evidence(artifact: dict, locator: str, facts: str, source_date: str | None = None) -> dict:
    return {"publisher": "South Carolina Regional Transmission Planning (SCRTP)", "url": artifact["url"],
            "artifact_sha256": artifact["sha256"], "locator": locator, "source_date": source_date,
            "retrieved_at": artifact["retrieved_at"], "access_review": ACCESS, "facts": facts}


def build(cache: Path, root: Path = REPO_ROOT) -> dict:
    manifest = verify_cache(cache, [n for n, row in load_json(cache / "manifest.json").items() if "sha256" in row])
    facilities = osm_extract(json.loads((cache / "osm-sc.json").read_bytes()), "SC")
    # The legacy register writes some IDs without spaces ("0167C-D" for "0167 C-D"): compare without whitespace.
    legacy = {re.sub(r"\s", "", p["native_id"]): p["_id"] for p in load_json(root / "data/national/projects.json")
              if p["_id"].startswith("legacy:DESC:")}
    projects, dispositions, sources = [], [], []

    # DESC $2M+ list (one vintage).
    artifact, sid = manifest["desc-2026-2030.pdf"], "southeast:scrtp-desc-2026"
    kept = 0
    for row in desc_rows(text_of(cache / "desc-2026-2030.pdf")):
        where = {"source_id": sid, "locator": f"page {row['page']}", "name": row["title"]}
        native = " ".join((row["id"] or "").split())
        if not native:
            dispositions.append(where | {"disposition": "excluded", "reason": "no project ID on the page"})
            continue
        if re.sub(r"\s", "", native) in legacy:
            dispositions.append(where | {"disposition": "duplicate", "project_id": legacy[re.sub(r"\s", "", native)],
                                         "reason": "same DESC project ID as the legacy DESC register record"})
            continue
        pid = f"{sid}:{slug(native)}"
        center, candidate = locate(site_name(row["title"]), row["description"], facilities, DESC_KEYS)
        in_service = when(row["date"])
        group = DESC_STATUS.get((row["status"] or "").lower(), "unknown")
        ev = evidence(artifact, f"page {row['page']}", f"Planned In-Service Date = {row['date']}")
        projects.append({
            "_id": pid, "source_id": sid, "native_id": native, "name": row["title"],
            "description": row["description"], "owner": "Dominion Energy South Carolina", "other_owners": [],
            "planning_region": "scrtp", "states": ["45"], "counties": [], "geography_basis": "source_state",
            "status": row["status"], "status_group": group, "in_service": in_service,
            "center": center, "location_review": "unreviewed" if center else "unlocated",
            "location_candidate": candidate,
            "project_events": [{"id": f"{pid}:planned-2026-list", "type": "planned_milestone",
                                "date": in_service["value"], "precision": in_service["precision"],
                                "native_project_link": native,
                                "description": f"Planned in-service {row['date']} in DESC's 2026–2030 list.",
                                "evidence": [ev]}] if in_service["value"] else [],
            "evidence": {"page": row["page"], "sheet": None, "row": None, "source_sha256": artifact["sha256"],
                         "raw": row},
        })
        kept += 1
        dispositions.append(where | {"disposition": "accepted", "project_id": pid,
                                     "location": candidate["tier"] or "unlocated"})
    sources.append({
        "_id": sid, "title": "DESC Planned Transmission Projects $2M and above, 2026–2030 (SCRTP)",
        "publisher": "Dominion Energy South Carolina (via SCRTP)", "authority": "utility", "role": "project_plan",
        "landing_url": SITE, "download_url": artifact["url"], "publication_date": None, "vintage": "2026-2030",
        "retrieved_at": artifact["retrieved_at"], "sha256": artifact["sha256"], "public_status": "verified_public",
        "import_status": "imported", "access_policy": "public_document", "planning_region": "scrtp",
        "states": ["45"], "project_count": kept,
        "notes": ["F39 dense Southeast (C40). Rows repeating a legacy DESC register ID are duplicates of it; the "
                  "legacy record keeps its own filing facts. Locations are unreviewed OSM name candidates."]})

    # Santee Cooper committed facilities, every deck. Identity: the exact normalized title. A project's primary
    # source is the deck that last lists it; earlier listings are duplicate rows and dated events.
    decks = sorted(name for name in manifest if name.startswith("deck-"))
    listed: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    per_deck = {}
    for name in decks:
        per_deck[name] = santee_rows(text_of(cache / name))
        for row in per_deck[name]:
            # Owner tags ("(SC)", "(DESC)") vary between decks for the same facility; they are not identity.
            listed[slug(re.sub(r"\([^)]*\)", " ", row["title"]))].append((name, row))
    newest = max(name for name in decks if per_deck[name])
    deck_sid = {name: f"southeast:scrtp-santee-cooper:{manifest[name]['meeting_date']}" for name in decks}
    for key, observations in sorted(listed.items()):
        name, row = observations[-1]
        day, native = manifest[name]["meeting_date"], key[:100]
        pid = f"southeast:scrtp-santee-cooper:{native}"
        for deck, obs in observations:
            last = (deck, obs) == (name, row)
            dispositions.append({"source_id": deck_sid[deck], "locator": f"page {obs['page']}: {obs['title']}",
                                 "name": obs["title"], "disposition": "accepted" if last else "duplicate",
                                 "project_id": pid, "reason": "latest listing" if last else "earlier deck listing"})
        events, previous = [], None
        for deck, obs in observations:
            value = when(obs["date"])
            if value["value"] is None or value["value"] == previous:
                continue
            previous = value["value"]
            events.append({"id": f"{pid}:{manifest[deck]['meeting_date']}", "type": "planned_milestone",
                           "date": value["value"], "precision": "day", "native_project_link": native,
                           "description": f"In-service {obs['date']} in the {manifest[deck]['meeting_date']} "
                                          "SCRTP deck's committed transmission facilities.",
                           "evidence": [evidence(manifest[deck], f"page {obs['page']}",
                                                 f"{obs['title']} — {obs['date']}", manifest[deck]["meeting_date"])]})
        current = name == newest
        center, candidate = locate(row["title"], None, facilities, SANTEE_KEYS)
        projects.append({
            "_id": pid, "source_id": deck_sid[name], "native_id": native, "name": row["title"], "description": None,
            "owner": "Santee Cooper", "other_owners": [], "planning_region": "scrtp", "states": ["45"],
            "counties": [], "geography_basis": "source_state",
            "status": "Committed transmission facility" if current else
            f"Last listed as committed in the {day} deck; not listed in later decks (not evidence of completion)",
            "status_group": "planned" if current else "unknown", "in_service": when(row["date"]),
            "center": center, "location_review": "unreviewed" if center else "unlocated",
            "location_candidate": candidate, "project_events": events,
            "evidence": {"page": row["page"], "sheet": None, "row": None, "source_sha256": manifest[name]["sha256"],
                         "raw": row | {"deck": name,
                                       "listed_in": [manifest[d]["meeting_date"] for d, _ in observations]}},
        })
    for name in decks:
        if not per_deck[name]:
            continue
        artifact = manifest[name]
        sources.append({
            "_id": deck_sid[name], "title": f"SCRTP stakeholder meeting {artifact['meeting_date']}: Santee Cooper "
                                            "committed transmission facilities",
            "publisher": "South Carolina Regional Transmission Planning (SCRTP)",
            "authority": "regional_planning_organization", "role": "project_plan", "landing_url": ARCHIVE_URL,
            "download_url": artifact["url"], "publication_date": artifact["meeting_date"],
            "vintage": artifact["meeting_date"], "retrieved_at": artifact["retrieved_at"],
            "sha256": artifact["sha256"], "public_status": "verified_public", "import_status": "imported",
            "access_policy": "public_document", "planning_region": "scrtp", "states": ["45"],
            "project_count": sum(p["source_id"] == deck_sid[name] for p in projects),
            "notes": ["F39 dense Southeast (C40). Titles carry no IDs; one project per exact normalized title across "
                      "decks. Dropping out of a later deck is not evidence of completion."]})
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
