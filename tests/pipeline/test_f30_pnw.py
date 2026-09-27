"""FIX-F30: the fixed Pacific Northwest release (C33) joins the national snapshot through load_snapshot."""

from common import REPO_ROOT, load_json
from national.build import load_snapshot, validate_snapshot_values


def test_load_snapshot_appends_the_pacific_northwest_release():
    snapshot = load_snapshot(REPO_ROOT)
    assert validate_snapshot_values(snapshot) == []
    release = load_json(REPO_ROOT / "data" / "pnw" / "releases" / "active.json")
    coverage = snapshot["coverage"]["pacific_northwest"]
    assert coverage["release_id"] == release["release_id"]
    assert coverage["projects"] == release["expected_counts"]["projects"]
    assert coverage["independently_confirmed_projects"] == 0
    released = {p["_id"] for p in load_json(REPO_ROOT / "data" / "pnw" / "projects.json")}
    added = [p for p in snapshot["projects"] if p["_id"] in released]
    assert len(added) == len(released)
    assert all(p["location_review"] in {"unreviewed", "unlocated"} for p in added)
