"""Pieces every F40 state adapter uses: bounded fetch, OSM substation extracts, candidate block, outputs."""

from __future__ import annotations

import hashlib
import json
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from common import REPO_ROOT, load_json, write_json
from common.names import norm_name

from .match import candidate_center, facilities_named, match_facility

USER_AGENT = "GridBridge/0.1 (https://github.com/fradicus/Shellhacks-2026)"
# Public instances from the OSM wiki, tried in order; the manifest records which one answered.
OVERPASS_URLS = ["https://overpass-api.de/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
MAX_BYTES = 16 * 1024 * 1024
OUT = REPO_ROOT / "data" / "greatlakes"
# Fixed publication order (C26): each state's projects are appended to data/greatlakes/projects.json.
STATES = ["mn", "wi", "miso", "ny", "aep"]
# Operator-name fragments per utility, matched against the OSM operator tag.
OPERATOR_KEYS = {
    "XEL": ["XCEL", "NORTHERN STATES"], "XCEL": ["XCEL", "NORTHERN STATES"], "GRE": ["GREAT RIVER"],
    "OTP": ["OTTER TAIL"], "MP": ["MINNESOTA POWER", "ALLETE"], "MPC": ["MINNKOTA"], "MRES": ["MISSOURI RIVER"],
    "ITCM": ["ITC"], "ITC": ["ITC"], "DPC": ["DAIRYLAND"], "SMP": ["SOUTHERN MINNESOTA MUNICIPAL", "SMMPA"],
    "SMMPA": ["SOUTHERN MINNESOTA MUNICIPAL", "SMMPA"], "RPU": ["ROCHESTER PUBLIC"],
    "CMPAS": ["CENTRAL MINNESOTA MUNICIPAL", "CMMPA"], "ATC": ["AMERICAN TRANSMISSION", "ATC"],
}


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def get(url: str, data: bytes | None = None, timeout: int = 180, attempts: int = 2) -> bytes:
    request = Request(url, data=data, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS URLs only
                body = response.read(MAX_BYTES + 1)
            break
        except OSError:
            if attempt == attempts:
                raise
            time.sleep(30 * attempt)
    if len(body) > MAX_BYTES:
        raise RuntimeError(f"{url}: exceeds {MAX_BYTES} bytes")
    return body


def fetch_into(cache: Path, name: str, url: str, manifest: dict, data: bytes | None = None, **extra) -> None:
    body = get(url, data)
    (cache / name).write_bytes(body)
    manifest[name] = {"url": url, "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body),
                      "retrieved_at": utc_now()} | extra
    time.sleep(1)


def overpass_query(state: str) -> str:
    return f'[out:json][timeout:170];area["ISO3166-2"="US-{state}"]->.a;nwr["power"="substation"](area.a);out center tags;'


def fetch_osm(cache: Path, state: str, manifest: dict) -> None:
    query = overpass_query(state)
    for url in OVERPASS_URLS:
        try:
            fetch_into(cache, f"osm-{state.lower()}.json", url, manifest, urlencode({"data": query}).encode(),
                       query=query)
            break
        except OSError:
            if url == OVERPASS_URLS[-1]:
                raise
    time.sleep(10)  # Overpass etiquette between heavy queries


def verify_cache(cache: Path, names: list[str]) -> dict:
    manifest = load_json(cache / "manifest.json")
    for name in names:
        if hashlib.sha256((cache / name).read_bytes()).hexdigest() != manifest[name]["sha256"]:
            raise SystemExit(f"{name}: cache bytes do not match the fetch manifest")
    return manifest


def osm_extract(raw: dict, state: str) -> list[dict]:
    """Named substations only, with the fields matching reads. OSM data (c) OpenStreetMap contributors, ODbL."""
    out = []
    for e in raw["elements"]:
        tags = e.get("tags", {})
        point = e if "lat" in e else e.get("center")
        if not tags.get("name") or not point:
            continue
        out.append({"id": f"{e['type']}/{e['id']}", "name": tags["name"], "norm": norm_name(tags["name"]),
                    "operator": tags.get("operator"), "voltage": tags.get("voltage"), "state": state,
                    "lat": round(point["lat"], 7), "lon": round(point["lon"], 7)})
    return sorted(out, key=lambda f: f["id"])


def locate(name: str, description: str | None, facilities: list[dict], keys: list[str], kv: set[int],
           dataset: str) -> tuple[dict | None, dict]:
    """C26 candidate center (or None) and the location_candidate evidence block."""
    return locate_named(facilities_named(name, description), facilities, keys, kv, dataset)


def locate_named(named: dict, facilities: list[dict], keys: list[str], kv: set[int], dataset: str
                 ) -> tuple[dict | None, dict]:
    """Candidate from facility names already stated by the source (e.g. a table's From/To terminal columns)."""
    matches = [match_facility(n, facilities, keys, kv) for n in named["names"]]
    center = candidate_center(named["kind"], matches) if named["kind"] else None
    fields = ("id", "name", "operator", "voltage", "state", "lat", "lon")
    endpoints = [{k: v for k, v in m.items() if k != "facility"}
                 | ({"facility": {f: m["facility"].get(f) for f in fields}} if m["status"] == "matched" else {})
                 for m in matches]
    return center, {"rule": "C26", "kind": named["kind"], "names_from": named["from"], "reason": named["reason"],
                    "voltages_kv": sorted(kv), "operator_keys": keys, "endpoints": endpoints, "dataset": dataset}


def summary(projects: list[dict]) -> dict:
    located = [p for p in projects if p["center"]]
    reasons = Counter(
        p["location_candidate"]["reason"] or ",".join(sorted({e["status"] for e in p["location_candidate"]["endpoints"]}))
        for p in projects if not p["center"])
    return {"projects": len(projects), "candidate_located": len(located),
            "distinct_points": len({(p["center"]["lat"], p["center"]["lon"]) for p in located}),
            "by_basis": dict(sorted(Counter(p["center"]["basis"] for p in located).items())),
            "by_status": dict(sorted(Counter(p["status_group"] for p in projects).items())),
            "located_by_status": dict(sorted(Counter(p["status_group"] for p in located).items())),
            "unlocated_reasons": dict(sorted(reasons.items())), "verified": 0}


def write_outputs(state: str, result: dict, check: bool) -> int:
    folder = OUT / state
    outputs = {folder / "projects.json": result["projects"], folder / "dispositions.json": result["dispositions"],
               folder / "sources.json": result["sources"], folder / "summary.json": summary(result["projects"])}
    if check:
        stale = [str(p) for p, v in outputs.items() if not p.exists() or load_json(p) != v]
        print("stale: " + ", ".join(stale) if stale else "ok")
        return 1 if stale else 0
    for path, value in outputs.items():
        write_json(path, value)
    combined = [p for s in STATES if (OUT / s / "projects.json").exists() for p in load_json(OUT / s / "projects.json")]
    ids = [p["_id"] for p in combined]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate _id across states")
    write_json(OUT / "projects.json", combined)
    print(json.dumps(summary(result["projects"]), indent=2))
    return 0
