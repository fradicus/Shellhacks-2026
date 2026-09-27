"""Benchmark the overlap matcher's candidate search against a scan of every pair, on synthetic projects only.

    uv run python -m matches.benchmark [--sizes 500 2000 8000] [--spread 12]

Synthetic records are generated here and never written anywhere; the numbers describe the algorithm, not the corpus.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from itertools import combinations
from typing import Any

from matches import core


def synthetic_projects(n: int, *, seed: int = 0, spread_deg: float = 12.0) -> list[dict[str, Any]]:
    """`n` test-only projects scattered over a `spread_deg` square, with some unlocated and unknown-utility records."""
    rng = random.Random(seed)
    out = []
    for i in range(n):
        roll = rng.random()
        utility = "unknown" if roll < 0.05 else rng.choice(core.KNOWN_UTILITIES)
        located = roll >= 0.1
        out.append(
            {
                "project_key": f"SYN:{seed}:{i:06d}",
                "utility": utility,
                "center": {"lat": 30 + rng.random() * spread_deg, "lon": -90 + rng.random() * spread_deg, "basis": "two"}
                if located
                else None,
                "in_service": {"raw": "", "date": f"20{rng.randint(20, 35)}-0{rng.randint(1, 9)}-1{rng.randint(0, 9)}",
                               "precision": "day"},
                "location_confidence": rng.choice(["high", "medium", "low"]),
            }
        )
    return out


def _full_scan(projects: list[dict[str, Any]]) -> int:
    return sum(1 for p, q in combinations(projects, 2) if core.is_overlap(p, q)[0])


def run(sizes: list[int], spread: float, max_full_scan: int) -> list[dict[str, Any]]:
    rows = []
    for n in sizes:
        projects = synthetic_projects(n, spread_deg=spread)
        t0 = time.perf_counter()
        matches = core.overlaps(projects, "2026-09-26")
        indexed = time.perf_counter() - t0
        candidates = len(core.candidate_pairs(projects))
        row: dict[str, Any] = {
            "projects": n,
            "all_pairs": n * (n - 1) // 2,
            "candidates": candidates,
            "matches": len(matches),
            "indexed_s": round(indexed, 4),
            "full_scan_s": None,
        }
        if n <= max_full_scan:
            t0 = time.perf_counter()
            full = _full_scan(projects)
            row["full_scan_s"] = round(time.perf_counter() - t0, 4)
            if full != len(matches):
                raise SystemExit(f"candidate search disagrees with the full scan at n={n}: {len(matches)} vs {full}")
        rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sizes", type=int, nargs="+", default=[500, 2000, 8000])
    parser.add_argument("--spread", type=float, default=12.0, help="side of the synthetic square, degrees")
    parser.add_argument("--max-full-scan", type=int, default=4000, help="skip the O(n²) reference above this size")
    args = parser.parse_args(argv)
    for row in run(args.sizes, args.spread, args.max_full_scan):
        print(json.dumps(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
