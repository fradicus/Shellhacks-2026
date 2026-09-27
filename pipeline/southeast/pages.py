"""Small official utility project pages: EKPC (KY), FirstEnergy (WV/VA), Georgia Power and Georgia Transmission (GA).

From pipeline/:
  uv run python -m southeast.pages fetch --cache <dir>   # network: index/project pages, EKPC brochures, OSM KY/WV/VA/GA
  uv run python -m southeast.pages build --cache <dir> [--check]
No page publishes coordinates. Locations are C40 candidates from facility names in the project title matched to OSM
substations of the page's state(s). Dates only from a page's own completion/ready-for-service statement: Georgia Power's
and Georgia Transmission's quarterly targets become year-precision planned milestones (quarter kept in the description);
FirstEnergy's "be complete on or about <date>" is a planned milestone even when that date has passed.
OSM data (c) OpenStreetMap contributors, ODbL 1.0.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError

from common import REPO_ROOT, load_json, write_json
from greatlakes.aep import page_text
from greatlakes.firstenergy import status_of
from greatlakes.match import facility_key, voltages_kv
from greatlakes.shared import fetch_into, fetch_osm, osm_extract, utc_now, verify_cache

from .dense import SE_STATES, locate, slug, write_batch

BATCH = "pages"
EKPC_URL = "https://www.ekpc.coop/current-projects"
EKPC_SITE = "https://www.ekpc.coop"
FE_SITE = "https://www.firstenergycorp.com"
FE_STATES = {"westvirginia": "WV", "virginia": "VA"}
GPC_SITE = "https://www.georgiapower.com"
GPC_PATH = "/about/grid-reliability/grid-improvements/grid-projects/transmission-projects"
GTC_PAGES = {"ecrp": "https://www.gatransmission.com/ecrp/",
             "dresden-talbot": "https://www.gatransmission.com/dresden-talbot/"}
OSM_STATES = ("KY", "WV", "VA", "GA")
MAX_PAGES = 40


def fe_index(state: str) -> str:
    return f"fe-{state}.html"


def fe_file(state: str, path: str) -> str:
    return f"fe-{state}--{path.rsplit('/', 1)[1]}"


def gpc_file(path: str) -> str:
    return "gpc--" + path.rsplit("/", 1)[1]


def ekpc_blocks(raw: str) -> list[dict]:
    """EKPC's 'Project summaries' accordion: one title per block, with the block's own text and links."""
    starts = list(re.finditer(r'<article[^>]*class="c-accordion"', raw))
    blocks = []
    for i, m in enumerate(starts):
        chunk = raw[m.start():starts[i + 1].start() if i + 1 < len(starts) else raw.find("</section>", m.end())]
        title = html.unescape(re.search(r'<span class="text">(.*?)</span>', chunk, re.S)[1]).strip()
        body = page_text(chunk[chunk.find("</h3>"):])
        blocks.append({"title": title, "text": body, "links": re.findall(r'href="([^"#]+)"', chunk)})
    return blocks


def ekpc_file(link: str) -> str:
    return "ekpc--" + link.rstrip("/").rsplit("/", 1)[1] + ("" if link.endswith(".pdf") else ".html")


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest: dict = {}
    pages: list[tuple[str, str]] = []
    fetch_into(cache, "ekpc.html", EKPC_URL, manifest)
    for block in ekpc_blocks((cache / "ekpc.html").read_text("utf-8")):
        pages += [(ekpc_file(link), EKPC_SITE + link) for link in block["links"] if link.startswith("/")]
    for state in FE_STATES:
        fetch_into(cache, fe_index(state), f"{FE_SITE}/about/transmission_projects/{state}.html", manifest)
        text = (cache / fe_index(state)).read_text("utf-8", "replace")
        pages += [(fe_file(state, p), FE_SITE + p) for p in
                  sorted(set(re.findall(rf'href="(/about/transmission_projects/{state}/[^"#?]+\.html)"', text)))]
    fetch_into(cache, "gpc.html", f"{GPC_SITE}{GPC_PATH}.html", manifest)
    text = (cache / "gpc.html").read_text("utf-8", "replace")
    pages += [(gpc_file(p), GPC_SITE + p) for p in sorted(set(re.findall(rf'href="({GPC_PATH}/[^"#?]+\.html)"', text)))]
    pages += [(f"gtc-{name}.html", url) for name, url in GTC_PAGES.items()]
    if len(pages) > MAX_PAGES:
        raise SystemExit(f"more than {MAX_PAGES} pages; review before raising the limit")
    for name, url in pages:
        try:
            fetch_into(cache, name, url, manifest)
        except HTTPError as error:
            manifest[name] = {"url": url, "http_status": error.code, "retrieved_at": utc_now()}
    # Overpass often times out: keep a previous run's state extracts (hash-checked at build) and save after each state.
    old = load_json(cache / "manifest.json") if (cache / "manifest.json").exists() else {}
    for state in OSM_STATES:
        name = f"osm-{state.lower()}.json"
        if name in old and (cache / name).exists():
            manifest[name] = old[name]
        else:
            fetch_osm(cache, state, manifest)
        write_json(cache / "manifest.json", manifest)


# --- schedules -----------------------------------------------------------------------------------------------------
MONTHS = "January February March April May June July August September October November December".split()
# FirstEnergy: "Construction … is expected to commence on or about April 2, 2024, and be complete on or about
# October 18, 2024." A planned date as stated, even once passed: the page never says the work was finished.
FE_DATE = re.compile(r"\bbe complete(?:d)? on or about (" + "|".join(MONTHS) + r") (\d{1,2}), (20\d\d)")
# Georgia Power timelines ("Q2 2028 Project complete", "Q4 2027 Project Completion Target") and Georgia Transmission
# ("ready for service Q2 2027", "ready for service by Q4 2031"). Component rows ("Q2 2028 Substation Complete",
# "Line Construction Complete") are not the project's completion and are not read.
GA_DATE = re.compile(r"\bQ([1-4]) (20\d\d) Project (?:complete|completion)(?: target)?\b"
                     r"|\bready for service (?:by |in )?Q([1-4]) (20\d\d)\b", re.I)


def fe_schedule(text: str) -> dict | None:
    """The page's one 'be complete on or about <date>'; None when absent or when it states several."""
    found = {(f"{m[3]}-{MONTHS.index(m[1]) + 1:02d}-{int(m[2]):02d}", m[0]) for m in FE_DATE.finditer(text)}
    if len({f[0] for f in found}) != 1:
        return None
    value, phrase = sorted(found)[0]
    return {"value": value, "precision": "day", "phrase": phrase}


