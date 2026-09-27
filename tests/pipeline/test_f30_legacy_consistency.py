"""State filtering must not resurrect rejected locations or infer utility footprints."""

import json
from copy import deepcopy

import pytest
from common import REPO_ROOT
from locations.boundaries import StateBoundaries
from national import legacy
from national.build import OUTPUTS, _coverage, rebuild_legacy, validate_snapshot_values


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    source = {"_id": "synthetic", "sha256": "a" * 64}
    project = {"_id": "GPC:1@synthetic", "project_key": "GPC:1", "native_id": "1", "active": True,
               "name": "Synthetic cross-border line", "utility": "unknown", "owner_code": None,
               "source": {"source_id": "synthetic", "page": 1},
               "in_service": {"date": None, "raw": None, "precision": "unknown"}}
    endpoints = [{"_id": name, "project_key": "GPC:1", "project_id": project["_id"],
                  "endpoint_index": i, "name": name, "confidence": "low", "lat": 1, "lon": lon,
                  "evidence": "Synthetic fixture"} for i, (name, lon) in enumerate((("a", 1), ("b", 3)))]
    records = {"projects": [project], "locations": endpoints, "reviews": [], "sources": [source]}
    monkeypatch.setattr(legacy, "collect", lambda _: (records, [], []))
    decisions = {}
    monkeypatch.setattr(legacy, "decide", lambda *_: decisions)
    source_path = tmp_path / "data/sources/sources.json"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(json.dumps([source]))
    # Deliberately synthetic rectangles, never used as production geography.
    geometries = {name: {"type": "Polygon", "coordinates": [[[x, 0], [x + 2, 0], [x + 2, 2],
                                                                [x, 2], [x, 0]]]}
                  for name, x in (("GA", 0), ("SC", 2))}
    boundaries = StateBoundaries(geometries, {"query_url": "https://example.test/synthetic",
                                "raw_geojson_sha256": "b" * 64, "source_vintage": "synthetic"})
    monkeypatch.setattr(legacy.StateBoundaries, "load", lambda _: boundaries)
    return tmp_path, records, decisions


def test_states_follow_each_eligible_endpoint_not_center_or_owner(inputs):
    root, _, _ = inputs
    project = legacy.normalize(root)[0]
    assert project["states"] == ["13", "45"]
    assert project["center"]["lon"] == 2
    assert project["location_review"] == "needs_review"
    assert project["evidence"]["raw"]["state_assignment"]["endpoints"] == [
        {"endpoint_id": "a", "state_fips": "13"}, {"endpoint_id": "b", "state_fips": "45"},
    ]


def test_rejection_removes_endpoint_from_center_and_state_but_preserves_reason(inputs):
    root, _, decisions = inputs
    decisions[("endpoint", "b")] = "rejected"
    project = legacy.normalize(root)[0]
    assert project["states"] == ["13"] and project["center"]["lon"] == 1
    assert project["evidence"]["raw"]["endpoint_reviews"]["b"] == "rejected"
    decisions[("endpoint", "a")] = "rejected"
    project = legacy.normalize(root)[0]
    assert project["states"] == [] and project["center"] is None
    assert project["location_review"] == "rejected"


def test_outside_or_missing_geometry_never_falls_back_to_utility_state(inputs):
    root, records, _ = inputs
    records["projects"][0]["utility"] = "GPC"
    for endpoint in records["locations"]:
        endpoint["lon"] = 10
    assert legacy.normalize(root)[0]["states"] == []
    records["locations"] = []
    project = legacy.normalize(root)[0]
    assert project["states"] == [] and project["center"] is None


def test_location_counts_separate_coordinates_county_references_and_rejections():
    def project(review, center=None, anchors=None):
        return {"source_id": "synthetic", "status_group": "unknown", "states": [], "counties": [],
                "location_review": review, "center": center,
                "approximate_location": {"anchors": anchors or []}}
    rows = [project("confirmed", {"lat": 1, "lon": 1}), project("needs_review", {"lat": 2, "lon": 2}),
            project("unreviewed", {"lat": 3, "lon": 3}), project("unlocated", anchors=[{"lat": 4, "lon": 4}]),
            project("unlocated"), project("rejected")]
    coverage = _coverage(rows, {"synthetic"})
    assert coverage["located_count"] == 3
    assert coverage["location_counts"] == {"confirmed_centers": 1, "candidate_centers": 2,
                                            "approximate_only": 1, "no_display_location": 2,
                                            "rejected_projects": 1}


def test_rebuild_only_legacy_is_replayable_and_fails_before_writing(tmp_path, monkeypatch):
    folder = tmp_path / "data/national"
    folder.mkdir(parents=True)
    for name in OUTPUTS:
        (folder / f"{name}.json").write_bytes((REPO_ROOT / "data/national" / f"{name}.json").read_bytes())
    before = json.loads((folder / "projects.json").read_text())
    rows = [deepcopy(p) for p in before if p["_id"].startswith("legacy:")]
    monkeypatch.setattr("national.build.normalize_legacy", lambda _: rows)
    result = rebuild_legacy(tmp_path)
    assert validate_snapshot_values(result) == []
    assert [p for p in result["projects"] if not p["_id"].startswith("legacy:")] == [
        p for p in before if not p["_id"].startswith("legacy:")]
    written = {p.name: p.read_bytes() for p in folder.iterdir()}
    rebuild_legacy(tmp_path)
    assert written == {p.name: p.read_bytes() for p in folder.iterdir()}
    rows[0]["states"] = ["99"]
    with pytest.raises(ValueError, match="unknown states"):
        rebuild_legacy(tmp_path)
    assert written == {p.name: p.read_bytes() for p in folder.iterdir()}


def test_committed_legacy_projection_keeps_all_ten_rejections():
    rows = json.loads((REPO_ROOT / "data/national/projects.json").read_text())
    legacy_rows = [p for p in rows if p["_id"].startswith("legacy:")]
    assert sum(p["center"] is not None for p in legacy_rows) == 69
    rejected = [p for p in legacy_rows if p["location_review"] == "rejected"]
    assert len(rejected) == 10
    assert all(p["center"] is None and p["states"] == [] for p in rejected)
    assert all(p["states"] for p in legacy_rows if p["center"] is not None)
