"""F39/C40: the dense Southeast release applies only unreviewed, labeled, source-bound batches."""

import json
import shutil

import pytest

from common import REPO_ROOT, load_json
from national.build import OUTPUTS, _coverage, validate_snapshot_values
from southeast import dense
from southeast.aep import legend_status, skip_reason


def base_snapshot():
    return {name: load_json(REPO_ROOT / "data" / "national" / f"{name}.json") for name in OUTPUTS}


def applied():
    snapshot = dense.apply_release(base_snapshot(), REPO_ROOT)
    imported = {s["_id"] for s in snapshot["sources"] if s["import_status"] == "imported"}
    snapshot["coverage"].update(_coverage(snapshot["projects"], imported))
    return snapshot


def test_committed_release_appends_unreviewed_southeast_points():
    snapshot = applied()
    assert validate_snapshot_values(snapshot) == []
    release = load_json(REPO_ROOT / dense.ACTIVE)
    ids = {p["_id"] for batch in release["batches"]
           for p in load_json(REPO_ROOT / dense.FOLDER / batch / "projects.json")}
    added = [p for p in snapshot["projects"] if p["_id"] in ids]
    assert len(added) == sum(b["expected_counts"]["projects"] for b in release["batches"].values())
    for project in added:
        if project["center"]:
            assert project["location_review"] == "unreviewed"
            assert project["location_candidate"]["tier"] in dense.TIERS
            assert project["location_candidate"]["independent_review"] is False
        else:
            assert project["location_review"] == "unlocated"


def test_missing_release_is_a_no_op(tmp_path):
    snapshot = base_snapshot()
    assert dense.apply_release(snapshot, tmp_path) is snapshot


def copy_release(tmp_path, batch="aep"):
    for rel in (dense.ACTIVE, dense.FOLDER / batch / "projects.json", dense.FOLDER / batch / "sources.json"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO_ROOT / rel, tmp_path / rel)
    return tmp_path / dense.FOLDER / batch / "projects.json"


def rewrite(path, change):
    projects = load_json(path)
    change(projects)
    path.write_text(json.dumps(projects, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    release = load_json(path.parents[1] / "releases" / "active.json")
    release["batches"][path.parent.name]["files"]["projects"] = dense.sha(projects)
    (path.parents[1] / "releases" / "active.json").write_text(json.dumps(release, indent=2, sort_keys=True) + "\n")


def test_edited_batch_fails_its_pinned_hash(tmp_path):
    path = copy_release(tmp_path)
    path.write_text(path.read_text().replace("AEP Transmission", "AEP Transmissions", 1))
    with pytest.raises(ValueError, match="hash changed"):
        dense.apply_release(base_snapshot(), tmp_path)


def test_confirmed_or_moved_points_are_rejected(tmp_path):
    path = copy_release(tmp_path)
    located = next(i for i, p in enumerate(load_json(path)) if p["center"])

    def confirm(projects):
        projects[located]["location_review"] = "confirmed"

    rewrite(path, confirm)
    with pytest.raises(ValueError, match="unreviewed"):
        dense.apply_release(base_snapshot(), tmp_path)

    path = copy_release(tmp_path)

    def move(projects):
        projects[located]["center"]["lat"] += 0.5

    rewrite(path, move)
    with pytest.raises(ValueError, match="source point|outside"):
        dense.apply_release(base_snapshot(), tmp_path)


def test_existing_identity_cannot_be_reused(tmp_path):
    copy_release(tmp_path)
    snapshot = base_snapshot()
    snapshot["projects"].append(dict(load_json(tmp_path / dense.FOLDER / "aep" / "projects.json")[0]))
    with pytest.raises(ValueError, match="identity"):
        dense.apply_release(snapshot, tmp_path)


def test_aep_map_labels_and_placeholders():
    assert legend_status("Projects Pending Approval") == "proposed"
    assert legend_status("Approved Projects") == legend_status("Current Projects") == "planned"
    assert legend_status(None) == "unknown"
    assert skip_reason({"name": "Projects Overview"}, {"center": {"lat": 37.0}})
    assert skip_reason({"name": "No Active Projects"}, {"center": {"lat": -55.1}})
    assert skip_reason({"name": "Belfry Area Improvements"}, {"center": {"lat": 37.6}}) is None


def test_duke_schedule_reads_one_stated_date_only():
    from southeast.duke import schedule, states_of

    assert schedule("Expected Completion : 2026 Project Map")["value"] == "2026"
    got = schedule("In-service Date: November 2023* *Dates are subject to change")
    assert (got["kind"], got["value"], got["precision"]) == ("planned_milestone", "2023-11", "month")
    assert schedule("This project was completed in March 2023.")["kind"] == "completion"
    # Phases stating different years leave the project date unknown rather than picking one.
    assert schedule("Project Completion and Restoration: Fall 2025 ... Project Completion and Restoration: "
                    "Fall 2026") is None
    assert schedule("Construction starts in 2025.") is None
    assert states_of("OH/KY") == ["21", "39"] and states_of("TX") == []
