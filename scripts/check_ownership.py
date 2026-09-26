#!/usr/bin/env python3
"""Ownership gate (specs/overnight.md §4). Stdlib only.

  check_ownership.py --lint-specs                      spec front matter is consistent
  check_ownership.py --title "[F05] Map" --base origin/main   every changed file is allowed for that title
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# --- minimal front matter parser (the subset our specs use) -----------------------------------------------------------

def _scalar(v: str):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        return [_scalar(x) for x in v[1:-1].split(",") if x.strip()]
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if v in ("true", "false"):
        return v == "true"
    return v


def _strip_comment(line: str) -> str:
    out, quote = [], None
    for ch in line:
        if quote:
            quote = None if ch == quote else quote
        elif ch in "\"'":
            quote = ch
        elif ch == "#":
            break
        out.append(ch)
    return "".join(out).rstrip()


def front_matter(text: str) -> dict:
    """Top-level `key: value`, `key: [a, b]` and `key:` + `  - item` block lists. Nested maps are kept as raw strings."""
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    data, current = {}, None
    for raw in m.group(1).splitlines():
        line = _strip_comment(raw)
        if not line.strip():
            continue
        if not line.startswith((" ", "\t")):
            key, _, val = line.partition(":")
            current = key.strip()
            data[current] = _scalar(val) if val.strip() else []
        elif current is not None and line.strip().startswith("- "):
            if isinstance(data[current], list):
                data[current].append(_scalar(line.strip()[2:]))
        # indented `k: v` lines belong to nested maps (lanes, local_workers); the gate doesn't need them
    return data


def load_specs(root: Path = ROOT) -> tuple[dict, dict[str, dict]]:
    roadmap = front_matter((root / "specs/roadmap.md").read_text())
    features = {}
    for p in sorted((root / "specs/features").glob("*/spec.md")):
        fm = front_matter(p.read_text())
        fm["_path"] = str(p.relative_to(root))
        features.setdefault(fm.get("id"), []).append(fm)
    return roadmap, features


# --- rules --------------------------------------------------------------------------------------------------------------

def _as_list(v) -> list[str]:
    return [x for x in (v if isinstance(v, list) else [v] if v else []) if x]


def lint_specs(roadmap: dict, features: dict[str, list[dict]]) -> list[str]:
    errors = []
    frozen = _as_list(roadmap.get("frozen_paths"))
    for fid, fms in features.items():
        if not fid:
            errors.append(f"{fms[0]['_path']}: missing id")
        elif len(fms) > 1:
            errors.append(f"duplicate id {fid}: " + ", ".join(f["_path"] for f in fms))
    specs = {fid: fms[0] for fid, fms in features.items() if fid}
    for fid, fm in specs.items():
        for dep in _as_list(fm.get("depends_on")):
            if dep not in specs:
                errors.append(f"{fid}: depends_on {dep} does not exist")
    entries = [(fid, e) for fid, fm in specs.items() for e in _as_list(fm.get("owns"))]
    for i, (fid, e) in enumerate(entries):
        for other_fid, o in entries[i + 1:]:
            if other_fid != fid and (o.startswith(e) or e.startswith(o)):
                errors.append(f"{fid} owns {e!r}, which overlaps {other_fid}'s {o!r}")
        for f in frozen:
            if f.startswith(e) or e.startswith(f):
                errors.append(f"{fid} owns {e!r}, which overlaps frozen path {f!r}")
    return sorted(set(errors))


TITLE = re.compile(r"^\[(?:(?P<fix>FIX-)?(?P<id>F\d+)|(?P<contract>C\d+)|REVERT-(?P<sha>[0-9a-f]{7,40}))\]")


def allowed_check(title: str, roadmap: dict, features: dict[str, list[dict]], revert_files=None):
    """Return (predicate(path) -> bool, description) for a PR title, or raise ValueError for an unknown prefix."""
    m = TITLE.match(title.strip())
    if not m:
        raise ValueError(f"title {title!r} has no recognised prefix ([F<n>], [FIX-F<n>], [C<n>], [REVERT-<sha>])")
    if m["contract"]:
        prefixes = _as_list(roadmap.get("frozen_paths")) + ["specs/"]
        return (lambda p: any(p.startswith(x) for x in prefixes)), f"contract change: {prefixes}"
    if m["sha"]:
        files = set(revert_files or [])
        return (lambda p: p in files), f"revert of {m['sha']}: {sorted(files)}"
    fid = m["id"]
    if fid not in features:
        raise ValueError(f"unknown feature {fid}")
    fm = features[fid][0]
    if fm.get("bootstrap") is True:
        return (lambda p: True), f"{fid} is bootstrap: anything"
    prefixes = _as_list(fm.get("owns")) + [f"changes/{fid}.md", f"specs/features/{fid}-", f"specs/decisions/{fid}-"]
    return (lambda p: any(p.startswith(x) for x in prefixes)), f"{fid}: {prefixes}"


def violations(title: str, files: list[str], roadmap: dict, features: dict, revert_files=None) -> list[str]:
    ok, _ = allowed_check(title, roadmap, features, revert_files)
    return [f for f in files if not ok(f)]


def _git(*args: str) -> list[str]:
    out = subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if line.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lint-specs", action="store_true")
    ap.add_argument("--title")
    ap.add_argument("--base", default="origin/main")
    args = ap.parse_args(argv)
    roadmap, features = load_specs()
    rc = 0
    if args.lint_specs:
        errs = lint_specs(roadmap, features)
        for e in errs:
            print(f"spec lint: {e}")
        print(f"spec lint: {len(features)} features, {'FAIL' if errs else 'ok'}")
        rc |= bool(errs)
    if args.title is not None:
        files = _git("diff", "--name-only", f"{args.base}...HEAD")
        m = TITLE.match(args.title.strip())
        revert_files = _git("show", "--name-only", "--format=", m["sha"]) if m and m["sha"] else None
        try:
            ok, desc = allowed_check(args.title, roadmap, features, revert_files)
        except ValueError as e:
            print(f"ownership: {e}")
            return 1
        bad = [f for f in files if not ok(f)]
        for f in bad:
            print(f"ownership: {f} is outside what {args.title!r} may change")
        print(f"ownership: {len(files)} changed files, allowed = {desc}; {'FAIL' if bad else 'ok'}")
        rc |= bool(bad)
    if not args.lint_specs and args.title is None:
        ap.print_help()
        return 2
    return rc


if __name__ == "__main__":
    sys.exit(main())
