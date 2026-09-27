"""Virginia: Dominion Energy's power-line project list (VA, NC, SC) and the Virginia SCC transmission-case list.

From pipeline/:
  uv run python -m southeast.virginia fetch --cache <dir>   # network: 2 list pages, Dominion project pages, OSM
  uv run python -m southeast.virginia build --cache <dir> [--check]
Neither source publishes coordinates. Locations are C40 candidates from facility names in the project title matched to
OSM substations of the reported state(s). A Dominion page's explicit energized/in-service date is the only date read;
an SCC case number's year is a filing year (`source_status`), never a certification or completion.
OSM data (c) OpenStreetMap contributors, ODbL 1.0.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError

from common import REPO_ROOT, load_json, write_json
from greatlakes.aep import page_text
from greatlakes.shared import fetch_into, fetch_osm, osm_extract, utc_now, verify_cache

from .dense import FOLDER, locate, slug, write_batch

BATCH = "virginia"
DOM_ID = "southeast:dominion"
SCC_ID = "southeast:va-scc"
DOM_URL = "https://www.dominionenergy.com/about/delivering-energy/electric-projects/power-line-projects"
SCC_URL = "https://www.scc.virginia.gov/consumers/public-utility/electricity-faqs/transmission-line-projects/"
DOM_PUB = "Dominion Energy"
SCC_PUB = "Virginia State Corporation Commission"
DOM_ACCESS = "Public Dominion Energy website; no login."
SCC_ACCESS = "Public Virginia SCC website; no login."
OSM_STATES = ("VA", "NC", "SC")
FIPS = {"VA": "51", "NC": "37", "SC": "45"}
MAX_PAGES = 150
CASE = re.compile(r"\bPU[ER]-\d{4}-\d{5}\b")


def page_url(raw: str | None) -> str | None:
    """Dominion's own project pages only (the list links http:// URLs; one entry links an outside wind site)."""
    if not raw or "dominionenergy.com/" not in raw.lower():
        return None
    return "https://" + raw.split("://", 1)[1]


def page_file(url: str) -> str:
    return "page--" + slug(url.rsplit("/", 1)[1])[:100] + ".html"


def listings(raw: str) -> dict:
    start = raw.index("{", raw.index("document.projectListings"))
    return json.JSONDecoder().raw_decode(raw[start:])[0]


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest: dict = {}
    fetch_into(cache, "dominion.html", DOM_URL, manifest)
    fetch_into(cache, "scc.html", SCC_URL, manifest)
    rows = [p for r in listings((cache / "dominion.html").read_text("utf-8"))["Regions"] for p in r["Projects"]]
    pages = sorted({u for p in rows if (u := page_url(p["ProjectPageUrl"]))})
    if len(pages) > MAX_PAGES:
        raise SystemExit(f"more than {MAX_PAGES} project pages; review before raising the limit")
    for url in pages:
        try:
            fetch_into(cache, page_file(url), url, manifest)
        except HTTPError as error:
            manifest[page_file(url)] = {"url": url, "http_status": error.code, "retrieved_at": utc_now()}
    for state in OSM_STATES:
        fetch_osm(cache, state, manifest)
    write_json(cache / "manifest.json", manifest)


# --- Dominion project pages -------------------------------------------------------------------------------------
MONTHS = "January February March April May June July August September October November December".split()
_MON = "(" + "|".join(MONTHS) + ")"
_QUAL = r"(?:(?:the )?(?:end of |early[- ]|mid[- ]|late[- ])?(?:spring |summer |fall |autumn |winter )?)"
DATE = _QUAL + "(?:" + _MON + r"\s+(?:(\d{1,2}),?\s+)?)?(20\d\d)\b"
# A date followed by an in-service or completion label, as Dominion's timelines print them: "2031 – In-service",
# "Late 2029 Line in-service", "Late 2025 - Project completion", "June 2028 - SCC approved in service date".
# Not "completion of boardwalk" or "completion of the final phase": that dates a part, not the project.
_LABEL = (r"\s*[-–—:]?\s*(?:SCC approved |anticipated |expected |projected |target(?:ed)? |tentative |estimated )?"
          r"(?:line |project |construction )?(?:in[- ]service|completion|complete|completed|energized)\b(?!\s+of\b)")
