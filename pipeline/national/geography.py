"""Normalize complete Census state/county reference geography without project inference."""

from __future__ import annotations

import csv
import io
import struct
import warnings
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from openpyxl import load_workbook

TERRITORY_FIPS = {"60", "66", "69", "72", "78"}


def _gazetteer(path: Path) -> list[dict[str, str]]:
    with ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.endswith(".txt")]
        if len(members) != 1:
            raise ValueError(f"{path.name}: expected one Gazetteer text member")
        text = archive.read(members[0]).decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text), delimiter="|"))


def _dbf(data: bytes, encoding: str = "utf-8") -> list[dict[str, str]]:
    count = struct.unpack_from("<I", data, 4)[0]
    header_len = struct.unpack_from("<H", data, 8)[0]
    record_len = struct.unpack_from("<H", data, 10)[0]
    fields: list[tuple[str, int]] = []
    position = 32
    while position + 32 <= header_len and data[position] != 0x0D:
        raw = data[position : position + 32]
        name = raw[:11].split(b"\0", 1)[0].decode("ascii")
        fields.append((name, raw[16]))
        position += 32
    rows = []
    for index in range(count):
        record = data[header_len + index * record_len : header_len + (index + 1) * record_len]
        if not record or record[:1] == b"*":
            continue
        offset = 1
        row = {}
        for name, length in fields:
            row[name] = record[offset : offset + length].decode(encoding, errors="replace").strip()
            offset += length
        rows.append(row)
    return rows


def _bounds(points: list[tuple[float, float]]) -> dict[str, float | bool] | None:
    if not points:
        return None
    longitudes = sorted(longitude % 360 for longitude, _ in points)
    if len(longitudes) == 1:
        start = end = longitudes[0]
    else:
        gaps = [(longitudes[i + 1] - longitudes[i], i) for i in range(len(longitudes) - 1)]
        gaps.append((longitudes[0] + 360 - longitudes[-1], len(longitudes) - 1))
        _, index = max(gaps)
        start, end = longitudes[(index + 1) % len(longitudes)], longitudes[index]
        if end < start:
            end += 360
    west = start if start < 180 else start - 360
    east_mod = end % 360
    east = east_mod if east_mod < 180 else east_mod - 360
    return {
        "west": round(west, 7),
        "south": round(min(latitude for _, latitude in points), 7),
        "east": round(east, 7),
        "north": round(max(latitude for _, latitude in points), 7),
        "crosses_antimeridian": end > 180 and west >= 0,
        "fit_west": round(west, 7),
        "fit_east_unwrapped": round(west + (end - start), 7),
    }


def _shapes(path: Path) -> list[dict[str, Any]]:
    with ZipFile(path) as archive:
        shp_names = [name for name in archive.namelist() if name.endswith(".shp")]
        dbf_names = [name for name in archive.namelist() if name.endswith(".dbf")]
        if len(shp_names) != 1 or len(dbf_names) != 1:
            raise ValueError(f"{path.name}: expected one SHP and one DBF")
        cpg = next((archive.read(name).decode("ascii", errors="ignore").strip() for name in archive.namelist()
                    if name.endswith(".cpg")), "UTF-8")
        rows = _dbf(archive.read(dbf_names[0]), "utf-8" if "UTF" in cpg.upper() else "latin1")
        data = archive.read(shp_names[0])
    shapes = []
    position = 100
    while position + 8 <= len(data):
        _, words = struct.unpack_from(">2i", data, position)
        position += 8
        content = data[position : position + words * 2]
        position += words * 2
        shape_type = struct.unpack_from("<i", content, 0)[0]
        points: list[tuple[float, float]] = []
        if shape_type in (5, 15, 25):
            parts, point_count = struct.unpack_from("<2i", content, 36)
            point_offset = 44 + 4 * parts
            points = [struct.unpack_from("<2d", content, point_offset + 16 * i) for i in range(point_count)]
        elif shape_type == 1:
            points = [struct.unpack_from("<2d", content, 4)]
        shapes.append(_bounds(points))
    if len(rows) != len(shapes):
        raise ValueError(f"{path.name}: DBF/SHP record counts differ")
    return [{**row, "_bounds": bounds} for row, bounds in zip(rows, shapes, strict=True)]


