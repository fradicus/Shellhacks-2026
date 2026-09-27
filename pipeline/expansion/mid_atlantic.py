"""Validate and assemble the fixed C28 Mid-Atlantic release; no network or database writes."""
from __future__ import annotations

import math
from collections import Counter
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from common import REPO_ROOT, load_json, validate
from expansion.new_england import facts_hash
from expansion.publish import center, check_evidence, record_hash, utc
from southeast.publish import check_date, check_events, release_hash, unique

ACTIVE_RELEASE = Path("data/expansion/mid-atlantic/releases/active.json")
EVIDENCE_SCHEMA = load_json(REPO_ROOT / "schemas/expansion-release.schema.json")["$defs"]["evidence"]
WORLD_MERCATOR_TRANSFORM = "Inverse ellipsoidal World Mercator (EPSG:3395), WGS84 a=6378137, e2=0.0066943799901413165"
WEB_MERCATOR_TRANSFORM = "Inverse spherical Web Mercator (EPSG:3857), radius=6378137 metres"


def world_mercator_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """Inverse EPSG:3395 using WGS84 ellipsoidal Mercator, longitude first.

    Iterate latitude to convergence (15 steps exceeds double precision here).
    This differs from EPSG:3857's spherical latitude by about 0.19 degrees
    around New York; substituting the spherical formula must fail validation.
    """
    eccentricity = math.sqrt(0.0066943799901413165)
    t = math.exp(-y / 6378137)
    latitude = math.pi / 2 - 2 * math.atan(t)
    for _ in range(15):
        esin = eccentricity * math.sin(latitude)
        latitude = math.pi / 2 - 2 * math.atan(t * ((1 - esin) / (1 + esin)) ** (eccentricity / 2))
    return math.degrees(x / 6378137), math.degrees(latitude)


def check_point(point: dict) -> None:
    original = point["original_geometry"]
    x, y = original["coordinates"]
    if not all(math.isfinite(v) for v in [x, y, point["lat"], point["lon"]]):
        raise ValueError("nonfinite point")
    if original["crs"] == "EPSG:4326":
        lon, lat = x, y
    elif original["crs"] in {"EPSG:3857", "EPSG:3395"}:
        if abs(x) > 20037509 or abs(y) > 20037509:
            raise ValueError("Mercator coordinate outside supported domain")
        if original["crs"] == "EPSG:3857" and original["transform"] == WEB_MERCATOR_TRANSFORM:
            lon, lat = math.degrees(x / 6378137), math.degrees(math.atan(math.sinh(y / 6378137)))
        elif original["crs"] == "EPSG:3395" and original["transform"] == WORLD_MERCATOR_TRANSFORM:
            lon, lat = world_mercator_to_wgs84(x, y)
        else:
            raise ValueError("source CRS transformation method is unsupported")
    else:
        raise ValueError("source CRS requires an independently reproduced supported transformation")
    if abs(lon - point["lon"]) > 1e-7 or abs(lat - point["lat"]) > 1e-7:
        raise ValueError("source transformation does not reproduce point")
    # Continental bounds permit evidenced cross-border endpoints. They do not establish state membership.
    if not (-125 < lon < -66 and 24 < lat < 50):
        raise ValueError("point outside continental release bounds or axes reversed")
    for evidence in point["geometry_evidence"] + point["identity_evidence"]:
        check_evidence(evidence)


def check_location(record: dict, project: dict) -> str:
    if record["project_facts_sha256"] != facts_hash(project):
        raise ValueError("location project facts changed")
    roles = [point["role"] for point in record["points"]]
    if len(set(roles)) != len(roles) or not set(roles) <= ({"site"} if record["location_kind"] == "site" else {"a", "b"}):
        raise ValueError("invalid or duplicate endpoint roles")
    unique(record["points"], "facility_id")
    for point in record["points"]:
        check_point(point)
    check_events(record["events"], project)
    unique(record["reviews"], "id")
    last_time = None
    evidence = [e for p in record["points"] for e in p["geometry_evidence"] + p["identity_evidence"]]
    evidence.extend(e for event in record["events"] for e in event["evidence"])
    acquired = max(utc(e["retrieved_at"]) for e in evidence)
    for review in record["reviews"]:
        when = utc(review["reviewed_at"])
        if review["reviewer"] == record["producer"]:
            raise ValueError("location self-review")
        if last_time is not None and when < last_time:
            raise ValueError("location reviews out of order")
        if review["facts_sha256"] == record_hash(record) and when < acquired:
            raise ValueError("location review predates evidence")
        last_time = when
    if not record["reviews"]:
        return "no_review"
    review = record["reviews"][-1]
    return review["decision"] if review["facts_sha256"] == record_hash(record) else "stale_review"


