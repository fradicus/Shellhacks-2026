from __future__ import annotations

import hashlib
from pathlib import Path

from common.schema import validate
from extract_desc.parser import (
    DESC_2025_METADATA_CHECKED_AT,
    DESC_2025_SNAPSHOT_SHA256,
    build_outputs,
    write_outputs,
)


def _record(outputs, project_key: str, source_id: str):
    return next(
        record
        for record in outputs["projects"]
        if record["project_key"] == project_key and record["source"]["source_id"] == source_id
    )


def test_card_counts_required_records_and_version_change():
    outputs = build_outputs()
    counts = {
        source_id: sum(record["source"]["source_id"] == source_id for record in outputs["projects"])
        for source_id in ("desc-2024", "desc-2025")
    }
    assert counts == {"desc-2024": 44, "desc-2025": 47}
    assert outputs["unparsed"] == []

    old = _record(outputs, "DESC:0139 M,N", "desc-2024")
    new = _record(outputs, "DESC:0139 M,N", "desc-2025")
    assert old["in_service"]["date"] == "2024-12-31"
    assert new["in_service"]["date"] == "2026-05-31"
    assert old["active"] is False
    assert new["active"] is True
    assert any(
        change["project_key"] == "DESC:0139 M,N"
        and change["field"] == "in_service.date"
        and change["old"] == "2024-12-31"
        and change["new"] == "2026-05-31"
        for change in outputs["version_changes"]
    )

    reactor = _record(outputs, "DESC:6888", "desc-2025")
    assert reactor["name"] == "Okatie – McIntosh 115kV Tie: Add Series Reactor"
    assert reactor["in_service"]["date"] == "2028-12-31"
    assert [endpoint["name"] for endpoint in reactor["endpoints"]] == ["Okatie", "McIntosh"]
    assert reactor["voltages_kv"] == [115]

    okatie_bluffton = _record(outputs, "DESC:6808 S", "desc-2025")
    assert [endpoint["name"] for endpoint in okatie_bluffton["endpoints"]] == [
        "Okatie",
        "Bluffton",
    ]

    hooks_modoc = _record(outputs, "DESC:6809 G", "desc-2025")
    assert [endpoint["name"] for endpoint in hooks_modoc["endpoints"]] == ["Hooks", "Modoc"]
    assert hooks_modoc["voltages_kv"] == [115, 46]

    harleyville = _record(outputs, "DESC:06005 B", "desc-2025")
    assert [endpoint["name"] for endpoint in harleyville["endpoints"]] == ["Harleyville"]


def test_all_records_and_manifests_validate_and_costs_reconcile():
    outputs = build_outputs()
    for record in outputs["projects"]:
        validate(record, "project")
        if record["yearly_spend"] and all(
            value is not None for value in record["yearly_spend"].values()
        ):
            mismatch = abs(sum(record["yearly_spend"].values()) - record["cost_usd"]) > 1
            assert ("cost_consistency_mismatch" in record["quality_flags"]) is mismatch
    for source in outputs["sources"]:
        validate(source, "source")
    desc_2025 = next(source for source in outputs["sources"] if source["_id"] == "desc-2025")
    assert desc_2025["sha256"] == DESC_2025_SNAPSHOT_SHA256
    assert desc_2025["source_metadata_checked_at"] == DESC_2025_METADATA_CHECKED_AT
    for change in outputs["version_changes"]:
        validate(change, "version_change")

    malformed = _record(outputs, "DESC:06367 A - C, H", "desc-2024")
    assert malformed["yearly_spend"]["2024"] is None
    assert "cost_amount_invalid:2024" in malformed["quality_flags"]
    assert "yearly_spend_incomplete" in malformed["quality_flags"]

    narrative = _record(outputs, "DESC:6238 H", "desc-2025")
    assert narrative["cost_usd"] == 20_350_000
    assert narrative["yearly_spend"] == {}
    assert "yearly_spend_not_published" in narrative["quality_flags"]

    mismatches = {
        (record["source"]["source_id"], record["source"]["page"])
        for record in outputs["projects"]
        if "cost_consistency_mismatch" in record["quality_flags"]
    }
    assert mismatches == {
        ("desc-2024", 3),
        ("desc-2024", 26),
        ("desc-2025", 27),
        ("desc-2025", 29),
    }


def test_full_rerun_is_byte_identical(tmp_path: Path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_outputs(build_outputs(), first)
    write_outputs(build_outputs(), second)
    relative_paths = (
        Path("data/projects/desc.json"),
        Path("data/projects/desc_unparsed.json"),
        Path("data/versions/desc.json"),
        Path("data/sources/sources.json"),
    )
    for relative_path in relative_paths:
        first_bytes = (first / relative_path).read_bytes()
        second_bytes = (second / relative_path).read_bytes()
        assert hashlib.sha256(first_bytes).digest() == hashlib.sha256(second_bytes).digest()
