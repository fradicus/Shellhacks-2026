"""Fixed C29/C26-pattern release of the F46 Midwest projects into the national snapshot.

`midwest.build build` writes data/midwest/{projects,sources}.json and releases/active.json. F30's load_snapshot calls
apply_release(snapshot, root) only when that fixed active file exists; it validates everything again and appends new
sources and projects. No folder scan, network or database access.
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from copy import deepcopy
from pathlib import Path

from common import REPO_ROOT, load_json, validate

FOLDER = Path("data/midwest")
ACTIVE = FOLDER / "releases" / "active.json"
RELEASE_ID = "midwest-spp-miso-candidates-4"
TIERS = ("candidate", "candidate_unique_name")
FIPS = {"19", "29", "20", "31", "38", "46"}  # IA, MO, KS, NE, ND, SD


def counts(projects: list[dict], sources: list[dict]) -> dict:
    tiers = Counter(p["location_candidate"]["tier"] for p in projects if p["center"])
    return {"projects": len(projects), "sources": len(sources), "centers": sum(tiers.values()),
            **{tier: tiers[tier] for tier in TIERS},
            "distinct_points": len({(p["center"]["lat"], p["center"]["lon"]) for p in projects if p["center"]})}


def release(outputs: dict[Path, object]) -> dict[Path, object]:
    from .build import OUT, sha

    projects, sources = outputs[OUT / "projects.json"], outputs[OUT / "sources.json"]
    return {REPO_ROOT / ACTIVE: {"release_id": RELEASE_ID, "policy": "C25", "rule": "C33",
                                 "files": {"projects": sha(projects), "sources": sha(sources)},
                                 "expected_counts": counts(projects, sources)}}


def _check_center(project: dict, snapshot: dict) -> None:
    center, candidate = project["center"], project["location_candidate"]
    if project["location_review"] != "unreviewed" or candidate["independent_review"] is not False:
        raise ValueError(f"{project['_id']}: a released location must be unreviewed")
    bounds = [s["bounds"] for s in snapshot["geography"]["states"] if s["state_fips"] in project["states"]]
    lat, lon = center["lat"], center["lon"]
    if not (math.isfinite(lat) and math.isfinite(lon)) or not any(
            b["south"] - 0.05 <= lat <= b["north"] + 0.05 and b["west"] - 0.05 <= lon <= b["east"] + 0.05
            for b in bounds):
        raise ValueError(f"{project['_id']}: center outside its states")
    points = [e["facility"] for e in candidate["endpoints"] if e["status"] == "matched"]
    basis = "source_point" if candidate["kind"] == "site" else ("two" if len(points) == 2 else "one")
    if (candidate["tier"] not in TIERS or not center["evidence"].startswith("Unverified candidate:")
            or not points or len(points) > 2 or center["basis"] != basis
            or abs(sum(p["lat"] for p in points) / len(points) - lat) > 1e-6
            or abs(sum(p["lon"] for p in points) / len(points) - lon) > 1e-6):
        raise ValueError(f"{project['_id']}: candidate center does not follow its matched facilities")


def apply_release(snapshot: dict, root: Path) -> dict:
    path = root / ACTIVE
    if not path.exists():
        return snapshot
    release_ = load_json(path)
    if release_["release_id"] != RELEASE_ID or release_["policy"] != "C25" or release_["rule"] != "C33":
        raise ValueError("Midwest release manifest changed")
    for name in ("projects", "sources"):
        if hashlib.sha256((root / FOLDER / f"{name}.json").read_bytes()).hexdigest() != release_["files"][name]:
            raise ValueError(f"Midwest release file hash changed: {name}")
    projects, sources = load_json(root / FOLDER / "projects.json"), load_json(root / FOLDER / "sources.json")
    by_source = {s["_id"]: s for s in sources}
    if len(by_source) != len(sources) or by_source.keys() & {s["_id"] for s in snapshot["sources"]}:
        raise ValueError("Midwest source identity conflicts")
    ids = [p["_id"] for p in projects]
    if len(set(ids)) != len(ids) or set(ids) & {p["_id"] for p in snapshot["projects"]}:
        raise ValueError("Midwest project identity conflicts")
    for source in sources:
        validate(source, "national-source")
    per_source = Counter(p["source_id"] for p in projects)
    for project in projects:
        validate(project, "national-project")
        source = by_source.get(project["source_id"])
        if source is None or project["evidence"]["source_sha256"] != source["sha256"]:
            raise ValueError(f"{project['_id']}: source or evidence hash mismatch")
        if not project["states"] or not set(project["states"]) <= FIPS:
            raise ValueError(f"{project['_id']}: states outside F46")
        if project["center"]:
            _check_center(project, snapshot)
        elif project["location_review"] != "unlocated":
            raise ValueError(f"{project['_id']}: unlocated project with a review state")
    if any(s["project_count"] != per_source[s["_id"]] for s in sources):
        raise ValueError("Midwest source project counts changed")
    measured = counts(projects, sources)
    if measured != release_["expected_counts"]:
        raise ValueError(f"Midwest counts changed: {measured} != {release_['expected_counts']}")
    result = deepcopy(snapshot)
    result["sources"].extend(deepcopy(sources))
    result["projects"].extend(deepcopy(projects))
    result["coverage"]["midwest"] = {
        "release_id": RELEASE_ID, **measured, "independently_confirmed_projects": 0,
        "notes": "SPP-approved transmission upgrades (Q3 2026 project tracking) and MISO MTEP26 projects under "
                 "evaluation in IA, MO, KS, NE, ND and SD. Candidate points are labeled and never confirmed; no "
                 "statewide completeness claim.",
    }
    return result
