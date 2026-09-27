"""OSRM driving-route client (route service, OpenStreetMap road network). Standard library only.

OSRM snaps each end to the nearest drivable road and returns the fastest route between the snapped points; the
snap distances are kept so a far-off-road center stays visible instead of silently shortening the drive.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

DEFAULT_BASE = "https://router.project-osrm.org"
PROFILE = "driving"
TRAVEL_MODE = "DRIVE"
ROUTING_PREFERENCE = "FASTEST"
DATA_SOURCE = "OpenStreetMap contributors (ODbL)"
USER_AGENT = "GridBridge-routes/1.0 (local research)"
METERS_PER_MILE = 1609.344
MAX_ATTEMPTS = 3
NO_ROUTE_CODES = ("NoRoute", "NoSegment")


class RoutesError(RuntimeError):
    pass


def base_url() -> str:
    return (os.environ.get("OSRM_URL") or DEFAULT_BASE).rstrip("/")


def request_url(origin: dict[str, float], destination: dict[str, float], base: str) -> str:
    coords = f"{origin['lon']:.7f},{origin['lat']:.7f};{destination['lon']:.7f},{destination['lat']:.7f}"
    return f"{base}/route/v1/{PROFILE}/{coords}?overview=full&geometries=polyline&alternatives=false&steps=false"


def _point(lon_lat: list[float] | None) -> dict[str, float] | None:
    if not lon_lat or len(lon_lat) != 2:
        return None
    return {"lat": float(lon_lat[1]), "lon": float(lon_lat[0])}


def parse_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Route fields from an OSRM route response. NoRoute/NoSegment mean no drivable route between the two points."""
    code = payload.get("code")
    routes = payload.get("routes") or []
    if code in NO_ROUTE_CODES or (code == "Ok" and not routes):
        return {"status": "no_route", "distance_m": None, "drive_mi": None, "duration_s": None,
                "polyline": None, "start": None, "end": None, "snap_m": None}
    if code != "Ok":
        raise RoutesError(f"OSRM code {code!r}: {payload.get('message', '')}")
    route = routes[0]
    if "distance" not in route:
        raise RoutesError("route without distance")
    waypoints = payload.get("waypoints") or [{}, {}]
    distance_m = float(route["distance"])
    duration = route.get("duration")
    return {
        "status": "ok",
        "distance_m": round(distance_m, 1),
        "drive_mi": distance_m / METERS_PER_MILE,
        "duration_s": round(duration) if isinstance(duration, (int, float)) else None,
        "polyline": route.get("geometry"),
        "start": _point(waypoints[0].get("location")),
        "end": _point(waypoints[-1].get("location")),
        "snap_m": [round(float(w.get("distance", 0.0)), 1) for w in (waypoints[0], waypoints[-1])],
    }


def compute_route(origin: dict[str, float], destination: dict[str, float], *, base: str | None = None,
                  timeout: float = 30.0, opener=urllib.request.urlopen) -> dict[str, Any]:
    """One driving route between two points. Retries transient failures; raises RoutesError on anything else."""
    base = base or base_url()
    url = request_url(origin, destination, base)
    last = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with opener(req, timeout=timeout) as resp:
                parsed = parse_response(json.loads(resp.read().decode()))
            break
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            try:
                payload = json.loads(body)
            except ValueError:
                payload = {}
            if payload.get("code") in NO_ROUTE_CODES:
                parsed = parse_response(payload)
                break
            last = RoutesError(f"HTTP {exc.code}: {body[:300]}")
            if exc.code not in (429, 500, 502, 503, 504):
                raise last from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            last = RoutesError(f"network error: {exc}")
        if attempt < MAX_ATTEMPTS:
            time.sleep(2**attempt)
    else:
        raise last  # type: ignore[misc]
    return {
        **parsed,
        "provider": f"osrm:{base.split('://', 1)[-1]}",
        "travel_mode": TRAVEL_MODE,
        "routing_preference": ROUTING_PREFERENCE,
        "data_source": DATA_SOURCE,
        "computed_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
