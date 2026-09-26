"""Validate and load the national snapshot without touching legacy collections or meta.active.

Run from ``pipeline/`` with ``uv run python -m national.load``. Without
``MONGODB_URI_RW`` this is validation-only and performs no database writes.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pymongo import ASCENDING, GEOSPHERE

from common import REPO_ROOT
from national.build import load_snapshot

COLLECTIONS = ("national_sources", "national_projects")
KEEP_DATASETS = 2


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def stage(snapshot: dict[str, Any], dataset: str) -> dict[str, list[dict[str, Any]]]:
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
    return {"national_sources": sources, "national_projects": projects}


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
    db.national_runs.create_index([("dataset", ASCENDING), ("status", ASCENDING)])


def _run(db: Any, dataset: str, started: str, status: str, counts: dict[str, int],
         coverage: dict[str, Any], errors: list[str] | None = None) -> None:
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
    if errors:
        document["errors"] = errors[:50]
    db.national_runs.replace_one({"_id": document["_id"]}, document, upsert=True)


def load(db: Any, snapshot: dict[str, Any], dataset: str) -> int:
    started = _now()
    records = stage(snapshot, dataset)
    counts = {collection: len(records[collection]) for collection in COLLECTIONS}
    meta = db.meta.find_one({"_id": "national_active"}) or {}
    if meta.get("dataset") == dataset:
        complete = all(db[collection].count_documents({"dataset": dataset}) == count
                       for collection, count in counts.items())
        if not complete:
            print(f"national load: active dataset {dataset} is incomplete; refusing in-place rewrite")
            return 1
        try:
            _run(db, dataset, started, "ok", counts, snapshot["coverage"])
        except Exception as exc:  # noqa: BLE001 - an active dataset must retain its coverage record
            print(f"national load: could not persist active coverage ({type(exc).__name__})")
            return 1
        print(f"national load: dataset {dataset} already loaded; nothing to do")
        return 0
    try:
        ensure_indexes(db)
        for collection, documents in records.items():
            db[collection].delete_many({"dataset": dataset})
            if documents:
                db[collection].insert_many(documents, ordered=False)
        _run(db, dataset, started, "ready", counts, snapshot["coverage"])
    except Exception as exc:  # noqa: BLE001 - any write/evidence failure must leave national_active unchanged
        try:
            _run(db, dataset, started, "failed", counts, snapshot["coverage"],
                 [f"write failed: {type(exc).__name__}"])
        except Exception:  # noqa: BLE001 - the original failure remains the actionable result
            pass
        return 1
    previous = meta.get("dataset")
    try:
        db.meta.replace_one(
            {"_id": "national_active"},
            {"_id": "national_active", "dataset": dataset, "previous": previous, "loaded_at": started},
            upsert=True,
        )
    except Exception as exc:  # noqa: BLE001 - the candidate is not active
        print(f"national load: activation did not complete ({type(exc).__name__})")
        return 1
    try:
        _run(db, dataset, started, "ok", counts, snapshot["coverage"])
    except Exception as exc:  # noqa: BLE001 - ready coverage was persisted before the active pointer moved
        print(f"national load: warning: active with ready coverage; final run status failed ({type(exc).__name__})")
    keep = [value for value in (dataset, previous) if value][:KEEP_DATASETS]
    for collection in COLLECTIONS:
        try:
            db[collection].delete_many({"dataset": {"$nin": keep}})
        except Exception as exc:  # noqa: BLE001 - retention cleanup cannot invalidate the active snapshot
            print(f"national load: warning: {collection} retention cleanup failed ({type(exc).__name__})")
    return 0


def dataset_id(root: Path = REPO_ROOT) -> str:
    return os.environ.get("GIT_SHA") or subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def main() -> int:
    try:
        snapshot = load_snapshot(REPO_ROOT)
    except (OSError, ValueError) as exc:
        print(f"national load: INVALID {exc}")
        return 1
    dataset = dataset_id()
    print(f"national load: sources  {len(snapshot['sources']):6} records")
    print(f"national load: projects {len(snapshot['projects']):6} records")
    uri = os.environ.get("MONGODB_URI_RW")
    if not uri:
        print("::warning::MONGODB_URI_RW is not set; validated only, nothing loaded")
        return 0
    from pymongo import MongoClient

    client = MongoClient(uri, serverSelectionTimeoutMS=20_000, appname="gridbridge-national-load")
    try:
        result = load(client[os.environ.get("MONGODB_DB", "gridbridge")], snapshot, dataset)
    finally:
        client.close()
    print(f"national load: dataset {dataset} {'active' if result == 0 else 'NOT activated'}")
    return result


if __name__ == "__main__":
    sys.exit(main())
