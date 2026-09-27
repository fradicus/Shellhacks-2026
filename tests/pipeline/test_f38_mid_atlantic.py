"""Synthetic releases exercise activation boundaries without claiming public evidence."""
from copy import deepcopy

import pytest
from common import write_json
from expansion.mid_atlantic import (
    ACTIVE_RELEASE,
    WEB_MERCATOR_TRANSFORM,
    WORLD_MERCATOR_TRANSFORM,
    apply_release,
    check_point,
    release_hash,
    world_mercator_to_wgs84,
)
from expansion.new_england import facts_hash
from expansion.publish import record_hash


def fixture_release():
    evidence = {"publisher": "Synthetic fixture", "url": "https://example.com/fixture", "artifact_sha256": "0" * 64,
                "locator": "row1", "source_date": None, "retrieved_at": "2025-01-01T00:00:00Z",
                "access_review": "Synthetic public example", "facts": "Fixture construction project"}
    source = {"_id": "mid-atlantic:fixture-source", "title": "Synthetic plan", "publisher": "Synthetic fixture",
              "authority": "state_government", "role": "project_plan", "landing_url": evidence["url"],
              "download_url": evidence["url"], "publication_date": None, "vintage": None,
              "retrieved_at": evidence["retrieved_at"], "sha256": evidence["artifact_sha256"],
              "public_status": "verified_public", "access_policy": "public_document", "import_status": "imported",
              "planning_region": "NYISO", "states": ["36"], "notes": ["Synthetic"], "project_count": 1}
    project = {"_id": "mid-atlantic:fixture:1", "source_id": source["_id"], "native_id": "fixture-1",
               "name": "Synthetic line", "owner": None, "other_owners": [], "planning_region": "NYISO",
               "states": ["36"], "counties": [], "geography_basis": "Synthetic fixture", "status": None,
               "status_group": "unknown", "in_service": {"raw": None, "value": None, "precision": "unknown"},
               "center": None, "location_review": "unlocated",
               "evidence": {"page": None, "sheet": None, "row": 1, "source_sha256": source["sha256"],
                            "raw": {"source_evidence": [evidence]}}}
    event = {"id": "fixture-certification", "type": "certification", "date": "2025", "precision": "year",
             "native_project_link": project["native_id"], "description": "Synthetic certification", "evidence": [evidence]}
    release = {"schema_version": "mid-atlantic-release-v1", "release_id": "fixture-only", "producer": "producer",
               "created_at": "2025-02-01T00:00:00Z", "sources": [source], "projects": [project],
               "location_verifications": [], "project_events": [{"project_id": project["_id"], "events": [event]}],
               "dispositions": [{"source_id": source["_id"], "locator": "row1", "disposition": "accepted",
                                 "project_id": project["_id"], "reason": "Synthetic fixture"}],
               "acquisition": [{"source_id": source["_id"], "scope": "Synthetic source", "row_locators": ["row1"],
                                "expected_source_rows": 1, "completeness": "complete", "enumeration_evidence": [evidence]}],
               "expected_counts": {"new_sources": 1, "new_projects": 1, "confirmed_projects": 0, "source_rows": 1},
               "coverage_notes": ["Synthetic test only"],
               "identity_review": {"reviewer": "reviewer", "reviewed_at": "2025-02-02T00:00:00Z",
                                   "facts_sha256": "", "decision": "approved", "evidence": "Synthetic review"}}
    approve(release)
    return release


def approve(release):
    release["identity_review"]["facts_sha256"] = release_hash(release)


