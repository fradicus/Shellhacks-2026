"""F42 Pacific Northwest build: official GIS projects plus transcribed document rows, located under C33.

From pipeline/:
  uv run python -m pnw.build fetch --cache /tmp/pnw-cache          # network: every URL in SOURCES
  uv run python -m pnw.build build --cache /tmp/pnw-cache [--check]
Document rows are transcribed into data/pnw/transcriptions/<file>.json; the build re-extracts each pinned document's
text and rejects any row whose quote, name or facility names are not on its cited page.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pdfplumber

from common import load_json, validate, write_json
from common.names import norm_name
from greatlakes.match import facilities_named, facility_key
from greatlakes.shared import fetch_into, verify_cache
from texas.statewide import inside_geometry

from . import cx
from .shared import OUT, STATES, counties, county_geoids, locate, osm, summary

ARC = "https://services3.arcgis.com/Iz3chmSt4P7oOoZy/arcgis/rest/services/{}/query?where=1%3D1&outFields=*&outSR=4326&f=geojson"
WECC = "https://www.wecc.org/sites/default/files/documents/progress_report/2025/{}"
BPA, WECC_ORG, UTIL, RPO = ("Bonneville Power Administration", "Western Electricity Coordinating Council", "utility",
                             "regional_planning_organization")
# file in cache -> (source_id, publisher, authority, title, vintage, url). One national source per project-bearing file.
SOURCES = {
    "bpa_gerp_line_projects.geojson": ("bpa-gerp-lines", BPA, UTIL, "BPA Evolving Grid (GERP) transmission line "
                                       "projects layer", None,
                                       ARC.format("Evolving_Grid_Transmission_Lines_Projects/FeatureServer/11")),
    "bpa_gerp_substation_projects.geojson": ("bpa-gerp-substations", BPA, UTIL, "BPA Evolving Grid (GERP) substation "
                                             "projects layer", None,
                                             ARC.format("Evolving_Grid_Substation_Projects/FeatureServer/10")),
    "westtec_planned.geojson": ("westtec-10yr-planned", "WestTEC (layer hosted by BPA)", RPO,
                                "WestTEC 10-year planned projects layer", None,
                                ARC.format("WestTEC_10yr_Planned_Projects/FeatureServer/0")),
    "westtec_identified.geojson": ("westtec-10yr-identified", "WestTEC (layer hosted by BPA)", RPO,
                                   "WestTEC 10-year identified upgrades layer", None,
                                   ARC.format("WestTEC_10yr_Identified_Upgrades/FeatureServer/0")),
    "bpa_2025_transmission_plan.pdf": ("bpa-transmission-plan-2025", BPA, UTIL, "2025 BPA Transmission Plan", "2025",
                                       "https://www.bpa.gov/-/media/Aep/transmission/attachment-k/"
                                       "2025-BPA-Transmission-Plan_Final.pdf"),
    "bpa_2023_transmission_plan.pdf": ("bpa-transmission-plan-2023", BPA, UTIL, "2023 BPA Transmission Plan", "2023",
                                       "https://www.bpa.gov/-/media/Aep/transmission/attachment-k/"
                                       "2023-BPA-Transmission-Plan.pdf"),
    "bpa_gerp_project_update.pdf": ("bpa-gerp-update", BPA, UTIL, "BPA GERP Project Update", None,
                                    "https://www.bpa.gov/-/media/Aep/transmission/Grid-Expansion-and-Reinforcement-"
                                    "Portfolio-GERP/GERP-Project-Update.pdf"),
    "northerngrid_2026-2027_study_scope.pdf": ("northerngrid-scope-2026-2027", "NorthernGrid", RPO,
                                               "NorthernGrid 2026-2027 Study Scope", "2026-2027",
                                               "https://www.northerngrid.net/private-media/documents/"
                                               "NG_Study_Scope_2026_2027_yAcCvCa.pdf"),
    "northerngrid_2024-2025_study_scope.pdf": ("northerngrid-scope-2024-2025", "NorthernGrid", RPO,
                                               "NorthernGrid 2024-2025 Approved Study Scope", "2024-2025",
                                               "https://www.northerngrid.net/private-media/documents/"
                                               "2024_2025_Approved_Study_Scope.pdf"),
    "wecc_apr_2025_summary.pdf": ("wecc-apr-2025-summary", WECC_ORG, RPO, "2025 Annual Progress Report Summary "
                                  "(waiver lists by year)", "2025",
                                  WECC.format("2025%20Annual%20Progress%20Report%20Summary_Draft.pdf")),
    **{f"apr_{code}.pdf": (f"wecc-apr-2025-{code.lower()}", WECC_ORG, RPO, f"{code} 2025 Annual Progress Report to "
                           "WECC", "2025", WECC.format(f"{code}%202025%20APR.pdf"))
       for code in ["AVA", "BPA", "CHPD", "GCPD", "IPC", "NWE", "PGE", "PSE", "SCL", "TPWR"]},
    "wecc_apr_2025_pacificorp.pdf": ("wecc-apr-2025-pacificorp", WECC_ORG, RPO, "PacifiCorp 2025 Annual Progress "
                                     "Report to WECC", "2025", WECC.format("PacifiCorp%202025%20APR.pdf")),
    "idahopower_current_projects.html": ("idahopower-current-projects", "Idaho Power", UTIL, "Current Projects", None,
                                         "https://www.idahopower.com/energy-environment/energy/planning-and-electrical-"
                                         "projects/current-projects/"),
    "snopud_system_improvements.html": ("snopud-system-improvements", "Snohomish County PUD", UTIL,
                                        "System Improvements", None,
                                        "https://www.snopud.com/community-environment/our-energy-future/reliability/"
                                        "system-improvements/"),
    "scl_current_projects.html": ("scl-current-projects", "Seattle City Light", UTIL, "Current Projects", None,
                                  "https://seattle.gov/city-light/in-the-community/current-projects"),
    **{name: (f"bpa-cx-{name[3:-4]}", BPA, "federal_government", "BPA categorical exclusion determination "
              f"{name[3:11]}", name[3:7], url) for name, url in cx.files().items()},
}
HIFLD = ("https://services5.arcgis.com/HDRa0B57OVrv2E1q/arcgis/rest/services/Electric_Substations/FeatureServer/0/"
         "query?where=STATE%3D%27{}%27&outFields=ID,NAME,CITY,STATE,COUNTY,STATUS,MAX_VOLT,MIN_VOLT,SOURCEDATE"
         "&orderByFields=OBJECTID_1&resultOffset={}&resultRecordCount=2000&outSR=4326&f=geojson")
# Geometry references used only to place or assign state/county, never project sources.
REFERENCES = {
    "bpa_substations.geojson": ARC.format("BPA_Substation_Storymap/FeatureServer/0"),
    "tiger_counties.geojson": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1/"
                              "query?where=STATE+IN+%28%2753%27%2C%2741%27%2C%2716%27%2C%2730%27%29&outFields=GEOID"
                              "%2CNAME%2CSTATE&outSR=4326&maxAllowableOffset=0.0005&returnGeometry=true&f=geojson",
    # HIFLD Open "Electric Substations" (DHS, public domain), a February 2021 copy hosted on ArcGIS Online by user
    # SGT_Peterson (item 45505e134cb14bbda4e939117459eb6b); HIFLD Open's own service is gone. Candidate geometry only.
    **{f"hifld_{st.lower()}_{offset}.geojson": HIFLD.format(st, offset)
       for st in ("WA", "OR", "ID", "MT") for offset in (0, 2000)},
}
FIPS = {v: k for k, v in STATES.items()}
BPA_KEYS = ["BONNEVILLE", "BPA"]
OPERATOR_KEYS = {
    "Bonneville Power Administration": BPA_KEYS, "Idaho Power": ["IDAHO POWER"], "Avista": ["AVISTA"],
    "Portland General Electric": ["PORTLAND GENERAL"], "Puget Sound Energy": ["PUGET SOUND"],
    "NorthWestern Energy": ["NORTHWESTERN"], "PacifiCorp": ["PACIFICORP", "PACIFIC POWER", "ROCKY MOUNTAIN"],
    "Seattle City Light": ["SEATTLE CITY LIGHT"], "Tacoma Power": ["TACOMA"], "Snohomish County PUD": ["SNOHOMISH"],
    "Chelan County PUD": ["CHELAN"], "Grant County PUD": ["GRANT COUNTY", "GRANT PUD"],
}
# Owner codes used by WECC/NorthernGrid lists -> one name per utility (joint projects keep the first-named owner).
OWNER_CODES = {"BPA": BPA, "IPC": "Idaho Power", "IPCO": "Idaho Power", "PGE": "Portland General Electric",
               "PGN": "Portland General Electric", "PAC": "PacifiCorp", "PACW": "PacifiCorp", "PACE": "PacifiCorp",
               "PSE": "Puget Sound Energy", "PSEI": "Puget Sound Energy", "NWE": "NorthWestern Energy",
               "NWMT": "NorthWestern Energy", "AVA": "Avista", "GCPD": "Grant County PUD", "GCPUD": "Grant County PUD",
               "CHPD": "Chelan County PUD", "SCL": "Seattle City Light", "TPWR": "Tacoma Power",
               "SNPD": "Snohomish County PUD", "MATL": "Montana Alberta Tie Ltd."}


def canonical_owner(raw: str | None) -> str | None:
    if not raw:
        return None
    first = re.split(r",| and ", raw)[0].strip()
    if first in OWNER_CODES:
        return OWNER_CODES[first]
    return next((name for name in OPERATOR_KEYS if name.split()[0].upper() in first.upper()), first)


ONE_STATE_OWNERS = {"Portland General Electric": "OR", "Puget Sound Energy": "WA", "Grant County PUD": "WA",
                    "Chelan County PUD": "WA", "Seattle City Light": "WA", "Tacoma Power": "WA",
                    "Snohomish County PUD": "WA", "NorthWestern Energy": "MT"}
# County utilities serve only these counties (HIFLD COUNTY spelling); a name-only match elsewhere is someone else's.
OWNER_COUNTIES = {"Grant County PUD": {"GRANT"}, "Chelan County PUD": {"CHELAN"},
                  "Snohomish County PUD": {"SNOHOMISH", "ISLAND"}}
# Service-territory states, used only when a row names no state (C33 unique-name rule still applies across them).
OWNER_STATES = {"Idaho Power": ["ID", "OR"], "Avista": ["WA", "ID"], BPA: list(STATES), "PacifiCorp": ["WA", "OR", "ID"],
                "NorthWestern Energy": ["MT"]}
STATUS = [(re.compile(r"cancel", re.I), "cancelled"), (re.compile(r"complet|in[- ]service|energized", re.I), "in_service"),
          (re.compile(r"under construction|construction (?:is )?underway|CONSTRUCTION", re.I), "under_construction")]
WS = re.compile(r"\s+")


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest: dict = {}
    for name, url in {**{n: v[-1] for n, v in SOURCES.items()}, **REFERENCES}.items():
        fetch_into(cache, name, url, manifest)
    write_json(cache / "manifest.json", manifest)


def flat(text: str) -> str:
    return WS.sub(" ", text).strip()


def pages(cache: Path, name: str) -> dict[int, str]:
    """Whitespace-collapsed text per page: pdfplumber for PDFs, tag-stripped text as page 1 for HTML."""
    path = cache / name
    memo = cache / "text" / f"{hashlib.sha256(path.read_bytes()).hexdigest()}.json"
    if memo.exists():  # extraction is deterministic per file hash; the memo lives in the cache, outside the repo
        return {int(k): v for k, v in load_json(memo).items()}
    memo.parent.mkdir(exist_ok=True)
    write_json(memo, text := _extract(path, name))
    return text


def _extract(path: Path, name: str) -> dict[int, str]:
    if name.endswith(".html"):
        raw = re.sub(r"<!--.*?-->|<(script|style|nav|footer|header|svg)\b.*?</\1>", " ", path.read_text(errors="replace"),
                     flags=re.S)
        return {1: flat(html.unescape(re.sub(r"<[^>]+>", "\n", raw)))}
    with pdfplumber.open(path) as pdf:
        return {i: flat(p.extract_text() or "") for i, p in enumerate(pdf.pages, start=1)}


class Places:
    """State and county of a WGS84 point from Census county polygons (WA/OR/ID/MT only)."""

    def __init__(self, raw: dict):
        self.features = []
        for f in raw["features"]:
            ring = [c for polygon in (f["geometry"]["coordinates"] if f["geometry"]["type"] == "MultiPolygon"
                                      else [f["geometry"]["coordinates"]]) for c in polygon[0]]
            box = (min(c[0] for c in ring), min(c[1] for c in ring), max(c[0] for c in ring), max(c[1] for c in ring))
            self.features.append((box, f))

    def county(self, lon: float, lat: float) -> str | None:
        hits = [f["properties"]["GEOID"] for (w, s, e, n), f in self.features
                if w <= lon <= e and s <= lat <= n and inside_geometry(lon, lat, f["geometry"])]
        return hits[0] if len(hits) == 1 else None


def status_group(*texts: str | None) -> str:
    text = " ".join(t for t in texts if t)
    return next((group for pattern, group in STATUS if pattern.search(text)), "planned" if text else "unknown")


def in_service(raw: str | int | None) -> dict:
    text = str(raw) if raw is not None else None
    if text and re.fullmatch(r"20\d\d", text):
        return {"raw": text, "value": text, "precision": "year"}
    return {"raw": text, "value": None, "precision": "unknown"}


def record(file: str, native: str, name: str, manifest: dict, **fields) -> dict:
    source_id = SOURCES[file][0]
    base = {"_id": f"{source_id}:{native}", "source_id": source_id, "native_id": native, "name": name,
            "description": None, "owner": None, "other_owners": [], "planning_region": None, "states": [],
            "counties": [], "geography_basis": None, "status": None, "status_group": "unknown",
            "in_service": in_service(None), "center": None}
    project = base | fields
    project["location_review"] = "unreviewed" if project["center"] else "unlocated"
    project["evidence"]["source_sha256"] = manifest[file]["sha256"]
    return project


def terminals(geometry: dict) -> list[list[float]]:
    parts = [geometry["coordinates"]] if geometry["type"] == "LineString" else geometry["coordinates"]
    return [parts[0][0], parts[-1][-1]]


def vertices(geometry: dict) -> list[list[float]]:
    if geometry["type"] == "Point":
        return [geometry["coordinates"]]
    return geometry["coordinates"] if geometry["type"] == "LineString" else sum(geometry["coordinates"], [])


def official(places: Places, points: list[list[float]], along: list[list[float]], what: str) -> tuple[dict | None, list]:
    """Center from source geometry: a point, or the mean of a line's two terminal vertices, plus touched counties."""
    lon = round(sum(p[0] for p in points) / len(points), 6)
    lat = round(sum(p[1] for p in points) / len(points), 6)
    geoids = sorted({g for v in along if (g := places.county(v[0], v[1]))})
    if places.county(lon, lat) is None:
        return None, geoids  # an interstate line whose midpoint leaves WA/OR/ID/MT: no pin outside its listed states
    basis = "source_point" if len(points) == 1 else "two"
    return {"lat": lat, "lon": lon, "basis": basis,
            "evidence": f"Official source geometry: {what}; not independently reviewed."}, geoids


