"""Exercise the fixed Texas release gate, including semantic tampering."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from shutil import copy2

import pytest

from texas.publish import FILES, apply_release

ROOT = Path(__file__).resolve().parents[2]


def _copy_release(tmp_path):
    folder = tmp_path / "data" / "texas"
    (folder / "releases").mkdir(parents=True)
    for name in FILES.values():
        copy2(ROOT / "data" / "texas" / name, folder / name)
    copy2(ROOT / "data" / "texas" / "releases" / "active.json", folder / "releases" / "active.json")
    return folder


def _rewrite(folder, key, mutate):
    path = folder / FILES[key]
    value = json.loads(path.read_text())
    mutate(value)
    path.write_text(json.dumps(value, indent=2) + "\n")
    release_path = folder / "releases" / "active.json"
    release = json.loads(release_path.read_text())
    release["files"][key] = hashlib.sha256(path.read_bytes()).hexdigest()
    release_path.write_text(json.dumps(release, indent=2) + "\n")


def test_release_adds_eight_unreviewed_candidates_without_mutating_base():
    base = {"sources": [], "projects": [], "coverage": {}}
    original = deepcopy(base)
    result = apply_release(base, ROOT)
    assert base == original
    assert len(result["sources"]) == 1
    assert len(result["projects"]) == 8
    assert len({(p["center"]["lat"], p["center"]["lon"]) for p in result["projects"]}) == 5
    assert {p["location_review"] for p in result["projects"]} == {"unreviewed"}
    assert result["coverage"]["texas"]["complete_endpoint_projects"] == 1
    assert result["coverage"]["texas"]["partial_endpoint_projects"] == 7


def test_release_fails_closed_for_changed_file_hash_and_existing_identity(tmp_path):
    folder = _copy_release(tmp_path)
    with (folder / "publication-source.json").open("a") as stream:
        stream.write(" ")
    with pytest.raises(ValueError, match="file hash changed"):
        apply_release({"sources": [], "projects": [], "coverage": {}}, tmp_path)
    existing = {"sources": [{"_id": "ercot-tpit-2026-07"}], "projects": [], "coverage": {}}
    with pytest.raises(ValueError, match="active identity"):
        apply_release(existing, ROOT)


@pytest.mark.parametrize("mutation,error", [
    (lambda projects: projects[0]["center"].update(lat=30.1), "candidate center changed"),
    (lambda projects: projects[0]["evidence"].update(row=941), "source row or hash changed"),
    (lambda projects: projects[0].update(location_review="confirmed"), "candidate identity/status changed"),
])
def test_release_rejects_semantic_changes_even_with_updated_file_hash(tmp_path, mutation, error):
    folder = _copy_release(tmp_path)
    _rewrite(folder, "projects", mutation)
    with pytest.raises(ValueError, match=error):
        apply_release({"sources": [], "projects": [], "coverage": {}}, tmp_path)


def test_release_requires_observed_retrieval_time(tmp_path):
    folder = _copy_release(tmp_path)
    release_path = folder / "releases" / "active.json"
    release = json.loads(release_path.read_text())
    release["workbook_retrieved_at"] = None
    release_path.write_text(json.dumps(release, indent=2) + "\n")
    with pytest.raises(ValueError, match="retrieval time"):
        apply_release({"sources": [], "projects": [], "coverage": {}}, tmp_path)


def test_release_rejects_changed_facility_coordinates_with_updated_hash(tmp_path):
    folder = _copy_release(tmp_path)
    def move_gabriel(ledger):
        next(item for item in ledger["facilities"] if item["name"] == "GABRIEL")["lat"] += 0.01

    _rewrite(folder, "facilities", move_gabriel)
    with pytest.raises(ValueError, match="candidate terminal or Texas coordinates changed"):
        apply_release({"sources": [], "projects": [], "coverage": {}}, tmp_path)
