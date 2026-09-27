"""SERTP expansion plans (Southern, TVA, Duke, LG&E/KU, AECI Balancing Authority Areas): current projects + history.

From pipeline/:
  uv run python -m southeast.sertp fetch --cache <dir>   # network: four SERTP PDFs + OSM substations of ten states
  uv run python -m southeast.sertp build --cache <dir> [--check]
The 2025 Preliminary Expansion Plan Report (Non-CEII) is the current edition. Older editions (2023 final, 2024
preliminary, 2024 final) only add `planned_milestone` events to a current project whose name they repeat exactly;
the 2025 report renamed most projects, so an older row without that exact link is excluded, never a project of its
own (a dropout cannot be told from a rename, and neither means built). D15 still excludes the 2026 preliminary
report; the 2025 final plan carries "(CEII)" page headings and is not used (specs/decisions/F39-sertp-editions.md).
Rows give no state: each Balancing Authority Area's footprint states are matched together, and a project's states
come from its matched OSM or HIFLD facility. A Southern row naming the same place as exactly one legacy Georgia Power
project (legacy:GPC:*) is recorded as that project's duplicate, not a new project.
OSM data (c) OpenStreetMap contributors, ODbL 1.0.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import quote

from california.caiso import match, named
from common import REPO_ROOT, load_json, write_json
from greatlakes.match import DUPLICATE_METERS, _meters, candidate_center, facility_key, voltages_kv
from greatlakes.shared import fetch_into, fetch_osm, osm_extract, verify_cache

from .dense import SE_STATES, locate, slug, write_batch
from .hifld import load as load_hifld

BATCH = "sertp"
PREFIX = "southeast:sertp"
SITE = "https://www.southeasternrtp.com/"
LANDING = SITE + "archive.cshtml"
PUBLISHER = "Southeastern Regional Transmission Planning (SERTP)"
ACCESS = ("Public SERTP archive PDF, no login; 'CEII' appears only in disclaimer sentences (no CEII page marking), "
          "checked at build.")
# Oldest first; the last edition is current.
EDITIONS = {
    "2023-final": ("2023 SERTP Regional Transmission Plan and Input Assumptions",
                   "docs/general/2023/2023_SERTP_Regional_Transmission_Plan_and_Input_Assumptions.pdf"),
    "2024-preliminary": ("2024 SERTP Preliminary Expansion Plan Report (Non-CEII)",
                         "docs/general/2024/2024_SERTP_Preliminary_Expansion_Plan_Report_(Non-CEII).pdf"),
    "2024-final": ("2024 SERTP Regional Transmission Plan and Input Assumptions",
                   "docs/general/2024/2024_Regional_Transmission_Plan_and_Input_Assumptions.pdf"),
    "2025-preliminary": ("2025 SERTP Preliminary Expansion Plan Report (Non-CEII)",
                         "docs/general/2025/2025 SERTP Preliminary Expansion Plan Report (Non-CEII).pdf"),
}
CURRENT = "2025-preliminary"
# Legacy Georgia Power register already in the national snapshot; a SERTP row naming the same place is a duplicate.
LEGACY = Path("data/national/projects.json")
# Editions checked but not ingested (specs/decisions/F39-sertp-editions.md): file, sha256, CEII lines, markings, verdict.
NOT_INGESTED = [
    ("2025 Regional Transmission Plan and Input Assumptions.pdf",
     "9183e3ffcb4fc06e46db2afc50510948b6c0f950312440b6272aaa862bc9da6b", 319, 194,
     "fail: \"TRANSMISSION PROJECTS (CEII)\" page headings"),
    ("2022_Regional_Transmission_Plan_and_Input_Assumptions_Final_Non-CEII.pdf",
     "bf4fbdfbb9d8f98143aab1882c8c6c7cf24873c9db62940bcf06c64564bcd80f", 5, 0,
     "pass (disclaimer only); not used: different page layout"),
    ("2021-Regional-Transmission-Plan-and-Input-Assumptions-Non-CEII.pdf",
     "679d4f16333ebfbc3d4563edb4b3a4730c41c5aeec5d333687c19c6a7611af85", 5, 0,
     "pass (disclaimer only); not used: older than the linked history"),
    ("2026 SERTP preliminary expansion report", None, None, None, "excluded by D15; not downloaded"),
]
# Reported area per Balancing Authority Area (the report's section heading); only F39 states are matched.
FOOTPRINT = {
    "SOUTHERN": ["GA", "AL", "MS", "FL"], "SOCO": ["GA", "AL", "MS", "FL"], "POWERSOUTH": ["AL", "FL"],
    "TVA": ["TN", "AL", "MS", "KY", "GA", "NC", "VA"], "LG&E/KU": ["KY"], "AECI": ["AR"],
    "DUKE CAROLINAS": ["NC", "SC"], "DUKE PROGRESS EAST": ["NC", "SC"], "DUKE PROGRESS WEST": ["NC"],
}
SOUTHERN_KEYS = ["GEORGIA POWER", "ALABAMA POWER", "MISSISSIPPI POWER", "GULF POWER", "SOUTHERN", "GEORGIA TRANSMISSION",
                 "MEAG", "MUNICIPAL ELECTRIC AUTHORITY", "OGLETHORPE", "DALTON", "POWERSOUTH"]
OPERATOR_KEYS = {
    "SOUTHERN": SOUTHERN_KEYS, "SOCO": SOUTHERN_KEYS, "POWERSOUTH": ["POWERSOUTH"],
    "TVA": ["TENNESSEE VALLEY", "TVA"], "LG&E/KU": ["LOUISVILLE GAS", "KENTUCKY UTILITIES", "LG&E", "LGE", "PPL"],
    "AECI": ["ASSOCIATED ELECTRIC", "AECI"], "DUKE CAROLINAS": ["DUKE"], "DUKE PROGRESS EAST": ["DUKE", "PROGRESS"],
    "DUKE PROGRESS WEST": ["DUKE", "PROGRESS"],
}
OSM_STATES = sorted({s for states in FOOTPRINT.values() for s in states})

HEAD = re.compile(r"^\s+(\S.*?) (?:Balancing|Planning) Authority Area\s*$")
FIELD = re.compile(r"^\s*(In-Service|Year:|Project Name:|Description:|Supporting|Statement:)\s*(.*)$")
# Page footers, alone or after a block's last line: "Revised 06/24/2024      Page 18 of 87".
FOOTER = re.compile(r"\s*(?:Revised \d\d/\d\d/\d{4})?\s*Page \d+ of \d+\s*$")
# Tags before the facility names: "GTC:", "MEAG:", "DU:", "PS:" name the owner as reported; "SAV:", "GRID:",
# "CC - " and "GRID - " are area/program tags.
OWNER_TAG = re.compile(r"^([A-Z&]{2,6}):\s*")
OWNERS = {"GTC", "MEAG", "DU", "PS"}
PROGRAM_TAG = re.compile(r"^(?:CC|GRID)\s*-\s*")
# The 2025 edition's trailing work phrase: "…TRANSMISSION LINE, REBUILD", "…, SWITCH, JUMPER, AND LINE TRAP REPLACEMENT".
ACTION = re.compile(r",[^,]*$")


def pdf_text(path: Path) -> str:
    return subprocess.run(["pdftotext", "-layout", str(path), "-"], check=True, capture_output=True,
                          text=True).stdout


def ceii_markings(text: str) -> tuple[int, list[str]]:
    """Lines naming CEII, and those that mark content as CEII (an all-caps heading, or a line ending "(CEII)")
    rather than disclaimer prose ("…does not include Critical Energy Infrastructure Information (CEII) materials")."""
    lines = [line.strip() for line in text.split("\n") if "CEII" in line]
    return len(lines), [line for line in lines if not re.search(r"[a-z]", line) or line.endswith("(CEII)")]


def parse(text: str) -> list[dict]:
    """Each project block: section (BAA), PDF page, In-Service Year, Project Name, Description, Supporting Statement."""
    rows: list[dict] = []
    baa, row, field = None, None, None
    for page, body in enumerate(text.split("\f"), start=1):
        field = None  # a page break ends the open field; blocks never continue onto the next page
        for line in body.split("\n"):
            line = FOOTER.sub("", line)
            if m := HEAD.match(line):
                baa, field = m[1].strip().upper(), None
                continue
            if "SERTP TRANSMISSION PROJECTS" in line or not line.strip() or line.strip().isdigit():
                continue
            if m := FIELD.match(line):
                key, value = m[1], m[2].strip()
                if key == "In-Service":
                    row = {"baa": baa, "page": page, "year": value, "name": "", "description": "", "support": ""}
                    rows.append(row)
                    field = "year"
                    continue
                field = {"Year:": "year", "Project Name:": "name", "Description:": "description",
                         "Supporting": "support", "Statement:": "support"}[key]
                if not value:
                    continue
            elif row is None or field in (None, "year"):
                continue
            else:
                value = line.strip()
            row[field] = row[field] + value if field == "year" else f"{row[field]} {value}".strip()
    for row in rows:
        row["name"] = re.sub(r"\s+", " ", row["name"])
    return rows


def key_of(baa: str, name: str) -> str:
    """Cross-edition identity: same BAA and the same name up to spacing, punctuation and "115KV"/"115 KV"."""
    baa = "SOUTHERN" if baa == "SOCO" else baa
    text = re.sub(r"(\d)\s*KV\b", r"\1 KV", name.upper())
    return f"{baa}|" + " ".join(re.findall(r"[A-Z0-9#/]+", text))


def links(old: list[dict], new: list[dict]) -> dict[int, int]:
    """Old row -> current row: exact key, else the current name without its ", ACTION" phrase; one-to-one only."""
    out: dict[int, int] = {}
    for strip in (False, True):
        index: dict[str, list[int]] = {}
        for j, r in enumerate(new):
            name = ACTION.sub("", r["name"]) if strip else r["name"]
            index.setdefault(key_of(r["baa"], name), []).append(j)
        old_keys = Counter(key_of(r["baa"], r["name"]) for r in old)
        for i, r in enumerate(old):
            k = key_of(r["baa"], r["name"])
            hits = index.get(k, [])
            if i not in out and len(hits) == 1 and old_keys[k] == 1 and hits[0] not in out.values():
                out[i] = hits[0]
    return out


def locate_name(name: str) -> str:
    """The name as a facility phrase: program/owner tags and the trailing work phrase removed, title case."""
    text = PROGRAM_TAG.sub("", OWNER_TAG.sub("", name))
    # "TIGER CREEK -WARTHEN": a one-sided dash still separates terminals (else a third terminal hides in a name).
    text = re.sub(r"(?<=\w) -(?=\w)|(?<=\w)- (?=\w)", " - ", text)
    text = ACTION.sub("", text) if "," in text else text
    small = {"To": "to", "And": "and", "Of": "of", "At": "at", "The": "the", "Kv": "kV"}
    return " ".join(small.get(w, w) for w in text.title().split())


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest = load_json(cache / "manifest.json") if (cache / "manifest.json").exists() else {}
    if manifest:
        verify_cache(cache, list(manifest))
    for edition, (_, path) in EDITIONS.items():
        if f"sertp-{edition}.pdf" not in manifest:
            fetch_into(cache, f"sertp-{edition}.pdf", SITE + quote(path), manifest)
            write_json(cache / "manifest.json", manifest)
    for state in OSM_STATES:
        if f"osm-{state.lower()}.json" not in manifest:
            fetch_osm(cache, state, manifest)
            write_json(cache / "manifest.json", manifest)


def footprint_facilities(states: list[str], by_state: dict[str, list[dict]]) -> tuple[list[dict], set[str]]:
    """The footprint's named substations, minus every name held by two sites more than 1 km apart anywhere in it:
    a name must be unique across the whole reported area, not just within the state that happens to corroborate."""
    facilities = [f for s in states for f in by_state[s]]
    groups: dict[str, list[dict]] = {}
    for f in facilities:
        groups.setdefault(facility_key(f["name"]), []).append(f)
    repeated = {k for k, fs in groups.items() if any(_meters(a, b) > DUPLICATE_METERS for a in fs for b in fs)}
    return [f for f in facilities if facility_key(f["name"]) not in repeated], repeated


def segment_start(name: str, text: str) -> bool:
    """The parsed facility name must begin the stated name or one of its " - " segments, and not be a customer."""
    return bool(re.search(r"(?:^|[-–]\s*)" + re.escape(name), text, re.I)) and not name.upper().startswith("CUSTOMER")


def rejected(endpoint: dict, text: str, kv: set[int], from_name: bool) -> str | None:
    """Counter-evidence against one matched endpoint, or None."""
    if from_name and not segment_start(endpoint["name"], text):
        # "Yates - Line Creek" parses "Creek" (LINE is a work word): a name cut mid-phrase is not the facility.
        return "endpoint_name_cut"
    tagged = {round(int(v) / 1000) for v in re.findall(r"\d+", endpoint["facility"].get("voltage") or "")
              if int(v) >= 1000}
    if endpoint["corroboration"] == ["unique_in_state"] and kv and tagged and not kv & tagged:
        # A name-only match whose tagged voltages exclude the project's (Georgia's Decatur 115 kV vs a 161 kV
        # "Decatur" in Alabama) is another facility with the same name.
        return "voltage_conflict"
    return None


def place(row: dict, by_state: dict[str, list[dict]], fallback: dict[str, list[dict]] | None = None
          ) -> tuple[dict | None, dict, list[str]]:
    baa = row["baa"]
    facilities, repeated = footprint_facilities(FOOTPRINT[baa], by_state)
    state_of = {f["id"]: f["state"] for f in facilities}
    text = locate_name(row["name"])
    center, candidate = locate(text, row["description"], facilities, OPERATOR_KEYS[baa])
    from_name = named(text, row["description"])["from"] == "name"
    endpoints = candidate["endpoints"]
    hifld, hifld_repeated = footprint_facilities(FOOTPRINT[baa], fallback) if fallback else ([], set())
    for endpoint in endpoints:
        if endpoint["status"] == "no_facility" and endpoint.get("norm") in repeated:
            endpoint["status"] = "ambiguous_in_footprint"
        if endpoint["status"] == "no_facility" and fallback:
            if endpoint.get("norm") in hifld_repeated:
                endpoint["status"] = "ambiguous_in_footprint"
            else:
                hit = match(endpoint["name"], hifld, OPERATOR_KEYS[baa], set(candidate["voltages_kv"]))
                endpoint.clear()
                endpoint.update(hit)
        if endpoint["status"] == "matched":
            endpoint["facility"]["state"] = endpoint["facility"].get("state") or state_of[endpoint["facility"]["id"]]
            if why := rejected(endpoint, text, set(candidate["voltages_kv"]), from_name):
                endpoint["status"] = why
    found = [e for e in endpoints if e["status"] == "matched"]
    if fallback or (center and len(found) < sum("facility" in e for e in endpoints)):
        center = candidate_center(candidate["kind"], found) if found else None
        candidate["tier"] = None if not center else "candidate" if all(
            e["corroboration"] != ["unique_in_state"] for e in found) else "candidate_unique_name"
    if any(e["facility"]["id"].startswith("hifld/") for e in found):
        center["evidence"] = center["evidence"].replace("OSM hifld/", "HIFLD substation ")
        candidate["dataset"] += "; HIFLD public substations, data/southeast/hifld/sources.json"
    candidate["footprint_states"] = FOOTPRINT[baa]
    return center, candidate, sorted({SE_STATES[e["facility"]["state"]] for e in found})


def identity(name: str) -> tuple | None:
    """What a project name states about where it is: ("line", {two endpoint keys}) or ("site", key, kV set)."""
    text = re.sub(r"(\d+)\s*-\s*(?=\d+(?:\s*[-/]\s*\d+)*\s*-?\s*kV)", r"\1/", locate_name(name), flags=re.I)
    got = named(text)
    names = [facility_key(n) for n in got["names"] if n]
    if got["kind"] == "line" and len(set(names)) == 2:
        return ("line", frozenset(names))
    if got["kind"] == "site" and len(names) == 1:
        return ("site", names[0], frozenset(voltages_kv(text)))
    return None


def same_place(a: tuple, b: tuple) -> bool:
    if a[0] != b[0] or a[1] != b[1]:
        return False
    return a[0] == "line" or not (a[2] and b[2]) or a[2] == b[2]  # a site's kV must agree when both state one


def legacy_duplicates(rows: list[dict], legacy: list[dict]) -> tuple[dict[int, dict], dict[int, str]]:
    """Southern rows naming the same endpoint pair (or site) as exactly one legacy Georgia Power project, and that
    project claimed by no other SERTP row. Returns {row: legacy project} and {row: why it stayed new}."""
    known = [(p, identity(p["name"])) for p in legacy]
    hits: dict[int, list[dict]] = {}
    for j, row in enumerate(rows):
        if row["baa"] in ("SOUTHERN", "SOCO") and (mine := identity(row["name"])):
            hits[j] = [p for p, theirs in known if theirs and same_place(mine, theirs)]
    claims = Counter(h[0]["_id"] for h in hits.values() if len(h) == 1)
    matched, kept = {}, {}
    for j, h in hits.items():
        if len(h) > 1:
            kept[j] = f"same named place as {len(h)} legacy GPC projects ({', '.join(p['_id'] for p in h)}); kept new"
        elif h and claims[h[0]["_id"]] > 1:
            kept[j] = (f"shares {h[0]['_id']} with {claims[h[0]['_id']] - 1} other SERTP row(s) (e.g. two circuits or "
                       "two work items on one line); kept new")
        elif h:
            matched[j] = h[0]
    return matched, kept


def event(pid: str, native: str, edition: str, row: dict, artifact: dict, title: str) -> dict:
    return {"id": f"{pid}:{edition}", "type": "planned_milestone", "date": row["year"], "precision": "year",
            "native_project_link": native,
            "description": f"Projected in-service year {row['year']} in the {title}. A planned year, not a completion.",
            "evidence": [{"publisher": PUBLISHER, "url": artifact["url"], "artifact_sha256": artifact["sha256"],
                          "locator": f"PDF page {row['page']}, {row['baa']} Balancing Authority Area",
                          "source_date": None, "retrieved_at": artifact["retrieved_at"], "access_review": ACCESS,
                          "facts": f"In-Service Year: {row['year']}; Project Name: {row['name']}"}]}


def build(cache: Path) -> dict:
    manifest = load_json(cache / "manifest.json")
    verify_cache(cache, [name for name, row in manifest.items() if "sha256" in row])
    fallback = load_hifld(OSM_STATES)
    by_state = {s: osm_extract(load_json(cache / f"osm-{s.lower()}.json"), s) for s in OSM_STATES}
    editions: dict[str, list[dict]] = {}
    checks: dict[str, tuple[int, list[str]]] = {}
    for edition in EDITIONS:
        text = pdf_text(cache / f"sertp-{edition}.pdf")
        checks[edition] = ceii_markings(text)
        if checks[edition][1]:
            raise SystemExit(f"{edition}: CEII page markings {checks[edition][1][:3]}; not ingested")
        rows = parse(text)
        unknown = {r["baa"] for r in rows} - set(FOOTPRINT)
        if len(rows) != text.count("Project Name:") or unknown or not all(r["name"] for r in rows):
            raise SystemExit(f"{edition}: parser drift ({len(rows)} blocks, unknown areas {unknown})")
        editions[edition] = rows
    current = editions[CURRENT]
    if not all(re.fullmatch(r"20\d\d", r["year"]) for r in current):
        raise SystemExit("current edition: an In-Service Year is not a year")
    keys = Counter(key_of(r["baa"], r["name"]) for r in current)
    natives = [f"{slug(r['baa'])}--{slug(r['name'])}" + (f"--p{r['page']}" if keys[key_of(r["baa"], r["name"])] > 1
                                                          else "") for r in current]
    history: dict[int, list[tuple[str, dict]]] = {j: [] for j in range(len(current))}
    dispositions = []
    for edition, rows in editions.items():
        linked = links(rows, current) if edition != CURRENT else {j: j for j in range(len(rows))}
        for i, row in enumerate(rows):
            where = {"source_id": f"{PREFIX}:{edition}", "locator": f"sertp-{edition}.pdf page {row['page']}, "
                     f"{row['baa']} section, block {i + 1}", "name": row["name"]}
            if i in linked:
                history[linked[i]].append((edition, row))
                pid = f"{PREFIX}:{natives[linked[i]]}"
                dispositions.append(where | ({"disposition": "accepted", "project_id": pid,
                                              "reason": "project block in the current SERTP expansion plan"}
                                             if edition == CURRENT else
                                             {"disposition": "duplicate", "project_id": pid,
                                              "reason": "same project name as a current-edition row; its In-Service "
                                                        "Year is kept as a planned_milestone observation"}))
            else:
                dispositions.append(where | {"disposition": "excluded", "reason": (
                    "no current-edition row with the same name: the 2025 report renamed most projects, so a dropout "
                    "cannot be told from a rename, and dropping out never establishes completion")})
    projects = []
    for j, row in enumerate(current):
        native = natives[j]
        pid = f"{PREFIX}:{native}"
        events, last = [], None
        for edition, observed in history[j]:  # oldest edition first; one event per changed year
            if re.fullmatch(r"20\d\d", observed["year"]) and observed["year"] != last:
                events.append(event(pid, native, edition, observed, manifest[f"sertp-{edition}.pdf"],
                                    EDITIONS[edition][0]))
                last = observed["year"]
        center, candidate, states = place(row, by_state, fallback)
        tag = OWNER_TAG.match(row["name"])
        owner = tag[1] if tag and tag[1] in OWNERS else None
        projects.append({
            "_id": pid, "source_id": f"{PREFIX}:{CURRENT}", "native_id": native, "name": row["name"],
            "description": row["description"] or None, "owner": owner, "other_owners": [],
            "planning_region": "sertp", "states": states, "counties": [],
            "geography_basis": "candidate_facility_state" if center else None,
            "status": f"Listed in the {EDITIONS[CURRENT][0]}; In-Service Year {row['year']}",
            "status_group": "planned",
            "in_service": {"raw": row["year"], "value": row["year"], "precision": "year"},
            "center": center, "location_review": "unreviewed" if center else "unlocated",
            "location_candidate": candidate, "project_events": events,
            "evidence": {"page": row["page"], "sheet": None, "row": j + 1,
                         "source_sha256": manifest[f"sertp-{CURRENT}.pdf"]["sha256"],
                         "raw": {"Balancing Authority Area": row["baa"], "In-Service Year": row["year"],
                                 "Project Name": row["name"], "Description": row["description"],
                                 "Supporting Statement": row["support"]}},
        })
    legacy = [p for p in load_json(REPO_ROOT / LEGACY) if p["_id"].startswith("legacy:GPC:")]
    matched, kept = legacy_duplicates(current, legacy)
    for j, note in kept.items():
        projects[j]["location_candidate"]["legacy_overlap"] = note
    moved = {projects[j]["_id"]: p for j, p in matched.items()}
    for d in dispositions:
        if (legacy_project := moved.get(d.get("project_id"))) is not None:
            d |= {"disposition": "duplicate", "project_id": legacy_project["_id"],
                  "reason": f"same two named endpoints as {legacy_project['name']} (legacy GPC register)"
                  if identity(legacy_project["name"])[0] == "line" else
                  f"same named site and kV as {legacy_project['name']} (legacy GPC register)"}
    projects = [p for p in projects if p["_id"] not in moved]
    fips = sorted({SE_STATES[s] for s in OSM_STATES})
    sources = []
    for edition, (title, _) in EDITIONS.items():
        artifact = manifest[f"sertp-{edition}.pdf"]
        hits, _ = checks[edition]
        sources.append({
            "_id": f"{PREFIX}:{edition}", "title": title, "publisher": PUBLISHER,
            "authority": "regional_planning_organization", "role": "project_plan", "landing_url": LANDING,
            "download_url": artifact["url"], "publication_date": None, "vintage": edition[:4],
            "retrieved_at": artifact["retrieved_at"], "sha256": artifact["sha256"], "public_status": "verified_public",
            "import_status": "imported", "access_policy": "public_document", "planning_region": "sertp",
            "states": fips, "project_count": sum(p["source_id"] == f"{PREFIX}:{edition}" for p in projects),
            "notes": [
                f"CEII content check (pdftotext -layout): {hits} line(s) name CEII, 0 CEII page markings; verdict "
                "pass (disclaimer sentences only). D15's 2026 preliminary-report exclusion stands; the 2025 final "
                "plan (\"TRANSMISSION PROJECTS (CEII)\" page headings) is not used. See "
                "specs/decisions/F39-sertp-editions.md.",
                *(["Other editions checked, not ingested: " + "; ".join(
                    f"{f} (sha256 {h or 'n/a'}, CEII lines {n if n is not None else 'n/a'}, markings "
                    f"{m if m is not None else 'n/a'}): {v}" for f, h, n, m, v in NOT_INGESTED)]
                  if edition == CURRENT else []),
                "F39 dense Southeast (C45). " + ("Current edition: one project per block." if edition == CURRENT else
                                                 "History only: rows whose name a current-edition row repeats add "
                                                 "planned_milestone events; other rows are excluded."),
                "Rows give no state or owner column: states come from the matched OSM or HIFLD facility within the Balancing "
                "Authority Area's footprint; unlocated rows keep states []. Owner is only a name tag such as \"GTC:\"."]})
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
