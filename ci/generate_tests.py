#!/usr/bin/env python3
"""Generate pytest tests for pipeline code changed on a feature branch.

Runs in Azure Pipelines (see azure-pipelines.yml) on pushes to feature branches.
For every changed `pipeline/**.py` file (excluding frozen shared code), it asks an
LLM to write a pytest module following `specs/conventions/python-tests.md`, runs it,
retries once with the failure output, and keeps only tests that pass. Files land in
`tests/pipeline/test_fNN_auto_*.py` so they stay inside the owning feature's `owns`
prefix and the ownership gate (scripts/check_ownership.py) stays green.

Usage:
    python ci/generate_tests.py --base origin/main --head HEAD [--branch f09-locations] [--dry-run]

Env:
    OPENAI_API_KEY     required unless --dry-run
    TESTGEN_MODEL      default gpt-4o-mini
    TESTGEN_MAX_FILES  default 5
    BUILD_SOURCEBRANCH set by Azure Pipelines (refs/heads/<branch>)
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONVENTIONS_PATH = ROOT / "specs" / "conventions" / "python-tests.md"
TESTS_DIR = ROOT / "tests" / "pipeline"
FROZEN_PIPELINE_PREFIXES = ("pipeline/common/", "pipeline/matches/")
FEATURE_BRANCH = re.compile(r"^(?:codex-|claude-)?f(?P<num>\d+)-", re.IGNORECASE)

MODEL = os.environ.get("TESTGEN_MODEL", "gpt-4o-mini")
MAX_FILES = int(os.environ.get("TESTGEN_MAX_FILES", "5"))


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def current_branch() -> str:
    ref = os.environ.get("BUILD_SOURCEBRANCH", "")
    if ref.startswith("refs/heads/"):
        return ref[len("refs/heads/") :]
    return git("rev-parse", "--abbrev-ref", "HEAD").strip()


def feature_id(branch: str) -> str | None:
    """f09-locations / codex-f09-locations -> F09. Anything else -> None (no generation)."""
    m = FEATURE_BRANCH.match(branch)
    return f"F{int(m['num']):02d}" if m else None


def changed_pipeline_files(base: str, head: str) -> list[str]:
    names = git("diff", "--name-only", "--diff-filter=AM", f"{base}...{head}").splitlines()
    out = []
    for name in names:
        if not name.endswith(".py") or not name.startswith("pipeline/"):
            continue
        if name.startswith(FROZEN_PIPELINE_PREFIXES):  # shared contracts: humans test these
            continue
        if name.endswith("__init__.py"):
            continue
        out.append(name)
    return out[:MAX_FILES]


def target_path(fid: str, source: str) -> Path:
    """pipeline/locations/geo.py -> tests/pipeline/test_f09_auto_locations_geo.py"""
    parts = Path(source).parts[1:]  # drop "pipeline/"
    tag = "_".join([*parts[:-1], Path(parts[-1]).stem])
    return TESTS_DIR / f"test_{fid.lower()}_auto_{tag}.py"


def style_anchor(fid: str) -> str:
    """First ~80 lines of an existing human test for this feature (or any feature)."""
    candidates = sorted(TESTS_DIR.glob(f"test_{fid.lower()}_*.py")) or sorted(TESTS_DIR.glob("test_*.py"))
    for path in candidates:
        if "_auto_" not in path.name:
            return "\n".join(path.read_text(encoding="utf-8").splitlines()[:80])
    return ""


def strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.removesuffix("```")
    return text.strip() + "\n"


def build_prompt(source_path: str, source: str, conventions: str, anchor: str, error: str | None) -> list[dict]:
    system = (
        "You write pytest tests for a data pipeline. Follow these conventions exactly:\n\n"
        f"{conventions}\n\n"
        "Output ONLY runnable Python test code. No markdown fences, no explanation, no comments "
        "describing the tests."
    )
    user_parts = [f"Write unit tests for the module `{source_path}`:\n\n```python\n{source}\n```"]
    if anchor:
        user_parts.append(f"Match the style of this existing test file:\n\n```python\n{anchor}\n```")
    if error:
        user_parts.append(
            "Your previous attempt produced a test file that failed. Fix it. "
            f"Pytest output (truncated):\n\n```\n{error[-4000:]}\n```"
        )
    return [{"role": "system", "content": system}, {"role": "user", "content": "\n\n".join(user_parts)}]


def run_pytest(test_file: Path) -> tuple[bool, str]:
    rel = test_file.relative_to(ROOT / "pipeline")  # ../tests/pipeline/test_*.py
    cmd = ["uv", "run", "pytest", str(rel), "-q", "--no-header"] if shutil.which("uv") else [
        sys.executable,
        "-m",
        "pytest",
        str(rel),
        "-q",
        "--no-header",
    ]
    try:
        proc = subprocess.run(cmd, cwd=ROOT / "pipeline", capture_output=True, text=True, timeout=300)
    except FileNotFoundError as exc:
        return False, f"pytest runner unavailable: {exc}"
    except subprocess.TimeoutExpired:
        return False, "pytest timed out after 300s"
    return proc.returncode == 0, proc.stdout + proc.stderr


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--branch", default=None, help="override branch detection (for local testing)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan; no API calls, no writes")
    args = ap.parse_args()

    branch = args.branch or current_branch()
    fid = feature_id(branch)
    print(f"branch: {branch} -> feature: {fid or 'none'}")
    if fid is None:
        print("not a feature branch (fNN-* / codex-fNN-*); nothing to generate")
        return 0

    files = changed_pipeline_files(args.base, args.head)
    if not files:
        print("no changed pipeline modules in diff; nothing to generate")
        return 0

    conventions = CONVENTIONS_PATH.read_text(encoding="utf-8")
    anchor = style_anchor(fid)
    plan = [(src, target_path(fid, src)) for src in files]
    print(f"plan ({len(plan)} file(s), cap {MAX_FILES}, model {MODEL}):")
    for src, dst in plan:
        print(f"  {src} -> {dst.relative_to(ROOT)}")
    if args.dry_run:
        print("dry-run: stopping before API calls and writes")
        return 0

    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set; aborting (use --dry-run to preview)")
        return 1

    from openai import OpenAI  # imported lazily so --dry-run needs no dependency

    client = OpenAI()
    kept, dropped = [], []
    for src, dst in plan:
        source = (ROOT / src).read_text(encoding="utf-8")
        error, success = None, False
        for attempt in (1, 2):
            resp = client.chat.completions.create(
                model=MODEL,
                temperature=0.2,
                max_tokens=4000,
                messages=build_prompt(src, source, conventions, anchor, error),
            )
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(strip_fences(resp.choices[0].message.content or ""), encoding="utf-8")
            success, log = run_pytest(dst)
            if success:
                print(f"kept {dst.relative_to(ROOT)} (attempt {attempt})")
                break
            error = log
        if success:
            kept.append(dst)
        else:
            dst.unlink(missing_ok=True)  # never commit a failing test
            dropped.append(dst)
            print(f"dropped {dst.relative_to(ROOT)} (failed after retry)")

    print(f"done: {len(kept)} kept, {len(dropped)} dropped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