def locate(release):
    project = release["projects"][0]
    evidence = project["evidence"]["raw"]["source_evidence"]
    record = {"project_id": project["_id"], "project_facts_sha256": facts_hash(project), "producer": "producer",
              "location_kind": "line", "events": [], "reviews": [], "points": [{
                  "role": "a", "facility_id": "fixture-facility", "facility_name": "Synthetic endpoint",
                  "lat": 41, "lon": -74, "original_geometry": {"crs": "EPSG:4326", "type": "Point",
                                                               "coordinates": [-74, 41], "transform": "Identity"},
                  "precision": None, "uncertainty_m": None, "geometry_evidence": evidence,
                  "identity_evidence": evidence, "identity_rationale": "Synthetic fixture identity"}]}
    record["reviews"].append({"id": "fixture-review", "reviewer": "reviewer", "reviewed_at": "2025-02-01T00:00:00Z",
                              "decision": "confirmed", "facts_sha256": record_hash(record), "reason": "Synthetic review"})
    release["location_verifications"] = [record]
    release["expected_counts"]["confirmed_projects"] = 1
    approve(release)


def assemble(tmp_path, release, snapshot=None):
    write_json(tmp_path / ACTIVE_RELEASE, release)
    return apply_release(snapshot or {"sources": [], "projects": [], "coverage": {"other": "preserved"}}, tmp_path)


def previous_snapshot():
    return {
        "sources": [{"_id": "iso-ne:rsp"}, {"_id": "southeast:plan"}],
        "projects": [{"_id": "iso-ne:rsp:1", "native_id": "1", "planning_region": "ISO-NE",
                      "center": {"lat": 42, "lon": -71}, "location_review": "confirmed"},
                     {"_id": "southeast:pjm:old", "native_id": "old", "planning_region": "PJM"}],
        "coverage": {"expansion": {"confirmed_projects": 345}, "southeast": {"new_projects": 4}},
    }


def test_no_activation_and_pure_replay_preserve_all_previous_producers(tmp_path):
    base = previous_snapshot()
    before = deepcopy(base)
    release = fixture_release()
    write_json(tmp_path / "data/expansion/mid-atlantic/batches/candidate.json", release)
    assert apply_release(base, tmp_path) is base
    first = assemble(tmp_path, release, base)
    assert first == assemble(tmp_path, release, base)
    assert base == before
    assert first["projects"][:-1] == base["projects"]
    assert first["sources"][:-1] == base["sources"]
    for key, value in base["coverage"].items():
        assert first["coverage"][key] == value
    assert first["projects"][-1]["center"] is None
    assert first["projects"][-1]["project_events"][0]["date"] == "2025"
    assert first["coverage"]["mid_atlantic"]["unresolved_reasons"] == {"no_location": 1}
    with pytest.raises(ValueError, match="overwrite"):
        assemble(tmp_path, release, first)