PLANNED = [re.compile(DATE + _LABEL, re.I),
           re.compile(r"\b(?:expected|projected|scheduled|anticipated|targeted|planned) to be (?:placed )?(?:in[- ]service"
                      r"|energized|complete|completed)\s+(?:by|in)\s+" + DATE, re.I),
           re.compile(r"\bin[- ]service (?:date )?(?:by|in|of)\s+" + DATE, re.I)]
# Past tense only: "was energized on February 26, 2019", "placed in service in May 2023".
DONE = re.compile(r"\b(?:was |were |been )?(?:energized|placed (?:in|into) service|put (?:in|into) service"
                  r"|went into service)\s+(?:on|in)\s+" + DATE, re.I)


def _when(m: re.Match) -> tuple[str, str]:
    month, day, year = m.group(1), m.group(2), m.group(3)
    if month and day:
        return f"{year}-{MONTHS.index(month.title()) + 1:02d}-{int(day):02d}", "day"
    return (f"{year}-{MONTHS.index(month.title()) + 1:02d}", "month") if month else (year, "year")


def schedule(text: str | None) -> dict | None:
    """The page's one stated in-service/energized date; None when absent or when the page states several years."""
    done = {(*_when(m), m.group(0).strip()) for m in DONE.finditer(text or "")}
    if done:
        if len({d[0] for d in done}) != 1:
            return None
        value, precision, phrase = sorted(done)[0]
        return {"kind": "in_service", "value": value, "precision": precision, "phrase": phrase}
    planned = {(*_when(m), m.group(0).strip()) for rx in PLANNED for m in rx.finditer(text or "")}
    if len({p[0][:4] for p in planned}) != 1:
        return None
    value, precision, phrase = sorted(planned, key=lambda p: (-len(p[0]), p[2]))[0]
    return {"kind": "planned_milestone", "value": value, "precision": precision, "phrase": phrase}


# --- SCC case list ------------------------------------------------------------------------------------------------
class _CaseList(HTMLParser):
    """Accordion panels (region) > utility <li> > case <li>; each case keeps its own text and docket link."""

    def __init__(self) -> None:
        super().__init__()
        self.region: str | None = None
        self.in_title = False
        self.depth = 0
        self.stack: list[dict] = []
        self.pending: list[dict] = []
        self.cases: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        a = dict(attrs)
        if tag == "div" and a.get("class") == "panel--header_title":
            self.in_title, self.region = True, ""
        elif self.region is None:
            return
        elif tag == "ul":
            self.depth += 1
        elif tag == "li":
            self.stack.append({"depth": self.depth, "text": "", "links": []})
        elif tag == "a" and self.stack and a.get("href"):
            self.stack[-1]["links"].append(a["href"])

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self.in_title:
            self.in_title = False
        elif self.region is None:
            return
        elif tag == "ul":
            self.depth -= 1
        elif tag == "li" and self.stack:
            item = self.stack.pop()
            text = re.sub(r"\s+", " ", item["text"].replace("\xa0", " ")).strip()
            if item["depth"] == 2 and CASE.match(text):
                self.pending.append({"region": self.region.strip(), "text": text, "links": item["links"]})
            elif item["depth"] == 1:
                self.cases += [c | {"utility": text} for c in self.pending]
                self.pending = []

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.region += data
        elif self.stack and self.stack[-1]["depth"] == self.depth:
            self.stack[-1]["text"] += data


def scc_cases(raw: str) -> list[dict]:
    parser = _CaseList()
    parser.feed(raw)
    if parser.pending:
        raise ValueError("SCC list: cases outside a utility heading; the page layout changed")
    return parser.cases


# The printed area before the work: counties/cities/towns, or a bare county name ("Goochland - West Creek …").
# "Chesterfield - Lanexa Corridor" is a line between two substations, so Chesterfield is never an area here.
AREA = re.compile(r"^([^–—:−-]*?\b(?:[Cc]ount(?:y|ies)|[Cc]it(?:y|ies)|Town|Goochland)\b[^–—:−-]*?)\s*[-–—:−]\s+(.+)$")


def split_case(text: str) -> dict:
    """"PUR-2026-00076 - Loudoun County - 500 kV Doubs-…" -> case, area (as printed) and the facility text."""
    case = CASE.match(text)[0]
    rest = re.sub(r"^\s*[-–—]\s*", "", text[len(case):]).strip()
    m = AREA.match(rest)
    return {"case": case, "area": m[1].strip() if m else None, "work": (m[2] if m else rest).strip()}


KV_TEXT = re.compile(r"\b[\d.]+(?:\s*[-/]\s*[\d.]+)*\s*-?\s*kV\b", re.I)


