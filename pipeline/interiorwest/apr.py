"""F50 part 2 (C50): 2026 WECC Annual Progress Report rows, transcribed with page quotes and re-verified here.

Each row in data/interiorwest/transcriptions/<file>.json cites a page and a verbatim quote. The build re-extracts the
pinned PDF's text and fails if the quote, title or a facility name is not on that page, or if a stated date or status
is not on that page or an adjacent one. Only transmission work in WY, NV, UT, ID or MT that no other rollout publishes
is kept. A row whose text names no state is placed only by an operator- or voltage-corroborated facility in the
owner's territory, and takes that facility's state.
"""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from california.caiso import match
from common import REPO_ROOT, load_json
from greatlakes.match import candidate_center

TRANSCRIPTIONS = REPO_ROOT / "data" / "interiorwest" / "transcriptions"
BASE = "https://www.wecc.org/sites/default/files/documents/progress_report/2026/"
# transcription file -> (cache name, URL, source ID, publisher)
REPORTS = {
    "apr_nve_2026": ("NVE_2026_APR.pdf", BASE + "NVE%202026%20APR.pdf", "wecc-apr-2026-nve", "NV Energy"),
    "apr_pacificorp_2026": ("PacifiCorp_2026_APR.pdf", BASE + "PacifiCorp%202026%20APR.pdf",
                            "wecc-apr-2026-pacificorp", "PacifiCorp"),
    "apr_ipc_2026": ("IPC_2026_APR.pdf", BASE + "IPC%202026%20APR.pdf", "wecc-apr-2026-ipc", "Idaho Power Company"),
    "apr_gbt_2026": ("GBT_2026_APR.pdf", BASE + "GBT%202026%20APR.pdf", "wecc-apr-2026-gbt", "Great Basin Transmission"),
    "apr_bhc_2026": ("BHC_2026_APR.pdf", BASE + "BHC%202026%20APR.pdf", "wecc-apr-2026-bhc", "Black Hills Corporation"),
}
TERRITORY = {"NV Energy": ["NV"], "PacifiCorp": ["WY", "UT", "ID"], "Idaho Power Company": ["ID"],
             "Great Basin Transmission": ["NV", "ID"], "Cheyenne Light Fuel & Power": ["WY"],
             "Black Hills Energy": ["WY"]}
OPERATOR_KEYS = {"NV Energy": ["NV ENERGY", "NEVADA POWER", "SIERRA PACIFIC"],
                 "PacifiCorp": ["PACIFICORP", "ROCKY MOUNTAIN POWER"], "Idaho Power Company": ["IDAHO POWER"],
                 "Great Basin Transmission": ["GREAT BASIN"], "Cheyenne Light Fuel & Power": ["CHEYENNE LIGHT", "BLACK HILLS"],
                 "Black Hills Energy": ["BLACK HILLS"]}
# Other rollouts' projects a transcribed row may point to with published_as.
PUBLISHED = ("data/pnw/projects.json", "data/southwest/projects.json")
MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov",
                                      "dec"), start=1)}


def flat(text: str) -> str:
    return " ".join(text.split())


def pages(path: Path) -> dict[int, str]:
    with pdfplumber.open(path) as pdf:
        return {i: flat(p.extract_text() or "") for i, p in enumerate(pdf.pages, start=1)}


def in_service(raw: str | None) -> dict:
    """The report's own precision: day, month or year when stated plainly; hedged or conflicting text stays unknown."""
    text = flat(raw or "")
    unknown = {"raw": raw, "value": None, "precision": "unknown"}
    if not text or re.search(r"earliest|no earlier|or later|\d{1,2}/\d{4}", text, re.I):
        return unknown
    if m := re.fullmatch(r"([A-Za-z]{3})[a-z]*\.? (\d{1,2}), (20\d\d)", text):
        if m[1].lower() in MONTHS:
            return {"raw": raw, "value": f"{m[3]}-{MONTHS[m[1].lower()]:02d}-{int(m[2]):02d}", "precision": "day"}
    if m := re.fullmatch(r"([A-Za-z]{3})[a-z]*\.? (20\d\d)", text):
        if m[1].lower() in MONTHS:
            return {"raw": raw, "value": f"{m[2]}-{MONTHS[m[1].lower()]:02d}", "precision": "month"}
    if m := re.fullmatch(r"(?:(?:Q[1-4]|Spring|Summer|Fall|Autumn|Winter|end of|mid-?)\s*)?(20\d\d)", text, re.I):
        return {"raw": raw, "value": m[1], "precision": "year"}
    return unknown


def status_group(status: str | None, isd: dict, retrieved: str) -> str:
    text = (status or "").lower()
    if re.search(r"in[- ]service|energized", text) and (isd["value"] is None or isd["value"] <= retrieved[:10]):
        return "in_service"
    if "construction" in text:
        return "under_construction"
    return "planned"


def published_ids(root: Path = REPO_ROOT) -> set[str]:
    return {p["_id"] for path in PUBLISHED for p in load_json(root / path)}


def verify(file: str, i: int, row: dict, text: dict[int, str]) -> None:
    page = text.get(row["page"], "")
    missing = [s for s in (row["quote"], row["name"], *row["facilities"]) if flat(s) not in page]
    near = " ".join(text.get(n, "") for n in (row["page"] - 1, row["page"], row["page"] + 1))
    missing += [s for s in (row["in_service_raw"], row["status_raw"]) if s and flat(s) not in near]
    if missing:
        raise SystemExit(f"{file} row {i}: not on page {row['page']}: {missing}")


