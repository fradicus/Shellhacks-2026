#!/usr/bin/env python3
"""Safety net: re-run every auto-generated test file and delete any that fail.

`ci/generate_tests.py` already validates before keeping a file; this step exists so the
pipeline has an independent gate and so previously committed `*_auto_*` tests that were
broken by newer branch commits get pruned instead of pushed back red.

Always exits 0: "nothing left to commit" is a success state.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests" / "pipeline"


def run_pytest(test_file: Path) -> bool:
    rel = os.path.relpath(test_file, ROOT / "pipeline")
    # A path outside pipeline/ makes pytest skip pipeline/pyproject.toml (and its pythonpath),
    # so the config and rootdir are pinned explicitly.
    args = ["pytest", rel, "-q", "--no-header", "-c", "pyproject.toml", "--rootdir", "."]
    cmd = ["uv", "run", *args] if shutil.which("uv") else [sys.executable, "-m", *args]
    try:
        return subprocess.run(cmd, cwd=ROOT / "pipeline", capture_output=True, text=True, timeout=300).returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def main() -> int:
    auto_files = sorted(TESTS_DIR.glob("test_*_auto_*.py"))
    if not auto_files:
        print("no auto-generated tests present")
        return 0
    kept, dropped = 0, 0
    for path in auto_files:
        if run_pytest(path):
            print(f"pass: {path.name}")
            kept += 1
        else:
            path.unlink()
            print(f"pruned failing auto test: {path.name}")
            dropped += 1
    print(f"validate: {kept} passing, {dropped} pruned")
    return 0


if __name__ == "__main__":
    sys.exit(main())
