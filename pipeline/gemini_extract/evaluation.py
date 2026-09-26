"""Agreement with F01, including failed pages; never advertised as independent accuracy."""

from typing import Any

from .prompt import PROMPT_VERSION, SCHEMA_VERSION
from .sources import CORPUS_PAGES, FIELD_NAMES


def evaluate(records: list[dict], model: str | None, *, live_calls: int, cache_hits: int, reason: str | None = None) -> dict:
    unavailable = not records
    per_field: dict[str, Any] = {}
    for field in FIELD_NAMES:
        matched = sum(
            record["comparison"].get(field) == "match" and record["fields"].get(field, {}).get("valid", False)
            for record in records
        )
        per_field[field] = {
            "matched": matched,
            "mismatched": sum(record["comparison"].get(field) == "mismatch" for record in records),
            "missing": sum(record["comparison"].get(field) == "missing" for record in records),
            "invalid": sum(not record["fields"].get(field, {}).get("valid", False) for record in records),
            "denominator": len(records),
            "accuracy": matched / len(records) if records else None,
        }
    return {
        "status": (
            "unavailable" if unavailable else
            "complete" if len(records) == CORPUS_PAGES and all(r["accepted"] for r in records) else "partial"
        ),
        "reason": reason,
        "measurement": "validated_field_agreement_with_f01_not_independent_human_accuracy",
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "corpus_pages": CORPUS_PAGES,
        "pages_processed": len(records),
        "responses_received": sum(r["status"] in ("accepted", "rejected") for r in records),
        "pages_accepted": sum(r["accepted"] for r in records),
        "pages_rejected": sum(r["status"] == "rejected" for r in records),
        "pages_failed": sum(r["status"] == "failed" for r in records),
        "live_calls": live_calls,
        "cache_hits": cache_hits,
        "per_field": per_field,
        "qa_checked": None,
    }
