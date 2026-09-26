"""Normalize recorded Overpass elements without inferring missing geographic facts."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any

from common import norm_name
from matches.core import haversine_mi

STATION_POWER_VALUES = {"plant", "substation", "switch"}
LANDMARKS = {
    "THURMOND": (33.6601, -82.1959),
    "MCINTOSH": (32.3521, -81.1751),
    "OKATIE": (32.3338, -81.0325),
}


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _coordinates(element: dict[str, Any]) -> tuple[float | None, float | None, str]:
    if element.get("type") == "node" and isinstance(element.get("lat"), (int, float)) and isinstance(
        element.get("lon"), (int, float)
    ):
        return element["lat"], element["lon"], "node_coordinates"
    center = element.get("center")
    if isinstance(center, dict) and isinstance(center.get("lat"), (int, float)) and isinstance(
        center.get("lon"), (int, float)
    ):
        # Overpass `out center` returns the center of a way/relation bounding box. F09 must
        # review it as evidence; it is not asserted to be a physical endpoint.
        return center["lat"], center["lon"], "overpass_bbox_center"
    return None, None, "unavailable"


def normalize_elements(payloads: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return one deterministic record per station-like OSM element plus transparent counts."""
    records: dict[str, dict[str, Any]] = {}
    duplicates = 0
    conflicting_duplicates = 0
    excluded_power_values: Counter[str] = Counter()
    for payload in payloads:
        cache_path = payload.get("_cache_path")
        for element in payload.get("elements", []):
            if not isinstance(element, dict):
                continue
            tags = element.get("tags")
            if not isinstance(tags, dict):
                continue
            power_value = tags.get("power")
            if power_value not in STATION_POWER_VALUES:
                if isinstance(power_value, str) and any(value in power_value for value in STATION_POWER_VALUES):
                    excluded_power_values[power_value] += 1
                continue
            element_type = element.get("type")
            element_id = element.get("id")
            if element_type not in {"node", "way", "relation"} or not isinstance(element_id, int):
                continue
            osm_id = f"{element_type}/{element_id}"
            name = _text(tags.get("name"))
            lat, lon, method = _coordinates(element)
            record: dict[str, Any] = {
                "coordinate_method": method,
                "lat": lat,
                "lon": lon,
                "name": name,
                "norm": norm_name(name or ""),
                "operator": _text(tags.get("operator")),
                "osm_id": osm_id,
                "osm_url": f"https://www.openstreetmap.org/{element_type}/{element_id}",
                "power": tags["power"],
                "tags": {str(key): value for key, value in sorted(tags.items()) if isinstance(value, str)},
                "voltage": _text(tags.get("voltage")),
            }
            if isinstance(cache_path, str):
                record["raw_cache_paths"] = [cache_path]
            county = _text(tags.get("addr:county")) or _text(tags.get("is_in:county"))
            if county:
                record["county"] = county
            previous = records.get(osm_id)
            if previous is not None:
                duplicates += 1
                previous_without_paths = {key: value for key, value in previous.items() if key != "raw_cache_paths"}
                record_without_paths = {key: value for key, value in record.items() if key != "raw_cache_paths"}
                if previous_without_paths != record_without_paths:
                    conflicting_duplicates += 1
                paths = set(previous.get("raw_cache_paths", []))
                paths.update(record.get("raw_cache_paths", []))
                if paths:
                    previous["raw_cache_paths"] = sorted(paths)
                continue
            records[osm_id] = record

    def sort_key(record: dict[str, Any]) -> tuple[str, int]:
        element_type, element_id = record["osm_id"].split("/", 1)
        return element_type, int(element_id)

    normalized = sorted(records.values(), key=sort_key)
    counts = {
        "conflicting_duplicates": conflicting_duplicates,
        "duplicate_elements": duplicates,
        "excluded_power_values": dict(sorted(excluded_power_values.items())),
        "missing_coordinates": sum(record["lat"] is None or record["lon"] is None for record in normalized),
        "missing_name": sum(record["name"] is None for record in normalized),
        "missing_operator": sum(record["operator"] is None for record in normalized),
        "normalized": len(normalized),
        "with_operator": sum(record["operator"] is not None for record in normalized),
    }
    return normalized, counts


def verify_landmarks(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Report the spec's three checks without assigning a name to an unnamed OSM feature."""
    located = [record for record in records if record["lat"] is not None and record["lon"] is not None]
    items = []
    for keyword, expected in LANDMARKS.items():
        named = [record for record in located if keyword in record["norm"]]
        nearest_named = min(
            named,
            key=lambda record: haversine_mi(expected[0], expected[1], record["lat"], record["lon"]),
            default=None,
        )
        nearest_any = min(
            located,
            key=lambda record: haversine_mi(expected[0], expected[1], record["lat"], record["lon"]),
            default=None,
        )
        named_distance = (
            haversine_mi(expected[0], expected[1], nearest_named["lat"], nearest_named["lon"])
            if nearest_named
            else None
        )
        item: dict[str, Any] = {
            "expected_lat": expected[0],
            "expected_lon": expected[1],
            "keyword": keyword,
            "nearest_named_distance_mi": named_distance,
            "nearest_named_osm_id": nearest_named["osm_id"] if nearest_named else None,
            "status": "matched" if named_distance is not None and named_distance < 1.0 else "missing_named_candidate",
        }
        if nearest_any:
            item["nearest_any"] = {
                "distance_mi": haversine_mi(expected[0], expected[1], nearest_any["lat"], nearest_any["lon"]),
                "name": nearest_any["name"],
                "osm_id": nearest_any["osm_id"],
                "power": nearest_any["power"],
            }
        items.append(item)
    matched = sum(item["status"] == "matched" for item in items)
    return {
        "expected": len(items),
        "items": items,
        "matched": matched,
        "status": "complete" if matched == len(items) else "partial",
    }
