"""Fixed C26/C29-pattern release of Great Lakes projects into the national snapshot.

From pipeline/:  uv run python -m greatlakes.publish [--check]
builds data/greatlakes/{projects,sources}.json and releases/active.json from the per-source outputs. F30's
load_snapshot calls apply_release(snapshot, root) only when that fixed active file exists; it validates everything
again and appends new sources and projects. No folder scan, network or database access.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import re
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path

from common import REPO_ROOT, load_json, validate, write_json

FOLDER = Path("data/greatlakes")
ACTIVE = FOLDER / "releases" / "active.json"
RELEASE_ID = "great-lakes-2026-09-candidates-1"
# Fixed producer order; each folder is one adapter's output.
PRODUCERS = ["mn", "wi", "miso", "ny", "aep", "firstenergy"]
OFFICIAL_SOURCES = {"aep-transmission-projects"}  # the owner's own project-map coordinate (C25 Official tier)
META = {
    "mn-btpr-2025": {"title": "2025 Minnesota Biennial Transmission Projects Report, Chapter 6",
                     "publisher": "Minnesota transmission-owning utilities (MPUC Docket E999/M-25-99)",
                     "authority": "utility", "landing_url": "https://www.minnelectrans.com/report-2025.html",
                     "publication_date": "2025-10-31", "vintage": "2025", "planning_region": "mn-biennial"},
    "atc-tya-2025": {"title": "ATC's 2025 10-Year Assessment Project List", "publisher": "American Transmission Company",
                     "authority": "utility",
                     "landing_url": "https://www.atc10yearplan.com/projects/network-projects-list/",
                     "publication_date": None, "vintage": "2025", "planning_region": "atc-tya"},
    "miso-mtep26-eval": {"title": "MISO MTEP Projects Under Evaluation", "publisher": "MISO",
                         "authority": "regional_planning_organization",
                         "landing_url": "https://www.misoenergy.org/planning/transmission-planning/mtep/",
                         "publication_date": None, "vintage": "MTEP26 cycle", "planning_region": "miso"},
    "nyiso-gold-book-2026": {"title": "NYISO 2026 Gold Book, Table VII: Proposed Transmission Facilities",
                             "publisher": "NYISO", "authority": "regional_planning_organization",
                             "landing_url": "https://www.nyiso.com/load-capacity-data-report-gold-book-",
                             "publication_date": None, "vintage": "as of 2026-03-15", "planning_region": "nyiso"},
    "aep-transmission-projects": {"title": "AEP Transmission state project map", "publisher": "AEP Transmission",
                                  "authority": "utility", "landing_url": "https://www.aeptransmission.com/",
                                  "publication_date": None, "vintage": None, "planning_region": None},
    "firstenergy-transmission-projects": {"title": "FirstEnergy transmission project page", "publisher": "FirstEnergy",
                                          "authority": "utility",
                                          "landing_url": "https://www.firstenergycorp.com/about/transmission_projects.html",
                                          "publication_date": None, "vintage": None, "planning_region": None},
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hash(project: dict) -> str:
    raw = project["evidence"]["raw"]
    return raw.get("source_sha256") or raw["map_sha256"]


def slug(artifact: dict) -> str:
    name = artifact.get("page") or artifact.get("file") or artifact["url"]
    return re.sub(r"(\.html?|\.json)$", "", name.replace("about--transmission_projects--", ""))


def build(root: Path = REPO_ROOT) -> dict[Path, object]:
    """Publication projects (one source per artifact, C25 tier added) plus national sources and the release."""
    projects, sources = [], []
    # Dates found after the source import (greatlakes.dates): fill unknown in-service only, with their evidence.
    dates = {k: v for path in sorted((root / FOLDER / "dates").glob("*.json")) for k, v in load_json(path).items()}
    for producer in PRODUCERS:
        base = load_json(root / FOLDER / producer / "sources.json")[0]
        artifacts = {a["sha256"]: a for a in base["artifacts"]}
        rows = deepcopy(load_json(root / FOLDER / producer / "projects.json"))
        used = Counter(artifact_hash(p) for p in rows)
        for digest in sorted(used, key=lambda d: slug(artifacts[d])):
            artifact = artifacts[digest]
            source_id = base["_id"] if len(used) == 1 else f"{base['_id']}:{slug(artifact)}"
            members = [p for p in rows if artifact_hash(p) == digest]
            meta = META[base["_id"]]
            sources.append({
                "_id": source_id, "title": meta["title"], "publisher": meta["publisher"],
                "authority": meta["authority"], "role": "project_plan", "landing_url": meta["landing_url"],
                "download_url": artifact["url"], "publication_date": meta["publication_date"],
                "vintage": meta["vintage"], "retrieved_at": artifact["retrieved_at"], "sha256": digest,
                "public_status": "verified_public", "import_status": "imported", "access_policy": "public_document",
                "planning_region": meta["planning_region"],
                "states": sorted({s for p in members for s in p["states"]}), "project_count": len(members),
                "notes": ["F40 Great Lakes release (C26). Locations are unverified candidates or the owner's own "
                          "map coordinate; none is independently confirmed. Source-bounded, not statewide coverage."],
            })
            for project in members:
                if project["in_service"]["precision"] == "unknown" and project["_id"] in dates:
                    project["in_service"] = dates[project["_id"]]["in_service"]
                    project["in_service_evidence"] = dates[project["_id"]]["evidence"]
                project["source_id"] = source_id
                project["evidence"]["source_sha256"] = digest
                if project["center"]:
                    project["location_candidate"]["tier"] = ("official" if base["_id"] in OFFICIAL_SOURCES
                                                             else "candidate")
                    project["location_candidate"]["independent_review"] = False
                projects.append(project)
    projects.sort(key=lambda p: p["_id"])
    sources.sort(key=lambda s: s["_id"])
    outputs: dict[Path, object] = {root / FOLDER / "projects.json": projects, root / FOLDER / "sources.json": sources}
    tiers = Counter(p["location_candidate"].get("tier") for p in projects if p["center"])
    release = {
        "release_id": RELEASE_ID, "policy": "C25", "rule": "C26",
        "files": {name: hashlib.sha256(_encode(value)).hexdigest() for name, value in
                  (("projects", projects), ("sources", sources))},
        "expected_counts": {"projects": len(projects), "sources": len(sources), "centers": sum(tiers.values()),
                            "candidate": tiers["candidate"], "official": tiers["official"],
                            "distinct_points": len({(p["center"]["lat"], p["center"]["lon"])
                                                    for p in projects if p["center"]})},
    }
    outputs[root / ACTIVE] = release
    return outputs


def _encode(value: object) -> bytes:
    """Byte-identical to common.write_json, so the release can pin committed file hashes."""
    import json

    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _bounds(snapshot: dict, states: list[str]) -> list[dict]:
    return [s["bounds"] for s in snapshot["geography"]["states"] if s["state_fips"] in states]


def _check_center(project: dict, snapshot: dict) -> None:
    center, candidate = project["center"], project["location_candidate"]
    if project["location_review"] != "unreviewed" or candidate.get("independent_review") is not False:
        raise ValueError(f"{project['_id']}: a released location must be unreviewed")
    lat, lon = center["lat"], center["lon"]
    if not (math.isfinite(lat) and math.isfinite(lon)) or not any(
            b["south"] - 0.05 <= lat <= b["north"] + 0.05 and b["west"] - 0.05 <= lon <= b["east"] + 0.05
            for b in _bounds(snapshot, project["states"])):
        raise ValueError(f"{project['_id']}: center outside its states")
    if candidate["tier"] == "official":
        marker = project["evidence"]["raw"]["marker_center"]
        if (center["basis"] != "source_point" or not center["evidence"].startswith("Official source:")
                or (round(marker["lat"], 6), round(marker["lng"], 6)) != (lat, lon)):
            raise ValueError(f"{project['_id']}: official point does not match the owner's marker")
        return
    points = [e["facility"] for e in candidate["endpoints"] if e["status"] == "matched"]
    basis = "source_point" if candidate["kind"] == "site" else ("two" if len(points) == 2 else "one")
    if (candidate["tier"] != "candidate" or not center["evidence"].startswith("Unverified candidate:")
            or not points or len(points) > 2 or center["basis"] != basis
            or (candidate["kind"] == "site" and len(points) != 1)
            or abs(sum(p["lat"] for p in points) / len(points) - lat) > 1e-6
            or abs(sum(p["lon"] for p in points) / len(points) - lon) > 1e-6):
        raise ValueError(f"{project['_id']}: candidate center does not follow its matched facilities")


def apply_release(snapshot: dict, root: Path) -> dict:
    path = root / ACTIVE
    if not path.exists():
        return snapshot
    release = load_json(path)
    if release["release_id"] != RELEASE_ID or release["policy"] != "C25" or release["rule"] != "C26":
        raise ValueError("Great Lakes release manifest changed")
    for name in ("projects", "sources"):
        if sha(root / FOLDER / f"{name}.json") != release["files"][name]:
            raise ValueError(f"Great Lakes release file hash changed: {name}")
    projects, sources = load_json(root / FOLDER / "projects.json"), load_json(root / FOLDER / "sources.json")
    by_source = {s["_id"]: s for s in sources}
    if len(by_source) != len(sources) or by_source.keys() & {s["_id"] for s in snapshot["sources"]}:
        raise ValueError("Great Lakes source identity conflicts")
    ids = [p["_id"] for p in projects]
    if len(set(ids)) != len(ids) or set(ids) & {p["_id"] for p in snapshot["projects"]}:
        raise ValueError("Great Lakes project identity conflicts")
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
        raise ValueError("Great Lakes source project counts changed")
    tiers = Counter(p["location_candidate"]["tier"] for p in projects if p["center"])
    measured = {"projects": len(projects), "sources": len(sources), "centers": sum(tiers.values()),
                "candidate": tiers["candidate"], "official": tiers["official"],
                "distinct_points": len({(p["center"]["lat"], p["center"]["lon"]) for p in projects if p["center"]})}
    if measured != release["expected_counts"]:
        raise ValueError(f"Great Lakes counts changed: {measured} != {release['expected_counts']}")
    result = deepcopy(snapshot)
    result["sources"].extend(deepcopy(sources))
    result["projects"].extend(deepcopy(projects))
    result["coverage"]["great_lakes"] = {
        "release_id": RELEASE_ID, **measured, "independently_confirmed_projects": 0,
        "notes": "Source-bounded Great Lakes registers (MN, WI, MI, IL, IN, OH, PA, NY). Candidate and official "
                 "points are labeled and never confirmed; no statewide completeness claim.",
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    outputs = build()
    if args.check:
        stale = [str(p) for p, v in outputs.items() if not p.exists() or load_json(p) != v]
        print("stale: " + ", ".join(stale) if stale else "ok")
        return 1 if stale else 0
    for path, value in outputs.items():
        write_json(path, value)
    print(outputs[REPO_ROOT / ACTIVE])
    return 0


if __name__ == "__main__":
    sys.exit(main())
