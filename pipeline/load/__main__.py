"""Load data/ into MongoDB Atlas. Run by the `load` GitHub Action only (the one Atlas writer).

    cd pipeline && MONGODB_URI_RW=... uv run python -m load

Every record is validated first. Documents are written under a dataset id (the git sha); the
`meta.active` pointer flips to it only when everything validated, so the API never reads a half-loaded dataset.
"""

import os
import subprocess
import sys
from datetime import UTC, datetime
from typing import Any

from pymongo import ASCENDING, GEOSPHERE

from common import REPO_ROOT
from load.build import COLLECTIONS, collect, stage

KEEP_DATASETS = 2  # active + previous, so a bad load can be flipped back by hand


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def ensure_indexes(db: Any) -> None:
    for coll in COLLECTIONS:
        db[coll].create_index([("dataset", ASCENDING), ("id", ASCENDING)], unique=True)
    db.projects.create_index([("dataset", ASCENDING), ("geo", GEOSPHERE)])
    db.projects.create_index([("dataset", ASCENDING), ("utility", ASCENDING), ("active", ASCENDING)])
    db.projects.create_index([("dataset", ASCENDING), ("project_key", ASCENDING)])
    db.matches.create_index(
        [("dataset", ASCENDING), ("view", ASCENDING), ("band", ASCENDING),
         ("time_gap_days", ASCENDING), ("distance_mi", ASCENDING)]
    )
    db.matches.create_index([("dataset", ASCENDING), ("rank", ASCENDING)])
    db.briefs.create_index([("dataset", ASCENDING), ("match_id", ASCENDING)])
    db.version_changes.create_index([("dataset", ASCENDING), ("project_key", ASCENDING)])


def _run(db: Any, dataset: str, started: str, status: str, counts: dict, errors: list[str] | None = None) -> None:
    doc = {"_id": f"load:{dataset}", "stage": "load", "dataset": dataset, "started_at": started,
           "finished_at": _now(), "status": status, "counts": counts}
    if errors:
        doc["errors"] = errors[:50]
    db.runs.replace_one({"_id": doc["_id"]}, doc, upsert=True)


def load(db: Any, records: dict[str, list[dict]], errors: list[str], dataset: str) -> int:
    started = _now()
    counts: dict[str, Any] = {coll: len(records.get(coll, [])) for coll in [*COLLECTIONS, "locations"]}
    if errors:
        counts["errors"] = len(errors)
        _run(db, dataset, started, "failed", counts, errors)
        return 1
    meta = db.meta.find_one({"_id": "active"}) or {}
    if meta.get("dataset") == dataset or db.runs.find_one({"_id": f"load:{dataset}", "status": "ok"}):
        # A sha's data never changes: a completed or active dataset is left exactly as served (no rewrite window).
        print(f"load: dataset {dataset} already loaded; nothing to do")
        return 0
    try:
        ensure_indexes(db)
        for coll, docs in stage(records, dataset).items():
            # Not active yet, so clearing leftovers from an earlier failed attempt can't affect readers.
            db[coll].delete_many({"dataset": dataset})
            if docs:
                db[coll].insert_many(docs, ordered=False)
    except Exception as e:  # noqa: BLE001 - any write failure must leave the active dataset untouched
        _run(db, dataset, started, "failed", counts, [f"write failed: {type(e).__name__}"])
        return 1
    previous = meta.get("dataset")
    db.meta.replace_one(
        {"_id": "active"}, {"_id": "active", "dataset": dataset, "previous": previous, "loaded_at": started}, upsert=True
    )
    keep = [d for d in (dataset, previous) if d][:KEEP_DATASETS]
    for coll in COLLECTIONS:
        db[coll].delete_many({"dataset": {"$nin": keep}})
    _run(db, dataset, started, "ok", counts)
    return 0


def main() -> int:
    dataset = os.environ.get("GIT_SHA") or subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    records, errors, skipped = collect(REPO_ROOT)
    for coll, recs in records.items():
        print(f"load: {coll:16} {len(recs):6} records")
    for f in skipped:
        print(f"load: skipped {f} (not a record array)")
    for e in errors:
        print(f"load: INVALID {e}")
    uri = os.environ.get("MONGODB_URI_RW")
    if not uri:
        # Not an error in CI: without the secret there's nothing to write to. Validation above still ran.
        print("::warning::MONGODB_URI_RW is not set; validated only, nothing loaded")
        return 1 if errors else 0
    from pymongo import MongoClient

    client = MongoClient(uri, serverSelectionTimeoutMS=20000, appname="gridbridge-load")
    try:
        rc = load(client[os.environ.get("MONGODB_DB", "gridbridge")], records, errors, dataset)
    finally:
        client.close()
    print(f"load: dataset {dataset} {'active' if rc == 0 else 'NOT activated (validation failed)'}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
