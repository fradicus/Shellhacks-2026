"""FIX-F47: completed SPP upgrades that only older Quarterly Project Tracking editions list (C47 states).

SPP drops an upgrade from its tracking workbook some time after it is complete, so the 2026 Q3 edition misses most of
the region's finished work. The Q4 editions F39 pins (2017–2025, public, no login) still list it. Each UID absent from
2026 Q3 is read from the newest edition that lists it and kept only if that edition calls it complete, closed out or
in service; an upgrade dropped while still planned says nothing about what happened next and is excluded. Records,
dates and locations follow C43 part 1 and F47 exactly.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote

from greatlakes.match import voltages_kv
from midwest import build as spp
from southeast import misospp

EDITIONS = [e for e in misospp.SPP_EDITIONS if e != "2026q3"]  # newest first


def source_id(edition: str, suffix: str = "south") -> str:
    return f"spp-qpt-{edition}-{suffix}"


def files() -> dict[str, str]:
    """Cache name -> URL for every older edition."""
    return {misospp.spp_file(e): "https://www.spp.org" + quote(misospp.SPP_EDITIONS[e]) for e in EDITIONS}


def project(uid: str, edition: str, n: int, sheet: str, member: str | None, c: dict, artifact: dict,
            facilities: dict[str, list[dict]], states: list[str], fips: dict[str, str], keys: dict[str, list[str]],
            suffix: str = "south") -> dict:
    sid = source_id(edition, suffix)
    pid = f"{sid}:{uid}"
    status = " ".join(str(c["projectstatus"] or "").split())
    locator = f"{misospp.spp_file(edition)}{'!' + member if member else ''}#{sheet}!row-{n}"
    title = misospp.spp_title(edition)
    evidence = {"publisher": "Southwest Power Pool", "url": artifact["url"], "artifact_sha256": artifact["sha256"],
                "locator": locator, "source_date": None, "retrieved_at": artifact["retrieved_at"],
                "access_review": "Public SPP workbook; no login.", "facts": ""}
    cell = c["projectownerindicatedin-servicedate"]
    value = misospp.day(cell)
    events = spp.dated_events(pid, uid, status, "in_service", value, artifact, evidence,
                              "Owner-indicated in-service date", "owner-in-service", title,
                              "Project Owner Indicated In-Service Date")
    name = " ".join(str(c["upgradename"]).split())
    owner = str(c["projectowner"] or "").strip()
    kv = voltages_kv(name) | {int(v) for v in re.findall(r"\d+", str(c.get("voltages(kv)") or "")) if int(v) > 0}
    center, candidate = spp.locate(name, kv, states, facilities, keys.get(owner, []))
    description = c.get("projectdescriptioncomments")
    return {
        "_id": pid, "source_id": sid, "native_id": uid, "name": name,
        "major_project": " ".join(str(c["projectname"]).split()) if c.get("projectname") else None, "part": name,
        "description": " ".join(str(description).split())[:500] if description else None,
        "owner": None if owner.upper() in ("", "TBD") else owner, "other_owners": [], "planning_region": "spp",
        "states": [fips[s] for s in states], "counties": [], "geography_basis": "source_state",
        "status": f"{status} (last listed in {title})", "status_group": "in_service",
        "in_service": {"raw": misospp.clean(cell) if cell is not None else None, "value": value,
                       "precision": "day" if value else "unknown"},
        "center": center, "location_review": "unreviewed" if center else "unlocated",
        "location_candidate": candidate, "project_events": events,
        "evidence": {"page": None, "sheet": sheet, "row": n, "source_sha256": artifact["sha256"],
                     "raw": {k: misospp.clean(v) for k, v in c.items() if k}},
    }


def projects(cache: Path, manifest: dict, current: set[str], taken: set[str], facilities: dict[str, list[dict]],
             fips: dict[str, str], keys: dict[str, list[str]], scope: str, suffix: str = "south"
             ) -> tuple[list[dict], list[dict], dict]:
    """Records, dispositions and the artifact of each edition used, for UIDs in `fips` states absent from `current`.
    Another SPP rollout passes its own states, operator keys and source-ID suffix."""
    seen, out, dispositions, used = set(current) | set(taken), [], [], {}
    for edition in EDITIONS:
        name = misospp.spp_file(edition)
        artifact = manifest[name]
        sheet, member, rows = misospp.spp_rows(cache / name)
        for n, c, _ in rows:
            uid = str(c["uid"]).strip()
            states = spp.row_states(c["state(s)"])
            if uid in seen or not states or not set(states) <= fips.keys():
                continue
            seen.add(uid)
            status = " ".join(str(c["projectstatus"] or "").split())
            where = {"source_id": source_id(edition, suffix), "sheet": sheet, "row": n, "uid": uid,
                     "name": " ".join(str(c["upgradename"] or "").split())}
            if misospp.spp_group(status) != "in_service":
                dispositions.append(where | {"disposition": "excluded", "reason": f"dropped after {edition} while "
                                             f"“{status}”; its outcome is not in any edition ({scope})"})
                continue
            record = project(uid, edition, n, sheet, member, c, artifact, facilities, states, fips, keys, suffix)
            out.append(record)
            used[edition] = artifact
            dispositions.append(where | {"disposition": "accepted", "_id": record["_id"],
                                         "location": record["location_candidate"]["tier"] or "unlocated"})
    return out, dispositions, used


def sources(used: dict, projects_: list[dict], scope_note: str, suffix: str = "south") -> list[dict]:
    out = []
    for edition, artifact in used.items():
        sid = source_id(edition, suffix)
        out.append({
            "_id": sid, "publisher": "Southwest Power Pool", "title": misospp.spp_title(edition),
            "authority": "regional_planning_organization", "role": "project_plan",
            "landing_url": misospp.SPP_INDEX, "download_url": artifact["url"], "publication_date": None,
            "vintage": f"{edition[:4]} {edition[4:].upper()}", "retrieved_at": artifact["retrieved_at"],
            "sha256": artifact["sha256"], "public_status": "verified_public", "import_status": "imported",
            "access_policy": "public_document", "planning_region": "spp",
            "states": sorted({s for p in projects_ if p["source_id"] == sid for s in p["states"]}),
            "project_count": sum(p["source_id"] == sid for p in projects_),
            "notes": [scope_note, "Only upgrades this edition calls complete, closed out or in service and that no "
                      "newer edition lists. Locations are unreviewed C33 candidates; none is independently confirmed."]})
    return out
