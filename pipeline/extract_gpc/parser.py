from __future__ import annotations

import hashlib
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import pdfplumber

from common.ids import project_id
from common.io import REPO_ROOT, write_json
from common.names import norm_name
from common.schema import validate

GPC_PDF = REPO_ROOT / (
    "docs/Sperry-Tech-Challenge/Project Listings/Georgia Power/"
    "2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf"
)
GPC_SOURCE_ID = "gpc-2025"
GPC_SOURCE_SHA256 = "0dae2fc3a38462f0930cc2eb0acedca35e329cd0924e4749c81422bdc8602a12"
GPC_SOURCE_PAGES = 668
TABLE_FIRST_PAGE = 177
TABLE_LAST_PAGE = 190
TABLE_NAME = "GA ITS Ten-Year Plan (2025-2034)"
SOURCE_CONTRADICTIONS = [
    {
        "native_id": "20482",
        "name": "PITTMAN ROAD - WEST POINT DAM (USA) 115KV REBUILD",
        "current_table": {
            "need_date": "6/1/2028",
            "page": 184,
            "table_status": "current",
        },
        "other_table": {
            "need_date": "6/1/2031",
            "page": 191,
            "table_status": "cancelled",
        },
        "resolution": "review_required",
    }
]

PROJECTS_PATH = Path("data/projects/gpc.json")
SUMMARY_PATH = Path("data/projects/gpc_summary.json")
OWNERS_PATH = Path("data/owners/owners.json")

ZONE_RIGHT = 75.0
YEAR_RIGHT = 105.0
TEAMS_RIGHT = 145.0
NAME_RIGHT = 270.0
DATE_RIGHT = 325.0
SPONSOR_RIGHT = 360.0
TABLE_BOTTOM = 540.0

ZONE_RE = re.compile(r"\d{3}")
YEAR_RE = re.compile(r"20\d{2}")
TEAMS_RE = re.compile(r"\d+")
DATE_RE = re.compile(r"\d{1,2}/\d{1,2}/\d{4}")
OWNER_PREFIX_RE = re.compile(r"^(?:SAV|GTC|MEAG):\s*", re.IGNORECASE)
PAREN_RE = re.compile(r"\(([^)]*)\)")
VOLTAGE_TOKEN_RE = re.compile(
    r"\b(?:(\d+(?:\.\d+)?)\s*[-/]\s*)?(\d+(?:\.\d+)?)\s*kV\b",
    re.IGNORECASE,
)
CIRCUIT_RE = re.compile(r"#\s*\d+", re.IGNORECASE)
WORK_WORD_RE = re.compile(
    r"\b(?:REBUILD|RECONDUCTOR|LINE|REACTORS?|UPGRADE)\b", re.IGNORECASE
)
SPACES_RE = re.compile(r"\s+")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_owner_records() -> list[dict[str, Any]]:
    records = [
        {
            "_id": "owner:DU",
            "citation": None,
            "code": "DU",
            "mapping_status": "unverified",
            "organization": None,
            "reason": "No approved owner-code legend or official code mapping was found within F02 scope.",
            "utility": "unknown",
        },
        {
            "_id": "owner:GPC",
            "basis": "The plan sponsor code is GPC; the cited official company page identifies Georgia Power.",
            "citation": {
                "accessed_at": "2026-09-26",
                "publisher": "Georgia Power Company",
                "title": "Company Overview",
                "url": "https://www.georgiapower.com/about/company.html",
            },
            "code": "GPC",
            "mapping_status": "verified",
            "organization": "Georgia Power Company",
            "utility": "GPC",
        },
        {
            "_id": "owner:GTC",
            "citation": None,
            "code": "GTC",
            "mapping_status": "unverified",
            "organization": None,
            "reason": "No approved owner-code legend or official code mapping was found within F02 scope.",
            "utility": "unknown",
        },
        {
            "_id": "owner:MEAG",
            "citation": None,
            "code": "MEAG",
            "mapping_status": "unverified",
            "organization": None,
            "reason": "No approved owner-code legend or official code mapping was found within F02 scope.",
            "utility": "unknown",
        },
        {
            "_id": "owner:SAV",
            "basis": (
                "Georgia Power's SEC-filed Form 8-K states that Savannah Electric merged with and into "
                "Georgia Power on 2006-07-01, with Georgia Power as the surviving corporation."
            ),
            "citation": {
                "accessed_at": "2026-09-26",
                "publisher": "U.S. Securities and Exchange Commission",
                "title": "Georgia Power Company Form 8-K - Savannah Electric merger",
                "url": (
                    "https://www.sec.gov/Archives/edgar/data/41091/"
                    "000009212206000285/gamerger8k07-06edg.htm"
                ),
            },
            "code": "SAV",
            "mapping_status": "verified",
            "organization": "Georgia Power Company",
            "utility": "GPC",
        },
    ]
    return sorted(records, key=lambda record: record["code"])


