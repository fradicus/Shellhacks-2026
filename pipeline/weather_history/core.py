"""Pure logic for the 10-year station weather history: centers, station choice, completeness and aligned series.

No network here; `__main__` does the fetching so every rule below is unit-testable with fixtures.
"""

from __future__ import annotations

from datetime import date, timedelta
from math import asin, cos, radians, sin, sqrt
from typing import Any

from matches.core import center

WINDOW = (date(2016, 1, 1), date(2025, 12, 31))  # last 10 complete calendar years at the 2026 run
RAIN_MAX_MI = 30.0  # nearest complete precipitation + temperature record
WIND_MAX_MI = 60.0  # wind is recorded mostly at airports, so the search reaches further and the distance is shown
MIN_COMPLETE = 0.95  # share of days with a value; below this a station is skipped, never gap-filled
RULE_VERSION = "weather-history-v1"


def haversine_mi(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = radians(lat1), radians(lat2)
    h = sin((p2 - p1) / 2) ** 2 + cos(p1) * cos(p2) * sin(radians(lon2 - lon1) / 2) ** 2
    return 3958.8 * 2 * asin(min(1.0, sqrt(h)))


def project_centers(locations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One center per DESC/GPC project filing, using the canonical matching `center()` rule. Unlocated projects are omitted."""
    by_project: dict[str, list[dict[str, Any]]] = {}
    meta: dict[str, dict[str, Any]] = {}
    for loc in locations:
        pid = loc.get("project_id")
        if not pid or loc.get("project_utility") not in ("DESC", "GPC"):
            continue
        by_project.setdefault(pid, []).append(loc)
        meta[pid] = {"project_key": loc["project_key"], "utility": loc["project_utility"]}
    out: dict[str, dict[str, Any]] = {}
    for pid in sorted(by_project):
        c = center(by_project[pid])
        key = meta[pid]["project_key"]
        if c is None or key in out:  # first filing version in sorted order wins; later versions share the key
            continue
        out[key] = {**meta[pid], "project_id": pid, "lat": c["lat"], "lon": c["lon"]}
    return [out[k] for k in sorted(out)]


def release_centers(releases: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Located project centers from the regional releases (data/<region>/**/projects.json), keyed by release `_id`."""
    out: dict[str, dict[str, Any]] = {}
    for region in sorted(releases):
        for p in releases[region]:
            c, pid = p.get("center"), p.get("_id")
            located = isinstance(c, dict) and isinstance(c.get("lat"), (int, float)) and isinstance(c.get("lon"), (int, float))
            if not pid or not located:
                continue
            if pid.startswith("legacy:") or pid in out:  # legacy rows repeat the DESC/GPC centers handled by project_centers
                continue
            out[pid] = {"project_key": pid, "project_id": pid, "utility": p.get("owner") or "Owner not stated", "region": region,
                        "name": p.get("name"), "lat": float(c["lat"]), "lon": float(c["lon"])}
    return [out[k] for k in sorted(out)]


def site_points(documents: dict[str, Any]) -> list[dict[str, Any]]:
    """Every coordinate the repo knows as a possible work site (project centers, located endpoints, OSM infrastructure,
    candidate locations), deduplicated to 0.01 degrees (~1 km). `documents` maps a top-level data folder to parsed JSON."""
    out: dict[tuple[float, float], dict[str, Any]] = {}

    def walk(node: Any, source: str) -> None:
        if isinstance(node, dict):
            c = node.get("center") if isinstance(node.get("center"), dict) else node
            lat, lon = c.get("lat"), c.get("lon")
            numeric = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (lat, lon))
            if numeric and -90 <= lat <= 90 and -180 <= lon <= 180:
                out.setdefault((round(lat, 2), round(lon, 2)), {"lat": round(lat, 2), "lon": round(lon, 2), "source": source})
            for v in node.values():
                walk(v, source)
        elif isinstance(node, list):
            for v in node:
                walk(v, source)

    for source in sorted(documents):
        for doc in documents[source]:
            walk(doc, source)
    return [out[k] for k in sorted(out)]


def tiles(points: list[dict[str, Any]], size_deg: float = 2.0) -> list[tuple[float, float, float, float]]:
    """Distinct size_deg grid cells holding at least one point, as (north, west, south, east), each padded by 1 degree."""
    cells = sorted({(int(p["lat"] // size_deg), int(p["lon"] // size_deg)) for p in points})
    return [((i + 1) * size_deg + 1, j * size_deg - 1, i * size_deg - 1, (j + 1) * size_deg + 1) for i, j in cells]


def _spans(station: dict[str, Any], data_type: str) -> bool:
    for t in station.get("dataTypes", []):
        if t.get("id") == data_type:
            return (t.get("startDate") or "9") <= WINDOW[0].isoformat() and (t.get("endDate") or "") >= WINDOW[1].isoformat()
    return False


def candidates(search_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stations whose published PRCP and TMAX records span the whole window (completeness is checked after download)."""
    out = []
    for r in search_results:
        st = (r.get("stations") or [{}])[0]
        lon, lat = (r.get("location") or {}).get("coordinates", [None, None])
        if lat is None or lon is None or not st.get("id"):
            continue
        if _spans(st, "PRCP") and _spans(st, "TMAX"):
            out.append({
                "id": st["id"], "name": st.get("name") or st["id"], "lat": lat, "lon": lon,
                "platforms": sorted({p["id"] for p in st.get("platforms", []) if p.get("id")}),
                "has_wind": _spans(st, "WSF2"),
            })
    return sorted(out, key=lambda s: s["id"])


def days() -> list[date]:
    n = (WINDOW[1] - WINDOW[0]).days + 1
    return [WINDOW[0] + timedelta(days=i) for i in range(n)]


def _num(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if v == v else None  # NaN stays missing


def aligned(rows: list[dict[str, Any]]) -> dict[str, list[float | None]]:
    """NCEI rows -> day-aligned arrays over the window. A missing day stays None; nothing is interpolated."""
    by_date = {r.get("DATE"): r for r in rows}
    series: dict[str, list[float | None]] = {"prcp_in": [], "tmax_f": [], "tmin_f": [], "snow_in": [], "wsf2_mph": []}
    for d in days():
        r = by_date.get(d.isoformat(), {})
        p, t, lo, sn, w = (_num(r.get(k)) for k in ("PRCP", "TMAX", "TMIN", "SNOW", "WSF2"))
        series["prcp_in"].append(None if p is None else round(p, 2))
        series["tmax_f"].append(None if t is None else round(t))
        series["tmin_f"].append(None if lo is None else round(lo))
        series["snow_in"].append(None if sn is None else round(sn, 1))
        series["wsf2_mph"].append(None if w is None else round(w, 1))
    return series


def completeness(values: list[float | None]) -> float:
    return round(sum(v is not None for v in values) / len(values), 4) if values else 0.0


def nearest(point: dict[str, Any], stations: list[dict[str, Any]], max_mi: float, accept) -> tuple[dict | None, float | None]:
    """Closest station within max_mi that `accept` passes (e.g. downloaded and complete); ties break on station id."""
    # Cheap degree box first (1 deg lat ~ 69 mi; longitude degrees shrink with latitude), then exact distances.
    dlat = max_mi / 69.0 + 0.01
    dlon = max_mi / max(1.0, 69.17 * cos(radians(min(89.0, abs(point["lat"]))))) + 0.01
    box = (s for s in stations if abs(s["lat"] - point["lat"]) <= dlat and abs(s["lon"] - point["lon"]) <= dlon)
    ranked = sorted((haversine_mi(point["lat"], point["lon"], s["lat"], s["lon"]), s["id"], s) for s in box)
    for miles, _, s in ranked:
        if miles > max_mi:
            break
        if accept(s):
            return s, round(miles, 2)
    return None, None
