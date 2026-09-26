"""Audit subjects (C7, #57): the facts a review confirms, projected and hashed the same way every time, so a
confirmation stops applying the moment any of those facts change. Pure functions; F13 reuses only the projection and
the hash, its own geometry/date/source audit stays independent.

Inputs are records as `load.build.join_projects` leaves them (filed names under `filed_endpoints`, located endpoints
under `endpoints`); raw parser records (filed names under `endpoints`) project the same way.
"""

import hashlib
import json
from typing import Any

FINGERPRINT_VERSION = "audit-subject-v1"
PROJECT_FIELDS = ("_id", "project_key", "native_id", "active", "name", "utility", "owner_code", "status", "description")
LOCATION_FIELDS = ("_id", "project_key", "project_id", "source_id", "endpoint_index", "name", "lat", "lon",
                   "confidence", "evidence", "osm_id", "osm_url")
MATCH_FIELDS = ("_id", "a", "b", "distance_mi", "time_gap_days", "band", "rule_version", "analysis_date", "view")


def subject_hash(subject: dict) -> str:
    """SHA-256 of the canonical JSON: sorted keys, no spaces, UTF-8, NaN/inf refused (ValueError)."""
    raw = json.dumps(subject, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _located(p: dict) -> list[dict]:
    """The accepted, coordinate-bearing endpoints a project's center is built from."""
    return [e for e in p.get("endpoints", []) if e.get("confidence") != "rejected" and e.get("lat") is not None]


def _project(p: dict, source: dict) -> dict:
    filed = p["filed_endpoints"] if "filed_endpoints" in p else p.get("endpoints", [])
    return {
        **{k: p.get(k) for k in PROJECT_FIELDS},
        "in_service": {k: p["in_service"].get(k) for k in ("raw", "date", "precision")},
        "source": {k: p["source"].get(k) for k in ("source_id", "page", "row_top")},
        "source_sha256": source["sha256"],
        "filed_endpoints": [{k: e.get(k) for k in ("name", "norm", "raw")} for e in filed],
    }


def endpoint_subject(location: dict, project: dict, source: dict) -> dict:
    """What an endpoint review confirms: the location record and the filing version it belongs to."""
    project_source_id = project["source"]["source_id"]
    if (location["project_key"] != project["project_key"]
            or location.get("project_id", project["_id"]) != project["_id"]
            or location.get("source_id", project_source_id) != project_source_id
            or source["_id"] != project_source_id):
        raise ValueError("contradictory endpoint project/source binding")
    bound_location = {**location, "project_id": project["_id"], "source_id": project_source_id}
    return {"fingerprint_version": FINGERPRINT_VERSION, "subject_type": "endpoint", "record_id": location["_id"],
            "project": _project(project, source), "location": {k: bound_location.get(k) for k in LOCATION_FIELDS}}


def pair_subject(match: dict, projects_by_key: dict[str, dict], locations_by_key: dict[str, list[dict]],
                 sources_by_id: dict[str, dict]) -> dict:
    """What a pair review confirms: the match facts, both projects (the one active version per key, sorted by key)
    and the accepted endpoints those centers came from. KeyError when a key or source is unresolved."""
    projects = [projects_by_key[k] for k in sorted((match["a"], match["b"]))]
    endpoints = [endpoint_subject(loc, p, sources_by_id[p["source"]["source_id"]])
                 for p in projects for loc in locations_by_key.get(p["project_key"], [])]
    endpoints.sort(key=lambda e: (e["project"]["project_key"], e["location"]["endpoint_index"], e["record_id"]))
    return {"fingerprint_version": FINGERPRINT_VERSION, "subject_type": "pair", "record_id": match["_id"],
            "match": {k: match.get(k) for k in MATCH_FIELDS},
            "projects": [_project(p, sources_by_id[p["source"]["source_id"]]) for p in projects],
            "endpoints": endpoints}


def current_subjects(ready: dict[str, list[dict]]) -> dict[tuple[str, str], dict]:
    """(subject_type, record_id) -> subject for every accepted located endpoint (on any filing version) and every
    match. A subject that can't be built (unknown source, zero or several active versions of a key, non-finite
    number) is left out, so no review of it can apply. Run before dataset-prefixing ids."""
    sources = {s["_id"]: s for s in ready.get("sources", [])}
    active: dict[str, list[dict]] = {}
    for p in ready.get("projects", []):
        if p.get("active"):
            active.setdefault(p["project_key"], []).append(p)
    projects_by_key = {k: ps[0] for k, ps in active.items() if len(ps) == 1}
    locations_by_key = {k: _located(p) for k, p in projects_by_key.items()}
    out: dict[tuple[str, str], dict] = {}

    def keep(subject: dict) -> None:
        subject_hash(subject)  # refuses NaN/inf now rather than at apply time
        out[(subject["subject_type"], subject["record_id"])] = subject

    for p in ready.get("projects", []):
        for loc in _located(p):
            try:
                keep(endpoint_subject(loc, p, sources[p["source"]["source_id"]]))
            except (KeyError, TypeError, ValueError):
                continue
    for m in ready.get("matches", []):
        try:
            keep(pair_subject(m, projects_by_key, locations_by_key, sources))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def supporting_endpoints(subject: dict[str, Any]) -> list[str]:
    """Record ids of the endpoints a pair subject rests on."""
    return [e["record_id"] for e in subject.get("endpoints", [])]