def _owner_lookup(owners: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {record["code"]: record for record in owners}


def _number(value: str) -> int | float:
    parsed = float(value)
    return int(parsed) if parsed.is_integer() else parsed


def _voltages(name: str) -> list[int | float]:
    values: list[int | float] = []
    for match in VOLTAGE_TOKEN_RE.finditer(name):
        if match.group(1) is not None:
            values.append(_number(match.group(1)))
        values.append(_number(match.group(2)))
    return list(dict.fromkeys(values))


def _endpoint(raw: str) -> dict[str, str] | None:
    qualifiers = [value.strip() for value in PAREN_RE.findall(raw) if value.strip()]
    value = PAREN_RE.sub(" ", raw)
    value = VOLTAGE_TOKEN_RE.sub(" ", value)
    value = CIRCUIT_RE.sub(" ", value)
    value = WORK_WORD_RE.sub(" ", value)
    value = SPACES_RE.sub(" ", value).strip(" ,-/")
    if not value:
        return None
    endpoint = {"name": value, "norm": norm_name(value), "raw": raw.strip()}
    if qualifiers:
        endpoint["qualifier"] = "; ".join(qualifiers)
    return endpoint


def _split_endpoint_parts(asset: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    for index, character in enumerate(asset):
        if character == "(":
            depth += 1
        elif character == ")":
            depth = max(depth - 1, 0)
        elif (
            character in "-\N{EN DASH}\N{EM DASH}"
            and depth == 0
            and index > 0
            and index + 1 < len(asset)
            and asset[index - 1].isspace()
            and asset[index + 1].isspace()
        ):
            parts.append(asset[start:index].strip())
            start = index + 1
    parts.append(asset[start:].strip())
    return [part for part in parts if part]


def _endpoint_data(name: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    asset = OWNER_PREFIX_RE.sub("", name).strip()
    parts = _split_endpoint_parts(asset)
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in parts:
        endpoint = _endpoint(raw)
        if endpoint is None or not endpoint["norm"] or endpoint["norm"] in seen:
            continue
        candidates.append(endpoint)
        seen.add(endpoint["norm"])
    if len(parts) > 2:
        return [], candidates
    return candidates, []


def extract_endpoints(name: str) -> list[dict[str, str]]:
    endpoints, _ = _endpoint_data(name)
    return endpoints


def _parse_date(raw: str | None, flags: list[str]) -> dict[str, str | None]:
    if raw is None or not DATE_RE.fullmatch(raw):
        flags.append("need_date_unparsed")
        return {"raw": raw, "date": None, "precision": "unknown"}
    try:
        value = datetime.strptime(raw, "%m/%d/%Y").date().isoformat()
    except ValueError:
        flags.append("need_date_unparsed")
        return {"raw": raw, "date": None, "precision": "unknown"}
    return {"raw": raw, "date": value, "precision": "day"}


def _text(
    words: list[dict[str, Any]],
    left: float,
    right: float,
    row_top: float,
    first_line_only: bool,
) -> str:
    selected = [
        word
        for word in words
        if left <= word["x0"] < right
        and (not first_line_only or abs(word["top"] - row_top) < 1.2)
    ]
    return " ".join(
        word["text"] for word in sorted(selected, key=lambda word: (word["top"], word["x0"]))
    ).strip()


def _page_rows(page: Any, physical_page: int) -> list[dict[str, Any]]:
    words = page.extract_words(x_tolerance=1, y_tolerance=1)
    zone_headers = [
        word
        for word in words
        if word["text"] == "Zone" and word["x0"] < ZONE_RIGHT and word["top"] < 180
    ]
    if len(zone_headers) != 1:
        raise ValueError(f"page {physical_page}: expected one Zone header, found {len(zone_headers)}")
    header_top = zone_headers[0]["top"]
    table_words = [
        word
        for word in words
        if word["x0"] < SPONSOR_RIGHT
        and header_top + 10 < word["top"] < TABLE_BOTTOM
    ]
    starts = sorted(
        (
            word
            for word in table_words
            if word["x0"] < ZONE_RIGHT and ZONE_RE.fullmatch(word["text"])
        ),
        key=lambda word: word["top"],
    )
    rows: list[dict[str, Any]] = []
    for index, start in enumerate(starts):
        row_top = start["top"]
        end_top = starts[index + 1]["top"] - 0.2 if index + 1 < len(starts) else TABLE_BOTTOM
        segment = [word for word in table_words if row_top - 0.2 <= word["top"] < end_top]
        rows.append(
            {
                "name": _text(segment, TEAMS_RIGHT, NAME_RIGHT, row_top, False),
                "need_date": _text(segment, NAME_RIGHT, DATE_RIGHT, row_top, True),
                "owner_code": _text(segment, DATE_RIGHT, SPONSOR_RIGHT, row_top, True),
                "page": physical_page,
                "row_top": round(row_top, 1),
                "teams": _text(segment, YEAR_RIGHT, TEAMS_RIGHT, row_top, True),
                "year": _text(segment, ZONE_RIGHT, YEAR_RIGHT, row_top, True),
                "zone": _text(segment, 0, ZONE_RIGHT, row_top, True),
            }
        )
    return rows


def _record(
    row: dict[str, Any], owner_by_code: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    flags: list[str] = []
    required_patterns = (
        ("zone", ZONE_RE),
        ("year", YEAR_RE),
        ("teams", TEAMS_RE),
        ("need_date", DATE_RE),
    )
    if any(not pattern.fullmatch(row[field]) for field, pattern in required_patterns):
        flags.append("wrap_ambiguous")
    if not row["name"] or not row["owner_code"]:
        flags.append("wrap_ambiguous")

    native_id = row["teams"] or f"UNPARSED-{row['page']}-{row['row_top']}"
    project_key = f"GPC:{native_id}"
    owner = owner_by_code.get(row["owner_code"])
    if owner is None:
        flags.append("owner_code_unlisted")
        utility = "unknown"
        owner_basis = None
        owner_mapping_status = "unverified"
    else:
        utility = owner["utility"]
        owner_basis = owner["_id"]
        owner_mapping_status = owner["mapping_status"]

    in_service = _parse_date(row["need_date"] or None, flags)
    endpoints, endpoint_candidates = _endpoint_data(row["name"])
    if endpoint_candidates:
        flags.append("endpoint_ambiguous")
    if native_id == "20482":
        flags.append("source_status_conflict")
    voltages = _voltages(row["name"])
    evidence = {
        "name": {"page": row["page"], "quote": row["name"]},
        "native_id": {"page": row["page"], "quote": native_id},
        "owner_code": {"page": row["page"], "quote": row["owner_code"]},
        "in_service": {"page": row["page"], "quote": row["need_date"]},
        "plan_year": {"page": row["page"], "quote": row["year"]},
        "zone": {"page": row["page"], "quote": row["zone"]},
    }
    record = {
        "_id": project_id(project_key, GPC_SOURCE_ID),
        "active": True,
        "cost_status": "redacted_not_retained",
        "cost_usd": None,
        "description": None,
        "endpoints": endpoints,
        "field_evidence": evidence,
        "in_service": in_service,
        "name": row["name"],
        "native_id": native_id,
        "owner_basis": owner_basis,
        "owner_code": row["owner_code"] or None,
        "owner_mapping_status": owner_mapping_status,
        "plan_year": int(row["year"]) if YEAR_RE.fullmatch(row["year"]) else None,
        "project_key": project_key,
        "quality_flags": sorted(set(flags)),
        "source": {
            "page": row["page"],
            "row_top": row["row_top"],
            "source_id": GPC_SOURCE_ID,
        },
        "status": None,
        "table": TABLE_NAME,
        "utility": utility,
        "voltage_kv": max(voltages) if voltages else None,
        "voltages_kv": voltages,
        "zone": int(row["zone"]) if ZONE_RE.fullmatch(row["zone"]) else None,
    }
    if endpoint_candidates:
        record["endpoint_candidates"] = endpoint_candidates
    return record


def parse_gpc_pdf(
    path: Path = GPC_PDF, owners: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    source_sha = _sha256(path)
    if source_sha != GPC_SOURCE_SHA256:
        raise ValueError(f"Georgia source SHA-256 changed: {source_sha}")
    owners = owners or build_owner_records()
    owner_by_code = _owner_lookup(owners)
    records: list[dict[str, Any]] = []
    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) != GPC_SOURCE_PAGES:
            raise ValueError(f"expected {GPC_SOURCE_PAGES} pages, found {len(pdf.pages)}")
        for physical_page in range(TABLE_FIRST_PAGE, TABLE_LAST_PAGE + 1):
            records.extend(
                _record(row, owner_by_code)
                for row in _page_rows(pdf.pages[physical_page - 1], physical_page)
            )

    records.sort(
        key=lambda record: (
            0 if record["zone"] in {215, 219} else 1,
            record["zone"] if record["zone"] is not None else 999,
            record["plan_year"] if record["plan_year"] is not None else 9999,
            record["source"]["page"],
            record["source"]["row_top"],
            record["native_id"],
        )
    )
    native_id_counts = Counter(record["native_id"] for record in records)
    duplicate_native_ids = sorted(
        native_id for native_id, count in native_id_counts.items() if count > 1
    )
    project_key_counts = Counter(record["project_key"] for record in records)
    duplicate_project_keys = sorted(
        project_key for project_key, count in project_key_counts.items() if count > 1
    )
    if duplicate_native_ids or duplicate_project_keys:
        raise ValueError(
            "Georgia current-plan table contains duplicate identifiers: "
            f"native_ids={duplicate_native_ids}, project_keys={duplicate_project_keys}"
        )
    for record in records:
        validate(record, "project")
    return records


def build_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    zone_counts = Counter(str(record["zone"]) for record in records)
    owner_counts = Counter(record["owner_code"] for record in records)
    mapped = sum(record["utility"] == "GPC" for record in records)
    return {
        "ambiguous_rows": sum("wrap_ambiguous" in record["quality_flags"] for record in records),
        "coverage_note": "full_current_plan",
        "denominator_rows": len(records),
        "duplicate_native_ids": [],
        "duplicate_project_keys": [],
        "endpoint_ambiguous_rows": sum(
            "endpoint_ambiguous" in record["quality_flags"] for record in records
        ),
        "excluded_tables": [
            {
                "page": 191,
                "reason": "Separate cancelled-projects table; rows are removed from the current Ten-Year Plan.",
            }
        ],
        "mapped_owner_rows": mapped,
        "rows_emitted": len(records),
        "rows_per_owner_code": dict(sorted(owner_counts.items())),
        "rows_per_zone": dict(sorted(zone_counts.items(), key=lambda item: int(item[0]))),
        "source_id": GPC_SOURCE_ID,
        "source_contradictions": SOURCE_CONTRADICTIONS,
        "table": TABLE_NAME,
        "table_pages": {"first": TABLE_FIRST_PAGE, "last": TABLE_LAST_PAGE},
        "unknown_owner_rows": len(records) - mapped,
    }


def build_outputs() -> dict[str, Any]:
    owners = build_owner_records()
    projects = parse_gpc_pdf(owners=owners)
    return {"owners": owners, "projects": projects, "summary": build_summary(projects)}


def write_outputs(outputs: dict[str, Any], output_root: Path = REPO_ROOT) -> None:
    write_json(output_root / PROJECTS_PATH, outputs["projects"])
    write_json(output_root / SUMMARY_PATH, outputs["summary"])
    write_json(output_root / OWNERS_PATH, outputs["owners"])
