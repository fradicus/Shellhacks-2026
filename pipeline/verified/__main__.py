from __future__ import annotations

import argparse
import json
from pathlib import Path

from .build import build_snapshot, write_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the reviewed EIA-861 verified public directory")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument(
        "--generated-at", required=True, help="Recorded ISO retrieval/build input; never inferred from wall clock"
    )
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument(
        "--refresh", action="store_true", help="Refresh only from the fixed allowlisted EIA URL and require the reviewed hash"
    )
    parser.add_argument("--check", action="store_true", help="Validate and compare with committed artifacts without writing")
    args = parser.parse_args()
    snapshot = build_snapshot(args.repo_root, generated_at=args.generated_at, cache_dir=args.cache_dir, refresh=args.refresh)
    output = args.repo_root / "data" / "verified"
    if args.check:
        expected = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        if expected["dataset"] != snapshot["dataset"]:
            raise SystemExit("committed verified dataset differs from deterministic replay")
    else:
        write_snapshot(snapshot, output)
    print(json.dumps({"dataset": snapshot["dataset"], "counts": snapshot["coverage"]["counts"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
