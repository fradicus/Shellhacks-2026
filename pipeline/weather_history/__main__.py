"""Build 10 years of daily station weather (NOAA NCEI GHCN-Daily) for every located DESC/GPC project center.

    uv run python -m weather_history --allow-public-network

Writes data/weather_history/index.json and one compact series file per station. A station that fails to download or
is less than 95% complete is skipped for the next-nearest one; a project with no qualifying station is listed as
unassigned with the reason. Nothing is interpolated or invented.
"""

import argparse
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


def search_url(centers: list[dict]) -> str:
    pad = 1.0  # degrees; wider than WIND_MAX_MI so edge projects still see airport stations
    north, south = max(c["lat"] for c in centers) + pad, min(c["lat"] for c in centers) - pad
    west, east = min(c["lon"] for c in centers) - pad, max(c["lon"] for c in centers) + pad
    return f"{SEARCH}?" + urllib.parse.urlencode({
        "dataset": "daily-summaries", "bbox": f"{north:.2f},{west:.2f},{south:.2f},{east:.2f}",
        "startDate": f"{WINDOW[0]}T00:00:00", "endDate": f"{WINDOW[1]}T23:59:59",
        "dataTypes": "TMAX", "limit": "1000",
    })


def data_url(station_id: str) -> str:
    return f"{DATA}?" + urllib.parse.urlencode({
        "dataset": "daily-summaries", "stations": station_id,
        "startDate": WINDOW[0].isoformat(), "endDate": WINDOW[1].isoformat(),
        "dataTypes": "PRCP,TMAX,WSF2", "units": "standard", "format": "json",
    })


def write_compact(path: Path, obj: dict) -> None:
    """Sorted keys and no indentation: 3,653-day arrays stay one line each, and reruns are byte-stable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-public-network", action="store_true")
    args = parser.parse_args()
    if not args.allow_public_network:
        parser.error("Explicit --allow-public-network is required; no calls made")

    centers = project_centers(load_json(REPO_ROOT / "data" / "locations" / "locations.json"))
    s_url = search_url(centers)
    stations = candidates(json.loads(get(s_url))["results"])
    print(f"{len(centers)} located projects; {len(stations)} stations span {WINDOW[0]}..{WINDOW[1]} for PRCP+TMAX")

    series: dict[str, dict] = {}  # station id -> {"ok": bool, ...}

    def load(station: dict) -> dict:
        sid = station["id"]
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
            "lat": round(c["lat"], 6), "lon": round(c["lon"], 6), "rain_station": rain["id"], "rain_distance_mi": rain_mi,
            "wind_station": wind["id"] if wind else None, "wind_distance_mi": wind_mi,
        })
        print(f"  {c['project_key']}: rain/heat {rain['id']} {rain_mi} mi; wind {wind['id'] if wind else 'none'}")

    used = sorted({p["rain_station"] for p in projects} | {p["wind_station"] for p in projects if p["wind_station"]})
    meta = {s["id"]: s for s in stations}
    for old in (OUT / "stations").glob("*.json") if (OUT / "stations").exists() else []:
        if old.stem not in used:
            old.unlink()  # only files this stage owns; keeps the folder equal to the index
    index_stations = {}
    for sid in used:
        e, m = series[sid], meta[sid]
        write_compact(OUT / "stations" / f"{sid}.json", {
            "station": {"id": sid, "name": m["name"], "lat": m["lat"], "lon": m["lon"], "platforms": m["platforms"]},
            "start": WINDOW[0].isoformat(), "end": WINDOW[1].isoformat(), **e["arrays"],
            "source": {
                "url": e["url"], "sha256": e["sha256"], "retrieved_at": e["retrieved_at"],
                "dataset": "NOAA NCEI GHCN-Daily (daily-summaries)", "units": "standard (in, °F, mph)",
            },
        })
        index_stations[sid] = {
            "name": m["name"], "lat": m["lat"], "lon": m["lon"], "platforms": m["platforms"],
            "completeness": e["completeness"], "file": f"stations/{sid}.json",
        }

    skipped = {sid: e["reason"] for sid, e in series.items() if not e["ok"]}
    write_json(OUT / "index.json", {
        "rule_version": RULE_VERSION, "window": {"start": WINDOW[0].isoformat(), "end": WINDOW[1].isoformat()},
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "selection": {"rain_max_mi": RAIN_MAX_MI, "wind_max_mi": WIND_MAX_MI, "min_complete": MIN_COMPLETE,
                      "center_rule": "pipeline/matches/core.py center() over located, non-rejected endpoints"},
        "source": {
            "search_url": s_url, "dataset": "NOAA NCEI GHCN-Daily (daily-summaries)",
            "citation": "https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily",
        },
        "stations": index_stations, "projects": projects, "unassigned": unassigned, "skipped_stations": skipped,
    })
    print(f"wrote {len(projects)} projects, {len(unassigned)} unassigned, {len(used)} stations, {len(skipped)} skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
