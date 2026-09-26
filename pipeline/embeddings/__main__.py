"""Embed the search corpus offline-by-default; --live explicitly permits Gemini calls.

    cd pipeline && uv run python -m embeddings          # cache-only; defers if anything needs embedding
    cd pipeline && uv run python -m embeddings --live   # needs GEMINI_API_KEY; embeds new/changed texts
"""

import argparse
import json
from pathlib import Path

from common import REPO_ROOT

from .runner import run_batch


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Requires GEMINI_API_KEY; performs real embedding calls for new/changed texts",
    )
    args = parser.parse_args()
    summary = run_batch(repo_root=args.repo_root, live=args.live)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
