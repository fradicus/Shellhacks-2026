"""Print docs or full for a PR diff; unknown paths always require full CI."""

import argparse
import subprocess
from pathlib import PurePosixPath


def docs_only(paths: list[str]) -> bool:
    return bool(paths) and all(
        path in {"README.md", "AGENTS.md", "CLAUDE.md"}
        or (PurePosixPath(path).parts[0] in {"specs", "reports", "changes"}
            and path.endswith(".md"))
        for path in paths
    )


def changed_paths(base: str, head: str) -> list[str]:
    # Disabling rename detection checks both old and new paths (code -> docs too).
    result = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", "-z", f"{base}...{head}"],
        check=True, capture_output=True,
    )
    return [p.decode("utf-8", errors="surrogateescape") for p in result.stdout.split(b"\0") if p]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    print("docs" if docs_only(changed_paths(args.base, args.head)) else "full")
