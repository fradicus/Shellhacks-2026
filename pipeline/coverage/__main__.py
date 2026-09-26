"""Offline CLI: ``uv run python -m coverage [--repo-root PATH]``."""

import argparse
from pathlib import Path

from common import REPO_ROOT, load_json, write_json
from coverage.core import summarize
from load.build import collect


def optional(path: Path) -> dict | None:
    return load_json(path) if path.is_file() else None


def run(repo_root: Path = REPO_ROOT) -> list[dict]:
    records, errors, _ = collect(repo_root)
    if errors:
        raise ValueError("coverage inputs failed validation:\n" + "\n".join(errors))
    result = summarize(records, optional(repo_root / "data/extraction/eval.json"),
                       optional(repo_root / "reports/audit/evidence.json"))
    write_json(repo_root / "data/coverage/coverage.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the deterministic per-source coverage ledger")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    result = run(args.repo_root.resolve())
    totals = result[0]["counts"]["global"] if result else {}
    print(f"coverage: {len(result)} sources, {totals.get('project_versions', 0)} project versions, "
          f"{totals.get('located_endpoints', 0)} located endpoints, {totals.get('matches', 0)} matches")


if __name__ == "__main__":
    main()
