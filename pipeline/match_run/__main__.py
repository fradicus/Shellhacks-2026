"""Run F10 against the committed full corpus.

    uv run python -m match_run [--fetch-routes]

--fetch-routes first requests driving routes for missing or stale candidate pairs (C41; public OSRM unless
OSRM_URL is set, one request per second) and rewrites data/routes/routes.json. Without it, no router is called.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from common import REPO_ROOT, load_json, write_json
from matches import core
from matches.routes import fetch_missing, load_routes

from .build import _bind_locations, _prepared_projects, build_matches

ROUTES = "data/routes/routes.json"


def fetch_routes(repo_root: Path) -> int:
    projects = [*load_json(repo_root / "data/projects/desc.json"), *load_json(repo_root / "data/projects/gpc.json")]
    active, by_project = _bind_locations(projects, load_json(repo_root / "data/locations/locations.json"))
    prepared, _, _ = _prepared_projects(active, by_project)
    records, failures = fetch_missing(core.route_candidates(prepared), load_routes(repo_root / ROUTES))
    write_json(repo_root / ROUTES, records)
    print(f"wrote {ROUTES}: {len(records)} route(s), {failures} failed request(s)")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--analysis-date", default=os.getenv("ANALYSIS_DATE", "2026-09-26"))
    parser.add_argument("--fetch-routes", action="store_true", help="request missing/stale routes first")
    args = parser.parse_args()
    if args.fetch_routes and fetch_routes(args.repo_root):
        return 1
    summary = build_matches(repo_root=args.repo_root, analysis_date=args.analysis_date)
    print(json.dumps(summary["pairs"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