def ga_schedule(text: str) -> dict | None:
    """The page's one quarterly completion/ready-for-service target, kept at year precision (no quarter precision)."""
    found = {(m[2] or m[4], f"Q{m[1] or m[3]} {m[2] or m[4]}", m[0]) for m in GA_DATE.finditer(text)}
    if len({f[1] for f in found}) != 1:
        return None
    year, quarter, phrase = sorted(found)[0]
    return {"value": year, "precision": "year", "quarter": quarter, "phrase": phrase}


# --- facts read from the page text --------------------------------------------------------------------------------
STATE_NAMES = {"Kentucky": "21", "West Virginia": "54", "Virginia": "51", "Maryland": "24", "Georgia": "13",
               "Alabama": "01"}
COUNTY_STATE = re.compile(r"\bCount(?:y|ies),? (West Virginia|Virginia|Maryland|Kentucky|Georgia|Alabama)\b")


def named_states(text: str) -> set[str]:
    """States a page names as '<X> County, <State>' (a project crossing into a neighbouring state)."""
    return {STATE_NAMES[m] for m in COUNTY_STATE.findall(text)}


def fe_body(raw: str) -> str:
    """FirstEnergy page body: after the site menu, up to 'Last Modified'."""
    text = page_text(raw)
    start = text.find("Corporate Responsibility")
    return text[start + len("Corporate Responsibility"):].split("Last Modified")[0].strip() if start >= 0 else ""


def fe_modified(raw: str) -> str | None:
    m = re.search(r"Last Modified: (" + "|".join(MONTHS) + r") (\d{1,2}), (20\d\d)", page_text(raw))
    return f"{m[3]}-{MONTHS.index(m[1]) + 1:02d}-{int(m[2]):02d}" if m else None


def gpc_parts(raw: str) -> tuple[str, str]:
    """Georgia Power page: the <title> project name and the 'About the Project' through timeline text."""
    title = html.unescape(re.search(r"<title>(.*?)</title>", raw, re.S)[1])
    title = re.sub(r"\s+", " ", re.sub(r":\s*What to Know\s*\|\s*Georgia Power\s*$", "", title)).strip()
    text = page_text(raw)
    start = text.find("About the Project")
    end = text.find("Note:", text.find("Project Timeline"))
    return title, text[start:end if end > start else None].strip()


