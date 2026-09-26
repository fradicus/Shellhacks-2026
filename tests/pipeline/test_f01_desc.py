from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from common.names import norm_name
from common.schema import validate
from extract_desc.parser import (
    DESC_2024_SNAPSHOT_SHA256,
    DESC_2025_METADATA_CHECKED_AT,
    DESC_2025_SNAPSHOT_SHA256,
    build_outputs,
    parse_card,
    parse_desc_pdf,
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
    assert sum(record["active"] for record in outputs["projects"]) == 54
    assert len(outputs["version_changes"]) == 58
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
    desc_2024 = next(source for source in outputs["sources"] if source["_id"] == "desc-2024")
    assert desc_2024["sha256"] == DESC_2024_SNAPSHOT_SHA256
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


def test_reviewed_endpoint_scope_rows_and_valid_counterexamples():
    outputs = build_outputs()
    multi_asset = {
        ("desc-2025", 2, "DESC:0139 M,N"): ["Okatie", "Jasper", "Yemassee"],
        ("desc-2025", 6, "DESC:6808 N,O"): ["VCS1", "Denny Terrace", "Pineland"],
        ("desc-2025", 13, "DESC:1060A, I, L"): [
            "Williams St Sub",
            "AM Williams Sub",
            "McMeekin Sub",
        ],
        ("desc-2024", 39, "DESC:6847 A-B, D-H"): [
            "Church Creek",
            "Faber Place",
            "Charleston Transmission",
        ],
        ("desc-2025", 33, "DESC:6847"): [
            "Church Creek",
            "Faber Place",
            "Charleston Transmission",
        ],
        ("desc-2025", 38, "DESC:6810 T"): [
            "Cameron Jct",
            "Cameron",
            "St Matthews",
        ],
    }
    scope_ambiguous = {
        ("desc-2024", 1, "DESC:6807 B"): [
            "Queensboro",
            "Ft Johnson",
            "Bayfront",
            "James Island",
        ],
        ("desc-2024", 14, "DESC:6809 E"): [
            "Stevens Creek",
            "Hooks",
            "LR Plumb Branch",
        ],
        ("desc-2025", 4, "DESC:6808 K"): [
            "Burton",
            "St Helena",
            "Frogmore Transmission",
        ],
        ("desc-2025", 5, "DESC:6808 L"): [
            "Burton",
            "St Helena",
            "Frogmore Distribution Tap",
        ],
        ("desc-2025", 10, "DESC:6808 V"): [
            "Faber Place",
            "Bayfront",
            "North Bridge Terrace",
        ],
        ("desc-2025", 24, "DESC:6809 M"): [
            "St George",
            "Sumter",
            "Santee Substation",
            "Duke/Progress Energy Tie",
        ],
        ("desc-2025", 43, "DESC:6877 A"): [
            "Church Creek",
            "Dawson",
            "Long Savannah",
            "Faber Place",
        ],
        ("desc-2025", 22, "DESC:06810 G"): [
            "Goose Creek Reservoir",
            "Williams",
            "Goose Creek",
            "Faber Place",
        ],
        ("desc-2025", 23, "DESC:06810 H"): ["Summerville 115kV Loop"],
    }
    expected = {**multi_asset, **scope_ambiguous}
    flagged = {
        (
            record["source"]["source_id"],
            record["source"]["page"],
            record["project_key"],
        ): record
        for record in outputs["projects"]
        if "endpoint_ambiguous" in record["quality_flags"]
    }
    assert set(flagged) == set(expected)
    for key, candidate_names in expected.items():
        record = flagged[key]
        assert record["endpoints"] == []
        assert [candidate["name"] for candidate in record["endpoint_candidates"]] == candidate_names
        combined_source = f"{record['name']}\n{record['description']}"
        for candidate in record["endpoint_candidates"]:
            assert candidate["norm"] == norm_name(candidate["name"])
            assert candidate["raw"] in combined_source
        class_flag = (
            "endpoint_multi_asset" if key in multi_asset else "endpoint_scope_ambiguous"
        )
        assert class_flag in record["quality_flags"]

    counterexamples = {
        ("DESC:6341 A-F", "desc-2025"): ["Cainhoy", "Hamlin"],
        ("DESC:6359", "desc-2025"): ["Yemassee", "Ritter"],
        ("DESC:6870 A", "desc-2025"): ["Saluda Hydro", "Bush River"],
        ("DESC:6805 G", "desc-2025"): ["Edenwood Sub"],
    }
    for (project_key, source_id), endpoint_names in counterexamples.items():
        record = _record(outputs, project_key, source_id)
        assert [endpoint["name"] for endpoint in record["endpoints"]] == endpoint_names
        assert "endpoint_ambiguous" not in record["quality_flags"]
        assert "endpoint_candidates" not in record


def test_reviewed_endpoint_override_rejects_wrong_project_key_and_source_bytes(tmp_path: Path):
    outputs = build_outputs()
    reviewed = _record(outputs, "DESC:6807 B", "desc-2024")
    tampered = reviewed["raw_text"].replace(
        "Project ID\n6807 B\n", "Project ID\n6807 C\n", 1
    )
    assert tampered != reviewed["raw_text"]
    with pytest.raises(ValueError, match="reviewed endpoint override key mismatch"):
        parse_card(tampered, "desc-2024", 1, 44)

    changed_pdf = tmp_path / "desc-2024-changed.pdf"
    changed_pdf.write_bytes(b"changed source bytes")
    with pytest.raises(ValueError, match="source SHA-256 changed"):
        parse_desc_pdf(changed_pdf, "desc-2024", 44)


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
