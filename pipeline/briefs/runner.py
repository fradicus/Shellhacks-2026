"""Offline-first batch, bounded live retries, fresh cache validation and artifact preservation."""

import hashlib
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path

from common import REPO_ROOT, load_json, validate, write_json
from extract_gpc.parser import GPC_SOURCE_SHA256, parse_gpc_pdf
from gemini_extract.sources import load_pages
from gemini_extract.transport import MODEL_RE, TransportFailure

from .facts import build_match_input, canonical_hash, unique
from .transport import GeminiTransport
from .validation import PROMPT_VERSION, SCHEMA_VERSION, validate_response


def timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def load_inputs(root: Path) -> dict:
    return {"projects": load_json(root / "data/projects/desc.json") + load_json(root / "data/projects/gpc.json"),
            "locations": load_json(root / "data/locations/locations.json"),
            "sources": load_json(root / "data/sources/sources.json"),
            "matches": load_json(root / "data/matches/matches.json")}


def verify_sources(root: Path, inputs: dict) -> None:
    """Before live/cache reuse, bind deterministic input to the original pinned PDFs (local parsing only)."""
    load_pages(root)  # F03's accepted DESC provenance guard, including fresh deterministic page parsing.
    source = unique(inputs["sources"])["gpc-2025"]
    relative = "docs/Sperry-Tech-Challenge/Project Listings/Georgia Power/2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf"
    if source["local_path"] != relative or source["sha256"] != GPC_SOURCE_SHA256:
        raise ValueError("georgia_source_not_approved")
    fresh = unique(parse_gpc_pdf(root / relative))
    for p in inputs["projects"]:
        if p.get("utility") == "GPC":
            fields = ("name", "native_id", "owner_code", "in_service", "source", "utility")
            if any(p.get(k) != fresh[p["_id"]].get(k) for k in fields):
                raise ValueError("georgia_permitted_facts_changed")


def select_matches(matches: list[dict]) -> list[dict]:
    unique(matches)
    return sorted((m for m in matches if m["view"] in ("future", "historical")),
                  key=lambda m: (0 if m["view"] == "future" else 1, m["rank"], m["_id"]))[:15]


def metadata(bundle: dict, model: str) -> dict:
    return {"input_hash": bundle["input_hash"], "model": model,
            "prompt_version": PROMPT_VERSION, "schema_version": SCHEMA_VERSION}


def cached(path: Path, expected: dict, facts: list[dict]) -> tuple[dict, str] | None:
    try:
        value = load_json(path)
        if value["metadata"] != expected or hashlib.sha256(value["response"].encode()).hexdigest() != value["response_sha256"]:
            return None
        at = value["generated_at"]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", at):
            return None
        datetime.fromisoformat(at.replace("Z", "+00:00"))
        response, failures = validate_response(value["response"], facts)
        return (response, at) if not failures else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def run_batch(*, repo_root: Path = REPO_ROOT, live: bool = False, model: str | None = None,
              transport=None, sleep=time.sleep) -> dict:
    inputs = load_inputs(repo_root)
    selected = select_matches(inputs["matches"])
    projects, locations, sources = (unique(inputs[k]) for k in ("projects", "locations", "sources"))
    unique([p for p in inputs["projects"] if p.get("active") is True], "project_key")
    bundles = [(m, build_match_input(m, projects, locations, sources)) for m in selected]
    folder = repo_root / "data/briefs"
    output = folder / "briefs.json"
    existing = load_json(output) if output.exists() else []
    records = unique(existing)
    summary = {"status": "unavailable", "reason": "live_execution_deferred", "model": None,
               "prompt_version": PROMPT_VERSION, "schema_version": SCHEMA_VERSION, "calls": 0,
               "selected": len(selected), "generated": 0, "passed": 0, "rejected": 0, "cache_hits": 0,
               "preserved_records": len(existing), "failures": [],
               "selected_inputs": [{"match_id": m["_id"], "input_hash": b["input_hash"]} for m, b in bundles]}
    owned_transport = False
    if live:
        model = model or os.getenv("GEMINI_MODEL")
        if not model or not MODEL_RE.fullmatch(model) or (transport is None and not os.getenv("GEMINI_API_KEY")):
            summary["reason"] = "gemini_configuration_unavailable"
        else:
            verify_sources(repo_root, inputs)
            if transport is None:
                transport = GeminiTransport(os.environ["GEMINI_API_KEY"], model)
                owned_transport = True
            summary.update(status="ok", reason=None, model=model)
            try:
                for match, bundle in bundles:
                    meta = metadata(bundle, model)
                    key = canonical_hash(meta)
                    cache_path = folder / "cache" / f"{key}.json"
                    hit = cached(cache_path, meta, bundle["facts"])
                    failures, response = [], None
                    if hit:
                        response, at = hit
                        summary["cache_hits"] += 1
                    else:
                        at = None
                        for _regeneration in range(2):
                            raw = None
                            for attempt in range(3):
                                try:
                                    summary["calls"] += 1
                                    raw = transport.generate(bundle, failures)
                                    at = timestamp()
                                    break
                                except TransportFailure as exc:
                                    if not exc.transient or attempt == 2:
                                        summary["failures"].append({"match_id": match["_id"], "reason": exc.reason})
                                        break
                                    sleep(2 ** attempt)
                            if raw is None:
                                break
                            response, failures = validate_response(raw, bundle["facts"])
                            if not failures:
                                write_json(cache_path, {"metadata": meta, "response": raw, "generated_at": at,
                                    "response_sha256": hashlib.sha256(raw.encode()).hexdigest()})
                                break
                        if at is not None:
                            summary["generated"] += 1
                    if at is None:
                        continue
                    if response is None:
                        response = {"supported_facts": [], "possible_shared_activities": [], "questions": [], "limitations": []}
                    verdict = "rejected" if failures else "passed"
                    brief = {**response, "_id": f"brief:{key}", "match_id": match["_id"], "facts": bundle["facts"],
                             "input_hash": bundle["input_hash"], "model": model, "prompt_version": PROMPT_VERSION,
                             "schema_version": SCHEMA_VERSION,
                             "generated_at": at, "validation": verdict, "rejection_reason": ";".join(failures) or None}
                    validate(brief, "brief")
                    if records.get(brief["_id"], {}).get("validation") != "passed" or verdict == "passed":
                        records[brief["_id"]] = brief
                    summary[verdict] += 1
            finally:
                if owned_transport:
                    transport.close()
            if summary["failures"] or summary["rejected"]:
                summary["status"] = "partial"
            if records != unique(existing):
                write_json(output, [records[k] for k in sorted(records)])
    # No-call runs never overwrite existing brief evidence, even if it is stale or malformed.
    if not output.exists():
        write_json(output, [])
    write_json(folder / "summary.json", summary)
    return summary
