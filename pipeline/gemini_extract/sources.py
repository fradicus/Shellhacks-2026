"""Fail-closed source boundary. There is deliberately no arbitrary document input."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import pdfplumber

from common import REPO_ROOT, load_json
from extract_desc.parser import parse_card

# Both paths and bytes were approved in F01. A manifest edit alone cannot authorize an upload.
APPROVED = {
    "desc-2024": (
        "docs/Sperry-Tech-Challenge/Project Listings/Dominion Energy/"
        "2024-2028-2million-and-above-project-descriptions.pdf",
        "890876d0faefd40576a0b5e598a804b54b4d8d2d56dd96fb7e40d5a406db0f46",
        44,
    ),
    "desc-2025": (
        "data/sources/desc-2025.pdf",
        "265453ccf14b4f95054fed304b7999270a478dbefc3a812163395b31422e74e0",
        47,
    ),
}
CORPUS_PAGES = sum(entry[2] for entry in APPROVED.values())
FIELD_NAMES = (
    "project_id", "name", "description", "need", "status", "in_service_raw",
    "total_cost", "yearly_spend", "endpoints", "voltage_kv",
)


class SourceError(ValueError):
    """Only a fixed reason code is ever exposed to logs or artifacts."""


@dataclass(frozen=True)
class Page:
    source_id: str
    source_sha256: str
    number: int
    text: str
    expected: dict[str, Any]
    quality_flags: tuple[str, ...] = ()

    @property
    def text_sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


def expected_fields(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": record["native_id"],
        "name": record["name"],
        "description": record["description"],
        "need": record["need"],
        "status": record["status"],
        "in_service_raw": record["in_service"]["raw"],
        "total_cost": record["cost_usd"],
        "yearly_spend": record["yearly_spend"],
        "endpoints": [endpoint["name"] for endpoint in record["endpoints"]],
        "voltage_kv": record["voltages_kv"],
    }


def assert_approved(page: Page) -> None:
    allowed = APPROVED.get(page.source_id)
    if not allowed or page.source_sha256 != allowed[1]:
        raise SourceError("source_not_approved")
    if type(page.number) is not int or not 1 <= page.number <= allowed[2]:
        raise SourceError("page_not_approved")


def verify_for_transport(page: Page) -> None:
    """Rebind text to approved bytes at the actual network boundary, even for direct callers."""
    assert_approved(page)
    relative, sha256, count = APPROVED[page.source_id]
    path = (REPO_ROOT / relative).resolve()
    if not path.is_relative_to(REPO_ROOT.resolve()):
        raise SourceError("source_hash_or_path_mismatch")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise SourceError("source_hash_or_path_mismatch")
    with pdfplumber.open(BytesIO(raw)) as pdf:
        if len(pdf.pages) != count:
            raise SourceError("source_page_count_mismatch")
        fresh = parse_card(pdf.pages[page.number - 1].extract_text() or "", page.source_id, page.number, count)
    if (page.text != fresh["raw_text"] or page.expected != expected_fields(fresh)
            or page.quality_flags != tuple(fresh["quality_flags"])):
        raise SourceError("page_text_not_approved")


def load_pages(root: Path = REPO_ROOT) -> list[Page]:
    """Hash every PDF before extracting any page; verify F01 against freshly parsed text."""
    manifests = load_json(root / "data/sources/sources.json")
    records = load_json(root / "data/projects/desc.json")
    if not isinstance(manifests, list) or not isinstance(records, list):
        raise SourceError("invalid_source_inputs")
    indexed = {}
    for record in records:
        source = record.get("source", {})
        key = (source.get("source_id"), source.get("page"))
        if key in indexed or record.get("utility") != "DESC" or key[0] not in APPROVED:
            raise SourceError("invalid_deterministic_corpus")
        indexed[key] = record
    if len(indexed) != CORPUS_PAGES:
        raise SourceError("incomplete_deterministic_corpus")

    paths = {}
    for source_id, (relative, sha256, _) in APPROVED.items():
        found = [source for source in manifests if source.get("_id") == source_id]
        if len(found) != 1:
            raise SourceError("source_manifest_missing_or_duplicate")
        manifest = found[0]
        if (manifest.get("public_status"), manifest.get("local_path"), manifest.get("sha256")) != (
            "public", relative, sha256
        ):
            raise SourceError("source_manifest_not_approved")
        path = (root / relative).resolve()
        raw = path.read_bytes()
        if not path.is_relative_to(root.resolve()) or hashlib.sha256(raw).hexdigest() != sha256:
            raise SourceError("source_hash_or_path_mismatch")
        paths[source_id] = raw

    pages = []
    for source_id, raw in paths.items():
        _, sha256, count = APPROVED[source_id]
        with pdfplumber.open(BytesIO(raw)) as pdf:
            if len(pdf.pages) != count:
                raise SourceError("source_page_count_mismatch")
            for number, pdf_page in enumerate(pdf.pages, 1):
                fresh = parse_card(pdf_page.extract_text() or "", source_id, number, count)
                stored = indexed.get((source_id, number))
                if (not stored or stored.get("raw_text") != fresh["raw_text"]
                        or expected_fields(stored) != expected_fields(fresh)):
                    raise SourceError("deterministic_source_mismatch")
                page = Page(
                    source_id, sha256, number, fresh["raw_text"], expected_fields(stored), tuple(fresh["quality_flags"])
                )
                assert_approved(page)
                pages.append(page)
    return pages