@pytest.mark.parametrize("case", [
    "self", "stale", "future", "early", "non-utc", "namespace", "geography", "source-namespace",
    "source-collision", "project-collision", "source-hash", "national-source-hash", "source-count", "source-url", "source-locator",
    "missing-row", "duplicate-row", "extra-row", "wrong-total", "unknown-complete", "counts",
    "unknown-project", "accepted-existing", "accepted-wrong-source", "known-native", "duplicate-native",
    "embedded-location", "bad-date", "native-link", "early-location-evidence", "unknown-location-project",
])
def test_invalid_release_preserves_input(tmp_path, case):
    release = fixture_release()
    base = previous_snapshot()
    project = release["projects"][0]
    source = release["sources"][0]
    ledger = release["acquisition"][0]
    if case == "self":
        release["identity_review"]["reviewer"] = release["producer"]
    elif case in {"future", "early", "non-utc"}:
        release["identity_review"]["reviewed_at"] = {
            "future": "2999-01-01T00:00:00Z", "early": "2024-01-01T00:00:00Z",
            "non-utc": "2025-02-02T00:00:00-05:00",
        }[case]
    elif case == "namespace":
        project["_id"] = "southeast:fixture:1"
    elif case == "source-namespace":
        source["_id"] = "unscoped-source"
    elif case == "geography":
        project["states"] = ["51", "54"]
    elif case == "source-collision":
        base["sources"].append(deepcopy(source))
    elif case == "project-collision":
        base["projects"].append(deepcopy(project))
    elif case == "source-hash":
        source["sha256"] = "1" * 64
    elif case == "national-source-hash":
        project["evidence"].pop("source_sha256")
    elif case == "source-count":
        source["project_count"] = 2
    elif case in {"source-url", "source-locator"}:
        project["evidence"]["raw"]["source_evidence"][0]["url" if case == "source-url" else "locator"] = "https://example.com/wrong"
    elif case == "missing-row":
        release["dispositions"] = []
    elif case == "duplicate-row":
        release["dispositions"] *= 2
    elif case == "extra-row":
        ledger["row_locators"].append("row2")
    elif case in {"wrong-total", "unknown-complete"}:
        ledger["expected_source_rows"] = 0 if case == "wrong-total" else None
    elif case == "counts":
        release["expected_counts"]["new_projects"] = 2
    elif case == "unknown-project":
        release["dispositions"][0]["project_id"] = "missing"
    elif case == "accepted-existing":
        release["dispositions"].append({**release["dispositions"][0], "locator": "row2", "project_id": base["projects"][0]["_id"]})
        ledger["row_locators"].append("row2")
        ledger["expected_source_rows"] = 2
        release["expected_counts"]["source_rows"] = 2
    elif case == "accepted-wrong-source":
        project["source_id"] = "mid-atlantic:other"
    elif case == "known-native":
        base["projects"][1].update(planning_region="NYISO", native_id=project["native_id"])
    elif case == "duplicate-native":
        release["projects"].append({**deepcopy(project), "_id": "mid-atlantic:fixture:renamed"})
    elif case == "embedded-location":
        project["location_verification"] = {}
    elif case == "bad-date":
        release["project_events"][0]["events"][0].update(date="2025-02-30", precision="day")
    elif case == "native-link":
        release["project_events"][0]["events"][0]["native_project_link"] = "unrelated"
    elif case in {"early-location-evidence", "unknown-location-project"}:
        locate(release)
        record = release["location_verifications"][0]
        if case == "unknown-location-project":
            record["project_id"] = base["projects"][0]["_id"]
        else:
            record["reviews"] = []
            record["points"][0]["geometry_evidence"] = [{**record["points"][0]["geometry_evidence"][0],
                                                        "retrieved_at": "2025-03-01T00:00:00Z"}]
            release["expected_counts"]["confirmed_projects"] = 0
    approve(release)
    if case == "stale":
        release["coverage_notes"].append("Changed after review")
    before = deepcopy(base)
    with pytest.raises(ValueError):
        assemble(tmp_path, release, base)
    assert base == before


@pytest.mark.parametrize("decision", ["insufficient", "rejected", "conflicting", "stale", "missing"])
def test_unconfirmed_geometry_and_unknown_fields_remain_visible(tmp_path, decision):
    release = fixture_release()
    locate(release)
    record = release["location_verifications"][0]
    if decision == "missing":
        record["reviews"] = []
    elif decision == "stale":
        record["reviews"][0]["facts_sha256"] = "0" * 64
    else:
        record["reviews"][0]["decision"] = decision
    release["expected_counts"]["confirmed_projects"] = 0
    approve(release)
    result = assemble(tmp_path, release)
    project = result["projects"][0]
    assert project["center"] is None
    assert project["owner"] is None and project["status"] is None
    assert project["location_review"] == ("rejected" if decision == "rejected" else "needs_review")
    assert project["location_verification"]["points"][0]["uncertainty_m"] is None
    assert result["coverage"]["mid_atlantic"]["distinct_map_positions"] == 0


@pytest.mark.parametrize("case", ["self", "stale-project", "role", "facility", "review-id", "review-order",
                                  "future", "axes", "crs", "transform", "coordinates"])
