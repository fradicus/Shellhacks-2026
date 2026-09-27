"""Exercise F30 assembly boundaries; F38 separately validates release evidence."""

import json
import shutil
import sys
from copy import deepcopy
from types import ModuleType

import pytest
from common import REPO_ROOT
from national.build import OUTPUTS, load_snapshot, validate_snapshot_values
from national.load import stage


@pytest.fixture
def base_root(tmp_path):
    target = tmp_path / "data" / "national"
    target.mkdir(parents=True)
    for name in OUTPUTS:
        shutil.copyfile(REPO_ROOT / "data" / "national" / f"{name}.json", target / f"{name}.json")
    return tmp_path


def release_hook(monkeypatch, root, hook):
    # Synthetic producer output tests assembly, without approving synthetic geography.
    path = root / "data" / "expansion" / "releases" / "active.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}")
    module = ModuleType("expansion.publish")
    module.apply_release = hook
    monkeypatch.setitem(sys.modules, "expansion.publish", module)


def test_missing_active_release_ignores_candidate_files(base_root):
    expected = {name: json.loads((base_root / "data" / "national" / f"{name}.json").read_text()) for name in OUTPUTS}
    candidates = base_root / "data" / "expansion" / "candidates"
    candidates.mkdir(parents=True)
    (candidates / "active.json").write_text("malformed candidate; never an activation input")
    assert load_snapshot(base_root) == expected


def test_assembly_recounts_locations_preserves_summary_and_base_files(base_root, monkeypatch):
    before = {path: path.read_bytes() for path in (base_root / "data" / "national").iterdir()}
    baseline = load_snapshot(base_root)

    def apply(snapshot, root):
        assert root == base_root and validate_snapshot_values(snapshot) == []
        snapshot = deepcopy(snapshot)
        project = snapshot["projects"][0]
        assert project["center"] is None
        project["center"] = {"lat": 42, "lon": -72, "basis": "one", "evidence": "synthetic assembly fixture"}
        project["location_review"] = "confirmed"
        snapshot["coverage"]["expansion"] = {"release_id": "synthetic-test", "confirmed_projects": 1}
        snapshot["coverage"]["failures"] = [{"source_id": "synthetic", "message": "preserved report"}]
        return snapshot

    release_hook(monkeypatch, base_root, apply)
    first = load_snapshot(base_root)
    assert load_snapshot(base_root) == first
    assert len(first["projects"]) == len(baseline["projects"]) == 1_286
    assert [p["_id"] for p in first["projects"]] == [p["_id"] for p in baseline["projects"]]
    assert first["coverage"]["located_count"] == baseline["coverage"]["located_count"] + 1
    iso = next(row for row in first["coverage"]["sources"] if row["source_id"] == "iso-ne-rsp-2026-06")
    assert iso["located_count"] == 1
    assert first["coverage"]["expansion"] == {"release_id": "synthetic-test", "confirmed_projects": 1}
    assert first["coverage"]["failures"] == [{"source_id": "synthetic", "message": "preserved report"}]
    assert "independently reviewed" in first["coverage"]["notes"][1]
    assert validate_snapshot_values(first) == []
    assert before == {path: path.read_bytes() for path in before}
    for original, projected in zip(baseline["projects"], first["projects"], strict=True):
        assert {k: v for k, v in original.items() if k not in {"center", "location_review"}} == {
            k: v for k, v in projected.items() if k not in {"center", "location_review"}
        }


def test_invalid_base_fails_before_release_hook(base_root, monkeypatch):
    def forbidden(*args):
        pytest.fail("release hook must not receive an invalid base")

    release_hook(monkeypatch, base_root, forbidden)
    path = base_root / "data" / "national" / "coverage.json"
    coverage = json.loads(path.read_text())
    coverage["projects_total"] += 1
    path.write_text(json.dumps(coverage))
    with pytest.raises(ValueError, match="national snapshot validation failed"):
        load_snapshot(base_root)


@pytest.mark.parametrize("failure", ["release", "assembled"])
def test_invalid_release_or_assembled_snapshot_fails_closed(base_root, monkeypatch, failure):
    def apply(snapshot, root):
        if failure == "release":
            raise ValueError("synthetic invalid release")
        snapshot["projects"][0]["states"] = ["99"]
        return snapshot

    release_hook(monkeypatch, base_root, apply)
    with pytest.raises(ValueError, match="invalid release|assembled national snapshot validation failed"):
        load_snapshot(base_root)


def test_stage_carries_location_evidence_in_same_dataset():
    project = {"_id": "synthetic", "center": None, "location_verification": {"reviews": ["synthetic"]}}
    staged = stage({"sources": [], "projects": [project]}, "candidate")["national_projects"][0]
    assert staged["location_verification"] == project["location_verification"]
    assert staged["dataset"] == "candidate"
    assert project["_id"] == "synthetic" and "dataset" not in project
