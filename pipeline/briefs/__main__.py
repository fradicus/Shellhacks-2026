"""Generate brief metadata offline by default; --live explicitly permits Gemini calls."""

import argparse
import json
from pathlib import Path

from common import REPO_ROOT

from .runner import run_batch


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--live", action="store_true", help="Requires GEMINI_API_KEY and GEMINI_MODEL; performs real calls")
    args = parser.parse_args()
    result = run_batch(repo_root=args.repo_root, live=args.live)
    print(json.dumps({k: result[k] for k in ("status", "reason", "model", "calls", "selected", "passed", "rejected")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
