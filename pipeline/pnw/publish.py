"""Fixed C33 release of Pacific Northwest projects into the national snapshot (C29/C26 pattern).

From pipeline/:  uv run python -m pnw.publish [--check]
pins data/pnw/{projects,sources}.json in data/pnw/releases/active.json. F30's load_snapshot calls
apply_release(snapshot, root) only when that fixed file exists; it validates everything again and appends new
sources and projects. No folder scan, network or database access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path

from common import REPO_ROOT, load_json, validate, write_json

FOLDER = Path("data/pnw")
ACTIVE = FOLDER / "releases" / "active.json"
RELEASE_ID = "pacific-northwest-2026-09-1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tier(project: dict) -> str | None:
    if not project["center"]:
        return None
    evidence = project["center"]["evidence"]
    return "official" if evidence.startswith("Official source") else "name_only" if "name-only" in evidence else "candidate"


def measure(projects: list[dict], sources: list[dict]) -> dict:
    tiers = Counter(tier(p) for p in projects)
    return {"projects": len(projects), "sources": len(sources), "official": tiers["official"],
            "candidate": tiers["candidate"], "candidate_name_only": tiers["name_only"],
            "unlocated": tiers[None],
            "distinct_points": len({(p["center"]["lat"], p["center"]["lon"]) for p in projects if p["center"]})}


def release(root: Path = REPO_ROOT) -> dict:
    projects, sources = load_json(root / FOLDER / "projects.json"), load_json(root / FOLDER / "sources.json")
    return {"release_id": RELEASE_ID, "policy": "C25", "rule": "C33",
            "files": {n: sha(root / FOLDER / f"{n}.json") for n in ("projects", "sources")},
            "expected_counts": measure(projects, sources)}


def _check_center(project: dict, snapshot: dict) -> None:
    center = project["center"]
    lat, lon = center["lat"], center["lon"]
    bounds = [s["bounds"] for s in snapshot["geography"]["states"] if s["state_fips"] in project["states"]]
    if project["location_review"] != "unreviewed" or not (math.isfinite(lat) and math.isfinite(lon)) or not any(
            b["south"] - 0.05 <= lat <= b["north"] + 0.05 and b["west"] - 0.05 <= lon <= b["east"] + 0.05
            for b in bounds):
        raise ValueError(f"{project['_id']}: center outside its states or not unreviewed")
    if tier(project) == "official":
        if center["basis"] not in ("two", "source_point") or project["evidence"]["page"] is not None:
            raise ValueError(f"{project['_id']}: official point must come from source geometry")
        return
    candidate = project["location_candidate"]
    points = [e["facility"] for e in candidate["endpoints"] if e["status"] == "matched"]
    basis = "source_point" if candidate["kind"] == "site" else ("two" if len(points) == 2 else "one")
    if (not center["evidence"].startswith("Unverified candidate:") or not points or len(points) > 2
            or center["basis"] != basis
            or abs(sum(p["lat"] for p in points) / len(points) - lat) > 1e-6
            or abs(sum(p["lon"] for p in points) / len(points) - lon) > 1e-6):
        raise ValueError(f"{project['_id']}: candidate center does not follow its matched facilities")


def apply_release(snapshot: dict, root: Path) -> dict:
    path = root / ACTIVE
    if not path.exists():
        return snapshot
    active = load_json(path)
    if active["release_id"] != RELEASE_ID or active["policy"] != "C25" or active["rule"] != "C33":
        raise ValueError("Pacific Northwest release manifest changed")
    for name in ("projects", "sources"):
        if sha(root / FOLDER / f"{name}.json") != active["files"][name]:
            raise ValueError(f"Pacific Northwest release file hash changed: {name}")
    projects, sources = load_json(root / FOLDER / "projects.json"), load_json(root / FOLDER / "sources.json")
    by_source = {s["_id"]: s for s in sources}
    if len(by_source) != len(sources) or by_source.keys() & {s["_id"] for s in snapshot["sources"]}:
        raise ValueError("Pacific Northwest source identity conflicts")
    ids = [p["_id"] for p in projects]
    if len(set(ids)) != len(ids) or set(ids) & {p["_id"] for p in snapshot["projects"]}:
        raise ValueError("Pacific Northwest project identity conflicts")
    for source in sources:
        validate(source, "national-source")
    counts = Counter(p["source_id"] for p in projects)
    for project in projects:
        validate(project, "national-project")
        source = by_source.get(project["source_id"])
        if source is None or project["evidence"]["source_sha256"] != source["sha256"]:
            raise ValueError(f"{project['_id']}: source or evidence hash mismatch")
        if project["center"]:
            _check_center(project, snapshot)
        elif project["location_review"] != "unlocated":
            raise ValueError(f"{project['_id']}: unlocated project with a review state")
    if any(s["project_count"] != counts[s["_id"]] for s in sources):
        raise ValueError("Pacific Northwest source project counts changed")
    measured = measure(projects, sources)
    if measured != active["expected_counts"]:
        raise ValueError(f"Pacific Northwest counts changed: {measured} != {active['expected_counts']}")
    result = deepcopy(snapshot)
    result["sources"].extend(deepcopy(sources))
    result["projects"].extend(deepcopy(projects))
    result["coverage"]["pacific_northwest"] = {
        "release_id": RELEASE_ID, **measured, "independently_confirmed_projects": 0,
        "notes": "Source-bounded WA, OR, ID, MT registers (C33), 2025-2035 work. Official and candidate locations are "
                 "labeled and never confirmed; no county dots; no statewide completeness claim.",
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    value = release()
    if args.check:
        ok = (REPO_ROOT / ACTIVE).exists() and load_json(REPO_ROOT / ACTIVE) == value
        print("ok" if ok else f"stale: {ACTIVE}")
        return 0 if ok else 1
    write_json(REPO_ROOT / ACTIVE, value)
    print(json.dumps(value, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
