"""Generate F09 endpoint locations from cached public evidence."""

from __future__ import annotations

import argparse
import json

from .build import build_locations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live-boundaries",
        action="store_true",
        help="Create the small GA/SC Census cache when it is absent; never calls Overpass",
    )
    args = parser.parse_args()
    coverage = build_locations(live_boundaries=args.live_boundaries)
    print(json.dumps({"per_utility": coverage["per_utility"], "totals": coverage["totals"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