def apply_release(snapshot: dict, root: Path) -> dict:
    path = root / ACTIVE_RELEASE
    if not path.exists():
        return snapshot
    release = load_json(path)
    validate(release, "mid-atlantic-release")
    created = utc(release["created_at"])
    review = release["identity_review"]
    reviewed = utc(review["reviewed_at"])
    if review["reviewer"] == release["producer"] or review["facts_sha256"] != release_hash(release):
        raise ValueError("missing independent current identity review")
    if reviewed < created:
        raise ValueError("identity review predates release")
    sources = unique(release["sources"], "_id")
    projects = unique(release["projects"], "_id")
    if len({(p["source_id"], p["native_id"]) for p in projects.values()}) != len(projects):
        raise ValueError("duplicate primary native project identity")
    existing_sources = unique(snapshot["sources"], "_id")
    existing_projects = unique(snapshot["projects"], "_id")
    if sources.keys() & existing_sources.keys() or projects.keys() & existing_projects.keys():
        raise ValueError("release cannot overwrite existing identities")
    # Planning-region/native identifiers are shared across vintages and producers.
    # Null/empty region or native IDs provide no known identity to compare.
    known = {(p["planning_region"], p["native_id"]) for p in existing_projects.values()
             if p.get("planning_region") and p.get("native_id")}
    for project in projects.values():
        if project.get("planning_region") and project.get("native_id"):
            identity = project["planning_region"], project["native_id"]
            if identity in known:
                raise ValueError("duplicate known planning region/native project identity")
            known.add(identity)
    acquisition = unique(release["acquisition"], "source_id")
    if acquisition.keys() != sources.keys():
        raise ValueError("every new source requires exactly one acquisition ledger")
    rows, accepted = set(), set()
    for row in release["dispositions"]:
        key = row["source_id"], row["locator"]
        if key in rows or row["source_id"] not in sources:
            raise ValueError("duplicate or unknown source disposition")
        rows.add(key)
        pid = row["project_id"]
        if row["disposition"] in {"accepted", "duplicate"} and pid not in projects and pid not in existing_projects:
            raise ValueError("disposition references unknown project")
        if row["disposition"] == "accepted":
            if pid not in projects or projects[pid]["source_id"] != row["source_id"]:
                raise ValueError("accepted row must reference its primary source and new project")
            accepted.add((row["source_id"], pid))
    for sid, source in sources.items():
        if source["retrieved_at"] is None or utc(source["retrieved_at"]) > reviewed:
            raise ValueError("source acquisition missing or after identity review")
        ledger = acquisition[sid]
        acquired = set(ledger["row_locators"])
        if acquired != {locator for source_id, locator in rows if source_id == sid}:
            raise ValueError("acquisition and disposition row sets differ")
        expected = ledger["expected_source_rows"]
        if expected is not None and expected < len(acquired):
            raise ValueError("acquired more rows than known source total")
        if ledger["completeness"] == "complete" and expected != len(acquired):
            raise ValueError("complete acquisition requires a matching known total")
        for evidence in ledger["enumeration_evidence"]:
            check_evidence(evidence)
            if utc(evidence["retrieved_at"]) > reviewed:
                raise ValueError("identity review predates enumeration")
        if not any(e["artifact_sha256"] == source["sha256"] for e in ledger["enumeration_evidence"]):
            raise ValueError("source hash missing from acquisition evidence")
        if source.get("project_count") != sum(p["source_id"] == sid for p in projects.values()):
            raise ValueError("source project count mismatch")
    for project in projects.values():
        sid = project["source_id"]
        if sid not in sources or (sid, project["_id"]) not in accepted:
            raise ValueError("new project lacks an accepted primary source row")
        if project["evidence"].get("source_sha256") != sources[sid]["sha256"]:
            raise ValueError("national project source hash missing or changed")
        check_date(project["in_service"]["value"], project["in_service"]["precision"])
        evidence = project["evidence"]["raw"].get("source_evidence", [])
        if not evidence:
            raise ValueError("project requires typed source_evidence in raw evidence")
        for item in evidence:
            Draft202012Validator(EVIDENCE_SCHEMA, format_checker=FormatChecker()).validate(item)
            check_evidence(item)
            if utc(item["retrieved_at"]) > reviewed:
                raise ValueError("identity review predates project evidence")
        project_rows = {row["locator"] for row in release["dispositions"] if row["source_id"] == sid
                        and row["project_id"] == project["_id"] and row["disposition"] == "accepted"}
        if not any(e["artifact_sha256"] == sources[sid]["sha256"] and e["locator"] in project_rows and
                   e["url"] in {sources[sid]["landing_url"], sources[sid]["download_url"]} for e in evidence):
            raise ValueError("project source hash and row locator not bound")
    locations = unique(release["location_verifications"], "project_id")
    histories = unique(release["project_events"], "project_id")
    if not locations.keys() <= projects.keys() or not histories.keys() <= projects.keys():
        raise ValueError("location or history references unknown new project")
    decisions = {pid: check_location(record, projects[pid]) for pid, record in locations.items()}
    if any(utc(review["reviewed_at"]) > reviewed for record in locations.values() for review in record["reviews"]):
        raise ValueError("identity review predates included location review")
    if any(utc(e["retrieved_at"]) > reviewed for record in locations.values() for point in record["points"]
           for e in point["geometry_evidence"] + point["identity_evidence"]):
        raise ValueError("identity review predates location evidence")
    for pid, history in histories.items():
        check_events(history["events"], projects[pid])
    all_events = {}
    event_projects = {event["id"]: pid for pid, project in existing_projects.items()
                      for event in project.get("project_events", []) + project.get("location_verification", {}).get("events", [])}
    for pid in projects:
        all_events[pid] = {}
        for event in histories.get(pid, {}).get("events", []) + locations.get(pid, {}).get("events", []):
            if event["id"] in event_projects and event_projects[event["id"]] != pid:
                raise ValueError("event id reused across projects")
            event_projects[event["id"]] = pid
            prior = all_events[pid].get(event["id"])
            if prior is not None and prior != event:
                raise ValueError("conflicting duplicate event id")
            if any(utc(e["retrieved_at"]) > reviewed for e in event["evidence"]):
                raise ValueError("identity review predates event evidence")
            all_events[pid][event["id"]] = event
    counts = {"new_sources": len(sources), "new_projects": len(projects),
              "confirmed_projects": sum(v == "confirmed" for v in decisions.values()), "source_rows": len(rows)}
    if counts != release["expected_counts"]:
        raise ValueError("release expected counts mismatch")
    result = deepcopy(snapshot)
    new_projects = deepcopy(list(projects.values()))
    for project in new_projects:
        pid = project["_id"]
        if all_events[pid]:
            project["project_events"] = list(all_events[pid].values())
        if pid in locations:
            project["location_verification"] = deepcopy(locations[pid])
            project["location_review"] = ("confirmed" if decisions[pid] == "confirmed" else
                                          "rejected" if decisions[pid] == "rejected" else "needs_review")
            if decisions[pid] == "confirmed":
                project["center"] = center(locations[pid])
        validate(project, "national-project")
    result["sources"].extend(deepcopy(list(sources.values())))
    result["projects"].extend(new_projects)
    confirmed = [locations[pid] for pid, decision in decisions.items() if decision == "confirmed"]
    result["coverage"]["mid_atlantic"] = {
        **counts, "release_id": release["release_id"], "notes": release["coverage_notes"],
        "state_counts": dict(Counter(state for p in new_projects for state in p["states"])),
        "status_counts": dict(Counter(p["status_group"] for p in new_projects)),
        "source_counts": dict(Counter(p["source_id"] for p in new_projects)),
        "review_counts": dict(Counter(decisions.values())),
        "unlocated_projects": sum(p["center"] is None for p in new_projects),
        "complete_endpoint_projects": sum(r["location_kind"] == "line" and len(r["points"]) == 2 for r in confirmed),
        "partial_endpoint_projects": sum(r["location_kind"] == "line" and len(r["points"]) == 1 for r in confirmed),
        "standalone_site_projects": sum(r["location_kind"] == "site" for r in confirmed),
        "distinct_map_positions": len({(p["center"]["lat"], p["center"]["lon"])
                                       for p in new_projects if p["center"] is not None}),
        "unresolved_reasons": dict(Counter(decisions.get(p["_id"], "no_location")
                                           for p in new_projects if p["center"] is None)),
        "distinct_facility_sites": len({p["facility_id"] for r in confirmed for p in r["points"]}),
        "source_completeness": {sid: row["completeness"] for sid, row in acquisition.items()},
        "source_freshness": {sid: {key: source[key] for key in ["publication_date", "vintage", "retrieved_at"]}
                             for sid, source in sources.items()},
        "confirmed_state_counts": dict(Counter(state for p in new_projects if p["center"] is not None
                                               for state in p["states"])),
        "event_type_counts": dict(Counter(event["type"] for events in all_events.values() for event in events.values())),
    }
    return result
