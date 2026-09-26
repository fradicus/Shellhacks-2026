"""Build the cached F04 OSM inventory; pass --live to permit public Overpass requests."""

from __future__ import annotations

import argparse
import json

from .fetch import run_inventory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Fetch missing cache entries from public Overpass")
    args = parser.parse_args()
    manifest = run_inventory(live=args.live)
    print(
        json.dumps(
            {
                "counts": manifest["counts"],
                "requests_made": manifest["requests_made"],
                "retrieval_requests": manifest["retrieval_requests"],
                "status": manifest["status"],
                "total_raw_bytes": manifest["total_raw_bytes"],
            },
            sort_keys=True,
        )
    )
    return 0 if manifest["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
