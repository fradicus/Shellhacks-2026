from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pdfplumber

from common.ids import project_id
from common.io import REPO_ROOT, write_json
from common.names import norm_name
from common.schema import validate

DESC_2024 = REPO_ROOT / (
    "docs/Sperry-Tech-Challenge/Project Listings/Dominion Energy/"
    "2024-2028-2million-and-above-project-descriptions.pdf"
)
DESC_2025 = REPO_ROOT / "data/sources/desc-2025.pdf"
GPC_2025 = REPO_ROOT / (
    "docs/Sperry-Tech-Challenge/Project Listings/Georgia Power/"
    "2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf"
)
SAMPLE = REPO_ROOT / "docs/Sperry-Tech-Challenge/Projects_Overlaps.xlsx"
DESC_2024_SNAPSHOT_SHA256 = "890876d0faefd40576a0b5e598a804b54b4d8d2d56dd96fb7e40d5a406db0f46"
DESC_2025_SNAPSHOT_SHA256 = "265453ccf14b4f95054fed304b7999270a478dbefc3a812163395b31422e74e0"
DESC_2025_METADATA_CHECKED_AT = "2026-09-26T09:04:40Z"
DESC_2025_HTTP_LAST_MODIFIED = "2026-06-18T13:15:14Z"

PROJECTS_PATH = Path("data/projects/desc.json")
UNPARSED_PATH = Path("data/projects/desc_unparsed.json")
VERSIONS_PATH = Path("data/versions/desc.json")
SOURCES_PATH = Path("data/sources/sources.json")

FIELD_LABELS = (
    "Project ID",
    "Project Description",
    "Project Need",
    "Project Status",
    "Planned In-Service Date",
    "Estimated Project Cost",
)
DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}/(?:\d{2}|\d{4})\b")
CARD_RE = re.compile(r"^Project\s+(\d+)\s+of\s+(\d+)$")
STRICT_AMOUNT_RE = re.compile(r"^\$?(?:\d+|\d{1,3}(?:,\d{3})+)$")
NARRATIVE_COST_RE = re.compile(r"Estimated cost of \$([\d,]+)", re.IGNORECASE)
VOLTAGE_TOKEN_RE = re.compile(
    r"\b(?:(\d+(?:\.\d+)?)\s*[-/]\s*)?(\d+(?:\.\d+)?)\s*kV\b",
    re.IGNORECASE,
)
ENDPOINT_SEPARATOR_RE = re.compile(r"\s+[-–]\s+|\s*–\s*|(?<=[A-Za-z0-9])-(?=[A-Z])")
TRAILING_ASSET_RE = re.compile(
    r"\s+(?:TIE|LINE|TAP|FOLD[- ]?IN|REBUILD|CONSTRUCT)\b.*$", re.IGNORECASE
)
CIRCUIT_SUFFIX_RE = re.compile(r"\s+#\d+\b.*$", re.IGNORECASE)
WORK_ONLY_RE = re.compile(r"^(?:ADD|CONSTRUCT|REBUILD|TAP|UPGRADE)\b", re.IGNORECASE)

