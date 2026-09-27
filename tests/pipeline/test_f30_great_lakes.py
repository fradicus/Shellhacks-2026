"""FIX-F30: the fixed Great Lakes release (C26) joins the national snapshot through load_snapshot."""

from common import REPO_ROOT, load_json
from national.build import load_snapshot, validate_snapshot_values


def test_load_snapshot_appends_the_great_lakes_release():
    snapshot = load_snapshot(REPO_ROOT)
    assert validate_snapshot_values(snapshot) == []
    release = load_json(REPO_ROOT / "data" / "greatlakes" / "releases" / "active.json")
    coverage = snapshot["coverage"]["great_lakes"]
    assert coverage["release_id"] == release["release_id"]
    assert coverage["projects"] == release["expected_counts"]["projects"]
    assert coverage["independently_confirmed_projects"] == 0
    released = {p["_id"] for p in load_json(REPO_ROOT / "data" / "greatlakes" / "projects.json")}
    added = [p for p in snapshot["projects"] if p["_id"] in released]
    assert len(added) == len(released)
    assert all(p["location_review"] in {"unreviewed", "unlocated"} for p in added)
    assert snapshot["coverage"]["located_count"] == sum(p["center"] is not None for p in snapshot["projects"])
