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
    series: dict[str, list[float | None]] = {"prcp_in": [], "tmax_f": [], "wsf2_mph": []}
    for d in days():
        r = by_date.get(d.isoformat(), {})
        p, t, w = _num(r.get("PRCP")), _num(r.get("TMAX")), _num(r.get("WSF2"))
        series["prcp_in"].append(None if p is None else round(p, 2))
        series["tmax_f"].append(None if t is None else round(t))
        series["wsf2_mph"].append(None if w is None else round(w, 1))
    return series


def completeness(values: list[float | None]) -> float:
    return round(sum(v is not None for v in values) / len(values), 4) if values else 0.0


def nearest(point: dict[str, Any], stations: list[dict[str, Any]], max_mi: float, accept) -> tuple[dict | None, float | None]:
    """Closest station within max_mi that `accept` passes (e.g. downloaded and complete); ties break on station id."""
    ranked = sorted((haversine_mi(point["lat"], point["lon"], s["lat"], s["lon"]), s["id"], s) for s in stations)
    for miles, _, s in ranked:
        if miles > max_mi:
            break
        if accept(s):
            return s, round(miles, 2)
    return None, None
