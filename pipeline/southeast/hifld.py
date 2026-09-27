"""Public HIFLD facility geometry for SERTP; inventories never become project records.

Run `python -m southeast.hifld --cache <dir>` to fetch pinned pages and publish extracts.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from common import REPO_ROOT, load_json, write_json
from common.names import norm_name
from greatlakes.shared import fetch_into, verify_cache
from pnw.build import HIFLD

FOLDER = REPO_ROOT / "data/southeast/hifld"
PAGE = 2000


def extract(features: list[dict], state: str) -> list[dict]:
    result = []
    for feature in features:
        p = feature["properties"]
        if p["STATE"] != state:
            raise ValueError("HIFLD returned a facility outside the requested state")
        if not p["NAME"] or p["NAME"].startswith(("NOT AVAILABLE", "UNKNOWN")) or not feature["geometry"]:
            continue
        lon, lat = feature["geometry"]["coordinates"]
        volts = [v for v in (p["MAX_VOLT"], p["MIN_VOLT"]) if v and v > 0]
        result.append({"id": f"hifld/{p['ID']}", "name": p["NAME"], "norm": norm_name(p["NAME"]),
                       "operator": None, "voltage": ";".join(str(round(v * 1000)) for v in volts) or None,
                       "state": state, "lat": round(lat, 7), "lon": round(lon, 7)})
    return sorted(result, key=lambda f: f["id"])


def build(cache: Path, states: list[str], check: bool = False) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    manifest = load_json(cache / "manifest.json") if (cache / "manifest.json").exists() else {}
    outputs = {}
    for state in states:
        features = []
        for page in range(20):
            name = f"hifld-{state.lower()}-{page}.json"
            if name not in manifest:
                if check:
                    raise ValueError(f"missing cached page: {name}")
                fetch_into(cache, name, HIFLD.format(state, page * PAGE), manifest)
                write_json(cache / "manifest.json", manifest)
            verify_cache(cache, [name])
            batch = load_json(cache / name)["features"]
            features.extend(batch)
            if len(batch) < PAGE:
                break
        else:
            raise ValueError(f"HIFLD {state}: pagination limit reached")
        ids = [f["properties"]["ID"] for f in features]
        if len(ids) != len(set(ids)):
            raise ValueError(f"HIFLD {state}: duplicate facilities across pages")
        outputs[FOLDER / f"{state.lower()}-substations.json"] = extract(features, state)
    outputs[FOLDER / "sources.json"] = {
        "publisher": "HIFLD Open Electric Substations, public February 2021 copy on ArcGIS Online",
        "role": "Candidate facility geometry only; no independent project-location verification",
        "pages": manifest}
    for path, value in outputs.items():
        if check:
            if not path.exists() or load_json(path) != value:
                raise ValueError(f"stale: {path}")
        else:
            write_json(path, value)


def load(states: list[str]) -> dict[str, list[dict]]:
    return {state: load_json(FOLDER / f"{state.lower()}-substations.json") for state in states}


if __name__ == "__main__":
    from southeast.sertp import OSM_STATES

    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    build(args.cache, OSM_STATES, args.check)