def locate(row: dict, states: list[str], facilities: dict[str, list[dict]], operator_keys: dict | None = None
           ) -> tuple[dict | None, dict]:
    """C33/C38 match per named facility across the row's states (or, with no stated state, the owner's territory)."""
    keys = (operator_keys or OPERATOR_KEYS).get(row["owner"], [])
    kv = set(row["voltages_kv"])
    pool = [f for s in states for f in facilities.get(s, [])]
    matches = [match(n, pool, keys, kv) for n in row["facilities"]] if row["kind"] else []
    if not row["states"]:  # territory search: a name alone is not enough
        matches = [m | {"status": "territory_needs_corroboration"} if m.get("corroboration") == ["unique_in_state"]
                   else m for m in matches]
    center = candidate_center(row["kind"], matches) if row["kind"] else None
    found = [m for m in matches if m["status"] == "matched"]
    tier = None
    if center:
        tier = "candidate" if all(m["corroboration"] != ["unique_in_state"] for m in found) else "candidate_unique_name"
    fields = ("id", "name", "operator", "voltage", "state", "lat", "lon")
    ends = [{k: v for k, v in m.items() if k not in ("facility", "facility_ids")}
            | ({"facility": {f: m["facility"].get(f) for f in fields}} if m["status"] == "matched" else {})
            for m in matches]
    return center, {"rule": "C33", "tier": tier, "independent_review": False, "kind": row["kind"],
                    "reason": None if row["kind"] else "no_named_facility", "voltages_kv": sorted(kv),
                    "operator_keys": keys, "endpoints": ends,
                    "dataset": f"OpenStreetMap power=substation, {'/'.join(states)} (ODbL)"}


def projects(cache: Path, manifest: dict, facilities: dict[str, list[dict]], fips: dict[str, str],
             reports: dict = REPORTS, territory: dict = TERRITORY, operator_keys: dict = OPERATOR_KEYS,
             transcriptions: Path = TRANSCRIPTIONS, published: set[str] | None = None, scope: str = "C50"
             ) -> tuple[list[dict], list[dict]]:
    """Accepted records and every row's disposition. Another rollout can pass its own reports, territory, operator
    keys, transcription folder and already-published IDs."""
    published = published_ids() if published is None else published
    out, dispositions = [], []
    for file, (name, _, source_id, publisher) in reports.items():
        artifact = manifest[name]
        text = pages(cache / name)
        for i, row in enumerate(load_json(transcriptions / f"{file}.json")["rows"], start=1):
            verify(file, i, row, text)
            native = row["native_id"]
            where = {"source_id": source_id, "locator": f"{name}#page={row['page']}", "name": row["name"]}
            stated = [s for s in row["states"] if s in fips]
            reason = (f"{row['work_type']} work, not a transmission project" if row["work_type"] != "transmission"
                      else f"same project as {row['published_as']}" if row["published_as"] in published
                      else f"published_as {row['published_as']} not found" if row["published_as"]
                      else f"outside {scope} states ({','.join(row['states'])})" if row["states"] and not stated
                      else None)
            if reason:
                dispositions.append(where | {"disposition": "excluded", "reason": reason})
                continue
            center, candidate = locate(row, stated or territory[row["owner"]], facilities, operator_keys)
            states = stated or sorted({e["facility"]["state"] for e in candidate["endpoints"] if "facility" in e})
            if not states:
                dispositions.append(where | {"disposition": "excluded", "reason": "no state in the text and no "
                                             "corroborated facility in the owner's territory"})
                continue
            if not stated:  # the territory search placed it; its point is outside no stated state
                candidate["state_basis"] = "owner_territory_facility"
            pid = f"{source_id}:{native}"
            isd = in_service(row["in_service_raw"])
            group = status_group(row["status_raw"], isd, artifact["retrieved_at"])
            evidence = {"publisher": publisher, "url": artifact["url"], "artifact_sha256": artifact["sha256"],
                        "locator": where["locator"], "source_date": None, "retrieved_at": artifact["retrieved_at"],
                        "access_review": "Public WECC Annual Progress Report PDF on wecc.org; no login.",
                        "facts": row["quote"]}
            events = []
            if group == "in_service":
                events.append({"id": f"{pid}:in-service", "type": "in_service", "date": isd["value"],
                               "precision": isd["precision"], "native_project_link": native,
                               "description": f"Reported “{row['status_raw']}”"
                                              + (f"; in service {isd['value']}." if isd["value"] else "."),
                               "evidence": [evidence]})
            elif isd["value"]:
                events.append({"id": f"{pid}:planned-in-service", "type": "planned_milestone", "date": isd["value"],
                               "precision": isd["precision"], "native_project_link": native,
                               "description": f"Expected in service {row['in_service_raw']} (2026 progress report).",
                               "evidence": [evidence]})
            out.append({
                "_id": pid, "source_id": source_id, "native_id": native, "name": flat(row["name"]),
                "description": flat(row["quote"])[:500], "owner": row["owner"], "other_owners": [],
                "planning_region": "WECC", "states": sorted(fips[s] for s in states), "counties": [],
                "geography_basis": "source_text" if stated else "owner_territory_facility",
                "status": row["status_raw"] or "Not stated", "status_group": group, "in_service": isd,
                "center": center, "location_review": "unreviewed" if center else "unlocated",
                "location_candidate": candidate, "project_events": events,
                "evidence": {"page": row["page"], "sheet": None, "row": None, "source_sha256": artifact["sha256"],
                             "raw": {"quote": row["quote"], "transcription": f"{transcriptions.name}/{file}.json#{i}",
                                     "in_service_raw": row["in_service_raw"], "status_raw": row["status_raw"]}},
            })
            dispositions.append(where | {"disposition": "accepted", "_id": pid,
                                         "location": candidate["tier"] or "unlocated"})
    return out, dispositions
