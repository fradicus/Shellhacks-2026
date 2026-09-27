"""National pairs: python -m national_pairs [--fetch-routes [--refresh] [--dry-run]].

Without flags, a read-only generation/coverage report. --fetch-routes is person-run: it requests the missing or stale
driving routes of the current straight-line candidates, one per second, and rewrites data/national_pairs/routes.json
after every batch so an interrupted run resumes where it stopped.
"""
import argparse
import json
import time
from time import perf_counter

from common import REPO_ROOT, match_id, write_json
from matches.routes import REQUEST_INTERVAL_S, fetch_missing, is_current, load_routes
from national.build import load_snapshot
from national_pairs.build import ROUTES, candidates, generate, route_candidates

BATCH = 100


def fetch_routes(refresh: bool, dry_run: bool) -> int:
    todo = route_candidates(candidates(load_snapshot())["pairs"])
    path = REPO_ROOT / ROUTES
    records = load_routes(path)
    wanted = {match_id(a["project_key"], b["project_key"]) for a, b, _ in todo}
    if not refresh:
        todo = [c for c in todo if not is_current(records.get(match_id(c[0]["project_key"], c[1]["project_key"])),
                                                   c[0]["center"], c[1]["center"])]
    print(f"{len(wanted)} candidate pair(s); {len(todo)} route(s) to request")
    if dry_run:
        return 0
    failures = 0
    for start in range(0, len(todo), BATCH):
        if start:
            time.sleep(REQUEST_INTERVAL_S)
        batch = todo[start:start + BATCH]
        fetched, failed = fetch_missing(batch, records, refresh=refresh)
        failures += failed
        for a, b, _ in batch:
            records.pop(match_id(a["project_key"], b["project_key"]), None)
        records.update({r["_id"]: r for r in fetched})
        write_json(path, [records[mid] for mid in sorted(records) if mid in wanted])
        print(f"saved {min(start + BATCH, len(todo))}/{len(todo)}")
    if not todo:
        write_json(path, [records[mid] for mid in sorted(records) if mid in wanted])
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m national_pairs")
    parser.add_argument("--fetch-routes", action="store_true")
    parser.add_argument("--refresh", action="store_true", help="re-request every candidate route")
    parser.add_argument("--dry-run", action="store_true", help="count the routes to request, send nothing")
    args = parser.parse_args()
    if args.fetch_routes:
        return fetch_routes(args.refresh, args.dry_run)
    start = perf_counter()
    result = generate(load_snapshot())
    print(json.dumps({**result["coverage"], "generation_seconds": round(perf_counter() - start, 3)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