def locate_text(text: str) -> str:
    """Voltages moved to a trailing parenthesis: names are read without them, corroboration still sees them."""
    kv = KV_TEXT.findall(text)
    bare = re.sub(r"\s+", " ", KV_TEXT.sub(" ", text)).strip()
    return f"{bare} ({', '.join(kv)})" if kv else bare


# --- build -------------------------------------------------------------------------------------------------------
REGION_STATE = {"VAC": "VA", "VAE": "VA", "VAN": "VA", "VAW": "VA", "NCA": "NC", "SCA": "SC", "SCB": "SC", "SCN": "SC"}
# Dominion's list status labels. "Restoration" (two storm-style rows without pages) and "Other" stay unknown.
STATUS = {"planning": "proposed", "proposed": "proposed", "preconstruction": "planned", "pre-construction": "planned",
          "construction": "under_construction", "under construction": "under_construction", "complete": "in_service"}
# Upper-case fragments of the OSM operator tag per owner. Not bare "DOMINION" (Old Dominion Electric Cooperative) nor
# bare "VIRGINIA ELECTRIC" (Northern/Central Virginia Electric Cooperative).
DOMINION_KEYS = ["DOMINION ENERGY", "DOMINION VIRGINIA", "VIRGINIA ELECTRIC AND POWER", "VIRGINIA ELECTRIC & POWER",
                 "DOMINION NORTH CAROLINA", "SCE&G", "SOUTH CAROLINA ELECTRIC", "SOUTH CAROLINA GAS"]
UTILITY_KEYS = {
    "Dominion Energy Virginia": DOMINION_KEYS,
    "Appalachian Power Company": ["APPALACHIAN POWER", "AMERICAN ELECTRIC POWER", "AEP"],
    "Delmarva Power & Light": ["DELMARVA"],
    "Old Dominion Electric Cooperative": ["OLD DOMINION ELECTRIC"],
    "Kentucky Utilities Company d/b/a Old Dominion Power Company": ["KENTUCKY UTILITIES", "OLD DOMINION POWER"],
    "Central Virginia Electric Cooperative": ["CENTRAL VIRGINIA ELECTRIC"],
    "Non-Utility Projects": [],
}
GENERATION = re.compile(r"\bsolar\b|generating facility", re.I)


def event(pid: str, native: str, kind: str, date: str, precision: str, description: str, evidence: list[dict]) -> dict:
    return {"id": pid + ":" + slug(f"{kind}-{date}"), "type": kind, "date": date, "precision": precision,
            "native_project_link": native, "description": description, "evidence": evidence}


