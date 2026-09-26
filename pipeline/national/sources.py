"""Build the reviewed source registry without inferring geographic coverage."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from common import load_json

ISO_SOURCE_ID = "iso-ne-rsp-2026-06"


def _legacy(root: Path, counts: dict[str, int]) -> list[dict[str, Any]]:
    records = load_json(root / "data" / "sources" / "sources.json")
    out = []
    for source in records:
        source_id = source["_id"]
        if source_id not in counts:
            continue
        banner = source["public_status"] == "public_with_banner"
        url = source.get("url")
        out.append({
            "_id": source_id,
            "title": source["title"],
            "publisher": source["publisher"],
            "authority": "utility" if source_id != "sample" else "sponsor_supplied",
            "role": "project_plan",
            "landing_url": url,
            "local_reference": source.get("local_path") if not url else None,
            "access_policy": "metadata_only" if banner else "public_document",
            "download_url": url,
            "publication_date": None,
            "vintage": source.get("filing"),
            "retrieved_at": source.get("source_metadata_checked_at"),
            "sha256": source["sha256"],
            "public_status": "public_with_banner" if banner else "verified_public",
            "import_status": "imported",
            "planning_region": None,
            "states": [],
            "project_count": counts[source_id],
            "notes": [source["restrictions"]] if source.get("restrictions") else [],
        })
    return out


def _iso(reference: dict[str, Any], project_count: int) -> dict[str, Any]:
    source = reference["iso_ne"]
    return {
        "_id": ISO_SOURCE_ID,
        "title": "June 2026 ISO-NE RSP Project List Update",
        "publisher": source["publisher"],
        "authority": "regional_planning_organization",
        "role": "project_plan",
        "landing_url": source["landing_url"],
        "local_reference": None,
        "access_policy": "public_document",
        "download_url": source["url"],
        "publication_date": source["published_at"],
        "vintage": source["source_vintage"],
        "retrieved_at": reference["retrieved_at"],
        "sha256": source["sha256"],
        "public_status": "verified_public",
        "import_status": "imported",
        "planning_region": "iso-ne",
        "states": ["09", "23", "25", "33", "44", "50"],
        "project_count": project_count,
        "notes": [
            "ISO New England is an independent nonprofit RTO, not a government agency or equipment owner.",
            "Only RSP_sortable is imported; overlapping and hidden worksheets are excluded.",
            "County and coordinate fields are absent and remain unknown.",
        ],
    }


def _census(manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for entry in manifest:
        if not entry["id"].startswith("census-"):
            continue
        vintage = "2026" if "2026" in entry["id"] else "2025"
        out.append({
            "_id": entry["id"],
            "title": f"U.S. Census reference artifact: {entry['cache_name']}",
            "publisher": "U.S. Census Bureau",
            "authority": "federal_government",
            "role": "geography_reference",
            "landing_url": entry["url"],
            "local_reference": None,
            "access_policy": "public_document",
            "download_url": entry["url"],
            "publication_date": None,
            "vintage": vintage,
            "retrieved_at": entry["retrieved_at"],
            "sha256": entry["sha256"],
            "public_status": "verified_public",
            "import_status": "reference_only",
            "planning_region": None,
            "states": [],
            "project_count": None,
            "notes": ["Reference geography only; bounds and representative points are never project locations."],
        })
    return out


def _federal_references(reference: dict[str, Any]) -> list[dict[str, Any]]:
    eia, ferc = reference["eia"], reference["ferc"]
    return [
        {
            "_id": "eia-861-2024",
            "title": "EIA-861 2024 final utility and service-territory directory",
            "publisher": eia["publisher"],
            "authority": "federal_government",
            "role": "utility_directory",
            "landing_url": eia["landing_url"],
            "local_reference": None,
            "access_policy": "public_document",
            "download_url": eia["url"],
            "publication_date": eia["index_updated"],
            "vintage": str(eia["vintage"]),
            "retrieved_at": reference["retrieved_at"],
            "sha256": eia["sha256"],
            "public_status": "verified_public",
            "import_status": "reference_only",
            "planning_region": None,
            "states": [],
            "project_count": None,
            "notes": [eia["semantics"], "The optional EIA directory adapter is not implemented in this snapshot."],
        },
        {
            "_id": "ferc-order-1000-regions-2024",
            "title": "FERC Order No. 1000 transmission planning regions map",
            "publisher": ferc["publisher"],
            "authority": "federal_government",
            "role": "planning_directory",
            "landing_url": ferc["landing_url"],
            "local_reference": None,
            "access_policy": "public_document",
            "download_url": ferc["url"],
            "publication_date": ferc["landing_updated"],
            "vintage": "2024",
            "retrieved_at": reference["retrieved_at"],
            "sha256": ferc["sha256"],
            "public_status": "verified_public",
            "import_status": "reference_only",
            "planning_region": None,
            "states": [],
            "project_count": None,
            "notes": [ferc["use"], ferc["coverage_caveat"]],
        },
    ]


def _planning_catalog(root: Path) -> list[dict[str, Any]]:
    out = []
    for item in load_json(root / "data" / "national" / "planning-catalog.json"):
        out.append({
            "_id": f"planning-directory:{item['region_id']}",
            "title": item["title"],
            "publisher": item["publisher"],
            "authority": item["authority"],
            "role": item["role"],
            "landing_url": item["resolved_url"],
            "local_reference": None,
            "access_policy": "catalog_only",
            "download_url": None,
            "publication_date": None,
            "vintage": None,
            "retrieved_at": item["verified_access_at"],
            "sha256": None,
            "public_status": "catalog_only",
            "import_status": "catalogued",
            "planning_region": item["region_id"],
            "states": [],
            "project_count": None,
            "adapter_status": item["adapter_status"],
            "landing_text_sha256": item["landing_text_sha256"],
            "notes": item["notes"],
        })
    return out


def build_sources(root: Path, manifest: list[dict[str, Any]], project_counts: dict[str, int]) -> list[dict[str, Any]]:
    reference = load_json(root / "data" / "national" / "reference-catalog.json")
    sources = [
        *_legacy(root, project_counts),
        _iso(reference, project_counts[ISO_SOURCE_ID]),
        *_census(manifest),
        *_federal_references(reference),
        *_planning_catalog(root),
    ]
    return sorted(sources, key=lambda source: source["_id"])