def gtc_items(raw: str) -> list[dict]:
    """Georgia Transmission ECRP 'Project Details': one h4 title and its paragraph per substation or line."""
    return [{"title": re.sub(r"\s+", " ", html.unescape(m[1])).strip(), "text": page_text(m[2])}
            for m in re.finditer(r'<h4 class="item-title">(.*?)</h4>\s*<div class="item-content">(.*?)</div>', raw,
                                 re.S)]


# --- legacy Georgia Power duplicates -------------------------------------------------------------------------------
def endpoints(name: str) -> tuple[frozenset[str], frozenset[int]] | None:
    """Named endpoints before the first voltage ('GTC: DRESDEN - TALBOT 500KV LINE' -> {DRESDEN, TALBOT}, {500})."""
    text = re.sub(r"\([^)]*\)", " ", re.sub(r"^[A-Z]{2,4}:\s*", "", name))
    m = re.search(r"\d[\d./]*\s*-?\s*kV", text, re.I)
    if not m:
        return None
    names = [facility_key(p) for p in re.split(r"\s*[-–—]\s*", text[:m.start()]) if p.strip()]
    return (frozenset(names), frozenset(voltages_kv(text))) if names and all(names) else None


def legacy_twin(name: str, legacy: list[dict]) -> str | None:
    """A legacy Georgia Power record with exactly the same endpoint names and voltages, if exactly one."""
    key = endpoints(name)
    hits = [p["_id"] for p in legacy if key and endpoints(p["name"]) == key]
    return hits[0] if len(hits) == 1 else None


# --- build ---------------------------------------------------------------------------------------------------------
KEYS = {"ekpc": ["EAST KENTUCKY", "EKPC"],
        "fe": ["FIRSTENERGY", "FIRST ENERGY", "MON POWER", "MONONGAHELA", "POTOMAC EDISON", "ALLEGHENY"],
        "gpc": ["GEORGIA POWER", "SOUTHERN"], "gtc": ["GEORGIA TRANSMISSION", "GTC"]}
PUBLISHERS = {"ekpc": "East Kentucky Power Cooperative", "fe": "FirstEnergy", "gpc": "Georgia Power",
              "gtc": "Georgia Transmission Corporation"}
ACCESS = "Public utility website; no login, no CEII banner."
NOTE = ("F39 dense Southeast (C40). No coordinates in the source: points are OSM substation candidates from facility "
        "names in the project title, not independently reviewed.")