def test_invalid_location_fails_closed(tmp_path, case):
    release = fixture_release()
    locate(release)
    record = release["location_verifications"][0]
    point = record["points"][0]
    if case == "self":
        record["reviews"][0]["reviewer"] = record["producer"]
    elif case == "stale-project":
        release["projects"][0]["name"] = "Changed facts"
    elif case == "role":
        point["role"] = "site"
    elif case == "facility":
        record["points"].append({**deepcopy(point), "role": "b"})
    elif case in {"review-id", "review-order"}:
        record["reviews"].append({**record["reviews"][0],
                                  "id": "other" if case == "review-order" else record["reviews"][0]["id"],
                                  "reviewed_at": "2025-01-15T00:00:00Z"})
    elif case == "future":
        record["reviews"][0]["reviewed_at"] = "2999-01-01T00:00:00Z"
    elif case == "axes":
        point["original_geometry"]["coordinates"] = [41, -74]
    elif case == "crs":
        point["original_geometry"]["crs"] = "EPSG:6439"
    elif case == "transform":
        point["original_geometry"].update(crs="EPSG:3395", transform="Assumed spherical Mercator")
    elif case == "coordinates":
        point["lat"] += 0.1
    for review in record["reviews"]:
        review["facts_sha256"] = record_hash(record)
    approve(release)
    base = previous_snapshot()
    before = deepcopy(base)
    with pytest.raises(ValueError):
        assemble(tmp_path, release, base)
    assert base == before


def test_bounded_partial_duplicate_and_exclusion_accounting(tmp_path):
    release = fixture_release()
    source = release["sources"][0]
    base = previous_snapshot()
    for disposition, pid in [("duplicate", base["projects"][0]["_id"]), ("excluded", None), ("rejected", None)]:
        release["dispositions"].append({"source_id": source["_id"], "locator": disposition,
                                        "disposition": disposition, "project_id": pid, "reason": "Fixture reason"})
    release["acquisition"][0].update(row_locators=["row1", "duplicate", "excluded", "rejected"],
                                      expected_source_rows=None, completeness="bounded_partial")
    release["expected_counts"]["source_rows"] = 4
    approve(release)
    result = assemble(tmp_path, release, base)
    assert result["coverage"]["mid_atlantic"]["source_rows"] == 4
    assert result["sources"][-1]["project_count"] == 1
    assert result["coverage"]["mid_atlantic"]["source_completeness"][source["_id"]] == "bounded_partial"


@pytest.mark.parametrize("kind,points,basis", [("site", 1, "source_point"), ("line", 1, "one"), ("line", 2, "two")])
def test_center_mean_and_coverage_preserve_status_and_precision(tmp_path, kind, points, basis):
    release = fixture_release()
    release["projects"][0]["states"] = ["36", "51"]
    locate(release)
    record = release["location_verifications"][0]
    record["location_kind"] = kind
    if kind == "site":
        record["points"][0]["role"] = "site"
    if points == 2:
        other = deepcopy(record["points"][0])
        other.update(role="b", facility_id="other", lat=43, lon=-72)
        other["original_geometry"]["coordinates"] = [-72, 43]
        record["points"].append(other)
    record["reviews"][0]["facts_sha256"] = record_hash(record)
    approve(release)
    result = assemble(tmp_path, release)
    project = result["projects"][0]
    assert project["center"]["basis"] == basis
    assert project["center"]["lat"] == (42 if points == 2 else 41)
    assert project["center"]["lon"] == (-73 if points == 2 else -74)
    assert project["status"] is None and project["in_service"]["precision"] == "unknown"
    coverage = result["coverage"]["mid_atlantic"]
    assert coverage["distinct_facility_sites"] == points
    assert coverage["distinct_map_positions"] == 1
    assert coverage["state_counts"] == {"36": 1, "51": 1}


def test_independent_world_mercator_reference_and_spherical_distinction():
    # NOAA feature 3322 / ID 135920; expected WGS84 independently computed with
    # pyproj EPSG:3395 -> EPSG:4326, always_xy=True in the acquired reference.
    x, y = -8059274.6723, 4968542.412299998
    expected = -72.39769617044438, 40.892653565332864
    assert world_mercator_to_wgs84(x, y) == pytest.approx(expected, abs=1e-10)
    release = fixture_release()
    locate(release)
    point = release["location_verifications"][0]["points"][0]
    point.update(lon=expected[0], lat=expected[1])
    point["original_geometry"].update(crs="EPSG:3395", coordinates=[x, y], transform=WORLD_MERCATOR_TRANSFORM)
    check_point(point)
    point["original_geometry"].update(crs="EPSG:3857", transform=WEB_MERCATOR_TRANSFORM)
    with pytest.raises(ValueError, match="does not reproduce"):
        check_point(point)
    # Separate known spherical result, not generated by the implementation.
    point.update(lon=-74, lat=41)
    point["original_geometry"]["coordinates"] = [-8237642.318702244, 5012341.663847517]
    check_point(point)