def gis_projects(cache: Path, manifest: dict, places: Places) -> tuple[list[dict], list[dict]]:
    projects, dispositions = [], []
    by_bundle: dict[str, list] = {}
    for name in ("bpa_gerp_line_projects.geojson", "bpa_gerp_substation_projects.geojson"):
        for f in load_json(cache / name)["features"]:
            by_bundle.setdefault(f["properties"]["Bundle_ID"], []).append((name, f))
    layers = [(bundle, feats, feats[0][1]["properties"]["Project_Name"]) for bundle, feats in sorted(by_bundle.items())]
    for name, field in (("westtec_planned.geojson", "Line_Name"), ("westtec_identified.geojson", "Upgrade_Na")):
        titled: dict[str, list] = {}
        for f in load_json(cache / name)["features"]:
            titled.setdefault(f["properties"][field], []).append((name, f))
        layers += [(re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-"), feats, t) for t, feats in sorted(titled.items())]
    for native, feats, title in layers:
        file, props = feats[0][0], feats[0][1]["properties"]
        # A GERP bundle can hold a line and a substation feature; the line's terminals win (mission endpoint rule).
        lines = [g for _, f in feats if (g := f["geometry"])["type"] != "Point"]
        geom = lines or [f["geometry"] for _, f in feats]
        points = [terminals(geom[0])[0], terminals(geom[-1])[1]] if lines else [g["coordinates"] for g in geom]
        what = (f"{file} feature '{title}'" + (", mean of the line's terminal vertices" if lines else
                                               " (BPA describes these as approximate point locations)"))
        along = [v for g in geom for v in vertices(g)]
        center, geoids = official(places, points, along[::10] + along[-1:], what)  # every 10th vertex is enough for counties
        locator = f"{file}#{title}"
        if not geoids:
            dispositions.append({"native_id": native, "locator": locator, "disposition": "excluded",
                                 "reason": "geometry outside WA/OR/ID/MT"})
            continue
        raw = {k: v for k, v in props.items() if k not in ("GlobalID", "FID", "OBJECTID", "OBJECTID_1")
               and not k.startswith("Shape")} | {"features": len(feats)}
        if file.startswith("bpa"):
            fields = {"description": props.get("Description"), "owner": BPA,
                      "planning_region": f"BPA GERP {props.get('Cycle') or ''}".strip(), "status": props.get("Status"),
                      "status_group": "under_construction" if props.get("Status") == "CONSTRUCTION" else "planned",
                      "in_service": in_service(props.get("Expected_Energization"))}
        else:
            fields = {"planning_region": "WestTEC 10-year",
                      "status": "; ".join(str(props[k]) for k in ("Upgrade_Ty", "Assessment") if props.get(k)),
                      "status_group": "proposed" if "identified" in file else "planned"}
        projects.append(record(file, native, title, manifest, **fields, states=sorted({g[:2] for g in geoids}),
                               counties=geoids, geography_basis="source_geometry", center=center,
                               evidence={"page": None, "sheet": file, "row": None, "raw": raw},
                               **({} if center else {"location_note": "interstate line; midpoint outside WA/OR/ID/MT"})))
        dispositions.append({"native_id": native, "locator": locator, "disposition": "accepted",
                             "reason": "project geometry touches WA/OR/ID/MT"})
    return projects, dispositions


def facilities(cache: Path, places: Places) -> dict[str, list[dict]]:
    """Per state: OSM named substations plus BPA's own substation points (operator BPA)."""
    by_state = {st: osm([st]) for st in STATES}
    for f in load_json(cache / "bpa_substations.geojson")["features"]:
        lon, lat = f["geometry"]["coordinates"]
        geoid = places.county(lon, lat)
        if not geoid:
            continue
        p = f["properties"]
        by_state[FIPS[geoid[:2]]].append({"id": f"bpa/{p['STA_CODE']}", "name": p["Name"], "norm": norm_name(p["Name"]),
                                          "operator": BPA, "voltage": None, "state": FIPS[geoid[:2]],
                                          "lat": round(lat, 7), "lon": round(lon, 7)})
    for name in sorted(n for n in REFERENCES if n.startswith("hifld_")):
        for f in load_json(cache / name)["features"]:
            p = f["properties"]
            if not p["NAME"] or p["NAME"].startswith(("NOT AVAILABLE", "UNKNOWN")) or not f["geometry"]:
                continue
            lon, lat = f["geometry"]["coordinates"]
            volts = [v for v in (p["MAX_VOLT"], p["MIN_VOLT"]) if v and v > 0]
            by_state[p["STATE"]].append({"id": f"hifld/{p['ID']}", "name": p["NAME"], "norm": norm_name(p["NAME"]),
                                         "operator": None, "voltage": ";".join(str(round(v * 1000)) for v in volts),
                                         "county": p["COUNTY"], "state": p["STATE"],
                                         "lat": round(lat, 7), "lon": round(lon, 7)})
    # "Sedro-Woolley" and "Sedro Woolley" are one name; the query side gets the same treatment in locate().
    return {st: [f | {"name": (n := f["name"].replace("-", " ")), "key": facility_key(n)} for f in fs]
            for st, fs in by_state.items()}


def excluded(row: dict) -> str | None:
    """Why a row is left out: not transmission work, or outside the user's 2025-2035 window (C33 focus)."""
    if row["work_type"] != "transmission":
        return f"{row['work_type']} work, not a transmission construction project"
    if row.get("memo_year") == "2024" and not row["window_years"]:
        return "2024 CX memo with no 2025-2035 year in its text"
    if re.search(r"cancel|complet", row["status_raw"] or "", re.I):
        return f"historical: {row['status_raw']}"
    years = [int(y) for y in re.findall(r"\b(20\d\d)\b", row["in_service_raw"] or "")]
    if years and not any(2025 <= y <= 2035 for y in years):
        return f"in-service {row['in_service_raw']} outside 2025-2035"
    listed = re.match(r"(20\d\d) List of Projects", row.get("section") or "")
    if listed and int(listed[1]) < 2024 and not years:
        return f"historical waiver list ({listed[1]}) with no 2025-2035 date"
    return None


def document_projects(cache: Path, manifest: dict, places: Places) -> tuple[list[dict], list[dict]]:
    by_state = facilities(cache, places)
    county_index = counties()
    projects, dispositions = [], []
    batches = [(next(n for n in SOURCES if n.rsplit(".", 1)[0] == path.stem), load_json(path)["rows"])
               for path in sorted((OUT / "transcriptions").glob("*.json"))]
    batches += [(name, [cx.rows(pages(cache, name)) | {"memo_year": name[3:7]}]) for name in cx.files()]
    for file, rows in batches:
        text = pages(cache, file)
        for i, row in enumerate(rows, start=1):
            locator = f"{file}#page={row['page']}"
            page = text.get(row["page"], "")
            missing = [s for s in (row["quote"], row["name"], *filter(None, row["facilities"])) if flat(s) not in page]
            if missing:
                raise SystemExit(f"{file} row {i}: not on page {row['page']}: {missing}")
            native = row["native_id"] or re.sub(r"[^a-z0-9]+", "-", row["name"].lower()).strip("-")[:80]
            if reason := excluded(row):
                dispositions.append({"native_id": native, "locator": locator, "disposition": "excluded",
                                     "reason": reason})
                continue
            owner = canonical_owner(row["owner"])
            states = [s for s in row["states"] if s in STATES]
            if not row["states"] and owner in ONE_STATE_OWNERS:  # TRANSCRIBE.md's owner_territory rule, applied uniformly
                states, row = [ONE_STATE_OWNERS[owner]], row | {"state_basis": "owner_territory"}
            if not row["kind"]:  # the same deterministic name parser F40 uses: "Harborton-St Mary 230 kV" is a line
                named = facilities_named(row["name"], None)
                row = row | {"kind": named["kind"], "facilities": named["names"]}
            counties_named = re.findall(r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)?) County\b", row["quote"])
            if states and not row["counties"] and counties_named:
                row = row | {"counties": counties_named}
            if row["states"] and not states:
                dispositions.append({"native_id": native, "locator": locator, "disposition": "excluded",
                                     "reason": "outside WA/OR/ID/MT"})
                continue
            center, block, geoids = None, None, []
            basis = row["state_basis"]
            # No state in the text: search the owner's service states; the name must still be unique across them.
            pool_states = states or OWNER_STATES.get(owner or "", [])
            if row["kind"] and pool_states:
                pool = [f for s in pool_states for f in by_state[s]]
                center, block = locate(row["kind"], [n and n.replace("-", " ") for n in row["facilities"]], pool,
                                       OPERATOR_KEYS.get(owner or "", []), set(row["voltages_kv"] or []),
                                       "OpenStreetMap (ODbL) data/pnw/osm + BPA substations GIS + HIFLD substations",
                                       {c.upper() for c in row["counties"]} or OWNER_COUNTIES.get(owner or ""))
                # A territory-only search (the owner also works outside WA/OR/ID/MT) needs operator/voltage agreement.
                if center and not states and any(e.get("corroboration") == ["unique_in_state"] for e in block["endpoints"]):
                    center, block["reason"] = None, "owner-territory search needs operator or voltage corroboration"
            if center:
                g = places.county(center["lon"], center["lat"])
                if not states and g:
                    states, basis = [FIPS[g[:2]]], "owner_territory_facility"
                geoids = [g] if g and FIPS.get(g[:2]) in states else []
            else:
                pairs = row.get("county_pairs") or [(s, c) for s in states for c in row["counties"]]
                geoids = county_geoids(pairs, county_index)
            projects.append(record(
                file, native, row["name"], manifest, owner=owner,
                planning_region=row.get("section"), states=sorted(STATES[s] for s in states), counties=geoids,
                geography_basis=basis, status=row["status_raw"],
                status_group=status_group(row["status_raw"]) if row["status_raw"] else "planned",
                in_service=in_service(row["in_service_raw"]), center=center,
                evidence={"page": row["page"], "sheet": file, "row": None,
                          "raw": {"quote": row["quote"], "cost": row["cost_raw"], "section": row.get("section"),
                                  "source_native_id": row["native_id"]}},
                **({"location_candidate": block} if block else {})))
            dispositions.append({"native_id": native, "locator": locator, "disposition": "accepted",
                                 "reason": "transcribed row verified on its cited page"})
    return projects, dispositions


def endpoints(p: dict, known: set[str]) -> str | None:
    """Normalized 'A|B' for a line between two named facilities, from its match block or (GIS layers) its title.
    Both names must be real facilities; otherwise "Cross-Cascades" or "SWIP-North" would read as endpoints."""
    lc = p.get("location_candidate")
    if lc:
        ends = [e.get("norm") for e in lc["endpoints"]] if lc.get("kind") == "line" else []
    else:
        named = facilities_named(p["name"], None)
        ends = [facility_key(n) for n in named["names"] if n] if named["kind"] == "line" else []
    return "|".join(sorted(ends)) if len(ends) == 2 and all(e in known for e in ends) else None


def identity(p: dict, known: set[str]) -> str:
    """Explicit identity only: a BPA bundle number, the same owner's line between the same two facilities, or the
    same owner with the same exact title. Name similarity never merges projects."""
    bundle = p["evidence"]["raw"].get("source_native_id") or p["evidence"]["raw"].get("Bundle_ID")
    if bundle and (m := re.fullmatch(r"P0?(\d{4})", bundle)):
        return f"bundle:P0{m[1]}"
    if p.get("location_candidate") and (pair := endpoints(p, known)):
        return f"line:{p['owner']}:{pair}"
    return f"title:{p['owner']}:{facility_key(re.sub(r'[(].*?[)]', ' ', p['name']))}"


def link_duplicates(projects: list[dict], known: set[str]) -> tuple[list[dict], list[dict]]:
    """One record per identity. Survivor: official geometry, then a pin, then the newest source."""
    def rank(p: dict) -> tuple:
        year = re.search(r"20\d\d", p["source_id"])
        return ("Official" not in (p["center"] or {}).get("evidence", ""), p["center"] is None,
                -int(year[0]) if year else 0, p["_id"])

    groups: dict[str, list[dict]] = {}
    for p in projects:
        groups.setdefault(identity(p, known), []).append(p)
    # WestTEC lists other utilities' lines with no owner: join the one owned project with the same two endpoints.
    by_pair: dict[str, set[str]] = {}
    for key, members in groups.items():
        for m in members:
            if m["owner"] and (pair := endpoints(m, known)):
                by_pair.setdefault(pair, set()).add(key)
    for key in [k for k, ms in groups.items() if all(m["owner"] is None for m in ms)]:
        targets = {t for m in groups[key] if (pair := endpoints(m, known)) for t in by_pair.get(pair, set())}
        if len(targets) == 1:
            groups[targets.pop()] += groups.pop(key)
    kept, dispositions = [], []
    for members in groups.values():
        members.sort(key=rank)
        first = members[0]
        if len(members) > 1:
            first["also_reported_by"] = [{"_id": m["_id"], "sheet": m["evidence"]["sheet"], "page": m["evidence"]["page"],
                                          "status": m["status"], "in_service": m["in_service"]["raw"]}
                                         for m in members[1:]]
            if first["in_service"]["precision"] == "unknown":
                first["in_service"] = next((m["in_service"] for m in members if m["in_service"]["value"]),
                                           first["in_service"])
        dispositions += [{"native_id": m["native_id"], "locator": m["evidence"]["sheet"], "disposition": "duplicate",
                          "reason": f"same project as {first['_id']}"} for m in members[1:]]
        kept.append(first)
    return sorted(kept, key=lambda p: p["_id"]), dispositions


def build(cache: Path) -> dict[Path, object]:
    manifest = verify_cache(cache, [*SOURCES, *REFERENCES])
    places = Places(load_json(cache / "tiger_counties.geojson"))
    gis, gis_disp = gis_projects(cache, manifest, places)
    docs, doc_disp = document_projects(cache, manifest, places)
    known = {f["key"] for fs in facilities(cache, places).values() for f in fs}
    projects, dup_disp = link_duplicates(gis + docs, known)
    counts = Counter(p["source_id"] for p in projects)
    sources = []
    for file, (source_id, publisher, authority, title, vintage, url) in SOURCES.items():
        if not counts[source_id]:
            continue
        sources.append({
            "_id": source_id, "title": title, "publisher": publisher, "authority": authority, "role": "project_plan",
            "landing_url": url, "download_url": url, "publication_date": None, "vintage": vintage,
            "retrieved_at": manifest[file]["retrieved_at"], "sha256": manifest[file]["sha256"],
            "public_status": "verified_public", "import_status": "imported", "access_policy": "public_document",
            "planning_region": None, "states": sorted({s for p in projects if p["source_id"] == source_id
                                                       for s in p["states"]}),
            "project_count": counts[source_id],
            "notes": ["F42 Pacific Northwest (C33). Pins are official source geometry or labeled candidates; none is "
                      "independently reviewed. Source-bounded, not statewide coverage."]})
    for p in projects:
        validate(p, "national-project")
    for s in sources:
        validate(s, "national-source")
    references = {"osm": load_json(OUT / "osm" / "sources.json"),
                  **{name: {"url": url} | manifest[name] for name, url in REFERENCES.items()}}
    return {OUT / "projects.json": projects, OUT / "sources.json": sorted(sources, key=lambda s: s["_id"]),
            OUT / "references.json": references, OUT / "dispositions.json": gis_disp + doc_disp + dup_disp,
            OUT / "summary.json": summary(projects)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["fetch", "build"])
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "fetch":
        fetch(args.cache)
        return 0
    outputs = build(args.cache)
    if args.check:
        stale = [str(p) for p, v in outputs.items() if not p.exists() or load_json(p) != v]
        print("stale: " + ", ".join(stale) if stale else "ok")
        return 1 if stale else 0
    for path, value in outputs.items():
        write_json(path, value)
    print(json.dumps(outputs[OUT / "summary.json"], indent=2))
    print(Counter(d["disposition"] for d in outputs[OUT / "dispositions.json"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
