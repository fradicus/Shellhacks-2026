"""Fixed C29/C26-pattern release of the F50 Interior West projects into the national snapshot.

`interiorwest.build build` writes data/interiorwest/{projects,sources}.json and releases/active.json. F30's load_snapshot calls
apply_release(snapshot, root) only when that fixed active file exists; it validates everything again and appends new
sources and projects. No folder scan, network or database access.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from copy import deepcopy
from pathlib import Path

from common import REPO_ROOT, load_json, validate
from midwest.publish import _check_center, counts

FOLDER = Path("data/interiorwest")
ACTIVE = FOLDER / "releases" / "active.json"
RELEASE_ID = "interiorwest-candidates-3"
FIPS = {"56", "32", "49", "16", "30"}  # WY, NV, UT, ID, MT


def release(outputs: dict[Path, object]) -> dict[Path, object]:
    from midwest.build import sha

    from .build import OUT

    projects, sources = outputs[OUT / "projects.json"], outputs[OUT / "sources.json"]
    return {REPO_ROOT / ACTIVE: {"release_id": RELEASE_ID, "policy": "C25", "rule": "C33",
                                 "files": {"projects": sha(projects), "sources": sha(sources)},
                                 "expected_counts": counts(projects, sources)}}


def apply_release(snapshot: dict, root: Path) -> dict:
    path = root / ACTIVE
    if not path.exists():
        return snapshot
    release_ = load_json(path)
    if release_["release_id"] != RELEASE_ID or release_["policy"] != "C25" or release_["rule"] != "C33":
        raise ValueError("Interior West release manifest changed")
    for name in ("projects", "sources"):
        if hashlib.sha256((root / FOLDER / f"{name}.json").read_bytes()).hexdigest() != release_["files"][name]:
            raise ValueError(f"Interior West release file hash changed: {name}")
    projects, sources = load_json(root / FOLDER / "projects.json"), load_json(root / FOLDER / "sources.json")
    by_source = {s["_id"]: s for s in sources}
    if len(by_source) != len(sources) or by_source.keys() & {s["_id"] for s in snapshot["sources"]}:
        raise ValueError("Interior West source identity conflicts")
    ids = [p["_id"] for p in projects]
    if len(set(ids)) != len(ids) or set(ids) & {p["_id"] for p in snapshot["projects"]}:
        raise ValueError("Interior West project identity conflicts")
    for source in sources:
        validate(source, "national-source")
    per_source = Counter(p["source_id"] for p in projects)
    for project in projects:
        validate(project, "national-project")
        source = by_source.get(project["source_id"])
        if source is None or project["evidence"]["source_sha256"] != source["sha256"]:
            raise ValueError(f"{project['_id']}: source or evidence hash mismatch")
        if not project["states"] or not set(project["states"]) <= FIPS:
            raise ValueError(f"{project['_id']}: states outside F50")
        if project["center"]:
            _check_center(project, snapshot)
        elif project["location_review"] != "unlocated":
            raise ValueError(f"{project['_id']}: unlocated project with a review state")
    if any(s["project_count"] != per_source[s["_id"]] for s in sources):
        raise ValueError("Interior West source project counts changed")
    measured = counts(projects, sources)
    if measured != release_["expected_counts"]:
        raise ValueError(f"Interior West counts changed: {measured} != {release_['expected_counts']}")
    result = deepcopy(snapshot)
    result["sources"].extend(deepcopy(sources))
    result["projects"].extend(deepcopy(projects))
    result["coverage"]["interiorwest"] = {
        "release_id": RELEASE_ID, **measured, "independently_confirmed_projects": 0,
        "notes": "WestConnect TPPL Wyoming projects and 2026 WECC progress report projects in WY, NV, UT, ID and "
                 "MT. Candidate points are labeled and never confirmed; no statewide completeness claim.",
    }
    return result
