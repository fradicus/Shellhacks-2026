"""Build 10 years of daily station weather (NOAA NCEI GHCN-Daily) for every located DESC/GPC project center.

    uv run python -m weather_history --allow-public-network

Writes data/weather_history/index.json and one compact series file per station. A station that fails to download or
is less than 95% complete is skipped for the next-nearest one; a project with no qualifying station is listed as
unassigned with the reason. Nothing is interpolated or invented.
"""

import argparse
import gzip
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from common.io import REPO_ROOT, load_json, write_json
from weather_history.core import (
    MIN_COMPLETE,
    RAIN_MAX_MI,
    RULE_VERSION,
    WIND_MAX_MI,
    WINDOW,
    aligned,
    candidates,
    completeness,
    nearest,
    project_centers,
    release_centers,
    site_points,
    tiles,
)

SEARCH = "https://www.ncei.noaa.gov/access/services/search/v1/data"
DATA = "https://www.ncei.noaa.gov/access/services/data/v1"
OUT = REPO_ROOT / "data" / "weather_history"
USER_AGENT = "GridBridge pipeline (https://github.com/fradicus/Shellhacks-2026/issues)"


def get(url: str, retries: int = 3) -> bytes:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=90) as res:
                return res.read()
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


def search_url(tile: tuple[float, float, float, float]) -> str:
    north, west, south, east = tile
    return f"{SEARCH}?" + urllib.parse.urlencode({
        "dataset": "daily-summaries", "bbox": f"{north:.2f},{west:.2f},{south:.2f},{east:.2f}",
        "startDate": f"{WINDOW[0]}T00:00:00", "endDate": f"{WINDOW[1]}T23:59:59",
        "dataTypes": "TMAX", "limit": "1000",
    })


def data_url(station_id: str) -> str:
    return f"{DATA}?" + urllib.parse.urlencode({
        "dataset": "daily-summaries", "stations": station_id,
        "startDate": WINDOW[0].isoformat(), "endDate": WINDOW[1].isoformat(),
        "dataTypes": "PRCP,TMAX,TMIN,SNOW,WSF2", "units": "standard", "format": "json",
    })


