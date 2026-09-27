"""HIFLD public electric substations for F40's states: a fallback name source when OSM names no facility (part 4).

OSM leaves many Great Lakes substations unnamed ("Hutchinson", "Nelson Dewey", "Sprain Brook"); HIFLD's public layer
names most of them. Extracts are committed like the OSM ones and read only when OSM has no facility of that name, so
no existing OSM match can become ambiguous. HIFLD has no operator field, so these matches rest on voltage
corroboration or C33's unique-name tier. F42 reads the same layer.

From pipeline/:
  uv run python -m greatlakes.hifld fetch --cache /tmp/gl-hifld
  uv run python -m greatlakes.hifld build --cache /tmp/gl-hifld [--check]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import load_json, write_json
from common.names import norm_name
from pnw.build import HIFLD

from .shared import OUT, fetch_into, verify_cache

FOLDER = OUT / "hifld"
STATES = ("MN", "WI", "MI", "IL", "IN", "OH", "PA", "NY")
PAGE = 2000


def fetch(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest = load_json(cache / "manifest.json") if (cache / "manifest.json").exists() else {}
    for state in STATES:
        for page in range(20):
            name = f"hifld-{state.lower()}-{page}.json"
            if name not in manifest:
                fetch_into(cache, name, HIFLD.format(state, page * PAGE), manifest)
                write_json(cache / "manifest.json", manifest)
            if len(load_json(cache / name)["features"]) < PAGE:
                break


def extract(features: list[dict], state: str) -> list[dict]:
    out = []
    for f in features:
        p = f["properties"]
        if not p["NAME"] or p["NAME"].startswith(("NOT AVAILABLE", "UNKNOWN")) or not f["geometry"]:
            continue
        lon, lat = f["geometry"]["coordinates"]
        volts = [v for v in (p["MAX_VOLT"], p["MIN_VOLT"]) if v and v > 0]
        out.append({"id": f"hifld/{p['ID']}", "name": p["NAME"], "norm": norm_name(p["NAME"]), "operator": None,
                    "voltage": ";".join(str(round(v * 1000)) for v in volts) or None, "state": state,
                    "lat": round(lat, 7), "lon": round(lon, 7)})
    return sorted(out, key=lambda f: f["id"])


def build(cache: Path) -> dict[Path, object]:
    manifest = verify_cache(cache, [n for n in load_json(cache / "manifest.json")])
    outputs: dict[Path, object] = {}
    for state in STATES:
        pages = sorted((n for n in manifest if n.startswith(f"hifld-{state.lower()}-")),
                       key=lambda n: int(n.rsplit("-", 1)[1].removesuffix(".json")))
        features = [f for n in pages for f in load_json(cache / n)["features"]]
        outputs[FOLDER / f"{state.lower()}-substations.json"] = extract(features, state)
    outputs[FOLDER / "sources.json"] = {
        "publisher": "Homeland Infrastructure Foundation-Level Data (HIFLD), Electric Substations (public layer)",
        "role": "candidate facility geometry only (C33), used when OSM names no facility",
        "pages": {n: manifest[n] for n in sorted(manifest)}}
    return outputs


def load(states: list[str]) -> list[dict]:
    return [f for s in states if (FOLDER / f"{s.lower()}-substations.json").exists()
            for f in load_json(FOLDER / f"{s.lower()}-substations.json")]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["fetch", "build"])
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "fetch":
        fetch(args.cache)
        return 0
    outputs = build(args.cache)
    if args.check:
        stale = [str(p) for p, v in outputs.items() if not p.exists() or load_json(p) != v]
        print("stale: " + ", ".join(stale) if stale else "ok")
        return 1 if stale else 0
    for path, value in outputs.items():
        write_json(path, value)
    print(json.dumps({p.name: len(v) for p, v in outputs.items() if isinstance(v, list)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