def build_geography(cache: Path, manifest: list[dict[str, Any]]) -> dict[str, Any]:
    gazetteer_2025_states = _gazetteer(cache / "2025_Gaz_state_national.zip")
    gazetteer_2026_states = _gazetteer(cache / "2026_Gaz_state_national.zip")
    gazetteer_2025_counties = _gazetteer(cache / "2025_Gaz_counties_national.zip")
    gazetteer_2026_counties = _gazetteer(cache / "2026_Gaz_counties_national.zip")
    identities = {
        "2025_vs_2026_states_added": sorted({(r["GEOID"], r["NAME"]) for r in gazetteer_2026_states}
                                               - {(r["GEOID"], r["NAME"]) for r in gazetteer_2025_states}),
        "2025_vs_2026_states_removed": sorted({(r["GEOID"], r["NAME"]) for r in gazetteer_2025_states}
                                                 - {(r["GEOID"], r["NAME"]) for r in gazetteer_2026_states}),
        "2025_vs_2026_counties_added": sorted({(r["GEOID"], r["NAME"]) for r in gazetteer_2026_counties}
                                                 - {(r["GEOID"], r["NAME"]) for r in gazetteer_2025_counties}),
        "2025_vs_2026_counties_removed": sorted({(r["GEOID"], r["NAME"]) for r in gazetteer_2025_counties}
                                                   - {(r["GEOID"], r["NAME"]) for r in gazetteer_2026_counties}),
    }
    if any(identities.values()):
        raise ValueError(f"Census 2025/2026 identities changed: {identities}")

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Cannot parse header or footer.*", category=UserWarning)
        workbook = load_workbook(cache / "state-geocodes-v2025.xlsx", read_only=True, data_only=True)
        code_rows = list(workbook.active.iter_rows(min_row=6, values_only=True))
        workbook.close()
    region_names = {str(region): name.removesuffix(" Region") for region, division, state, name in code_rows
                    if str(state) == "00" and str(division) == "0"}
    division_names = {str(division): name.removesuffix(" Division") for region, division, state, name in code_rows
                      if str(state) == "00" and str(division) != "0"}
    state_regions = {str(state).zfill(2): (str(region), str(division))
                     for region, division, state, name in code_rows if str(state) != "00"}

    gazetteer_states = {row["GEOID"]: row for row in gazetteer_2026_states}
    state_rows = _shapes(cache / "cb_2025_us_state_500k.zip")
    states = []
    for raw in state_rows:
        state_fips = raw["STATEFP"]
        scope = "territory" if state_fips in TERRITORY_FIPS else ("district" if state_fips == "11" else "state")
        region, division = state_regions.get(state_fips, (None, None))
        gazetteer = gazetteer_states.get(state_fips)
        states.append({
            "state_fips": state_fips,
            "usps": raw["STUSPS"],
            "name": raw["NAME"],
            "scope": scope,
            "selectable_primary": scope != "territory",
            "census_region_code": region,
            "census_region_name": region_names.get(region),
            "census_division_code": division,
            "census_division_name": division_names.get(division),
            "representative_point": ([float(gazetteer["INTPTLONG"]), float(gazetteer["INTPTLAT"])]
                                     if gazetteer else None),
            "bounds": raw["_bounds"],
            "geometry": {"vintage": "2025", "layer": "state", "geoid": raw["GEOID"]},
        })

    by_state = {state["state_fips"]: state for state in states}
    gazetteer_counties = {row["GEOID"]: row for row in gazetteer_2026_counties}
    counties = []
    for raw in _shapes(cache / "cb_2025_us_county_500k.zip"):
        geoid, state_fips = raw["GEOID"], raw["STATEFP"]
        state, gazetteer = by_state[state_fips], gazetteer_counties.get(geoid)
        counties.append({
            "county_geoid": geoid,
            "state_fips": state_fips,
            "county_fips": raw["COUNTYFP"],
            "name": raw["NAME"],
            "full_name": raw.get("NAMELSAD") or raw["NAME"],
            "state_usps": state["usps"],
            "state_name": state["name"],
            "scope": state["scope"],
            "selectable_primary": state["scope"] != "territory",
            "representative_point": ([float(gazetteer["INTPTLONG"]), float(gazetteer["INTPTLAT"])]
                                     if gazetteer else None),
            "bounds": raw["_bounds"],
            "geometry": {"vintage": "2025", "layer": "county", "geoid": geoid},
        })

    regions = [{"region_code": row["REGIONCE"], "name": row["NAME"], "bounds": row["_bounds"]}
               for row in _shapes(cache / "cb_2025_us_region_5m.zip")]
    divisions = [{"division_code": row["DIVISIONCE"], "name": row["NAME"], "bounds": row["_bounds"]}
                 for row in _shapes(cache / "cb_2025_us_division_5m.zip")]
    counts = {
        "regions": len(regions),
        "divisions": len(divisions),
        "states_and_dc": sum(state["selectable_primary"] for state in states),
        "states_only": sum(state["scope"] == "state" for state in states),
        "districts": sum(state["scope"] == "district" for state in states),
        "territories": sum(state["scope"] == "territory" for state in states),
        "counties_primary": sum(county["selectable_primary"] for county in counties),
        "territory_county_equivalents": sum(not county["selectable_primary"] for county in counties),
        "counties_total": len(counties),
        "gazetteer_2026_counties": len(gazetteer_2026_counties),
    }
    return {
        "schema_version": "national-geography-v1",
        "authority": "U.S. Census Bureau",
        "provenance": {
            "sources": [entry for entry in manifest if entry["id"].startswith("census-")],
            "identity_check": identities,
            "notes": [
                "2026 Gazetteer supplies names and representative points where available.",
                "2025 cartographic boundaries supply reference map-fit bounds; they are not project geometry.",
                "Census region/division membership comes from the 2025 Population Estimates FIPS workbook.",
                "Territories remain separate and have null Census region/division codes.",
            ],
        },
        "counts": counts,
        "regions": sorted(regions, key=lambda row: row["region_code"]),
        "divisions": sorted(divisions, key=lambda row: row["division_code"]),
        "states": sorted(states, key=lambda row: row["state_fips"]),
        "counties": sorted(counties, key=lambda row: row["county_geoid"]),
    }
