from __future__ import annotations

import hashlib
import json
from pathlib import Path

from common.schema import validate
from extract_gpc.parser import build_outputs, write_outputs


def _record(outputs, native_id: str):
    return next(record for record in outputs["projects"] if record["native_id"] == native_id)


def test_required_rows_dates_and_endpoints():
    outputs = build_outputs()

    mcintosh = _record(outputs, "20277")
    assert mcintosh["name"] == "SAV: MCINTOSH - PURRYSBURG 230KV REACTORS"
    assert mcintosh["in_service"] == {
        "raw": "6/1/2026",
        "date": "2026-06-01",
        "precision": "day",
    }
    assert mcintosh["owner_code"] == "SAV"
    assert mcintosh["utility"] == "GPC"
    assert mcintosh["source"]["page"] == 180
    assert [endpoint["name"] for endpoint in mcintosh["endpoints"]] == [
        "MCINTOSH",
        "PURRYSBURG",
    ]

    jesup = _record(outputs, "11821")
    assert jesup["name"] == "JESUP - LUDOWICI PRIMARY 115KV REBUILD"
    assert jesup["in_service"]["date"] == "2025-06-01"
    assert jesup["source"]["page"] == 177

    evans = [
        record for record in outputs["projects"] if "EVANS PRIMARY - THURMOND DAM" in record["name"]
    ]
    assert {record["native_id"] for record in evans} == {"20793", "20794"}
    assert {record["in_service"]["date"] for record in evans} == {"2033-06-01"}
    assert [endpoint["name"] for endpoint in evans[0]["endpoints"]] == [
        "EVANS PRIMARY",
        "THURMOND DAM",
    ]
    assert evans[0]["endpoints"][1]["qualifier"] == "USA"


def test_full_current_plan_coverage_owners_and_schema():
    outputs = build_outputs()
    projects = outputs["projects"]
    assert len(projects) == 208
    assert len({project["_id"] for project in projects}) == 208
    assert len({project["native_id"] for project in projects}) == 208
    assert len({project["project_key"] for project in projects}) == 208
    assert outputs["summary"]["denominator_rows"] == 208
    assert outputs["summary"]["duplicate_native_ids"] == []
    assert outputs["summary"]["duplicate_project_keys"] == []
    assert outputs["summary"]["rows_per_zone"]["215"] == 13
    assert outputs["summary"]["rows_per_zone"]["219"] == 16
    assert outputs["summary"]["rows_per_owner_code"] == {
        "DU": 2,
        "GPC": 122,
        "GTC": 54,
        "MEAG": 14,
        "SAV": 16,
    }
    assert outputs["summary"]["ambiguous_rows"] == 0

    border_done = False
    for project in projects:
        validate(project, "project")
        assert project["cost_usd"] is None
        assert "raw_text" not in project
        if project["zone"] not in {215, 219}:
            border_done = True
        if border_done:
            assert project["zone"] not in {215, 219}
    assert "REDACTED" not in json.dumps(projects)

    owners = {record["code"]: record for record in outputs["owners"]}
    assert owners["GPC"]["utility"] == "GPC"
    assert owners["GPC"]["citation"]["url"].startswith("https://www.georgiapower.com/")
    assert owners["SAV"]["utility"] == "GPC"
    assert owners["SAV"]["citation"]["url"].startswith("https://www.sec.gov/")
    assert {code for code, owner in owners.items() if owner["utility"] == "unknown"} == {
        "DU",
        "GTC",
        "MEAG",
    }


def test_full_rerun_is_byte_identical(tmp_path: Path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_outputs(build_outputs(), first)
    write_outputs(build_outputs(), second)
    for relative_path in (
        Path("data/projects/gpc.json"),
        Path("data/projects/gpc_summary.json"),
        Path("data/owners/owners.json"),
    ):
        first_bytes = (first / relative_path).read_bytes()
        second_bytes = (second / relative_path).read_bytes()
        assert hashlib.sha256(first_bytes).digest() == hashlib.sha256(second_bytes).digest()
