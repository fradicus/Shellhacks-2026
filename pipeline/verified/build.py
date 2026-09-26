from __future__ import annotations

import hashlib
import io
import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import openpyxl

from .fetch import ARCHIVE_SHA256, ARCHIVE_URL, checked_archive, sha256_bytes
from .geography import GeographyIndex
from .validate import validate_snapshot

SCHEMA_VERSION = "verified-directory-v1"
SOURCE_EIA = "eia-861-2024-final"
SOURCE_CENSUS = "census-geography-reference"
MEMBER_HASHES = {
    "Frame_2024.xlsx": "220c6e9080e084271303b3ebdca147cf46e74cea4019f155fa35d4d5a260f14a",
    "Utility_Data_2024.xlsx": "6eab71294e7738c712d103b7a4d19764bc8b27822a358e5a9c8736f52a7cbcb1",
    "Service_Territory_2024.xlsx": "0292f880da42e06b443704af4ce373c73923322371b5346e46cfd22573c7eae7",
}
EIA_RETRIEVED_AT = "2026-09-26T18:00:22.262176+00:00"


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        return value.strip()
    return value


def _utility_id(value: Any) -> str:
    cleaned = _clean(value)
    if isinstance(cleaned, int):
        return str(cleaned)
    if isinstance(cleaned, str) and cleaned.isdigit():
        return str(int(cleaned))
    raise ValueError(f"invalid EIA utility number: {value!r}")


def _rows(member: bytes, sheet: str, start: int) -> Iterable[tuple[int, tuple[Any, ...]]]:
    workbook = openpyxl.load_workbook(io.BytesIO(member), read_only=True, data_only=True)
    try:
        worksheet = workbook[sheet]
        for row_number, row in enumerate(worksheet.iter_rows(min_row=start, values_only=True), start):
            if any(value is not None for value in row):
                yield row_number, tuple(_clean(value) for value in row)
    finally:
        workbook.close()


def _evidence(member: str, sheet: str, row: int, raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": SOURCE_EIA,
        "source_sha256": ARCHIVE_SHA256,
        "member": member,
        "member_sha256": MEMBER_HASHES[member],
        "sheet": sheet,
        "row": row,
        "raw": raw,
    }


def _source_records(geography: dict[str, Any], geography_sha: str) -> list[dict[str, Any]]:
    census_sources = geography.get("provenance", {}).get("sources", [])
    return [
        {
            "id": SOURCE_CENSUS,
            "publisher": "U.S. Census Bureau",
            "title": "Census geography identities used by the national reference index",
            "vintage": "2025 boundaries / 2026 Gazetteer identities",
            "retrieved_at": min((item.get("retrieved_at") for item in census_sources if item.get("retrieved_at")), default=None),
            "landing_url": "https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html",
            "content_sha256": geography_sha,
            "upstream_lineage": "census-geography-reference",
            "role": "geography_identity_reference",
            "limitations": [
                "Census validates state, county-equivalent identity and parentage only.",
                "It does not independently corroborate an EIA utility service-territory claim.",
            ],
        },
        {
            "id": SOURCE_EIA,
            "publisher": "U.S. Energy Information Administration",
            "title": "Form EIA-861 2024 final data",
            "vintage": "2024 final",
            "retrieved_at": EIA_RETRIEVED_AT,
            "landing_url": "https://www.eia.gov/electricity/data/eia861/",
            "download_url": ARCHIVE_URL,
            "content_sha256": ARCHIVE_SHA256,
            "member_sha256": MEMBER_HASHES,
            "upstream_lineage": "eia-861-2024-final",
            "role": "utility_directory_and_distribution_equipment_counties",
            "limitations": [
                "County rows report distribution-equipment presence, not exclusive service polygons.",
                "They are not transmission project locations.",
            ],
        },
    ]


