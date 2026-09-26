"""Small, cached Census boundary source used for state and border evidence."""

from __future__ import annotations

import hashlib
import json
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from common.io import load_json, write_json

LAYER_URL = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/4"
QUERY_PARAMS = [
    ("where", "STATE IN ('13','45')"),
    ("outFields", "STATE,GEOID,STUSAB,BASENAME"),
    ("returnGeometry", "true"),
    ("outSR", "4326"),
    ("f", "geojson"),
]
QUERY_URL = f"{LAYER_URL}/query?{urllib.parse.urlencode(QUERY_PARAMS)}"
METADATA_URL = f"{LAYER_URL}?f=pjson"
EXPECTED_VINTAGE = "January 1, 2026"
STATE_CODES = {"13": "GA", "45": "SC"}


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _read_verified(path: Path, expected_sha256: str) -> bytes:
    content = path.read_bytes()
    actual = sha256_bytes(content)
    if actual != expected_sha256:
        raise ValueError(f"cached Census bytes changed for {path}: expected {expected_sha256}, got {actual}")
    return content


def _get(url: str, timeout: float = 60.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "GridBridge/1.0 public-data-cache"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed public Census URL
        if response.status != 200:
            raise RuntimeError(f"Census request returned HTTP {response.status}")
        return response.read()


def ensure_boundary_cache(cache_dir: Path, *, live: bool = False) -> dict[str, Any]:
    """Load a bound cache or make the two authorized Census requests when absent."""
    manifest_path = cache_dir / "manifest.json"
    geojson_path = cache_dir / "raw" / "ga-sc-states-2026.geojson"
    metadata_path = cache_dir / "raw" / "states-layer-4.pjson"
    if manifest_path.exists():
        manifest = load_json(manifest_path)
        if manifest.get("query_url") != QUERY_URL or manifest.get("metadata_url") != METADATA_URL:
            raise ValueError("cached Census manifest is bound to a different query")
        geometry = _read_verified(geojson_path, manifest["raw_geojson_sha256"])
        metadata = _read_verified(metadata_path, manifest["raw_metadata_sha256"])
        _validate_payloads(json.loads(geometry), json.loads(metadata))
        return manifest
    if not live:
        raise FileNotFoundError("Census boundary cache is missing; pass --live-boundaries once to create it")

    geometry = _get(QUERY_URL)
    metadata = _get(METADATA_URL)
    geojson = json.loads(geometry)
    layer = json.loads(metadata)
    _validate_payloads(geojson, layer)
    cache_dir.joinpath("raw").mkdir(parents=True, exist_ok=True)
    geojson_path.write_bytes(geometry)
    metadata_path.write_bytes(metadata)
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    manifest = {
        "cache_version": "census-state-boundary-v1",
        "copyright": layer.get("copyrightText"),
        "feature_count": len(geojson["features"]),
        "layer_description": layer["description"],
        "metadata_url": METADATA_URL,
        "query_parameters": dict(QUERY_PARAMS),
        "query_url": QUERY_URL,
        "raw_geojson_path": "raw/ga-sc-states-2026.geojson",
        "raw_geojson_sha256": sha256_bytes(geometry),
        "raw_metadata_path": "raw/states-layer-4.pjson",
        "raw_metadata_sha256": sha256_bytes(metadata),
        "retrieved_at": now,
        "source": "U.S. Census Bureau TIGERweb",
        "source_vintage": EXPECTED_VINTAGE,
        "states": ["GA", "SC"],
    }
    write_json(manifest_path, manifest)
    return manifest


def _validate_payloads(geojson: dict[str, Any], layer: dict[str, Any]) -> None:
    if layer.get("type") != "Feature Layer" or layer.get("geometryType") != "esriGeometryPolygon":
        raise ValueError("unexpected Census layer metadata")
    if EXPECTED_VINTAGE not in str(layer.get("description", "")):
        raise ValueError("Census layer vintage changed; review before using new boundaries")
    if geojson.get("type") != "FeatureCollection" or not isinstance(geojson.get("features"), list):
        raise ValueError("unexpected Census GeoJSON response")
    states = {
        str(feature.get("properties", {}).get("STATE"))
        for feature in geojson["features"]
        if isinstance(feature, dict)
    }
    if states != set(STATE_CODES):
        raise ValueError(f"expected only Georgia and South Carolina boundaries, got {sorted(states)}")


def _polygons(geometry: dict[str, Any]) -> list[list[list[list[float]]]]:
    coordinates = geometry.get("coordinates")
    if geometry.get("type") == "Polygon":
        return [coordinates]
    if geometry.get("type") == "MultiPolygon":
        return coordinates
    raise ValueError(f"unsupported Census geometry type: {geometry.get('type')}")


def _point_on_segment(lon: float, lat: float, a: list[float], b: list[float]) -> bool:
    ax, ay = a[:2]
    bx, by = b[:2]
    cross = (lon - ax) * (by - ay) - (lat - ay) * (bx - ax)
    if abs(cross) > 1e-10:
        return False
    return min(ax, bx) - 1e-10 <= lon <= max(ax, bx) + 1e-10 and min(ay, by) - 1e-10 <= lat <= max(
        ay, by
    ) + 1e-10


def _in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    inside = False
    previous = ring[-1]
    for point in ring:
        if _point_on_segment(lon, lat, previous, point):
            return True
        x1, y1 = previous[:2]
        x2, y2 = point[:2]
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
        previous = point
    return inside


def _in_geometry(lon: float, lat: float, geometry: dict[str, Any]) -> bool:
    for polygon in _polygons(geometry):
        if _in_ring(lon, lat, polygon[0]) and not any(_in_ring(lon, lat, hole) for hole in polygon[1:]):
            return True
    return False


def _segment_distance_miles(lon: float, lat: float, a: list[float], b: list[float]) -> float:
    """Local equirectangular point-to-segment distance; retain full precision for the 10 mi rule."""
    lon_scale = 69.172 * math.cos(math.radians(lat))
    lat_scale = 69.0
    ax, ay = (a[0] - lon) * lon_scale, (a[1] - lat) * lat_scale
    bx, by = (b[0] - lon) * lon_scale, (b[1] - lat) * lat_scale
    dx, dy = bx - ax, by - ay
    denominator = dx * dx + dy * dy
    fraction = 0.0 if denominator == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / denominator))
    return math.hypot(ax + fraction * dx, ay + fraction * dy)


@dataclass(frozen=True)
class StateBoundaries:
    geometries: dict[str, dict[str, Any]]
    manifest: dict[str, Any]

    @classmethod
    def load(cls, cache_dir: Path, *, live: bool = False) -> StateBoundaries:
        manifest = ensure_boundary_cache(cache_dir, live=live)
        raw_path = cache_dir / manifest["raw_geojson_path"]
        payload = json.loads(_read_verified(raw_path, manifest["raw_geojson_sha256"]))
        geometries = {
            STATE_CODES[str(feature["properties"]["STATE"])]: feature["geometry"] for feature in payload["features"]
        }
        return cls(geometries=geometries, manifest=manifest)

    def state_for(self, lon: float, lat: float) -> str | None:
        for state in ("GA", "SC"):
            if _in_geometry(lon, lat, self.geometries[state]):
                return state
        return None

    def distance_to_state_miles(self, lon: float, lat: float, state: str) -> float:
        return min(
            _segment_distance_miles(lon, lat, start, end)
            for polygon in _polygons(self.geometries[state])
            for ring in polygon
            for start, end in zip(ring, ring[1:], strict=False)
        )