# These source-page decisions were reviewed against the pinned public PDFs. They deliberately
# replace automatic endpoint inference only for the listed cards. Candidate labels retain source
# language for later review; they are not accepted endpoints.
ENDPOINT_REVIEW_OVERRIDES: dict[tuple[str, int], dict[str, Any]] = {
    ("desc-2025", 2): {
        "project_key": "DESC:0139 M,N",
        "class_flag": "endpoint_multi_asset",
        "candidates": (
            ("Okatie", "Okatie 230-115kV Substation"),
            ("Jasper", "Jasper"),
            ("Yemassee", "Yemassee 230kV #1 Fold-in"),
        ),
    },
    ("desc-2025", 6): {
        "project_key": "DESC:6808 N,O",
        "class_flag": "endpoint_multi_asset",
        "candidates": (
            ("VCS1", "VCS1"),
            ("Denny Terrace", "Denny Terrace 230kV"),
            ("Pineland", "Pineland 230kV"),
        ),
    },
    ("desc-2025", 13): {
        "project_key": "DESC:1060A, I, L",
        "class_flag": "endpoint_multi_asset",
        "candidates": (
            ("Williams St Sub", "Williams St Sub"),
            ("AM Williams Sub", "AM Williams Sub"),
            ("McMeekin Sub", "McMeekin Sub"),
        ),
    },
    ("desc-2024", 39): {
        "project_key": "DESC:6847 A-B, D-H",
        "class_flag": "endpoint_multi_asset",
        "candidates": (
            ("Church Creek", "Church Creek"),
            ("Faber Place", "Faber Place"),
            ("Charleston Transmission", "Charleston Transmission"),
        ),
    },
    ("desc-2025", 33): {
        "project_key": "DESC:6847",
        "class_flag": "endpoint_multi_asset",
        "candidates": (
            ("Church Creek", "Church Creek"),
            ("Faber Place", "Faber Place"),
            ("Charleston Transmission", "Charleston Transmission"),
        ),
    },
    ("desc-2025", 38): {
        "project_key": "DESC:6810 T",
        "class_flag": "endpoint_multi_asset",
        "candidates": (
            ("Cameron Jct", "Cameron Jct"),
            ("Cameron", "Cameron"),
            ("St Matthews", "St Matthews"),
        ),
    },
    ("desc-2024", 1): {
        "project_key": "DESC:6807 B",
        "class_flag": "endpoint_scope_ambiguous",
        "candidates": (
            ("Queensboro", "Queensboro"),
            ("Ft Johnson", "Ft Johnson 115 kV"),
            ("Bayfront", "Bayfront 115kV"),
            ("James Island", "James Island Sect"),
        ),
    },
    ("desc-2024", 14): {
        "project_key": "DESC:6809 E",
        "class_flag": "endpoint_scope_ambiguous",
        "candidates": (
            ("Stevens Creek", "Stevens Creek"),
            ("Hooks", "Hooks 115kV"),
            ("LR Plumb Branch", "LR Plumb Branch 46kV Rebuilds"),
        ),
    },
    ("desc-2025", 4): {
        "project_key": "DESC:6808 K",
        "class_flag": "endpoint_scope_ambiguous",
        "candidates": (
            ("Burton", "Burton"),
            ("St Helena", "St Helena 115kV"),
            ("Frogmore Transmission", "Frogmore Transmission Section"),
        ),
    },
    ("desc-2025", 5): {
        "project_key": "DESC:6808 L",
        "class_flag": "endpoint_scope_ambiguous",
        "candidates": (
            ("Burton", "Burton"),
            ("St Helena", "St Helena"),
            ("Frogmore Distribution Tap", "Frogmore Distribution Tap"),
        ),
    },
    ("desc-2025", 10): {
        "project_key": "DESC:6808 V",
        "class_flag": "endpoint_scope_ambiguous",
        "candidates": (
            ("Faber Place", "Faber Place"),
            ("Bayfront", "Bayfront"),
            ("North Bridge Terrace", "North Bridge Terrace"),
        ),
    },
    ("desc-2025", 24): {
        "project_key": "DESC:6809 M",
        "class_flag": "endpoint_scope_ambiguous",
        "candidates": (
            ("St George", "St George"),
            ("Sumter", "Sumter 230kV Tie"),
            ("Santee Substation", "Santee Substation"),
            ("Duke/Progress Energy Tie", "Duke/Progress Energy Tie"),
        ),
    },
    ("desc-2025", 43): {
        "project_key": "DESC:6877 A",
        "class_flag": "endpoint_scope_ambiguous",
        "candidates": (
            ("Church Creek", "Church Creek"),
            ("Dawson", "Dawson"),
            ("Long Savannah", "Long Savannah"),
            ("Faber Place", "Faber Place"),
        ),
    },
    ("desc-2025", 22): {
        "project_key": "DESC:06810 G",
        "class_flag": "endpoint_scope_ambiguous",
        "candidates": (
            ("Goose Creek Reservoir", "Goose Creek Reservoir"),
            ("Williams", "Williams"),
            ("Goose Creek", "Goose Creek"),
            ("Faber Place", "Faber Place"),
        ),
    },
    ("desc-2025", 23): {
        "project_key": "DESC:06810 H",
        "class_flag": "endpoint_scope_ambiguous",
        "candidates": (("Summerville 115kV Loop", "Summerville 115kV Loop"),),
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean_text(text: str) -> str:
    # The PDFs' embedded font maps en dashes to U+FFFD. The visual glyph is an en dash.
    return "\n".join(
        line.strip()
        for line in text.replace("\ufffd", "–").replace("\u00a0", " ").splitlines()
        if line.strip()
    )


def _section(lines: list[str], start: str, end: str) -> str | None:
    try:
        begin = lines.index(start) + 1
        finish = lines.index(end, begin)
    except ValueError:
        return None
    value = " ".join(lines[begin:finish]).strip()
    return value or None


def _parse_date(raw: str | None, flags: list[str]) -> dict[str, Any]:
    if not raw:
        flags.append("in_service_missing")
        return {"raw": raw, "date": None, "precision": "unknown"}

    iso_dates: list[str] = []
    for token in DATE_RE.findall(raw):
        try:
            fmt = "%m/%d/%Y" if len(token.rsplit("/", 1)[-1]) == 4 else "%m/%d/%y"
            iso_dates.append(datetime.strptime(token, fmt).date().isoformat())
        except ValueError:
            flags.append("in_service_invalid")

    if len(iso_dates) == 1:
        return {"raw": raw, "date": iso_dates[0], "precision": "day"}
    if len(iso_dates) > 1:
        flags.append("in_service_multiple_dates")
        return {
            "raw": raw,
            "date": None,
            "precision": "unknown",
            "dates": iso_dates,
        }

    if "in_service_invalid" not in flags:
        flags.append("in_service_unparsed")
    return {"raw": raw, "date": None, "precision": "unknown"}


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


def _endpoint_name(raw: str) -> str:
    voltage = VOLTAGE_TOKEN_RE.search(raw)
    value = raw[: voltage.start()] if voltage else raw
    value = CIRCUIT_SUFFIX_RE.sub("", value)
    value = TRAILING_ASSET_RE.sub("", value)
    value = re.sub(r"\s+", " ", value).strip(" ,-/")
    return value


def _endpoints(name: str) -> list[dict[str, str]]:
    # A colon introduces the work scope on these cards; the part before it names the asset.
    asset = name.split(":", 1)[0].strip()
    raw_parts = ENDPOINT_SEPARATOR_RE.split(asset)[:2]
    endpoints: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in raw_parts:
        cleaned = _endpoint_name(raw)
        normalized = norm_name(cleaned)
        if not cleaned or not normalized or WORK_ONLY_RE.match(cleaned) or normalized in seen:
            continue
        endpoints.append({"name": cleaned, "norm": normalized, "raw": raw.strip()})
        seen.add(normalized)
    return endpoints


def _reviewed_endpoint_data(
    source_id: str,
    page: int,
    project_key: str,
    name: str,
    description: str | None,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[str]]:
    review = ENDPOINT_REVIEW_OVERRIDES.get((source_id, page))
    if review is None:
        return _endpoints(name), [], []
    if project_key != review["project_key"]:
        raise ValueError(
            f"reviewed endpoint override key mismatch for {source_id} page {page}: {project_key}"
        )

    source_fields = f"{name}\n{description or ''}"
    candidates: list[dict[str, str]] = []
    for candidate_name, raw in review["candidates"]:
        if raw not in source_fields:
            raise ValueError(
                f"reviewed endpoint candidate missing for {source_id} page {page}: {raw}"
            )
        candidates.append(
            {"name": candidate_name, "norm": norm_name(candidate_name), "raw": raw}
        )
    return [], candidates, ["endpoint_ambiguous", review["class_flag"]]


def _parse_amount(token: str, label: str, flags: list[str]) -> int | None:
    if not STRICT_AMOUNT_RE.fullmatch(token):
        flags.append(f"cost_amount_invalid:{label}")
        return None
    if not token.startswith("$"):
        flags.append(f"cost_currency_symbol_missing:{label}")
    return int(token.removeprefix("$").replace(",", ""))


def _parse_costs(
    lines: list[str], cost_text: str | None, flags: list[str]
) -> tuple[int | None, dict[str, int | None], dict[str, Any]]:
    header_index = next(
        (index for index, line in enumerate(lines) if line.startswith("Previous ")), None
    )
    if header_index is None:
        match = NARRATIVE_COST_RE.search(cost_text or "")
        if match:
            flags.append("yearly_spend_not_published")
            value = int(match.group(1).replace(",", ""))
            return value, {}, {"labels": [], "amounts": [], "text": cost_text}
        flags.append("cost_unparsed")
        return None, {}, {"labels": [], "amounts": [], "text": cost_text}

    labels = lines[header_index].split()
    amount_line = lines[header_index + 1] if header_index + 1 < len(lines) else ""
    amount_tokens = amount_line.split()
    if len(labels) != len(amount_tokens):
        flags.append("cost_column_count_mismatch")

    parsed: list[int | None] = []
    for index, label in enumerate(labels):
        token = amount_tokens[index] if index < len(amount_tokens) else ""
        parsed.append(_parse_amount(token, label.rstrip("*"), flags))

    total_index = next(
        (index for index, label in enumerate(labels) if label.rstrip("*") == "Total"), None
    )
    total = parsed[total_index] if total_index is not None and total_index < len(parsed) else None
    yearly = {
        label.rstrip("*"): parsed[index]
        for index, label in enumerate(labels)
        if label.rstrip("*") != "Total" and index < len(parsed)
    }
    if total is None:
        flags.append("cost_total_missing")
    elif any(value is None for value in yearly.values()):
        flags.append("yearly_spend_incomplete")
    elif abs(sum(yearly.values()) - total) > 1:  # type: ignore[arg-type]
        flags.append("cost_consistency_mismatch")

    return total, yearly, {
        "labels": labels,
        "amounts": amount_tokens,
        "text": " ".join((lines[header_index], amount_line)),
    }


def _evidence(page: int, quote: Any) -> dict[str, Any]:
    return {"page": page, "quote": quote}


def parse_card(text: str, source_id: str, page: int, expected_total: int) -> dict[str, Any]:
    raw_text = _clean_text(text)
    lines = raw_text.splitlines()
    flags: list[str] = []

    card_match = CARD_RE.fullmatch(lines[0]) if lines else None
    if not card_match:
        flags.append("card_header_unparsed")
        card_number = page
        card_total = expected_total
    else:
        card_number, card_total = map(int, card_match.groups())
        if card_number != page:
            flags.append("card_page_mismatch")
        if card_total != expected_total:
            flags.append("card_total_mismatch")

    missing_labels = [label for label in FIELD_LABELS if label not in lines]
    flags.extend(f"field_label_missing:{label}" for label in missing_labels)

    try:
        name_end = lines.index("Project ID")
        name = " ".join(lines[4:name_end]).strip()
    except ValueError:
        name = f"Unparsed DESC card page {page}"

    native_id = _section(lines, "Project ID", "Project Description") or f"UNPARSED-{page}"
    native_id = re.sub(r"\s+", " ", native_id).strip()
    description = _section(lines, "Project Description", "Project Need")
    need = _section(lines, "Project Need", "Project Status")
    status = _section(lines, "Project Status", "Planned In-Service Date")
    in_service_raw = _section(lines, "Planned In-Service Date", "Estimated Project Cost")
    cost_text = None
    if "Estimated Project Cost" in lines:
        cost_text = " ".join(lines[lines.index("Estimated Project Cost") + 1 :]).strip() or None

    in_service = _parse_date(in_service_raw, flags)
    cost_usd, yearly_spend, cost_raw = _parse_costs(lines, cost_text, flags)
    key = f"DESC:{native_id}"
    endpoints, endpoint_candidates, endpoint_flags = _reviewed_endpoint_data(
        source_id, page, key, name, description
    )
    flags.extend(endpoint_flags)
    voltages = _voltages(name)

    field_evidence = {
        "name": _evidence(page, name),
        "native_id": _evidence(page, native_id),
        "description": _evidence(page, description),
        "need": _evidence(page, need),
        "status": _evidence(page, status),
        "in_service": _evidence(page, in_service_raw),
        "cost_usd": _evidence(page, cost_raw["text"]),
        "yearly_spend": _evidence(page, cost_raw["text"]),
        "endpoints": _evidence(page, name),
        "voltages_kv": _evidence(page, name),
    }
    record: dict[str, Any] = {
        "_id": project_id(key, source_id),
        "active": False,
        "card_number": card_number,
        "card_total": card_total,
        "cost_raw": cost_raw,
        "cost_usd": cost_usd,
        "description": description,
        "endpoints": endpoints,
        "field_evidence": field_evidence,
        "in_service": in_service,
        "name": name,
        "native_id": native_id,
        "need": need,
        "owner_code": None,
        "project_key": key,
        "quality_flags": sorted(set(flags)),
        "raw_text": raw_text,
        "source": {"source_id": source_id, "page": page},
        "status": status,
        "utility": "DESC",
        "voltage_kv": max(voltages) if voltages else None,
        "voltages_kv": voltages,
        "yearly_spend": yearly_spend,
    }
    if endpoint_candidates:
        record["endpoint_candidates"] = endpoint_candidates
    return record


def parse_desc_pdf(path: Path, source_id: str, expected_cards: int) -> list[dict[str, Any]]:
    expected_sha = {
        "desc-2024": DESC_2024_SNAPSHOT_SHA256,
        "desc-2025": DESC_2025_SNAPSHOT_SHA256,
    }.get(source_id)
    if expected_sha is None:
        raise ValueError(f"unsupported DESC source: {source_id}")
    actual_sha = _sha256(path)
    if actual_sha != expected_sha:
        raise ValueError(f"{source_id}: source SHA-256 changed: {actual_sha}")

    records: list[dict[str, Any]] = []
    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) != expected_cards:
            raise ValueError(f"{source_id}: expected {expected_cards} pages, found {len(pdf.pages)}")
        for page_number, page in enumerate(pdf.pages, start=1):
            records.append(parse_card(page.extract_text() or "", source_id, page_number, expected_cards))
    return records


def _mark_active(records: list[dict[str, Any]]) -> None:
    source_order = {"desc-2024": 0, "desc-2025": 1}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["project_key"]].append(record)
    for versions in grouped.values():
        latest = max(versions, key=lambda record: source_order[record["source"]["source_id"]])
        latest["active"] = True


