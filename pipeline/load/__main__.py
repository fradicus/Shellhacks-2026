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
        [("dataset", ASCENDING), ("view", ASCENDING), ("band", ASCENDING), ("time_gap_days", ASCENDING), ("distance_mi", ASCENDING)]
    )
    db.matches.create_index([("dataset", ASCENDING), ("rank", ASCENDING)])
    db.briefs.create_index([("dataset", ASCENDING), ("match_id", ASCENDING)])
    db.version_changes.create_index([("dataset", ASCENDING), ("project_key", ASCENDING)])


def load(db: Any, records: dict[str, list[dict]], errors: list[str], dataset: str) -> int:
    started = _now()
    counts: dict[str, Any] = {coll: len(records.get(coll, [])) for coll in [*COLLECTIONS, "locations"]}
    if errors:
        counts["errors"] = len(errors)
        db.runs.replace_one(
            {"_id": f"load:{dataset}"},
            {"_id": f"load:{dataset}", "stage": "load", "dataset": dataset, "started_at": started,
             "finished_at": _now(), "status": "failed", "counts": counts, "errors": errors[:50]},
            upsert=True,
        )
        return 1
    ensure_indexes(db)
    for coll, docs in stage(records, dataset).items():
        # Rewrite this dataset wholesale: reloading the same sha yields the same documents (idempotent).
        db[coll].delete_many({"dataset": dataset})
        if docs:
            db[coll].insert_many(docs, ordered=False)
    meta = db.meta.find_one({"_id": "active"}) or {}
    previous = meta.get("previous") if meta.get("dataset") == dataset else meta.get("dataset")
    db.meta.replace_one(
        {"_id": "active"}, {"_id": "active", "dataset": dataset, "previous": previous, "loaded_at": started}, upsert=True
    )
    keep = [d for d in (dataset, previous) if d][:KEEP_DATASETS]
    for coll in COLLECTIONS:
        db[coll].delete_many({"dataset": {"$nin": keep}})
    db.runs.replace_one(
        {"_id": f"load:{dataset}"},
        {"_id": f"load:{dataset}", "stage": "load", "dataset": dataset, "started_at": started,
         "finished_at": _now(), "status": "ok", "counts": counts},
        upsert=True,
    )
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
