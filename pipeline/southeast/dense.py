"""C45 dense Southeast release: labeled, unreviewed batches appended after the Florida tentative release.

Each source module writes one batch folder, data/southeast/dense/<batch>/{projects,sources,dispositions,summary}.json,
and records its pinned file hashes and expected counts in the single fixed release file. `apply_release` replays
those checks; a missing release file changes nothing. No folder scan, network or database access.
OSM data (c) OpenStreetMap contributors, ODbL 1.0.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path

from california.caiso import match, named
from common import REPO_ROOT, load_json, validate, write_json
from greatlakes.match import candidate_center, voltages_kv

FOLDER = Path("data/southeast/dense")
ACTIVE = FOLDER / "releases" / "active.json"
RELEASE_ID = "southeast-dense-1"
# Fixed application order; a batch absent from the release file is simply not applied.
BATCHES = ("aep", "duke", "scrtp")
FILES = ("projects", "sources")
TIERS = ("official", "candidate", "candidate_unique_name")
SE_STATES = {"FL": "12", "GA": "13", "AL": "01", "MS": "28", "SC": "45", "NC": "37", "TN": "47", "KY": "21",
             "VA": "51", "WV": "54", "AR": "05", "LA": "22"}
OSM_DATASET = "OpenStreetMap power=substation (ODbL), reported state"


def sha(value: object) -> str:
    """Byte-identical to common.write_json, so the release can pin committed file hashes."""
    return hashlib.sha256((json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()).hexdigest()


def official_center(lat: float, lon: float, evidence: str) -> dict:
    return {"lat": round(lat, 6), "lon": round(lon, 6), "basis": "source_point",
            "evidence": f"Official source: {evidence}; placement precision unstated; not independently reviewed."}


def locate(name: str, description: str | None, facilities: list[dict], keys: list[str]) -> tuple[dict | None, dict]:
    """C33 candidate (C38 operator guard) from facility names the source text states, else None with the reason."""
    # "230-115 kV" names two voltages; F40's key only strips the slash form, so the facility name kept "230-115".
    name = re.sub(r"(\d+)\s*-\s*(?=\d+(?:\s*[-/]\s*\d+)*\s*-?\s*kV)", r"\1/", name, flags=re.I)
    got = named(name, description)
    kv = voltages_kv(name)
    matches = [match(n, facilities, keys, kv) if n else {"status": "not_a_facility", "name": None}
               for n in got["names"]]
    center = candidate_center(got["kind"], matches) if got["kind"] else None
    fields = ("id", "name", "operator", "voltage", "lat", "lon")
    endpoints = [{k: v for k, v in m.items() if k not in ("facility", "facility_ids")}
                 | ({"facility": {f: m["facility"].get(f) for f in fields}} if m["status"] == "matched" else {})
                 for m in matches]
    found = [m for m in matches if m["status"] == "matched"]
    tier = None
    if center:
        tier = "candidate" if all(m["corroboration"] != ["unique_in_state"] for m in found) else "candidate_unique_name"
    return center, {"rule": "C45", "tier": tier, "independent_review": False, "kind": got["kind"],
                    "reason": got["reason"], "voltages_kv": sorted(kv), "operator_keys": keys,
                    "endpoints": endpoints, "dataset": OSM_DATASET}


def counts(projects: list[dict], sources: list[dict]) -> dict:
    located = [p for p in projects if p["center"]]
    tiers = Counter(p["location_candidate"]["tier"] for p in located)
    return {"projects": len(projects), "sources": len(sources), "located": len(located),
            **{tier: tiers[tier] for tier in TIERS},
            "distinct_points": len({(p["center"]["lat"], p["center"]["lon"]) for p in located}),
            "located_not_in_service": sum(p["status_group"] not in ("in_service", "cancelled") for p in located),
            "located_dated": sum(bool(p.get("project_events") or p["in_service"]["value"]) for p in located),
            "by_state": dict(sorted(Counter(s for p in projects for s in p["states"]).items())),
            "located_by_state": dict(sorted(Counter(s for p in located for s in p["states"]).items()))}


def summary(projects: list[dict], sources: list[dict]) -> dict:
    reasons = Counter(
        p["location_candidate"].get("reason") or ",".join(sorted({e["status"] for e in
                                                                  p["location_candidate"].get("endpoints", [])}))
        or "none" for p in projects if not p["center"])
    return {**counts(projects, sources), "verified": 0,
            "by_status": dict(sorted(Counter(p["status_group"] for p in projects).items())),
            "unlocated_reasons": dict(sorted(reasons.items()))}


def write_batch(batch: str, projects: list[dict], sources: list[dict], dispositions: list[dict],
                check: bool = False, root: Path = REPO_ROOT) -> int:
    """Write (or with check, compare) one batch and its pinned release entry."""
    if batch not in BATCHES:
        raise ValueError(f"unknown batch {batch}")
    projects = sorted(projects, key=lambda p: p["_id"])
    folder = root / FOLDER / batch
    release_path = root / ACTIVE
    release = load_json(release_path) if release_path.exists() else {
        "release_id": RELEASE_ID, "policy": "C25", "rule": "C45", "batches": {}}
    release["batches"][batch] = {"files": {"projects": sha(projects), "sources": sha(sources)},
                                 "expected_counts": counts(projects, sources)}
    release["batches"] = {b: release["batches"][b] for b in BATCHES if b in release["batches"]}
    outputs = {folder / "projects.json": projects, folder / "sources.json": sources,
               folder / "dispositions.json": dispositions, folder / "summary.json": summary(projects, sources),
               release_path: release}
    if check:
        stale = [str(p) for p, v in outputs.items() if not p.exists() or load_json(p) != v]
        print("stale: " + ", ".join(stale) if stale else "ok")
        return 1 if stale else 0
    for path, value in outputs.items():
        write_json(path, value)
    print(json.dumps(outputs[folder / "summary.json"], indent=2))
    return 0


def _in_states(lat: float, lon: float, states: list[str], snapshot: dict) -> bool:
    bounds = [s["bounds"] for s in snapshot["geography"]["states"] if s["state_fips"] in states]
    return any(b["south"] - 0.05 <= lat <= b["north"] + 0.05 and b["west"] - 0.05 <= lon <= b["east"] + 0.05
               for b in bounds)


def check_center(project: dict, snapshot: dict) -> None:
    pid, center, candidate = project["_id"], project["center"], project["location_candidate"]
    if project["location_review"] != "unreviewed" or candidate["independent_review"] is not False:
        raise ValueError(f"{pid}: a released location must be unreviewed")
    lat, lon = center["lat"], center["lon"]
    if not (math.isfinite(lat) and math.isfinite(lon)) or not _in_states(lat, lon, project["states"], snapshot):
        raise ValueError(f"{pid}: center outside the project's reported states")
    if candidate["tier"] == "official":
        point = candidate["source_point"]
        if (center["basis"] != "source_point" or not center["evidence"].startswith("Official source:")
                or abs(point["lat"] - lat) > 1e-6 or abs(point["lon"] - lon) > 1e-6):
            raise ValueError(f"{pid}: official center does not reproduce its source point")
        return
    points = [e["facility"] for e in candidate["endpoints"] if e["status"] == "matched"]
    basis = "source_point" if candidate["kind"] == "site" else ("two" if len(points) == 2 else "one")
    if (candidate["tier"] not in TIERS or not center["evidence"].startswith("Unverified candidate:")
            or not points or len(points) > 2 or center["basis"] != basis
            or abs(sum(p["lat"] for p in points) / len(points) - lat) > 1e-6
            or abs(sum(p["lon"] for p in points) / len(points) - lon) > 1e-6):
        raise ValueError(f"{pid}: candidate center does not follow its matched facilities")


def check_batch(batch: str, entry: dict, snapshot: dict, root: Path) -> tuple[list[dict], list[dict]]:
    for name in FILES:
        if hashlib.sha256((root / FOLDER / batch / f"{name}.json").read_bytes()).hexdigest() != entry["files"][name]:
            raise ValueError(f"Southeast dense file hash changed: {batch}/{name}")
    projects = load_json(root / FOLDER / batch / "projects.json")
    sources = load_json(root / FOLDER / batch / "sources.json")
    by_source = {s["_id"]: s for s in sources}
    existing = {s["_id"] for s in snapshot["sources"]} | {p["_id"] for p in snapshot["projects"]}
    ids = [p["_id"] for p in projects]
    if len(by_source) != len(sources) or len(set(ids)) != len(ids) or existing & (set(ids) | set(by_source)):
        raise ValueError(f"Southeast dense {batch}: identity conflicts")
    for source in sources:
        validate(source, "national-source")
    se = set(SE_STATES.values())
    for project in projects:
        validate(project, "national-project")
        source = by_source.get(project["source_id"])
        if not project["_id"].startswith("southeast:") or source is None:
            raise ValueError(f"{project['_id']}: namespace or source missing")
        if project["evidence"]["source_sha256"] != source["sha256"]:
            raise ValueError(f"{project['_id']}: evidence hash does not match its source")
        # A multi-state footprint source (e.g. one planning region) may leave an unlocated row's state unknown.
        if project["states"] and not se & set(project["states"]) or project["center"] and not project["states"]:
            raise ValueError(f"{project['_id']}: no Southeast state")
        if project["center"]:
            check_center(project, snapshot)
        elif project["location_review"] != "unlocated":
            raise ValueError(f"{project['_id']}: unlocated project with a review state")
    per_source = Counter(p["source_id"] for p in projects)
    if any(s["project_count"] != per_source[s["_id"]] for s in sources):
        raise ValueError(f"Southeast dense {batch}: source project counts changed")
    measured = counts(projects, sources)
    if measured != entry["expected_counts"]:
        raise ValueError(f"Southeast dense {batch}: counts changed: {measured} != {entry['expected_counts']}")
    return projects, sources


def apply_release(snapshot: dict, root: Path) -> dict:
    path = root / ACTIVE
    if not path.exists():
        return snapshot
    release = load_json(path)
    if release["release_id"] != RELEASE_ID or release["policy"] != "C25" or release["rule"] != "C45":
        raise ValueError("Southeast dense release manifest changed")
    if not set(release["batches"]) <= set(BATCHES):
        raise ValueError("Southeast dense release names an unknown batch")
    result = deepcopy(snapshot)
    coverage = {}
    for batch in BATCHES:
        if batch not in release["batches"]:
            continue
        projects, sources = check_batch(batch, release["batches"][batch], result, root)
        result["sources"].extend(deepcopy(sources))
        result["projects"].extend(deepcopy(projects))
        coverage[batch] = release["batches"][batch]["expected_counts"]
    result["coverage"]["southeast_dense"] = {
        "release_id": RELEASE_ID, "batches": coverage, "independently_confirmed_projects": 0,
        "notes": "C45 labeled tiers: official source points and OSM name candidates, all unreviewed; "
                 "source-bounded, no statewide completeness claim."}
    return result


def refresh(root: Path = REPO_ROOT) -> dict:
    """Re-pin every committed batch (after a merge of two batch branches); producers still own the batch files."""
    release = {"release_id": RELEASE_ID, "policy": "C25", "rule": "C45", "batches": {}}
    for batch in BATCHES:
        folder = root / FOLDER / batch
        if (folder / "projects.json").exists():
            projects, sources = load_json(folder / "projects.json"), load_json(folder / "sources.json")
            release["batches"][batch] = {"files": {"projects": sha(projects), "sources": sha(sources)},
                                         "expected_counts": counts(projects, sources)}
    write_json(root / ACTIVE, release)
    return release


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


if __name__ == "__main__":
    print(json.dumps(refresh(), indent=2))
