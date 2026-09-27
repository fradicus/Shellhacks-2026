"""MISO "MTEP Projects Under Evaluation" workbook -> Great Lakes national-project records with C26 candidates.

From pipeline/:
  uv run python -m greatlakes.miso fetch --cache /tmp/gl-cache-miso   # network: 1 public workbook on cdn.misoenergy.org
  uv run python -m greatlakes.miso build --cache /tmp/gl-cache-miso   # offline; add --check to compare
Rows whose MTEP ID was already imported from the Minnesota or ATC registers are linked, not duplicated.
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import openpyxl

from common import load_json, validate, write_json

from . import osm as osm_data
from .match import voltages_kv
from .shared import OUT, fetch_into, locate, verify_cache, write_outputs

SOURCE_ID = "miso-mtep26-eval"
FILE = "MTEP Projects Under Evaluation368757.xlsx"
URL = "https://cdn.misoenergy.org/MTEP%20Projects%20Under%20Evaluation368757.xlsx"
SHEET = "MTEP Projects Under Evaluation"
GREAT_LAKES = ["MN", "WI", "MI", "IL", "IN", "OH", "PA", "NY"]
OSM_STATES = ["MN", "WI", "MI", "IL", "IN"]  # the Great Lakes states in MISO's footprint
FIPS = {"MN": "27", "WI": "55", "MI": "26", "IL": "17", "IN": "18", "OH": "39", "PA": "42", "NY": "36", "IA": "19",
        "MO": "29", "ND": "38", "SD": "46", "KY": "21", "AR": "05", "LA": "22", "MS": "28", "TX": "48", "MT": "30"}
STATUS = {"M1": "proposed", "M2": "planned", "M3": "under_construction", "M4": "in_service"}
DATASET = "OpenStreetMap (ODbL), data/greatlakes/osm/<state>-substations.json"
# Submitting-TO name fragment -> OSM operator-name fragments that corroborate it.
OPERATORS = [
    ("AMERICAN TRANSMISSION", ["AMERICAN TRANSMISSION", "ATC"]), ("NORTHERN STATES", ["XCEL", "NORTHERN STATES"]),
    ("AMEREN", ["AMEREN"]), ("GREAT RIVER", ["GREAT RIVER"]), ("METC", ["ITC", "METC", "MICHIGAN ELECTRIC TRANS"]),
    ("ITC", ["ITC", "INTERNATIONAL TRANSMISSION"]), ("HOOSIER", ["HOOSIER"]), ("DUKE", ["DUKE"]),
    ("PRAIRIE POWER", ["PRAIRIE POWER"]), ("CENTERPOINT", ["CENTERPOINT", "VECTREN", "SOUTHERN INDIANA GAS"]),
    ("WABASH VALLEY", ["WABASH VALLEY"]), ("INDIANAPOLIS POWER", ["INDIANAPOLIS POWER", "AES INDIANA"]),
    ("WOLVERINE", ["WOLVERINE"]), ("MINNESOTA POWER", ["MINNESOTA POWER", "ALLETE"]), ("DAIRYLAND", ["DAIRYLAND"]),
    ("NORTHERN INDIANA", ["NIPSCO", "NORTHERN INDIANA"]), ("SOUTHERN MINNESOTA", ["SOUTHERN MINNESOTA", "SMMPA"]),
    ("MISSOURI RIVER", ["MISSOURI RIVER"]), ("OTTER TAIL", ["OTTER TAIL"]), ("MINNKOTA", ["MINNKOTA"]),
    ("SOUTHERN ILLINOIS POWER", ["SOUTHERN ILLINOIS POWER"]), ("CENTRAL MINNESOTA", ["CENTRAL MINNESOTA", "CMMPA"]),
    ("GRIDLIANCE", ["GRIDLIANCE"]),
]


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest: dict = {}
    fetch_into(cache, FILE, URL, manifest)
    write_json(cache / "manifest.json", manifest)


def operator_keys(submitter: str) -> list[str]:
    up = submitter.upper()
    return next((keys for fragment, keys in OPERATORS if fragment in up), [])


def imported_mtep_ids() -> dict[str, str]:
    """MTEP IDs already carried by earlier Great Lakes registers, mapped to their record IDs."""
    ids = {}
    for state, field in (("mn", "MTEP Project Number"), ("wi", "MTEP PRJID")):
        for p in load_json(OUT / state / "projects.json"):
            value = str(p["evidence"]["raw"].get(field) or "")
            if value.isdigit():
                ids.setdefault(value, p["_id"])
    return ids


def build(cache: Path) -> dict:
    manifest = verify_cache(cache, [FILE])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # openpyxl: unsupported data-validation extension
        workbook = openpyxl.load_workbook(cache / FILE, read_only=True)
    rows = list(workbook[SHEET].iter_rows(values_only=True))
    header = [str(h) for h in rows[1]]
    if header[:6] != ["Target MTEP Cycle", "Target Appendix", "Submitting TO", "Planning Region", "State(s)",
                      "MTEP Project ID"]:
        raise SystemExit(f"unexpected header: {header}")
    linked = imported_mtep_ids()
    projects, dispositions = [], []
    for index, values in enumerate(rows[2:], start=3):
        c = dict(zip(header, values, strict=True))
        native = str(c["MTEP Project ID"])
        locator = f"{FILE}#{SHEET}!row-{index}"
        states = [s.strip() for s in (c["State(s)"] or "").split(";") if s.strip()]
        if not set(states) & set(GREAT_LAKES):
            dispositions.append({"native_id": native, "locator": locator, "disposition": "excluded",
                                 "reason": f"outside F40 states ({', '.join(states) or 'none'})"})
            continue
        if native in linked:
            dispositions.append({"native_id": native, "locator": locator, "disposition": "duplicate",
                                 "reason": f"same MTEP project ID as {linked[native]}"})
            continue
        status = c["Planning Status"] or ""
        isd = c["Expected ISD"]
        in_service = ({"raw": isd.date().isoformat(), "value": isd.date().isoformat(), "precision": "day"} if isd
                      else {"raw": None, "value": None, "precision": "unknown"})
        name, description = c["Project Name"], c["Project Description"]
        kv = {int(v) for v in (c["Max kV"], c["Min kV"]) if isinstance(v, int | float)} | voltages_kv(name, description)
        facilities = osm_data.load([s for s in states if s in OSM_STATES])
        center, candidate = locate(name, description, facilities, operator_keys(c["Submitting TO"]), kv, DATASET)
        raw = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in c.items()}
        project = {
            "_id": f"{SOURCE_ID}:{native}", "source_id": SOURCE_ID, "native_id": native, "name": name,
            "description": description, "owner": c["Submitting TO"], "other_owners": [], "planning_region": "miso",
            "states": [FIPS[s] for s in states if s in FIPS], "counties": [], "geography_basis": "source_state",
            "status": status, "status_group": STATUS.get(status[:2], "unknown"), "in_service": in_service,
            "center": center, "location_review": "unreviewed" if center else "unlocated",
            "location_candidate": candidate,
            "estimated_cost": {"raw": c["Current Cost"], "usd": c["Current Cost"]},
            "evidence": {"page": None, "sheet": SHEET, "row": index,
                         "raw": raw | {"source_url": URL, "source_sha256": manifest[FILE]["sha256"]}},
        }
        validate(project, "national-project")
        projects.append(project)
        dispositions.append({"native_id": native, "locator": locator, "disposition": "accepted",
                             "reason": "Great Lakes row in MISO's projects-under-evaluation workbook"})
    projects.sort(key=lambda p: p["_id"])
    sources = [{"_id": SOURCE_ID, "publisher": "Midcontinent Independent System Operator (MISO)",
                "title": "MTEP Projects Under Evaluation (MTEP26 cycle)", "vintage": "MTEP26 cycle, retrieved date",
                "rights": "Published openly on cdn.misoenergy.org",
                "note": "Under-evaluation projects are proposals; M2 rows are Appendix A approved. The MTEP Appendix A "
                        "status workbook returned HTTP 403 and was not used.",
                "artifacts": [{"file": FILE} | manifest[FILE]]}]
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
    return write_outputs("miso", build(args.cache), args.check)


if __name__ == "__main__":
    sys.exit(main())