def build(cache: Path) -> dict:
    manifest = load_json(cache / "manifest.json")
    verify_cache(cache, [name for name, row in manifest.items() if "sha256" in row])
    facilities = [f for st in OSM_STATES for f in osm_extract(json.loads((cache / f"osm-{st.lower()}.json").read_bytes()),
                                                                 FIPS[st])]
    dom, scc = manifest["dominion.html"], manifest["scc.html"]
    cases = scc_cases((cache / "scc.html").read_text("utf-8"))
    listed = {split_case(c["text"])["case"]: i for i, c in enumerate(cases)}
    projects: list[dict] = []
    dispositions: list[dict] = []

    def placed(record: dict, text: str, description: str | None, keys: list[str]) -> dict:
        pool = [f for f in facilities if f["state"] in record["states"]]
        center, candidate = locate(locate_text(text), description, pool, keys)
        record |= {"center": center, "location_review": "unreviewed" if center else "unlocated",
                   "location_candidate": candidate | {"located_text": locate_text(text)}}
        return record

    # Dominion: one project per project page (the list repeats a page under a second region or ID).
    regions = listings((cache / "dominion.html").read_text("utf-8"))["Regions"]
    by_key: dict[str, dict] = {}
    for r_index, region in enumerate(regions):
        for p_index, row in enumerate(region["Projects"]):
            title = re.sub(r"\s+", " ", row["ProjectTitle"]).strip()
            locator = f"dominion.html#projectListings.Regions[{r_index}].Projects[{p_index}]"
            where = {"source_id": DOM_ID, "locator": locator, "name": title}
            state = FIPS[REGION_STATE[region["RegionId"]]]
            url = page_url(row["ProjectPageUrl"])
            key = url or f"id:{row['ProjectId'] or slug(title)}"
            if key in by_key:
                first = by_key[key]
                same = title.lower() == first["name"].lower()
                if same:  # the same project listed under a second region: both states are the source's
                    first["states"] = sorted({*first["states"], state})
                first["evidence"]["raw"]["listings"].append({"locator": locator, "region": region["RegionTitle"],
                                                             "row": row})
                dispositions.append(where | {"disposition": "duplicate", "project_id": first["_id"],
                                             "reason": "same project page listed again" + (
                                                 " (another region)" if same else f" under another title; the page is "
                                                 f"{first['name']}'s, so this listing's region is not added")})
                continue
            native = slug(url.rsplit("/", 1)[1]) if url else slug(row["ProjectId"] or title)
            pid = f"{DOM_ID}:{native}"
            page = manifest.get(page_file(url)) if url else None
            text = page_text((cache / page_file(url)).read_bytes().decode("utf-8", "replace")) \
                if page and "sha256" in page else None
            stated = schedule(text)
            cited = sorted(set(CASE.findall(text or "")))
            page_evidence = {"publisher": DOM_PUB, "url": url, "artifact_sha256": page.get("sha256") if page else None,
                             "locator": "project page text", "source_date": None,
                             "retrieved_at": page["retrieved_at"] if page else None, "access_review": DOM_ACCESS}
            events = []
            if stated:
                done = stated["kind"] == "in_service"
                events.append(event(pid, native, stated["kind"], stated["value"], stated["precision"],
                                    f"Dominion's project page states “{stated['phrase']}”."
                                    + ("" if done else " A timeline date as the page states it, not evidence of completion."),
                                    [page_evidence | {"facts": stated["phrase"]}]))
            for case in cited:
                evidence = [page_evidence | {"facts": f"The project page cites SCC Case No. {case}."}]
                if case in listed:
                    evidence.append({"publisher": SCC_PUB, "url": SCC_URL, "artifact_sha256": scc["sha256"],
                                     "locator": f"scc.html case {case}", "source_date": None,
                                     "retrieved_at": scc["retrieved_at"], "access_review": SCC_ACCESS,
                                     "facts": cases[listed[case]]["text"][:400]})
                events.append(event(pid, native, "source_status", case.split("-")[1], "year",
                                    f"SCC case {case} (case number year): a regulatory filing, not a certification "
                                    "or completion.", evidence))
            status = (row["Status"] or "").strip() or None
            group = STATUS.get((status or "").lower(), "unknown")
            if stated and stated["kind"] == "in_service":
                group = "in_service"
            record = {
                "_id": pid, "source_id": DOM_ID, "native_id": native, "name": title,
                "description": (row["Purpose"] or "").strip() or None, "owner": DOM_PUB, "other_owners": [],
                "planning_region": None, "states": [state], "counties": [], "geography_basis": "source_state",
                "status": status, "status_group": group,
                "in_service": ({"raw": stated["phrase"], "value": stated["value"], "precision": stated["precision"]}
                               if stated else {"raw": None, "value": None, "precision": "unknown"}),
                "project_events": events,
                "evidence": {"page": None, "sheet": "dominion.html", "row": None, "source_sha256": dom["sha256"],
                             "raw": {"listings": [{"locator": locator, "region": region["RegionTitle"], "row": row}],
                                     "project_url": url, "page_sha256": page.get("sha256") if page else None,
                                     "page_http_status": page.get("http_status") if page else None,
                                     "scc_cases_cited": cited}},
            }
            by_key[key] = record
            projects.append(record)
            dispositions.append(where | {"disposition": "accepted", "project_id": pid,
                                         "reason": "project listed on Dominion's power-line projects page"})
    for record in projects:
        placed(record, record["name"], record["description"], DOMINION_KEYS)
    dominion_count = len(projects)

    # SCC: a case a Dominion (or AEP) project page cites is that project; any other listed case is its own project.
    # A case cited by several pages goes to the page citing the fewest cases (one Dominion page names a neighbouring
    # project's case in a copied paragraph); the other citing pages are named in the disposition.
    citing: dict[str, list[dict]] = {}
    for record in projects:
        for case in record["evidence"]["raw"]["scc_cases_cited"]:
            citing.setdefault(case, []).append(record)
    cited_by = {case: min(rows, key=lambda r: len(r["evidence"]["raw"]["scc_cases_cited"]))["_id"]
                for case, rows in citing.items()}
    also = {case: [r["_id"] for r in rows if r["_id"] != cited_by[case]] for case, rows in citing.items()}
    aep_file = REPO_ROOT / FOLDER / "aep" / "projects.json"
    for record in load_json(aep_file) if aep_file.exists() else []:
        for case in CASE.findall(json.dumps(record["evidence"]["raw"])):
            cited_by.setdefault(case, record["_id"])
    seen: set[str] = set()
    for index, row in enumerate(cases):
        parts = split_case(row["text"])
        case = parts["case"]
        locator = f"scc.html case list item {index} ({row['region']} / {row['utility']})"
        where = {"source_id": SCC_ID, "locator": locator, "name": row["text"][:200]}
        if case in seen:
            dispositions.append(where | {"disposition": "duplicate", "project_id": f"{SCC_ID}:{case}",
                                         "reason": "same case listed twice"})
            continue
        seen.add(case)
        if case in cited_by:
            dispositions.append(where | {"disposition": "duplicate", "project_id": cited_by[case],
                                         "reason": f"the project's own page cites SCC Case No. {case}"
                                         + (f"; also cited by {', '.join(also[case])}" if also.get(case) else "")})
            continue
        if row["utility"] == "Non-Utility Projects" and GENERATION.search(parts["work"]):
            dispositions.append(where | {"disposition": "excluded", "reason": "generating-facility case (solar plant "
                                         "and its interconnection), not a transmission project"})
            continue
        pid = f"{SCC_ID}:{case}"
        docket = next((link for link in row["links"] if "docketsearch" in link.lower()), None)
        record = {
            "_id": pid, "source_id": SCC_ID, "native_id": case, "name": parts["work"],
            "description": row["text"], "owner": None if row["utility"] == "Non-Utility Projects" else row["utility"],
            "other_owners": [], "planning_region": None, "states": ["51"], "counties": [],
            "geography_basis": "source_state", "status": None, "status_group": "unknown",
            "in_service": {"raw": None, "value": None, "precision": "unknown"},
            "project_events": [event(pid, case, "source_status", case.split("-")[1], "year",
                                     f"SCC case {case} (case number year): a regulatory filing, not a certification "
                                     "or completion.",
                                     [{"publisher": SCC_PUB, "url": SCC_URL, "artifact_sha256": scc["sha256"],
                                       "locator": locator, "source_date": None, "retrieved_at": scc["retrieved_at"],
                                       "access_review": SCC_ACCESS, "facts": row["text"][:400]}])],
            "evidence": {"page": None, "sheet": "scc.html", "row": index + 1, "source_sha256": scc["sha256"],
                         "raw": row | {"area": parts["area"], "docket_link": docket}},
        }
        projects.append(placed(record, parts["work"], None, UTILITY_KEYS[row["utility"]]))
        dispositions.append(where | {"disposition": "accepted", "project_id": pid,
                                     "reason": "case listed on the SCC transmission line projects page"})
    note = ("F39 dense Southeast (C40). No coordinates in the source: points are OSM substation candidates from "
            "facility names in the title, not independently reviewed.")
    sources = [
        {"_id": DOM_ID, "title": "Dominion Energy power line projects", "publisher": DOM_PUB, "authority": "utility",
         "role": "project_plan", "landing_url": DOM_URL, "download_url": DOM_URL, "publication_date": None,
         "vintage": None, "retrieved_at": dom["retrieved_at"], "sha256": dom["sha256"],
         "public_status": "verified_public", "import_status": "imported", "access_policy": "public_document",
         "planning_region": None, "states": sorted({s for p in projects[:dominion_count] for s in p["states"]}),
         "project_count": dominion_count,
         "notes": [note + " Status is the list's own label; dates only from a page's explicit in-service or "
                   "completion statement (one year per page)."]},
        {"_id": SCC_ID, "title": "Virginia SCC transmission line projects", "publisher": SCC_PUB,
         "authority": "state_government", "role": "project_plan", "landing_url": SCC_URL, "download_url": SCC_URL,
         "publication_date": None, "vintage": None, "retrieved_at": scc["retrieved_at"], "sha256": scc["sha256"],
         "public_status": "verified_public", "import_status": "imported", "access_policy": "public_document",
         "planning_region": None, "states": ["51"], "project_count": len(projects) - dominion_count,
         "notes": [note + " A case number's year is a filing year (source_status), never certification or "
                   "completion. Cases a Dominion or AEP project page cites are duplicates of that project."]}]
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
