"""F42 pieces every Pacific Northwest adapter uses: OSM facilities, C33 locating, county anchors, outputs.

OSM, from pipeline/:
  uv run python -m greatlakes.osm fetch --cache /tmp/pnw-osm WA OR ID MT   # the fetch half is state-generic
  uv run python -m pnw.shared osm --cache /tmp/pnw-osm [--check]
OSM data (c) OpenStreetMap contributors, ODbL 1.0.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from common import REPO_ROOT, load_json, write_json
from greatlakes.match import DUPLICATE_METERS, _meters, candidate_center, facility_key, match_facility
from greatlakes.shared import osm_extract, verify_cache

OUT = REPO_ROOT / "data" / "pnw"
STATES = {"WA": "53", "OR": "41", "ID": "16", "MT": "30"}
GEOGRAPHY = REPO_ROOT / "data" / "national" / "geography.json"


def osm(states: list[str]) -> list[dict]:
    return [f for s in states for f in load_json(OUT / "osm" / f"{s.lower()}-substations.json")]


def match(name: str | None, facilities: list[dict], keys: list[str], kv: set[int],
          counties: set[str] | None = None) -> dict:
    """C26 match, loosened by C33: an uncorroborated exact name held by one facility in the state still matches,
    unless the facility contradicts the source: tagged voltages that miss every voltage the source names, or a
    county outside the counties the source (or a county utility's territory) allows."""
    if name is not None:  # narrow to same-key facilities first; keys are precomputed by callers with large pools
        key = facility_key(name)
        facilities = [f for f in facilities if f.get("key") == key or ("key" not in f and facility_key(f["name"]) == key)]
    result = match_facility(name, facilities, keys, kv)
    if result["status"] == "ambiguous" and keys:
        # The same site in several datasets can sit >1 km apart; the owner-tagged points alone may still be one site.
        tagged = [f for f in facilities if any(k in (f.get("operator") or "").upper() for k in keys)]
        retry = match_facility(name, tagged, keys, set())
        return retry if retry["status"] == "matched" else result
    if result["status"] != "not_corroborated":
        return result
    hits = [f for f in facilities if f["id"] in result["facility_ids"]]
    # One physical site mapped twice (node + area) is still one facility; farther apart stays ambiguous.
    if any(_meters(a, b) > DUPLICATE_METERS for a in hits for b in hits):
        return result | {"status": "ambiguous"}
    facility = sorted(hits, key=lambda f: (f["id"].startswith("node"), f["id"]))[0]
    if kv and any(f.get("voltage") for f in hits):
        return result | {"status": "voltage_conflict"}
    if counties and any(f.get("county") and f["county"].upper() not in counties for f in hits):
        return result | {"status": "county_conflict"}
    return {"status": "matched", "name": name, "norm": result["norm"], "facility": facility,
            "corroboration": ["unique_in_state"]}


DATASETS = {"bpa/": "BPA substations GIS ", "hifld/": "HIFLD substations (2021 copy) ", "": "OSM "}


def locate(kind: str | None, names: list[str | None], facilities: list[dict], keys: list[str], kv: set[int],
           dataset: str, counties: set[str] | None = None) -> tuple[dict | None, dict]:
    """C33 candidate center (or None) and the location_candidate evidence block."""
    matches = [match(n, facilities, keys, kv, counties) for n in names] if kind else []
    center = candidate_center(kind, matches) if kind else None
    if center:  # candidate_center says "OSM" for every facility; name each point's real dataset
        center["evidence"] = re.sub(r"OSM (bpa/|hifld/|)", lambda m: DATASETS[m[1]] + m[1], center["evidence"])
    if center and all(m.get("corroboration") == ["unique_in_state"] for m in matches if m["status"] == "matched"):
        center["evidence"] = center["evidence"].replace("corroborated by unique_in_state",
                                                        "the only facility with that name in the state (C33 name-only)")
    elif center:
        center["evidence"] = center["evidence"].replace("unique_in_state", "a name unique in the state")
    fields = ("id", "name", "operator", "voltage", "state", "lat", "lon")
    endpoints = [{k: v for k, v in m.items() if k != "facility"}
                 | ({"facility": {f: m["facility"].get(f) for f in fields}} if m["status"] == "matched" else {})
                 for m in matches]
    return center, {"rule": "C33", "kind": kind, "voltages_kv": sorted(kv), "operator_keys": keys,
                    "endpoints": endpoints, "dataset": dataset}


def counties() -> dict[tuple[str, str], dict]:
    """(state USPS, county name upper) -> Census county record, PNW states only."""
    out = {}
    for c in load_json(GEOGRAPHY)["counties"]:
        if c["state_usps"] in STATES:
            out[(c["state_usps"], c["name"].upper())] = c
    return out


def county_geoids(named: list[tuple[str, str]], index: dict) -> list[str]:
    """Census GEOIDs of the counties the source names (filter metadata only; no map dot, per the user)."""
    keys = [(st, name.upper().removesuffix(" COUNTY").strip()) for st, name in named]
    return sorted({index[k]["county_geoid"] for k in keys if k in index})


def summary(projects: list[dict]) -> dict:
    located = [p for p in projects if p["center"]]
    tiers = Counter("official" if "Official" in p["center"]["evidence"] else
                    "candidate_name_only" if "name-only" in p["center"]["evidence"] else "candidate" for p in located)
    return {"projects": len(projects), "located": len(located),
            "distinct_points": len({(p["center"]["lat"], p["center"]["lon"]) for p in located}),
            "by_tier": dict(sorted(tiers.items())),
            "by_basis": dict(sorted(Counter(p["center"]["basis"] for p in located).items())),
            "unlocated": sum(1 for p in projects if not p["center"]),
            "by_state": dict(sorted(Counter(s for p in projects for s in p["states"]).items())),
            "by_status": dict(sorted(Counter(p["status_group"] for p in projects).items())), "verified": 0}


def build_osm(cache: Path) -> dict[Path, object]:
    manifest = load_json(cache / "manifest.json")
    verify_cache(cache, list(manifest))
    outputs: dict[Path, object] = {}
    artifacts = []
    for name, entry in sorted(manifest.items()):
        state = name.removeprefix("osm-").removesuffix(".json").upper()
        extract = osm_extract(json.loads((cache / name).read_bytes()), state)
        outputs[OUT / "osm" / f"{state.lower()}-substations.json"] = extract
        artifacts.append({"state": state, "named_substations": len(extract), **entry})
    outputs[OUT / "osm" / "sources.json"] = {"publisher": "OpenStreetMap contributors",
                                             "rights": "ODbL 1.0; attribution required",
                                             "role": "candidate facility geometry only (C33)", "artifacts": artifacts}
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["osm"])
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    outputs = build_osm(args.cache)
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
