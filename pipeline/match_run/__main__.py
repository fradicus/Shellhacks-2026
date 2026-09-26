"""Run F10 against the committed full corpus."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from common import REPO_ROOT

from .build import build_matches


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--analysis-date", default=os.getenv("ANALYSIS_DATE", "2026-09-26"))
    args = parser.parse_args()
    summary = build_matches(repo_root=args.repo_root, analysis_date=args.analysis_date)
    print(json.dumps(summary["pairs"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