def write_compact(path: Path, obj: dict) -> None:
    """Gzipped compact JSON with a fixed mtime: hundreds of 10-year stations stay small, and reruns are byte-stable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    path.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-public-network", action="store_true")
    args = parser.parse_args()
    if not args.allow_public_network:
        parser.error("Explicit --allow-public-network is required; no calls made")

    centers = project_centers(load_json(REPO_ROOT / "data" / "locations" / "locations.json"))
    releases: dict[str, list[dict]] = {}
    for path in sorted((REPO_ROOT / "data").glob("*/**/projects.json")):
        region = path.relative_to(REPO_ROOT / "data").parts[0]
        if region in ("fixtures", "osm", "weather_history", "projects"):
            continue
        rows = load_json(path)
        if isinstance(rows, list):
            releases.setdefault(region, []).extend(r for r in rows if isinstance(r, dict))
    centers += release_centers(releases)
    # Every other known site (OSM infrastructure, candidate locations, verified directory...) also gets a station.
    documents: dict[str, list] = {}
    for path in sorted((REPO_ROOT / "data").glob("**/*.json")):
        top = path.relative_to(REPO_ROOT / "data").parts[0]
        if top in ("weather_history", "fixtures") or path.stat().st_size > 80_000_000:
            continue
        try:
            documents.setdefault(top, []).append(load_json(path))
        except (ValueError, UnicodeDecodeError):
            continue
    sites = site_points(documents)
    print(f"{len(sites)} distinct site coordinates (0.01 deg) across {len(documents)} data folders")
    by_id: dict[str, dict] = {}
    search_urls = []
    for tile in tiles(centers + sites):
        url = search_url(tile)
        search_urls.append(url)
        try:
            for s in candidates(json.loads(get(url))["results"]):
                by_id[s["id"]] = s
        except Exception as error:  # noqa: BLE001 - a failed tile leaves its projects unassigned with the reason
            print(f"  search failed for tile {tile}: {str(error)[:100]}")
    stations = [by_id[k] for k in sorted(by_id)]
    s_url = f"{len(search_urls)} regional NCEI search tiles"
    print(f"{len(centers)} located projects; {len(stations)} stations span {WINDOW[0]}..{WINDOW[1]} for PRCP+TMAX")

    series: dict[str, dict] = {}  # station id -> {"ok": bool, ...}

    def cached(sid: str) -> dict | None:
        """Reuse a station file from a previous run of the same window instead of downloading it again."""
        path = OUT / "stations" / f"{sid}.json.gz"
        if not path.exists():
            return None
        try:
            old = json.loads(gzip.decompress(path.read_bytes()))
        except (OSError, ValueError):
            return None
        keys = ("prcp_in", "tmax_f", "tmin_f", "snow_in", "wsf2_mph")
        same_window = old.get("start") == WINDOW[0].isoformat() and old.get("end") == WINDOW[1].isoformat()
        if not same_window or any(k not in old for k in keys):
            return None
        arrays = {k: old[k] for k in keys}
        src = old["source"]
        return {"ok": True, "url": src["url"], "sha256": src["sha256"], "retrieved_at": src["retrieved_at"],
                "arrays": arrays, "completeness": {k: completeness(v) for k, v in arrays.items()}}

    def load(station: dict) -> dict:
        sid = station["id"]
        if sid not in series and (hit := cached(sid)) is not None:
            series[sid] = hit
        if sid not in series:
            url = data_url(sid)
            try:
                raw = get(url)
                arrays = aligned(json.loads(raw))
                series[sid] = {
                    "ok": True, "url": url, "sha256": hashlib.sha256(raw).hexdigest(), "arrays": arrays,
                    "retrieved_at": datetime.now(UTC).isoformat(timespec="seconds"),
                    "completeness": {k: completeness(v) for k, v in arrays.items()},
                }
            except Exception as error:  # noqa: BLE001 - any failure means "skip this station", recorded below
                series[sid] = {"ok": False, "reason": f"download failed: {str(error)[:120]}"}
        return series[sid]

    def rain_ok(station: dict) -> bool:
        e = load(station)
        return e["ok"] and e["completeness"]["prcp_in"] >= MIN_COMPLETE and e["completeness"]["tmax_f"] >= MIN_COMPLETE

    def wind_ok(station: dict) -> bool:
        if not station["has_wind"]:
            return False
        e = load(station)
        return e["ok"] and e["completeness"]["wsf2_mph"] >= MIN_COMPLETE

    projects, unassigned = [], []
    for c in centers:
        rain, rain_mi = nearest(c, stations, RAIN_MAX_MI, rain_ok)
        wind, wind_mi = nearest(c, stations, WIND_MAX_MI, wind_ok)
        if rain is None:
            reason = f"no station within {RAIN_MAX_MI:g} mi with >= {MIN_COMPLETE:.0%} complete PRCP and TMAX"
            unassigned.append({"project_key": c["project_key"], "reason": reason})
            continue
        projects.append({
            "project_key": c["project_key"], "project_id": c["project_id"], "utility": c["utility"],
            "region": c.get("region", "desc-gpc"),
            "lat": round(c["lat"], 6), "lon": round(c["lon"], 6), "rain_station": rain["id"], "rain_distance_mi": rain_mi,
            "wind_station": wind["id"] if wind else None, "wind_distance_mi": wind_mi,
        })
        if len(projects) % 200 == 0:
            print(f"  {len(projects)} projects assigned, {len(series)} stations downloaded")

    coverage: dict[str, dict[str, int]] = {}
    site_stations: set[str] = set()
    for i, site in enumerate(sites):
        rain, _ = nearest(site, stations, RAIN_MAX_MI, rain_ok)
        wind, _ = nearest(site, stations, WIND_MAX_MI, wind_ok) if rain else (None, None)
        row = coverage.setdefault(site["source"], {"sites": 0, "covered": 0, "with_wind": 0})
        row["sites"] += 1
        if rain:
            row["covered"] += 1
            site_stations.add(rain["id"])
            if wind:
                row["with_wind"] += 1
                site_stations.add(wind["id"])
        if (i + 1) % 2000 == 0:
            print(f"  {i + 1}/{len(sites)} sites checked, {len(series)} stations loaded")

    project_stations = {p["rain_station"] for p in projects} | {p["wind_station"] for p in projects if p["wind_station"]}
    used = sorted(project_stations | site_stations)
    meta = {s["id"]: s for s in stations}
    for old in (OUT / "stations").glob("*.json*") if (OUT / "stations").exists() else []:
        if old.name != f"{old.name.split('.')[0]}.json.gz" or old.name.split(".")[0] not in used:
            old.unlink()  # only files this stage owns; keeps the folder equal to the index
    index_stations = {}
    for sid in used:
        e, m = series[sid], meta[sid]
        write_compact(OUT / "stations" / f"{sid}.json.gz", {
            "station": {"id": sid, "name": m["name"], "lat": m["lat"], "lon": m["lon"], "platforms": m["platforms"]},
            "start": WINDOW[0].isoformat(), "end": WINDOW[1].isoformat(), **e["arrays"],
            "source": {
                "url": e["url"], "sha256": e["sha256"], "retrieved_at": e["retrieved_at"],
                "dataset": "NOAA NCEI GHCN-Daily (daily-summaries)", "units": "standard (in, °F, mph)",
            },
        })
        index_stations[sid] = {
            "name": m["name"], "lat": m["lat"], "lon": m["lon"], "platforms": m["platforms"],
            "completeness": e["completeness"], "file": f"stations/{sid}.json.gz",
        }

    skipped = {sid: e["reason"] for sid, e in series.items() if not e["ok"]}
    write_json(OUT / "index.json", {
        "rule_version": RULE_VERSION, "window": {"start": WINDOW[0].isoformat(), "end": WINDOW[1].isoformat()},
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "selection": {"rain_max_mi": RAIN_MAX_MI, "wind_max_mi": WIND_MAX_MI, "min_complete": MIN_COMPLETE,
                      "center_rule": "pipeline/matches/core.py center() over located, non-rejected endpoints"},
        "source": {
            "search_url": s_url, "search_urls": search_urls, "dataset": "NOAA NCEI GHCN-Daily (daily-summaries)",
            "citation": "https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily",
        },
        "stations": index_stations, "projects": projects, "unassigned": unassigned, "skipped_stations": skipped,
        "site_coverage": {
            "rule": "every coordinate in data/ (0.01 deg), nearest complete station within the same caps",
            "by_source": coverage, "sites": len(sites), "covered": sum(r["covered"] for r in coverage.values()),
        },
    })
    print(f"wrote {len(projects)} projects, {len(unassigned)} unassigned, {len(used)} stations, {len(skipped)} skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