def test_history_duplicate_must_agree_and_is_consumed_once(tmp_path):
    release = fixture_release()
    locate(release)
    record = release["location_verifications"][0]
    record["events"] = deepcopy(release["project_events"][0]["events"])
    record["reviews"][0]["facts_sha256"] = record_hash(record)
    approve(release)
    result = assemble(tmp_path, release)
    assert len(result["projects"][0]["project_events"]) == 1
    record["events"][0]["description"] = "Conflicting observation"
    record["reviews"][0]["facts_sha256"] = record_hash(record)
    approve(release)
    with pytest.raises(ValueError, match="conflicting duplicate"):
        assemble(tmp_path, release)


def test_event_identity_cannot_be_reused_from_previous_producer(tmp_path):
    release = fixture_release()
    base = previous_snapshot()
    base["projects"][0]["project_events"] = deepcopy(release["project_events"][0]["events"])
    before = deepcopy(base)
    with pytest.raises(ValueError, match="event id reused"):
        assemble(tmp_path, release, base)
    assert base == before


def test_shared_map_position_is_not_counted_as_separate_visible_sites(tmp_path):
    release = fixture_release()
    locate(release)
    other = deepcopy(release["projects"][0])
    other.update(_id="mid-atlantic:fixture:2", native_id="fixture-2")
    release["projects"].append(other)
    second = deepcopy(release["location_verifications"][0])
    second.update(project_id=other["_id"], project_facts_sha256=facts_hash(other))
    second["reviews"][0].update(id="second-review", facts_sha256=record_hash(second))
    release["location_verifications"].append(second)
    # Two separate works may be observations on the same source table row.
    other["evidence"]["raw"]["source_evidence"][0]["locator"] = "row2"
    second["project_facts_sha256"] = facts_hash(other)
    second["reviews"][0]["facts_sha256"] = record_hash(second)
    release["dispositions"].append({**release["dispositions"][0], "locator": "row2", "project_id": other["_id"]})
    release["acquisition"][0].update(row_locators=["row1", "row2"], expected_source_rows=2)
    release["sources"][0]["project_count"] = 2
    release["expected_counts"].update(new_projects=2, confirmed_projects=2, source_rows=2)
    approve(release)
    coverage = assemble(tmp_path, release)["coverage"]["mid_atlantic"]
    assert coverage["confirmed_projects"] == 2
    assert coverage["distinct_map_positions"] == 1
    assert coverage["distinct_facility_sites"] == 1


def test_committed_release_passes_full_national_validation_and_preserves_previous_producers():
    from common import REPO_ROOT, load_json
    from expansion.publish import apply_release as apply_new_england
    from national.build import OUTPUTS, _coverage, validate_snapshot_values
    from southeast.publish import apply_release as apply_southeast

    path = REPO_ROOT / ACTIVE_RELEASE
    assert path.exists(), "This delivery includes an independently reviewed activation artifact"
    baseline = {name: load_json(REPO_ROOT / "data/national" / f"{name}.json") for name in OUTPUTS}
    baseline = apply_southeast(apply_new_england(baseline, REPO_ROOT), REPO_ROOT)
    before = deepcopy(baseline)
    result = apply_release(baseline, REPO_ROOT)
    assert baseline == before
    assert result["projects"][:len(before["projects"])] == before["projects"]
    assert result["sources"][:len(before["sources"])] == before["sources"]
    result["coverage"].update(_coverage(result["projects"], {
        s["_id"] for s in result["sources"] if s["import_status"] == "imported"
    }))
    assert validate_snapshot_values(result) == []
    release = load_json(path)
    assert result["coverage"]["mid_atlantic"]["confirmed_projects"] == release["expected_counts"]["confirmed_projects"]
