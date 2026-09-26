"""Sequential batch execution, bounded retries, provenance cache, and honest offline outputs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from common import REPO_ROOT, load_json, validate, write_json

from .evaluation import evaluate
from .prompt import PROMPT_VERSION, SCHEMA_VERSION
from .sources import FIELD_NAMES, Page, SourceError, assert_approved, load_pages
from .transport import MODEL_RE, GeminiTransport, TransportFailure
from .validation import parse_response, validate_response

MAX_RETRIES = 2


class Transport(Protocol):
    def generate(self, page: Page) -> str: ...


def timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def cache_metadata(page: Page, model: str) -> dict:
    return {
        "source_sha256": page.source_sha256,
        "page": page.number,
        "model": model,
        "prompt_version": PROMPT_VERSION,
    }


def cache_key(page: Page, model: str) -> str:
    return hashlib.sha256(json.dumps(cache_metadata(page, model), sort_keys=True).encode()).hexdigest()


def _cached(path: Path, page: Page, model: str) -> dict | None:
    try:
        cached = load_json(path)
        if not isinstance(cached, dict) or set(cached) != {"metadata", "response", "generated_at", "text_sha256"}:
            return None
        if cached["metadata"] != cache_metadata(page, model) or cached["text_sha256"] != page.text_sha256:
            return None
        # Validate actual timezone-bearing timestamps; no invented generation time on cache hits.
        generated_at = cached["generated_at"]
        if not isinstance(generated_at, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", generated_at
        ):
            return None
        datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        return cached
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def extract_page(page: Page, model: str, transport: Transport, cache_dir: Path, *, sleep: Callable = time.sleep) -> dict:
    assert_approved(page)  # Checked even for cache hits; Georgia never bypasses this boundary.
    key = cache_key(page, model)
    cache_path = cache_dir / f"{key}.json"
    cached = _cached(cache_path, page, model)
    attempts = 0
    response: Any = None
    failure = None
    generated_at = None
    if cached is not None:
        response = cached["response"]
        generated_at = cached["generated_at"]
    else:
        for attempt in range(MAX_RETRIES + 1):
            attempts += 1
            try:
                raw_response = transport.generate(page)
                generated_at = timestamp()
                response = parse_response(raw_response)
                break
            except TransportFailure as exc:
                failure = exc.reason
                if not exc.transient or attempt == MAX_RETRIES:
                    break
                sleep(2 ** attempt)
            except SourceError:
                raise  # Fail closed; a prevented request must not be reported as an API call.
            except (ValueError, TypeError):
                failure = "response_json_invalid"
                break
            except Exception:
                failure = "gemini_unexpected_failure"
                break
        if response is not None:
            failure = None
            # An object without _id is intentionally skipped by the recursive Atlas loader.
            write_json(cache_path, {
                "metadata": cache_metadata(page, model), "text_sha256": page.text_sha256,
                "generated_at": generated_at, "response": response,
            })
    if response is None:
        fields, comparison, reasons = {}, dict.fromkeys(FIELD_NAMES, "missing"), [failure or "response_json_invalid"]
    else:
        fields, comparison, reasons = validate_response(response, page)
    record = {
        "_id": f"{page.source_id}:page-{page.number}:{key}",
        "source_id": page.source_id,
        "source_sha256": page.source_sha256,
        "page": page.number,
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "source_text": page.text,
        "source_quality_flags": list(page.quality_flags),
        "deterministic": page.expected,
        "fields": fields,
        "comparison": comparison,
        "accepted": not reasons,
        "status": "failed" if generated_at is None else "rejected" if reasons else "accepted",
        "rejection_reason": "; ".join(reasons) if reasons else None,
        "validation": {"passed": not reasons, "reasons": reasons},
        "call_attempted": attempts > 0,
        "attempts": attempts,
        "cache_hit": cached is not None,
    }
    if generated_at is not None:
        record["generated_at"] = generated_at
    validate(record, "extraction")
    return record


def run_batch(*, live: bool = False, root: Path = REPO_ROOT) -> tuple[list[dict], dict]:
    """No environment variable alone enables the network, and no document overrides exist."""
    output = root / "data/extraction"
    # Verify the entire approved corpus before any client initialization or cache access.
    pages = load_pages(root)
    model = os.environ.get("GEMINI_MODEL", "")
    api_key = os.environ.get("GEMINI_API_KEY", "")
    model = model if MODEL_RE.fullmatch(model) else None
    records: list[dict] = []
    reason = "live_execution_not_requested" if not live else "gemini_credentials_or_model_unavailable"
    if live and model and api_key:
        client = None
        try:
            client = GeminiTransport(api_key, model)
            records = [extract_page(page, model, client, output / "cache") for page in pages]
            reason = None
        finally:
            if client is not None:
                client.close()
    report = evaluate(
        records, model,
        live_calls=sum(record["attempts"] for record in records),
        cache_hits=sum(record["cache_hit"] for record in records),
        reason=reason,
    )
    for record in records:
        record["evaluation"] = report
    write_json(output / "desc.json", records)
    write_json(output / "eval.json", report)
    return records, report