def _in_service_value(record: dict[str, Any]) -> Any:
    value = record["in_service"]
    return value["date"] if value["date"] is not None else value.get("dates", value["raw"])


def build_version_changes(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for record in records:
        by_key[record["project_key"]][record["source"]["source_id"]] = record

    changes: list[dict[str, Any]] = []
    comparisons = (
        ("in_service.date", _in_service_value),
        ("cost_usd", lambda record: record["cost_usd"]),
        ("status", lambda record: record["status"]),
        ("name", lambda record: record["name"]),
    )
    for key in sorted(by_key):
        versions = by_key[key]
        if not {"desc-2024", "desc-2025"}.issubset(versions):
            continue
        old = versions["desc-2024"]
        new = versions["desc-2025"]
        for field, getter in comparisons:
            old_value = getter(old)
            new_value = getter(new)
            if old_value == new_value:
                continue
            change = {
                "_id": f"{key}|{field}|desc-2024>desc-2025",
                "field": field,
                "from_page": old["source"]["page"],
                "from_source": "desc-2024",
                "new": new_value,
                "old": old_value,
                "project_key": key,
                "to_page": new["source"]["page"],
                "to_source": "desc-2025",
            }
            validate(change, "version_change")
            changes.append(change)
    return changes


def build_sources() -> list[dict[str, Any]]:
    desc_2024_sha256 = _sha256(DESC_2024)
    if desc_2024_sha256 != DESC_2024_SNAPSHOT_SHA256:
        raise ValueError("desc-2024 PDF changed; reviewed endpoint decisions require pinned bytes")
    desc_2025_sha256 = _sha256(DESC_2025)
    if desc_2025_sha256 != DESC_2025_SNAPSHOT_SHA256:
        raise ValueError(
            "desc-2025.pdf changed; refresh its pinned SHA-256 and retrieval metadata together"
        )
    sources = [
        {
            "_id": "desc-2024",
            "filing": "2024-2028",
            "local_path": str(DESC_2024.relative_to(REPO_ROOT)).replace("\\", "/"),
            "pages": 44,
            "public_status": "public",
            "publisher": "Dominion Energy South Carolina",
            "sha256": desc_2024_sha256,
            "title": "DESC Planned Transmission Projects $2M and Above Total - 2024-2028",
            "url": "https://www.scrtp.com/assets/pdfs/home/2024-2028-2million-and-above-project-descriptions.pdf",
        },
        {
            "_id": "desc-2025",
            "filing": "2025-2029",
            "http_last_modified": DESC_2025_HTTP_LAST_MODIFIED,
            "local_path": str(DESC_2025.relative_to(REPO_ROOT)).replace("\\", "/"),
            "pages": 47,
            "public_status": "public",
            "publisher": "Dominion Energy South Carolina",
            "source_metadata_checked_at": DESC_2025_METADATA_CHECKED_AT,
            "sha256": desc_2025_sha256,
            "title": "DESC Planned Transmission Projects $2M and Above Total - 2025-2029",
            "url": "https://www.scrtp.com/assets/pdfs/home/2025-2029-2million-and-above-project-descriptions.pdf",
        },
        {
            "_id": "gpc-2025",
            "filing": "2025 IRP",
            "local_path": str(GPC_2025.relative_to(REPO_ROOT)).replace("\\", "/"),
            "pages": 668,
            "public_status": "public_with_banner",
            "publisher": "Georgia Power Company",
            "restrictions": (
                "Decision D2: deterministic Ten-Year Plan table parsing only; no Gemini, page images, "
                "or excerpts beyond project names."
            ),
            "sha256": _sha256(GPC_2025),
            "title": "2025 IRP Technical Appendix Volume 3 - Transmission Plan - Public Disclosure",
        },
        {
            "_id": "sample",
            "filing": "ShellHacks 2026 Gridlock challenge",
            "local_path": str(SAMPLE.relative_to(REPO_ROOT)).replace("\\", "/"),
            "pages": None,
            "public_status": "public",
            "publisher": "Sperry Tech",
            "sha256": _sha256(SAMPLE),
            "title": "Projects_Overlaps.xlsx sponsor sample",
        },
    ]
    for source in sources:
        validate(source, "source")
    return sources


def build_outputs() -> dict[str, list[dict[str, Any]]]:
    records = parse_desc_pdf(DESC_2024, "desc-2024", 44)
    records.extend(parse_desc_pdf(DESC_2025, "desc-2025", 47))
    _mark_active(records)
    records.sort(key=lambda record: (record["source"]["source_id"], record["source"]["page"]))
    for record in records:
        validate(record, "project")

    unparsed = [
        {
            "page": record["source"]["page"],
            "quality_flags": record["quality_flags"],
            "source_id": record["source"]["source_id"],
        }
        for record in records
        if record["native_id"].startswith("UNPARSED-")
        or any(flag.startswith("field_label_missing:") for flag in record["quality_flags"])
    ]
    return {
        "projects": records,
        "sources": build_sources(),
        "unparsed": unparsed,
        "version_changes": build_version_changes(records),
    }


def write_outputs(outputs: dict[str, list[dict[str, Any]]], output_root: Path = REPO_ROOT) -> None:
    write_json(output_root / PROJECTS_PATH, outputs["projects"])
    write_json(output_root / UNPARSED_PATH, outputs["unparsed"])
    write_json(output_root / VERSIONS_PATH, outputs["version_changes"])
    write_json(output_root / SOURCES_PATH, outputs["sources"])
