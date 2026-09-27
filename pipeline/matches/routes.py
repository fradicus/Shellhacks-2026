"""Stored driving routes for the drive rule (C46). Every producer binds and fetches routes through this module.

A route record is bound to the exact centers it was computed from, so a moved center makes its route stale instead
of silently reusing an old drive. Records validate against schemas/route.schema.json.

    uv run python -m matches.routes --corpus fixtures|golden [--dry-run] [--refresh]

fetches the contract fixtures' routes. Feature producers call `fetch_missing` for their own corpus.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from common import REPO_ROOT, load_json, match_id, validate, write_json
from matches import core
from matches.osrm import RoutesError, base_url, compute_route

REQUEST_INTERVAL_S = 1.1  # the public OSRM demo allows at most one request per second
ROUTE_FIELDS = (
    "provider", "travel_mode", "routing_preference", "data_source", "computed_at",
    "duration_s", "polyline", "start", "end", "snap_m",
)
STATES = ("ok", "no_route", "missing", "stale")

Candidate = tuple[dict[str, Any], dict[str, Any], float]


def _same_point(a: dict[str, Any] | None, b: dict[str, Any] | None) -> bool:
    return bool(a and b) and round(a["lat"], 9) == round(b["lat"], 9) and round(a["lon"], 9) == round(b["lon"], 9)


def load_routes(path: Path) -> dict[str, dict[str, Any]]:
    """match _id -> route record; {} when the file does not exist yet."""
    if not path.exists():
        return {}
    by_id: dict[str, dict[str, Any]] = {}
    for record in load_json(path):
        validate(record, "route")
        if record["_id"] in by_id:
            raise ValueError(f"duplicate route record {record['_id']!r}")
        by_id[record["_id"]] = record
    return by_id


def is_current(record: dict[str, Any] | None, origin: dict[str, Any], destination: dict[str, Any]) -> bool:
    return bool(record) and _same_point(record.get("origin"), origin) and _same_point(record.get("destination"), destination)


def drives_for(
    candidates: list[Candidate], routes: dict[str, dict[str, Any]]
) -> tuple[dict[str, float | None], dict[str, str]]:
    """(match _id -> drive miles or None, match _id -> state) for every candidate pair.

    States: ok, no_route (the router found none), missing (never fetched), stale (a center moved since the fetch)."""
    drives: dict[str, float | None] = {}
    states: dict[str, str] = {}
    for pa, pb, _ in candidates:
        mid = match_id(pa["project_key"], pb["project_key"])
        record = routes.get(mid)
        if record is None:
            drives[mid], states[mid] = None, "missing"
        elif not is_current(record, pa["center"], pb["center"]):
            drives[mid], states[mid] = None, "stale"
        elif record["status"] != "ok":
            drives[mid], states[mid] = None, "no_route"
        else:
            drives[mid], states[mid] = record["drive_mi"], "ok"
    return drives, states


def route_summary(record: dict[str, Any]) -> dict[str, Any]:
    """The route facts a match record carries (nothing recomputed)."""
    return {field: record.get(field) for field in ROUTE_FIELDS}


def fetch_missing(
    candidates: list[Candidate],
    stored: dict[str, dict[str, Any]],
    *,
    refresh: bool = False,
    compute: Callable[..., dict[str, Any]] = compute_route,
    interval_s: float = REQUEST_INTERVAL_S,
    sleep: Callable[[float], None] = time.sleep,
    log: Callable[[str], None] = print,
) -> tuple[list[dict[str, Any]], int]:
    """Request every missing or stale candidate route (all of them with `refresh`), one request per `interval_s`.

    Returns (records for exactly the current candidates, sorted by _id; failed request count). A failed request keeps
    the pair unknown; it is never guessed."""
    records = dict(stored)
    todo = [c for c in candidates
            if refresh or not is_current(stored.get(match_id(c[0]["project_key"], c[1]["project_key"])),
                                         c[0]["center"], c[1]["center"])]
    log(f"{len(candidates)} pair(s) within {core.OVERLAP_MI:g} straight-line mi; {len(todo)} to request")
    failures = 0
    for i, (pa, pb, _) in enumerate(todo):
        mid = match_id(pa["project_key"], pb["project_key"])
        if i:
            sleep(interval_s)
        try:
            route = compute(pa["center"], pb["center"])
        except RoutesError as exc:
            failures += 1
            records.pop(mid, None)
            log(f"  FAILED {mid}: {exc}")
            continue
        records[mid] = {"_id": mid, "a": pa["project_key"], "b": pb["project_key"],
                        "origin": {"lat": pa["center"]["lat"], "lon": pa["center"]["lon"]},
                        "destination": {"lat": pb["center"]["lat"], "lon": pb["center"]["lon"]}, **route}
        shown = "no drivable route" if route["drive_mi"] is None else f"{route['drive_mi']:.2f} drive mi"
        log(f"  [{i + 1}/{len(todo)}] {mid}: {shown}")
    wanted = {match_id(pa["project_key"], pb["project_key"]) for pa, pb, _ in candidates}
    return [records[mid] for mid in sorted(records) if mid in wanted], failures


FIXTURES = REPO_ROOT / "data/fixtures"


def golden_projects(repo_root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    return [
        {"project_key": f"{g['project_id'].split('_')[0]}:{g['project_id']}", "utility": g["utility"],
         "center": core.center(g["endpoints"])}
        for g in load_json(repo_root / "data/fixtures/golden/projects.json")
    ]


CORPORA = {
    "fixtures": (lambda root: load_json(root / "data/fixtures/projects.json"), "data/fixtures/routes.json"),
    "golden": (golden_projects, "data/fixtures/golden/routes.json"),
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", choices=sorted(CORPORA), required=True)
    ap.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    ap.add_argument("--dry-run", action="store_true", help="list the pairs that would be requested; no requests")
    ap.add_argument("--refresh", action="store_true", help="re-request every candidate, not only missing/stale ones")
    args = ap.parse_args(argv)
    projects, rel = CORPORA[args.corpus]
    out = args.repo_root / rel
    candidates = core.route_candidates(projects(args.repo_root))
    stored = load_routes(out)
    if args.dry_run:
        _, states = drives_for(candidates, stored)
        for mid, state in sorted(states.items()):
            print(f"  {state:9} {mid}")
        return 0
    print(f"requesting from {base_url()}")
    records, failures = fetch_missing(candidates, stored, refresh=args.refresh)
    write_json(out, records)
    print(f"wrote {rel} ({failures} failed request(s))", file=sys.stderr if failures else sys.stdout)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
