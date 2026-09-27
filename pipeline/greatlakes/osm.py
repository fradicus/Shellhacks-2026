"""Shared candidate geometry: named OSM substations per state, committed once and read by every adapter.

From pipeline/:
  uv run python -m greatlakes.osm fetch --cache /tmp/gl-osm MN WI MI IL IN   # skips states already in the cache
  uv run python -m greatlakes.osm build --cache /tmp/gl-osm [--check]
OSM data (c) OpenStreetMap contributors, ODbL 1.0.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import load_json, write_json

from .shared import OUT, fetch_osm, osm_extract, verify_cache

FOLDER = OUT / "osm"


def fetch(cache: Path, states: list[str]) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest = load_json(cache / "manifest.json") if (cache / "manifest.json").exists() else {}
    for state in states:
        if f"osm-{state.lower()}.json" not in manifest:
            fetch_osm(cache, state, manifest)
            write_json(cache / "manifest.json", manifest)


def build(cache: Path) -> dict[Path, object]:
    manifest = load_json(cache / "manifest.json")
    verify_cache(cache, list(manifest))
    outputs: dict[Path, object] = {}
    sources = []
    for name, entry in sorted(manifest.items()):
        state = name.removeprefix("osm-").removesuffix(".json").upper()
        extract = osm_extract(json.loads((cache / name).read_bytes()), state)
        outputs[FOLDER / f"{state.lower()}-substations.json"] = extract
        sources.append({"state": state, "named_substations": len(extract), **entry})
    outputs[FOLDER / "sources.json"] = {"publisher": "OpenStreetMap contributors",
                                         "rights": "ODbL 1.0; attribution required",
                                         "role": "candidate facility geometry only (C26)", "artifacts": sources}
    return outputs


def load(states: list[str]) -> list[dict]:
    return [f for s in states for f in load_json(FOLDER / f"{s.lower()}-substations.json")]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["fetch", "build"])
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("states", nargs="*")
    args = parser.parse_args(argv)
    if args.command == "fetch":
        fetch(args.cache, args.states)
        return 0
    outputs = build(args.cache)
    if args.check:
        stale = [str(p) for p, v in outputs.items() if not p.exists() or load_json(p) != v]
        print("stale: " + ", ".join(stale) if stale else "ok")
        return 1 if stale else 0
    for path, value in outputs.items():
        write_json(path, value)
    print({p.name: len(v) for p, v in outputs.items() if isinstance(v, list)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