def build(cache: Path) -> dict:
    manifest = load_json(cache / "manifest.json")
    verify_cache(cache, [name for name, row in manifest.items() if "sha256" in row])
    facilities = [f for st in OSM_STATES
                  for f in osm_extract(json.loads((cache / f"osm-{st.lower()}.json").read_bytes()), SE_STATES[st])]
    legacy = [p for p in load_json(REPO_ROOT / "data" / "national" / "projects.json")
              if p["_id"].startswith("legacy:GPC:")]
    raw_of = {name: (cache / name).read_bytes().decode("utf-8", "replace") for name, row in manifest.items()
              if "sha256" in row and name.endswith(".html")}
    projects: list[dict] = []
    dispositions: list[dict] = []
    sources: list[dict] = []

    def evidence(pub: str, name: str, locator: str, facts: str, source_date: str | None = None) -> dict:
        row = manifest[name]
        return {"publisher": PUBLISHERS[pub], "url": row["url"], "artifact_sha256": row["sha256"], "locator": locator,
                "source_date": source_date, "retrieved_at": row["retrieved_at"], "access_review": ACCESS,
                "facts": facts[:400]}

    def add(pub: str, source_id: str, index: str, native: str, name: str, located: str, text: str,
            states: set[str], where: dict, raw: dict, stated: dict | None = None, stated_evidence: dict | None = None,
            status: str | None = None, group: str = "unknown") -> dict:
        pid = f"{source_id}:{native}"
        events = []
        if stated:
            quarter = f" (tentative quarter {stated['quarter']}; kept at year precision)" if "quarter" in stated else ""
            events.append({"id": f"{pid}:planned-{slug(stated['value'])}", "type": "planned_milestone",
                           "date": stated["value"], "precision": stated["precision"], "native_project_link": native,
                           "description": f"{PUBLISHERS[pub]}'s page states “{stated['phrase']}”{quarter}. A planned "
                                          "date as the page states it, not evidence of completion.",
                           "evidence": [stated_evidence | {"facts": stated["phrase"]}]})
        pool = [f for f in facilities if f["state"] in states]
        center, candidate = locate(located, text, pool, KEYS[pub])
        record = {
            "_id": pid, "source_id": source_id, "native_id": native, "name": name, "description": text[:1500] or None,
            "owner": PUBLISHERS[pub], "other_owners": [], "planning_region": None, "states": sorted(states),
            "counties": [], "geography_basis": "source_state", "status": status, "status_group": group,
            "in_service": ({"raw": stated["phrase"], "value": stated["value"], "precision": stated["precision"]}
                           if stated else {"raw": None, "value": None, "precision": "unknown"}),
            "center": center, "location_review": "unreviewed" if center else "unlocated",
            "location_candidate": candidate | {"located_text": located}, "project_events": events,
            "evidence": {"page": None, "sheet": index, "row": None, "source_sha256": manifest[index]["sha256"],
                         "raw": raw},
        }
        projects.append(record)
        dispositions.append(where | {"disposition": "accepted", "project_id": pid,
                                     "reason": f"project listed on {PUBLISHERS[pub]}'s project page"})
        return record

    def source(pub: str, source_id: str, index: str, title: str, note: str, states: set[str] = frozenset()) -> None:
        row = manifest[index]
        own = [p for p in projects if p["source_id"] == source_id]
        sources.append({
            "_id": source_id, "title": title, "publisher": PUBLISHERS[pub], "authority": "utility",
            "role": "project_plan", "landing_url": row["url"], "download_url": row["url"], "publication_date": None,
            "vintage": None, "retrieved_at": row["retrieved_at"], "sha256": row["sha256"],
            "public_status": "verified_public", "import_status": "imported", "access_policy": "public_document",
            "planning_region": None, "states": sorted({s for p in own for s in p["states"]} | states),
            "project_count": len(own), "notes": [NOTE + " " + note]})

    # EKPC: one accordion block per project on the current-projects page; brochures/project pages kept as evidence.
    sid = "southeast:ekpc"
    for i, block in enumerate(ekpc_blocks(raw_of["ekpc.html"])):
        locator = f"ekpc.html project summaries block {i + 1}"
        docs = [{"url": manifest[f]["url"], "sha256": manifest[f].get("sha256")} for link in block["links"]
                if link.startswith("/") and (f := ekpc_file(link)) in manifest]
        # The title is the project's name; the work words after the endpoints are not facility names.
        name = re.sub(r"\s+(?:double-circuit )?transmission line(?: & substation)?(?: project)?$", "", block["title"])
        add("ekpc", sid, "ekpc.html", slug(block["title"]), block["title"], name, block["text"], {"21"},
            {"source_id": sid, "locator": locator, "name": block["title"]},
            {"locator": locator, "block_text": block["text"], "documents": docs})
    source("ekpc", sid, "ekpc.html", "East Kentucky Power Cooperative current transmission projects",
           "Brochures give construction windows, not in-service dates, so no date is read.")

    # FirstEnergy: one project per project page; a page listed on both state indexes is one project (WV index first).
    by_page: dict[str, dict] = {}
    for state, abbrev in FE_STATES.items():
        sid, index = f"southeast:firstenergy-{abbrev.lower()}", fe_index(state)
        links = sorted(set(re.findall(rf'href="(/about/transmission_projects/{state}/[^"#?]+\.html)"', raw_of[index])))
        for path in links:
            name, page = path.rsplit("/", 1)[1].removesuffix(".html"), fe_file(state, path)
            where = {"source_id": sid, "locator": f"{index} link {path}", "name": name}
            if page not in raw_of:
                dispositions.append(where | {"disposition": "excluded", "reason": "project page could not be fetched "
                                             f"(HTTP {manifest.get(page, {}).get('http_status')})"})
                continue
            raw = raw_of[page]
            title = html.unescape(re.search(r"<title[^>]*>(.*?)</title>", raw, re.S)[1]).strip()
            body = fe_body(raw)
            if name in by_page:
                first = by_page[name]
                first["states"] = sorted({*first["states"], SE_STATES[abbrev]})
                first["evidence"]["raw"]["also_listed"].append({"index": index, "page": manifest[page]["url"],
                                                                "page_sha256": manifest[page]["sha256"]})
                dispositions.append(where | {"disposition": "duplicate", "project_id": first["_id"],
                                             "reason": f"same project page also listed on the {abbrev} index"})
                continue
            if not body:
                dispositions.append(where | {"disposition": "excluded", "reason": "page body not readable"})
                continue
            stated = fe_schedule(body)
            status = status_of(body)
            by_page[name] = add(
                "fe", sid, index, name, title, title, body, {SE_STATES[abbrev]} | named_states(body), where,
                {"title": title, "page": manifest[page]["url"], "page_sha256": manifest[page]["sha256"],
                 "last_modified": fe_modified(raw), "also_listed": []},
                stated, evidence("fe", page, "project page text", body, fe_modified(raw)),
                status=None if status == "unknown" else status, group=status)
    for abbrev in FE_STATES.values():
        source("fe", f"southeast:firstenergy-{abbrev.lower()}", fe_index(next(k for k, v in FE_STATES.items()
                                                                               if v == abbrev)),
               f"FirstEnergy transmission projects: {abbrev}",
               "Status from the page's own wording; a 'be complete on or about' date is a planned milestone even "
               "when past. A page also listed on another state's index is counted once.")

    # Georgia Power: one project per project page; exact endpoint-name/voltage twins of legacy records are duplicates.
    sid = "southeast:georgia-power"
    for path in sorted(set(re.findall(rf'href="({GPC_PATH}/[^"#?]+\.html)"', raw_of["gpc.html"]))):
        page = gpc_file(path)
        where = {"source_id": sid, "locator": f"gpc.html link {path}", "name": page}
        if page not in raw_of:
            dispositions.append(where | {"disposition": "excluded", "reason": "project page could not be fetched "
                                         f"(HTTP {manifest.get(page, {}).get('http_status')})"})
            continue
        title, text = gpc_parts(raw_of[page])
        stated = ga_schedule(text)
        where["name"] = title
        if twin := legacy_twin(title, legacy):
            dispositions.append(where | {"disposition": "duplicate", "project_id": twin,
                                         "reason": "same endpoint names and voltage as the legacy Georgia Power "
                                         "record" + (f"; this page states “{stated['phrase']}”" if stated else "")})
            continue
        add("gpc", sid, "gpc.html", page.removeprefix("gpc--").removesuffix(".html"), title, title, text,
            {"13"} | named_states(text), where,
            {"title": title, "page": manifest[page]["url"], "page_sha256": manifest[page]["sha256"]},
            stated, evidence("gpc", page, "project page timeline", text))
    source("gpc", sid, "gpc.html", "Georgia Power transmission projects",
           "Timelines are tentative quarters; a 'Project complete(ion)' quarter is a year-precision planned milestone "
           "with the quarter kept in the event description. Pages whose endpoints and voltage equal a legacy "
           "Georgia Power record are that record's duplicates.")

    # Georgia Transmission: ECRP's six substations/lines (one shared ready-for-service target) and Dresden-Talbot.
    sid, index = "southeast:gtc-ecrp", "gtc-ecrp.html"
    stated = ga_schedule(page_text(raw_of[index]))
    if not stated:
        raise ValueError("ECRP page no longer states one ready-for-service quarter; review the page")
    for i, item in enumerate(i for i in gtc_items(raw_of[index]) if re.search(r"\bkV\b", i["title"])):
        name = re.sub(r"\s*\([^)]*\)$", "", item["title"])
        where = {"source_id": sid, "locator": f"{index} Project Details item {i + 1}", "name": item["title"]}
        if twin := legacy_twin(name, legacy):
            dispositions.append(where | {"disposition": "duplicate", "project_id": twin,
                                         "reason": "same facility name and voltage as the legacy Georgia Power record "
                                         "(GTC-owned); the page states all projects “" + stated["phrase"] + "”"})
            continue
        add("gtc", sid, index, slug(name), name, name, item["text"], {"13"}, where,
            {"title": item["title"], "text": item["text"]}, stated,
            evidence("gtc", index, "What To Expect: Next Steps", stated["phrase"]))
    source("gtc", sid, index, "Georgia Transmission East Central Georgia Reliability Projects",
           "The page's one ready-for-service quarter applies to all six projects; kept at year precision.")
    sid, index = "southeast:gtc-dresden-talbot", "gtc-dresden-talbot.html"
    text = page_text(raw_of[index])
    stated = ga_schedule(text)
    name = html.unescape(re.search(r"<title>(.*?)</title>", raw_of[index], re.S)[1]).rsplit("–", 1)[0].strip()
    where = {"source_id": sid, "locator": f"{index} page title", "name": name}
    if twin := legacy_twin(name, legacy):
        dispositions.append(where | {"disposition": "duplicate", "project_id": twin,
                                     "reason": "same endpoint names and voltage as the legacy Georgia Power record "
                                     "(GTC-owned)" + (f"; this page states “{stated['phrase']}”" if stated else "")})
    else:
        add("gtc", sid, index, slug(name), name, name, text[:1500], {"13"}, where, {"title": name}, stated,
            evidence("gtc", index, "What To Expect: Next Steps", stated["phrase"]) if stated else None)
    source("gtc", sid, index, "Georgia Transmission Dresden - Talbot 500 kV Transmission Line", "One project page.",
           {"13"})
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
