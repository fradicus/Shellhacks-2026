"""Build, validate, or intentionally refresh the reviewed national snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import REPO_ROOT
from national.build import build_snapshot, load_snapshot
from national.fetch import refresh_ids
from national.registry import entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "validate", "refresh"), nargs="?", default="build")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--source", action="append", default=[], help="Reviewed manifest source id; repeat as needed")
    args = parser.parse_args()
    if args.command == "refresh":
        source_ids = args.source or sorted(entries(args.repo_root))
        paths = refresh_ids(source_ids, args.repo_root)
        print(json.dumps({"refreshed": [path.name for path in paths]}, sort_keys=True))
        return 0
    snapshot = build_snapshot(args.repo_root) if args.command == "build" else load_snapshot(args.repo_root)
    print(json.dumps({
        "sources": len(snapshot["sources"]),
        "projects": len(snapshot["projects"]),
        "located": snapshot["coverage"]["located_count"],
        "states_and_dc": snapshot["geography"]["counts"]["states_and_dc"],
        "counties_primary": snapshot["geography"]["counts"]["counties_primary"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
