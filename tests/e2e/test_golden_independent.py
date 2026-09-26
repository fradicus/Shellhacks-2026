"""Prove the auditor rejects plausible corruptions, not just the passing workbook."""

import copy
import json
import subprocess
import sys
from pathlib import Path

import golden_independent as verifier
import pytest


@pytest.fixture
def inputs():
    source, sheet, projects, centers, pairs = verifier.reference()
    result = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("core_snapshot.py"))],
        input=json.dumps(projects), text=True, capture_output=True, check=True,
    )
    fixtures = json.loads((verifier.ROOT / "data/fixtures/golden/projects.json").read_text())
    return [source, sheet, projects, centers, pairs, json.loads(result.stdout), fixtures]


def test_real_workbook_agrees(inputs):
    assert verifier.audit(*inputs)[0] == []


@pytest.mark.parametrize("fault", ["distance", "gap", "missing_pair", "rank", "center", "fixture_date", "sheet_distance"])
def test_rejects_corrupted_results(inputs, fault):
    values = copy.deepcopy(inputs)
    core = values[5]
    if fault == "distance":
        core["matches"][0]["distance_mi"] += 0.001  # Still rounds to the same two-decimal value.
    elif fault == "gap":
        core["matches"][0]["time_gap_days"] += 1
    elif fault == "missing_pair":
        core["matches"].pop()
    elif fault == "rank":
        core["matches"].reverse()
    elif fault == "center":
        core["centers"]["DESC:DESC_1"]["lat"] += 0.01
    elif fault == "fixture_date":
        values[6][0]["in_service_date"] = "2024-01-01"
    elif fault == "sheet_distance":
        values[1][0]["distance_mi"] += 1
    assert verifier.audit(*values)[0], fault


def test_reports_tiny_differences(inputs):
    core = inputs[5]
    core["matches"][0]["distance_mi"] += 1e-12
    errors, notes, _, _ = verifier.audit(*inputs)
    assert errors == []
    assert any("core distance" in note for note in notes)
