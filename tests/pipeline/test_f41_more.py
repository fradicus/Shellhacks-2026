"""Check the Texas second cohort against its committed source observations."""

import json
from pathlib import Path

import pytest

from texas.more import FUTURE, stage_future
from texas.project import stage

FOLDER = Path(__file__).resolve().parents[2] / "data" / "texas"


def _read(name):
    return json.loads((FOLDER / name).read_text())


def test_future_candidate_centers_and_source_reconciliation():
    future = _read("future-observations.json")
    completed = _read("completed-observations.json")
    summary = _read("more-summary.json")
    planned = _read("planned-observations.json")
    planned_summary = _read("planned-summary.json")
    source, projects = stage(planned, planned_summary, future)

    assert len(future) == summary["sheets"][FUTURE]["observations"] == 1429
    assert len(completed) == 262
    assert source["project_count"] == len(projects) == 8
    assert {item["native_id"] for item in projects} == {
        "80546B", "92629", "80546C", "85973", "109790", "109814", "110120", "110122"
    }
    assert all(item["location_review"] == "unreviewed" for item in projects)
    assert all(item["in_service"]["precision"] == "month" for item in projects)
    assert all(item["source_id"] == source["_id"] for item in projects)
    assert {item["source_sha256"] for item in future + completed} == {source["sha256"]}
    assert not any(item["candidate_location"] for item in completed)
    assert next(item for item in future if item["row"] == 555)["candidate_location"] is None
    assert next(item for item in completed if item["row"] == 35)["status_raw"] == "Planned"

    line = next(item for item in projects if item["native_id"] == "109790")
    endpoints = line["location_candidate"]["endpoints"]
    assert line["center"]["basis"] == "two"
    assert len(endpoints) == 2
    assert line["center"]["lat"] == sum(end["lat"] for end in endpoints) / 2
    assert line["center"]["lon"] == sum(end["lon"] for end in endpoints) / 2
    assert {item["center"]["basis"] for item in projects if item["native_id"] != "109790"} == {"one"}


def test_future_staging_rejects_changed_identity_and_status():
    future = _read("future-observations.json")
    source_hash = _read("more-summary.json")["source_sha256"]
    candidate = next(item for item in future if item["row"] == 940).copy()
    candidate["native_id"] = "unreviewed"
    with pytest.raises(ValueError, match="unreviewed project"):
        stage_future([candidate], source_hash)

    candidate["native_id"] = "109790"
    candidate["status_raw"] = "Conceptual"
    with pytest.raises(ValueError, match="unreviewed project"):
        stage_future([candidate], source_hash)
