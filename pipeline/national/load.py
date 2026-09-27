"""Validate and load the national snapshot without touching legacy collections or meta.active.

Run from ``pipeline/`` with ``uv run python -m national.load``. Without
``MONGODB_URI_RW`` this is validation-only and performs no database writes.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pymongo import ASCENDING, GEOSPHERE

from common import REPO_ROOT, load_summary
from national.build import load_snapshot
from national_pairs.build import COLLECTION as PAIRS_COLLECTION
from national_pairs.build import generate

COLLECTIONS = ("national_sources", "national_projects", PAIRS_COLLECTION)
KEEP_DATASETS = 2


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def stage(snapshot: dict[str, Any], dataset: str, pairs: list[dict] | None = None) -> dict[str, list[dict[str, Any]]]:
    sources = [{**source, "_id": f"{dataset}:{source['_id']}", "id": source["_id"], "dataset": dataset}
               for source in snapshot["sources"]]
    projects = []
    for project in snapshot["projects"]:
        center = project.get("center")
        geo = {"type": "Point", "coordinates": [center["lon"], center["lat"]]} if center else None
        projects.append({
            **project,
            "_id": f"{dataset}:{project['_id']}",
            "id": project["_id"],
            "dataset": dataset,
            "geo": geo,
        })
    pairs = generate(snapshot)["pairs"] if pairs is None else pairs
    staged_pairs = [{**pair, "_id": f"{dataset}:{pair['_id']}", "id": pair["_id"], "dataset": dataset}
                    for pair in pairs]
    return {"national_sources": sources, "national_projects": projects, PAIRS_COLLECTION: staged_pairs}


def ensure_indexes(db: Any) -> None:
    db.national_sources.create_index([("dataset", ASCENDING), ("id", ASCENDING)], unique=True)
    db.national_projects.create_index([("dataset", ASCENDING), ("id", ASCENDING)], unique=True)
    db.national_projects.create_index([("dataset", ASCENDING), ("states", ASCENDING)])
    db.national_projects.create_index([("dataset", ASCENDING), ("counties", ASCENDING)])
    db.national_projects.create_index([("dataset", ASCENDING), ("planning_region", ASCENDING)])
    db.national_projects.create_index([("dataset", ASCENDING), ("owner", ASCENDING)])
    db.national_projects.create_index([("dataset", ASCENDING), ("status_group", ASCENDING)])
    db.national_projects.create_index([("dataset", ASCENDING), ("in_service.value", ASCENDING)])
    db.national_projects.create_index([("dataset", ASCENDING), ("geo", GEOSPHERE)])
    db[PAIRS_COLLECTION].create_index([("dataset", ASCENDING), ("id", ASCENDING)], unique=True)
    db[PAIRS_COLLECTION].create_index([("dataset", ASCENDING), ("rank", ASCENDING)], unique=True)
    for field in ("shared_states", "shared_regions", "shared_plans"):
        db[PAIRS_COLLECTION].create_index([("dataset", ASCENDING), (field, ASCENDING), ("rank", ASCENDING)])
    for field in ("geo_a", "geo_b"):
        db[PAIRS_COLLECTION].create_index([("dataset", ASCENDING), (field, GEOSPHERE)])
    db.national_runs.create_index([("dataset", ASCENDING), ("status", ASCENDING)])


def _run(db: Any, dataset: str, started: str, status: str, counts: dict[str, int],
         coverage: dict[str, Any], errors: list[str] | None = None,
         candidate_coverage: dict[str, Any] | None = None) -> None:
    document: dict[str, Any] = {
        "_id": f"national-load:{dataset}",
        "stage": "national_load",
        "dataset": dataset,
        "started_at": started,
        "finished_at": _now(),
        "status": status,
        "counts": counts,
        "coverage": coverage,
    }
    if candidate_coverage is not None:
        document["candidate_pair_coverage"] = candidate_coverage
    if errors:
        document["errors"] = errors[:50]
    db.national_runs.replace_one({"_id": document["_id"]}, document, upsert=True)


def _metrics(snapshot: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    failures = (snapshot.get("coverage") or {}).get("failures")
    return (load_summary.source_freshness(snapshot.get("sources", [])),
            {"failed_sources": len(failures) if isinstance(failures, list) else None})


def load_release(db: Any, snapshot: dict[str, Any], dataset: str, candidates: dict | None = None) -> dict[str, Any]:
    """Stage and activate one national release; the named outcome says what was staged and what is active."""
    freshness, quarantined = _metrics(snapshot)
    try:
        candidates = generate(snapshot) if candidates is None else candidates
        records = stage(snapshot, dataset, candidates["pairs"])
    except (ValueError, KeyError, TypeError) as exc:
        meta = db.meta.find_one({"_id": "national_active"}) or {}
        return load_summary.summary(
            "national load", load_summary.VALIDATION_FAILED, requested=dataset, staged=None, active=meta.get("dataset"),
            previous=meta.get("previous"), counts={}, freshness=freshness, quarantined=quarantined,
            failures=[f"candidate generation failed ({type(exc).__name__})"], detail="previous dataset retained",
        )
    counts = {collection: len(records[collection]) for collection in COLLECTIONS}
    outcome, staged, failures, detail = _load(db, snapshot, dataset, records, counts, candidates["coverage"])
    meta = db.meta.find_one({"_id": "national_active"}) or {}
    return load_summary.summary(
        "national load", outcome, requested=dataset, staged=staged, active=meta.get("dataset"), previous=meta.get("previous"),
        counts=counts, freshness=freshness, quarantined=quarantined, failures=failures, detail=detail,
    )


def load(db: Any, snapshot: dict[str, Any], dataset: str, candidates: dict | None = None) -> int:
    result = load_release(db, snapshot, dataset, candidates)
    load_summary.emit(result)
    return 0 if result["ok"] else 1


def rollback(db: Any) -> dict[str, Any]:
    """Serve national_active.previous again when its documents are still complete; stages nothing."""
    meta = db.meta.find_one({"_id": "national_active"}) or {}
    active, previous = meta.get("dataset"), meta.get("previous")
    receipt = db.national_runs.find_one({"_id": f"national-load:{previous}", "status": "ok"}) if previous else None
    recorded = (receipt or {}).get("counts") or {}
    intact = bool(receipt) and all(db[c].count_documents({"dataset": previous}) == recorded.get(c, 0) for c in COLLECTIONS)
    outcome, failures, detail = load_summary.PUBLICATION_FAILED, ["no previous national release recorded"], None
    if previous and not intact:
        outcome, failures = load_summary.PRUNED_RECEIPT, [f"previous national release {previous} is no longer complete"]
        detail = "Rollback refused; the active national release is unchanged. Check out that commit and load it again."
    elif previous:
        db.meta.replace_one({"_id": "national_active"},
                            {"_id": "national_active", "dataset": previous, "previous": active, "loaded_at": _now()}, upsert=True)
        outcome, failures, detail = load_summary.REACTIVATED, [], f"rolled back from {active} to {previous}"
    meta = db.meta.find_one({"_id": "national_active"}) or {}
    return load_summary.summary("national load", outcome, requested=previous, staged=None, active=meta.get("dataset"),
                                previous=meta.get("previous"), counts={}, freshness=None, quarantined=None,
                                failures=failures, detail=detail)


def _load(db: Any, snapshot: dict[str, Any], dataset: str, records: dict[str, list[dict[str, Any]]],
          counts: dict[str, int], candidate_coverage: dict[str, Any]) -> tuple[str, str | None, list[str], str | None]:
    started = _now()
    failed = load_summary.PUBLICATION_FAILED
    meta = db.meta.find_one({"_id": "national_active"}) or {}
    if meta.get("dataset") == dataset:
        complete = all(db[collection].count_documents({"dataset": dataset}) == count
                       for collection, count in counts.items())
        if not complete:
            return failed, None, [f"active dataset {dataset} is incomplete; refusing in-place rewrite"], None
        try:
            _run(db, dataset, started, "ok", counts, snapshot["coverage"], candidate_coverage=candidate_coverage)
        except Exception as exc:  # noqa: BLE001 - an active dataset must retain its coverage record
            return failed, None, [f"could not persist active coverage ({type(exc).__name__})"], None
        return load_summary.ALREADY_ACTIVE, None, [], f"dataset {dataset} is already active; nothing to do"
    try:
        ensure_indexes(db)
        for collection, documents in records.items():
            db[collection].delete_many({"dataset": dataset})
            if documents:
                db[collection].insert_many(documents, ordered=False)
        if any(db[collection].count_documents({"dataset": dataset}) != count
               for collection, count in counts.items()):
            raise RuntimeError("staged dataset count mismatch")
        _run(db, dataset, started, "ready", counts, snapshot["coverage"], candidate_coverage=candidate_coverage)
    except Exception as exc:  # noqa: BLE001 - any write/evidence failure must leave national_active unchanged
        try:
            _run(db, dataset, started, "failed", counts, snapshot["coverage"],
                 [f"write failed: {type(exc).__name__}"], candidate_coverage=candidate_coverage)
        except Exception:  # noqa: BLE001 - the original failure remains the actionable result
            pass
        return failed, None, [f"write failed: {type(exc).__name__}"], None
    previous = meta.get("dataset")
    try:
        db.meta.replace_one(
            {"_id": "national_active"},
            {"_id": "national_active", "dataset": dataset, "previous": previous, "loaded_at": started},
            upsert=True,
        )
    except Exception as exc:  # noqa: BLE001 - the candidate is not active
        return failed, dataset, [f"activation did not complete ({type(exc).__name__})"], "staged but not activated"
    warnings = []
    try:
        _run(db, dataset, started, "ok", counts, snapshot["coverage"], candidate_coverage=candidate_coverage)
    except Exception as exc:  # noqa: BLE001 - ready coverage was persisted before the active pointer moved
        warnings.append(f"active with ready coverage; final run status failed ({type(exc).__name__})")
    keep = [value for value in (dataset, previous) if value][:KEEP_DATASETS]
    for collection in COLLECTIONS:
        try:
            db[collection].delete_many({"dataset": {"$nin": keep}})
        except Exception as exc:  # noqa: BLE001 - retention cleanup cannot invalidate the active snapshot
            warnings.append(f"{collection} retention cleanup failed ({type(exc).__name__})")
    return load_summary.ACTIVATED, dataset, [], "; ".join(f"warning: {w}" for w in warnings) or None


def dataset_id(root: Path = REPO_ROOT) -> str:
    return os.environ.get("GIT_SHA") or subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m national.load")
    parser.add_argument("--rollback", action="store_true", help="serve national_active.previous again if complete; loads nothing")
    args = parser.parse_args([] if argv is None else argv)
    uri = os.environ.get("MONGODB_URI_RW")
    if args.rollback:
        if not uri:
            print("national load: --rollback needs MONGODB_URI_RW; nothing changed")
            return 1
        from pymongo import MongoClient

        client = MongoClient(uri, serverSelectionTimeoutMS=20_000, appname="gridbridge-national-load")
        try:
            result = rollback(client[os.environ.get("MONGODB_DB", "gridbridge")])
        finally:
            client.close()
        load_summary.emit(result)
        return 0 if result["ok"] else 1
    try:
        snapshot = load_snapshot(REPO_ROOT)
        candidates = generate(snapshot)
    except (OSError, ValueError) as exc:
        print(f"national load: INVALID {exc}")
        load_summary.emit(load_summary.summary(
            "national load", load_summary.VALIDATION_FAILED, requested=None, staged=None, active=None, previous=None,
            counts={}, freshness=None, quarantined=None, failures=[str(exc)[:500]]))
        return 1
    dataset = dataset_id()
    print(f"national load: sources  {len(snapshot['sources']):6} records")
    print(f"national load: projects {len(snapshot['projects']):6} records")
    print("national candidate coverage: " + json.dumps(candidates["coverage"], sort_keys=True))
    if not uri:
        print("::warning::MONGODB_URI_RW is not set; validated only, nothing loaded")
        freshness, quarantined = _metrics(snapshot)
        load_summary.emit(load_summary.summary(
            "national load", load_summary.VALIDATED_ONLY, requested=dataset, staged=None, active=None, previous=None,
            counts={"national_sources": len(snapshot["sources"]), "national_projects": len(snapshot["projects"]),
                    PAIRS_COLLECTION: len(candidates["pairs"])},
            freshness=freshness, quarantined=quarantined,
            detail="no write credentials: the snapshot validated, nothing was written, and the active release was not read"))
        return 0
    from pymongo import MongoClient

    client = MongoClient(uri, serverSelectionTimeoutMS=20_000, appname="gridbridge-national-load")
    try:
        db = client[os.environ.get("MONGODB_DB", "gridbridge")]
        result = load(db, snapshot, dataset, candidates)
        if result == 0:
            actual = db[PAIRS_COLLECTION].count_documents({"dataset": dataset})
            if actual != len(candidates["pairs"]):
                print("national candidate readback mismatch")
                return 1
            rule = ("Stored driving route <=25 mi (straight-line prefilter)"
                    if "route_states" in candidates["coverage"] else "Straight-line distance <25 mi; no driving-route claim")
            report = (f"\n## Provisional national pairs\n\nDataset `{dataset}`: {actual:,} pairs. "
                      f"{rule}; no construction-window claim.\n\n"
                      + "```json\n" + json.dumps(candidates["coverage"], indent=2) + "\n```\n")
            print(report)
            if os.environ.get("GITHUB_STEP_SUMMARY"):
                with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as out:
                    out.write(report)
        return result
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
