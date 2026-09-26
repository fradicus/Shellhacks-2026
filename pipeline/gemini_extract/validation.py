"""Evidence checks are deliberately conservative; parser agreement is not human accuracy."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from typing import Any

from jsonschema import Draft202012Validator

from extract_desc.parser import DATE_RE, parse_card

from .prompt import response_schema
from .sources import APPROVED, FIELD_NAMES, Page, expected_fields

ID_RE = re.compile(r"\d{4,5}(?:\s*[A-Z](?:\s*[-,]\s*[A-Z])*)?")
VALIDATOR = Draft202012Validator(response_schema())
MAX_RESPONSE_CHARS = 200_000
LABELS = {
    "project_id": ("Project ID", "Project Description"),
    "description": ("Project Description", "Project Need"),
    "need": ("Project Need", "Project Status"),
    "status": ("Project Status", "Planned In-Service Date"),
    "in_service_raw": ("Planned In-Service Date", "Estimated Project Cost"),
}


def normalize(value: Any) -> Any:
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    return value


def section(page: Page, field: str) -> str:
    """Keep exact substrings; only the value comparison normalizes whitespace."""
    lines = page.text.splitlines(keepends=True)
    labels = [line.strip() for line in lines]
    try:
        if field in ("name", "endpoints", "voltage_kv"):
            return "".join(lines[4:labels.index("Project ID")]).strip()
        if field in ("total_cost", "yearly_spend"):
            return "".join(lines[labels.index("Estimated Project Cost") + 1:]).strip()
        first, last = LABELS[field]
        start = labels.index(first) + 1
        return "".join(lines[start:labels.index(last, start)]).strip()
    except ValueError:
        return ""


def _finite(value: Any) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(_finite(item) for item in value.values())
    if isinstance(value, list):
        return all(_finite(item) for item in value)
    return True


def parse_response(text: str) -> Any:
    if not isinstance(text, str) or len(text) > MAX_RESPONSE_CHARS:
        raise ValueError("invalid_response")

    def unique_pairs(pairs: list) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_response_key")
            result[key] = value
        return result

    def invalid_constant(value: str) -> None:
        raise ValueError("nonfinite_json_number")

    response = json.loads(text, object_pairs_hook=unique_pairs, parse_constant=invalid_constant)
    if not _finite(response):
        raise ValueError("nonfinite_json_number")
    return response


def validate_response(response: Any, page: Page) -> tuple[dict, dict, list[str]]:
    comparison = {field: "missing" for field in FIELD_NAMES}
    if not _finite(response) or not VALIDATOR.is_valid(response):
        return {}, comparison, ["response_schema_invalid"]
    # Derive support from the actual labeled source, not from an arbitrary matching substring
    # or from the supplied expected values. F01 agreement is a separate measurement below.
    source_record = parse_card(page.text, page.source_id, page.number, APPROVED[page.source_id][2])
    supported = expected_fields(source_record)
    fields = {}
    record_reasons = []
    for name in FIELD_NAMES:
        proposed = response[name]
        value, quote = proposed["value"], proposed["quote"]
        reasons = []
        segment = section(page, name)
        if proposed["page"] != page.number:
            reasons.append("wrong_page")
        if quote is None:
            if segment or value not in (None, [], {}):
                reasons.append("quote_missing")
        elif quote not in page.text:
            reasons.append("quote_not_in_source")
        elif quote not in segment:
            reasons.append("quote_wrong_section")

        if normalize(value) != normalize(supported[name]):
            reasons.append("value_not_supported")
        # A broad section may contain many numbers: quote must include the actual support,
        # not merely a different valid token from the same section.
        if quote is not None:
            if name in ("total_cost", "yearly_spend"):
                cost = source_record["cost_raw"]
                budget = " ".join(cost.get("labels", []) + cost.get("amounts", []))
                if budget:
                    if budget not in normalize(quote):
                        reasons.append("budget_columns_not_cited")
                elif normalize(segment) != normalize(quote):
                    reasons.append("cost_narrative_not_cited")
            elif normalize(quote) != normalize(segment):
                reasons.append("field_not_fully_cited")

        if name == "project_id" and (not isinstance(value, str) or not ID_RE.fullmatch(value)):
            reasons.append("project_id_invalid")
        if name == "name" and (not isinstance(value, str) or not value.strip()):
            reasons.append("name_missing")
        if name == "in_service_raw" and isinstance(value, str):
            for token in DATE_RE.findall(value):
                try:
                    datetime.strptime(token, "%m/%d/%Y" if len(token.rsplit("/", 1)[1]) == 4 else "%m/%d/%y")
                except ValueError:
                    reasons.append("date_invalid")
        expected = page.expected[name]
        comparison[name] = (
            "missing" if value is None and expected is not None else
            "match" if normalize(value) == normalize(expected) else "mismatch"
        )
        fields[name] = {**proposed, "valid": not reasons, "reasons": sorted(set(reasons))}
        record_reasons.extend(f"{name}:{reason}" for reason in sorted(set(reasons)))
    return fields, comparison, record_reasons
