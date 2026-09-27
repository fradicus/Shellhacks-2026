"""Load data/ into MongoDB Atlas. Run by the `load` GitHub Action only (the one Atlas writer).

    cd pipeline && MONGODB_URI_RW=... uv run python -m load              # stage and activate this checkout's sha
    cd pipeline && MONGODB_URI_RW=... uv run python -m load --rollback   # serve meta.active.previous again
    cd pipeline && MONGODB_URI_RW=... uv run python -m load --activate   # serve this sha if it is retained intact
    cd pipeline && MONGODB_URI_RW=... uv run python -m load --restage    # re-stage a sha whose documents were pruned

Every record is validated first. Documents are written under a dataset id (the git sha); the
`meta.active` pointer flips to it only when everything validated, so the API never reads a half-loaded dataset.
Atlas keeps the active release and the previous one. Loading a sha that is neither is a real activation; a sha that
is retained but inactive, or whose documents retention pruned, is reported as such and left alone unless asked.
Every run ends in one named outcome (common/load_summary.py).
"""

import argparse
import os
import subprocess
import sys
from datetime import UTC, datetime
from typing import Any

from pymongo import ASCENDING, GEOSPHERE

from common import REPO_ROOT, load_summary
from load.build import COLLECTIONS, collect, stage

KEEP_DATASETS = 2  # active + previous, so `--rollback` can serve the previous release again


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


def intact(db: Any, dataset: str) -> bool:
    """True when every collection still holds exactly what the release's successful run receipt recorded."""
    receipt = db.runs.find_one({"_id": f"load:{dataset}", "status": "ok"})
    if not receipt:
        return False
    recorded = receipt.get("counts") or {}
    return all(db[coll].count_documents({"dataset": dataset}) == recorded.get(coll, 0) for coll in COLLECTIONS)


def _flip(db: Any, dataset: str, previous: str | None, at: str) -> None:
    pointer = {"_id": "active", "dataset": dataset, "previous": previous, "loaded_at": at}
    db.meta.replace_one({"_id": "active"}, pointer, upsert=True)
    keep = [d for d in (dataset, previous) if d][:KEEP_DATASETS]
    for coll in COLLECTIONS:
        db[coll].delete_many({"dataset": {"$nin": keep}})


def _summary(outcome: str, *, dataset: str | None, staged: str | None, db: Any | None, counts: dict,
             freshness: dict | None, quarantined: dict | None, failures: list[str] | None = None,
             detail: str | None = None) -> dict:
    meta = (db.meta.find_one({"_id": "active"}) if db is not None else None) or {}
    return load_summary.summary(
        "load", outcome, requested=dataset, staged=staged, active=meta.get("dataset"), previous=meta.get("previous"),
        counts=counts, freshness=freshness, quarantined=quarantined, failures=failures, detail=detail,
    )


def load_release(db: Any, records: dict[str, list[dict]], errors: list[str], dataset: str, *,
                 restage: bool = False, activate: bool = False, skipped: list[str] | None = None) -> dict:
    """Load one release and say exactly what happened. The three cases a repeated sha can be in stay distinct:
    active (no-op), intact but inactive (left alone unless `activate`), and a pruned receipt (refused unless `restage`)."""
    started = _now()
    counts: dict[str, Any] = {coll: len(records.get(coll, [])) for coll in [*COLLECTIONS, "locations"]}
    freshness = load_summary.source_freshness(records.get("sources", []))
    quarantined = {"invalid_records": len(errors), "skipped_files": len(skipped or [])}
    common = {"dataset": dataset, "db": db, "counts": counts, "freshness": freshness, "quarantined": quarantined}
    if errors:
        counts["errors"] = len(errors)
        _run(db, dataset, started, "failed", counts, errors)
        return _summary(load_summary.VALIDATION_FAILED, staged=None, failures=errors[:50], **common)
    meta = db.meta.find_one({"_id": "active"}) or {}
    if meta.get("dataset") == dataset:
        # A sha's data never changes: the active dataset is left exactly as served (no rewrite window).
        return _summary(load_summary.ALREADY_ACTIVE, staged=None, **common,
                        detail=f"dataset {dataset} is already active; nothing to do")
    receipt = db.runs.find_one({"_id": f"load:{dataset}", "status": "ok"})
    if receipt and intact(db, dataset):
        if not activate:
            return _summary(load_summary.RETAINED_INACTIVE, staged=None, **common, detail=(
                f"dataset {dataset} is retained and intact but not active; the active release is unchanged. "
                "Pass --activate to serve it, or --rollback to return to the previous release."))
        _flip(db, dataset, meta.get("dataset"), started)
        return _summary(load_summary.REACTIVATED, staged=None, **common,
                        detail=f"re-activated retained dataset {dataset} without re-staging")
    if receipt and not restage:
        return _summary(load_summary.PRUNED_RECEIPT, staged=None, **common, detail=(
            f"dataset {dataset} loaded once, but retention has since pruned its documents; the receipt is historical. "
            "Nothing was written. To serve it again, check out that commit and re-run with --restage."))
    try:
        ensure_indexes(db)
        for coll, docs in stage(records, dataset).items():
            # Not active yet, so clearing leftovers from an earlier failed attempt can't affect readers.
            db[coll].delete_many({"dataset": dataset})
            if docs:
                db[coll].insert_many(docs, ordered=False)
    except Exception as e:  # noqa: BLE001 - any write failure must leave the active dataset untouched
        failure = f"write failed: {type(e).__name__}"
        _run(db, dataset, started, "failed", counts, [failure])
        return _summary(load_summary.PUBLICATION_FAILED, staged=None, failures=[failure], **common)
    _flip(db, dataset, meta.get("dataset"), started)
    _run(db, dataset, started, "ok", counts)
    return _summary(load_summary.ACTIVATED, staged=dataset, **common,
                    detail="re-staged from a pruned receipt" if receipt else None)