def _frame_utilities(member: bytes) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row_number, row in _rows(member, "Frame", 2):
        utility_id = _utility_id(row[1])
        records.append(
            {
                "id": f"eia861-2024-utility-{utility_id}",
                "eia_utility_id": utility_id,
                "data_year": 2024,
                "name": str(row[2]),
                "short_form": row[3] or None,
                "ownership_code": row[4] or None,
                "ownership": row[5] or None,
                "filing_flags": {
                    "monthly": row[6] or None,
                    "service_territory": row[19] or None,
                    "utility_data": row[20] or None,
                },
                "state_fips": [],
                "county_geoids": [],
                "source_ids": [SOURCE_EIA],
                "validation_status": "accepted",
                "limitations": [],
                "evidence": _evidence(
                    "Frame_2024.xlsx",
                    "Frame",
                    row_number,
                    {
                        "Data Year": row[0],
                        "Utility Number": row[1],
                        "Utility Name": row[2],
                        "Short Form": row[3],
                        "Ownership": row[5],
                    },
                ),
            }
        )
    return records


def _activities(member: bytes, geography: GeographyIndex, known: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    quarantine: list[dict[str, Any]] = []
    for sheet in ("States", "Territories"):
        for row_number, row in _rows(member, sheet, 3):
            utility_id = _utility_id(row[1])
            state_raw = str(row[3] or "")
            state_fips = geography.state_fips(state_raw)
            limitations: list[str] = []
            status = "accepted"
            if utility_id not in known:
                status = "rejected"
                limitations.append("utility number is absent from the reviewed Frame workbook")
            if state_fips is None:
                limitations.append("state or foreign area has no Census state FIPS identity in the reference index")
            record_id = f"eia861-2024-activity-{sheet.casefold()}-{row_number}"
            record = {
                "id": record_id,
                "eia_utility_id": utility_id,
                "data_year": 2024,
                "name": str(row[2]),
                "state_raw": state_raw or None,
                "state_fips": state_fips,
                "ownership": row[4] or None,
                "nerc_region": row[5] or None,
                "nerc_flags": {
                    name: row[index] or None
                    for index, name in enumerate(("TRE", "FRCC", "MRO", "NPCC", "RFC", "SERC", "SPP", "WECC"), 6)
                },
                "rto_flags": {
                    name: row[index] or None
                    for index, name in enumerate(("CAISO", "ERCOT", "PJM", "NYISO", "SPP", "MISO", "ISONE", "Other"), 14)
                },
                "activities": {
                    name: row[index] or None
                    for index, name in enumerate(
                        (
                            "generation",
                            "transmission",
                            "buying_transmission",
                            "distribution",
                            "buying_distribution",
                            "wholesale_marketing",
                            "retail_marketing",
                            "bundled",
                            "alt_fuel_vehicle",
                            "alt_fuel_vehicle_2",
                        ),
                        22,
                    )
                },
                "validation_status": status,
                "limitations": limitations,
                "evidence": _evidence(
                    "Utility_Data_2024.xlsx",
                    sheet,
                    row_number,
                    {"Data Year": row[0], "Utility Number": row[1], "Utility Name": row[2], "State": row[3]},
                ),
            }
            records.append(record)
            if status == "rejected":
                quarantine.append(
                    {
                        "id": f"quarantine-{record_id}",
                        "record_type": "utility_activity",
                        "record_id": record_id,
                        "reason": "unknown_utility_number",
                        "evidence": record["evidence"],
                    }
                )
    return records, quarantine


def _territories(
    member: bytes, geography: GeographyIndex, known: set[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    territories: list[dict[str, Any]] = []
    assertions: list[dict[str, Any]] = []
    quarantine: list[dict[str, Any]] = []
    for sheet in ("Counties_States", "Counties_Territories"):
        for row_number, row in _rows(member, sheet, 2):
            utility_id = _utility_id(row[1])
            state_raw, county_raw = str(row[4] or ""), str(row[5] or "")
            state_fips = geography.state_fips(state_raw)
            match = geography.match_county(state_raw, county_raw) if state_fips else None
            status = match.status if match else "unresolved"
            if utility_id not in known:
                status = "rejected"
            record_id = f"eia861-2024-territory-{sheet.casefold()}-{row_number}"
            limitations = [
                "EIA reports distribution-equipment presence; this is not an exclusive service polygon.",
                "This row is not a transmission project location.",
            ]
            if status != "accepted":
                limitations.append("county identity did not resolve uniquely against the Census reference")
            evidence = _evidence(
                "Service_Territory_2024.xlsx",
                sheet,
                row_number,
                {"Data Year": row[0], "Utility Number": row[1], "Utility Name": row[2], "State": row[4], "County": row[5]},
            )
            record = {
                "id": record_id,
                "eia_utility_id": utility_id,
                "data_year": 2024,
                "name": str(row[2]),
                "short_form": row[3] or None,
                "state_raw": state_raw or None,
                "county_raw": county_raw or None,
                "state_fips": state_fips,
                "county_geoid": match.county_geoid if match else None,
                "candidate_geoids": list(match.candidates) if match else [],
                "identity_match_method": match.method if match else None,
                "validation_status": status,
                "exclusive": False,
                "project_location": False,
                "source_ids": [SOURCE_EIA, SOURCE_CENSUS],
                "limitations": limitations,
                "evidence": evidence,
            }
            territories.append(record)
            assertion = {
                "id": f"assertion-{record_id}",
                "subject": {"eia_utility_id": utility_id, "data_year": 2024},
                "predicate": "distribution_equipment_present_in_county",
                "object": {"county_geoid": record["county_geoid"], "state_fips": state_fips, "county_raw": county_raw},
                "claim_source_id": SOURCE_EIA,
                "identity_reference_source_id": SOURCE_CENSUS,
                "upstream_lineages": ["eia-861-2024-final"],
                "independent_lineage_count": 1,
                "independently_corroborated": False,
                "validation_status": status,
                "limitations": ["Census identity validation is not independent corroboration of the service claim."],
                "evidence": evidence,
            }
            assertions.append(assertion)
            if status != "accepted":
                reason = "ambiguous_county_identity" if status == "conflicting" else "unresolved_county_identity"
                if utility_id not in known:
                    reason = "unknown_utility_number"
                quarantine.append(
                    {
                        "id": f"quarantine-{record_id}",
                        "record_type": "service_territory",
                        "record_id": record_id,
                        "reason": reason,
                        "candidate_geoids": record["candidate_geoids"],
                        "evidence": evidence,
                    }
                )
    return territories, assertions, quarantine


def _decorate_utilities(
    utilities: list[dict[str, Any]], activities: list[dict[str, Any]], territories: list[dict[str, Any]]
) -> None:
    states: dict[str, set[str]] = defaultdict(set)
    counties: dict[str, set[str]] = defaultdict(set)
    unresolved: Counter[str] = Counter()
    for record in activities:
        if record["validation_status"] == "accepted" and record["state_fips"]:
            states[record["eia_utility_id"]].add(record["state_fips"])
    for record in territories:
        utility_id = record["eia_utility_id"]
        if record["validation_status"] == "accepted" and record["county_geoid"]:
            states[utility_id].add(record["state_fips"])
            counties[utility_id].add(record["county_geoid"])
        else:
            unresolved[utility_id] += 1
    for utility in utilities:
        utility_id = utility["eia_utility_id"]
        utility["state_fips"] = sorted(states[utility_id])
        utility["county_geoids"] = sorted(counties[utility_id])
        if utility["county_geoids"]:
            utility["source_ids"] = [SOURCE_EIA, SOURCE_CENSUS]
            utility["limitations"].append(
                "County membership means reported distribution-equipment presence, not an exclusive polygon."
            )
        if unresolved[utility_id]:
            utility["validation_status"] = "needs_review"
            utility["limitations"].append(
                f"{unresolved[utility_id]} service-territory row(s) have unresolved or conflicting county identity."
            )
        if not utility["state_fips"] and not utility["county_geoids"]:
            utility["limitations"].append("No Census-resolved state or county service identity was published for this utility.")


def _coverage(
    sources: list[dict[str, Any]],
    utilities: list[dict[str, Any]],
    activities: list[dict[str, Any]],
    territories: list[dict[str, Any]],
    assertions: list[dict[str, Any]],
    quarantine: list[dict[str, Any]],
) -> dict[str, Any]:
    territory_status = Counter(record["validation_status"] for record in territories)
    utility_status = Counter(record["validation_status"] for record in utilities)
    return {
        "schema_version": SCHEMA_VERSION,
        "data_year": 2024,
        "source_vintages": {record["id"]: record["vintage"] for record in sources},
        "counts": {
            "sources": len(sources),
            "utilities": len(utilities),
            "utility_activities": len(activities),
            "service_territory_rows": len(territories),
            "assertions": len(assertions),
            "quarantine": len(quarantine),
            "utilities_by_validation_status": dict(sorted(utility_status.items())),
            "service_territory_by_validation_status": dict(sorted(territory_status.items())),
            "resolved_county_rows": territory_status["accepted"],
            "unresolved_county_rows": territory_status["unresolved"],
            "conflicting_county_rows": territory_status["conflicting"],
            "rejected_county_rows": territory_status["rejected"],
            "independently_corroborated_service_claims": 0,
        },
        "limitations": [
            "Coverage measures rows in the reviewed EIA-861 2024 final archive, "
            "not every operating utility or exclusive territory.",
            "Census validates geographic identity and parentage only; it does not corroborate EIA service membership.",
            "Unresolved, conflicting and rejected rows are preserved in quarantine and excluded from utility county filters.",
        ],
    }


def build_snapshot(repo_root: Path, *, generated_at: str, cache_dir: Path | None = None, refresh: bool = False) -> dict[str, Any]:
    data_dir = repo_root / "data" / "verified"
    cache = cache_dir or data_dir / "cache"
    archive_path = cache / "f8612024.zip"
    _, members = checked_archive(archive_path, refresh=refresh)
    for name, expected in MEMBER_HASHES.items():
        if sha256_bytes(members[name]) != expected:
            raise ValueError(f"reviewed member hash changed: {name}")
    geography_path = repo_root / "data" / "national" / "geography.json"
    geography_bytes = geography_path.read_bytes()
    geography = json.loads(geography_bytes)
    index = GeographyIndex(geography)
    utilities = _frame_utilities(members["Frame_2024.xlsx"])
    known = {record["eia_utility_id"] for record in utilities}
    activities, activity_quarantine = _activities(members["Utility_Data_2024.xlsx"], index, known)
    territories, assertions, territory_quarantine = _territories(members["Service_Territory_2024.xlsx"], index, known)
    _decorate_utilities(utilities, activities, territories)
    sources = _source_records(geography, sha256_bytes(geography_bytes))
    quarantine = sorted(activity_quarantine + territory_quarantine, key=lambda item: item["id"])
    utilities.sort(key=lambda item: item["id"])
    activities.sort(key=lambda item: item["id"])
    territories.sort(key=lambda item: item["id"])
    assertions.sort(key=lambda item: item["id"])
    sources.sort(key=lambda item: item["id"])
    coverage = _coverage(sources, utilities, activities, territories, assertions, quarantine)
    content = {
        "sources": sources,
        "utilities": utilities,
        "utility-activities": activities,
        "service-territory": territories,
        "assertions": assertions,
        "quarantine": quarantine,
        "coverage": coverage,
    }
    dataset = hashlib.sha256(canonical(content)).hexdigest()
    snapshot = {"schema_version": SCHEMA_VERSION, "dataset": dataset, "generated_at": generated_at, **content}
    validate_snapshot(snapshot, geography)
    return snapshot


def write_snapshot(snapshot: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_files: dict[str, dict[str, Any]] = {}
    for name in ("sources", "utilities", "utility-activities", "service-territory", "assertions", "quarantine"):
        envelope = {
            "schema_version": snapshot["schema_version"],
            "dataset": snapshot["dataset"],
            "generated_at": snapshot["generated_at"],
            "records": snapshot[name],
        }
        payload = canonical(envelope)
        filename = f"{name}.json"
        (output_dir / filename).write_bytes(payload)
        manifest_files[filename] = {"sha256": sha256_bytes(payload), "records": len(snapshot[name])}
    coverage = {
        **snapshot["coverage"],
        "dataset": snapshot["dataset"],
        "generated_at": snapshot["generated_at"],
    }
    coverage_bytes = canonical(coverage)
    (output_dir / "coverage.json").write_bytes(coverage_bytes)
    manifest_files["coverage.json"] = {"sha256": sha256_bytes(coverage_bytes), "records": None}
    manifest = {
        "schema_version": snapshot["schema_version"],
        "dataset": snapshot["dataset"],
        "generated_at": snapshot["generated_at"],
        "content_hash_excludes": ["generated_at", "dataset", "manifest"],
        "files": manifest_files,
    }
    (output_dir / "manifest.json").write_bytes(canonical(manifest))