def rollback(db: Any) -> dict:
    """Serve the previous release again, if it is still intact. The supported rollback: no re-staging, no new data."""
    started = _now()
    meta = db.meta.find_one({"_id": "active"}) or {}
    active, previous = meta.get("dataset"), meta.get("previous")
    common = {"dataset": previous, "db": db, "counts": {}, "freshness": None, "quarantined": None}
    if not previous:
        return _summary(load_summary.PUBLICATION_FAILED, staged=None, failures=["no previous release recorded"], **common)
    if not intact(db, previous):
        return _summary(load_summary.PRUNED_RECEIPT, staged=None, **common,
                        failures=[f"previous release {previous} is no longer intact"],
                        detail="Rollback refused; the active release is unchanged. Re-stage the older commit with --restage.")
    _flip(db, previous, active, started)
    return _summary(load_summary.REACTIVATED, staged=None, detail=f"rolled back from {active} to {previous}", **common)


def load(db: Any, records: dict[str, list[dict]], errors: list[str], dataset: str, **options: Any) -> int:
    result = load_release(db, records, errors, dataset, **options)
    load_summary.emit(result)
    return 0 if result["ok"] else 1


def _args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m load", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--rollback", action="store_true", help="serve meta.active.previous again if it is intact; loads nothing")
    mode.add_argument("--activate", action="store_true", help="if this sha is retained intact but inactive, make it active")
    mode.add_argument("--restage", action="store_true",
                      help="re-stage this checkout's data even though a pruned run receipt exists for its sha, then activate")
    return parser.parse_args([] if argv is None else argv)


def _client(uri: str) -> Any:
    from pymongo import MongoClient

    return MongoClient(uri, serverSelectionTimeoutMS=20000, appname="gridbridge-load")


def main(argv: list[str] | None = None) -> int:
    args = _args(argv)
    uri = os.environ.get("MONGODB_URI_RW")
    db_name = os.environ.get("MONGODB_DB", "gridbridge")
    if args.rollback:
        if not uri:
            print("load: --rollback needs MONGODB_URI_RW; nothing changed")
            return 1
        client = _client(uri)
        try:
            result = rollback(client[db_name])
        finally:
            client.close()
        load_summary.emit(result)
        return 0 if result["ok"] else 1
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
    if not uri:
        # Not an error in CI: without the secret there's nothing to write to. Validation above still ran.
        print("::warning::MONGODB_URI_RW is not set; validated only, nothing loaded")
        counts = {coll: len(records.get(coll, [])) for coll in [*COLLECTIONS, "locations"]}
        result = load_summary.summary(
            "load", load_summary.VALIDATION_FAILED if errors else load_summary.VALIDATED_ONLY,
            requested=dataset, staged=None, active=None, previous=None, counts=counts,
            freshness=load_summary.source_freshness(records.get("sources", [])),
            quarantined={"invalid_records": len(errors), "skipped_files": len(skipped)}, failures=errors[:50],
            detail="no write credentials: every record was validated, nothing was written, and the active release was not read",
        )
        load_summary.emit(result)
        return 0 if result["ok"] else 1
    client = _client(uri)
    try:
        return load(client[db_name], records, errors, dataset, restage=args.restage, activate=args.activate, skipped=skipped)
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
