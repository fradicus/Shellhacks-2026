"""Synthetic releases exercise activation boundaries without claiming public evidence."""
from copy import deepcopy

import pytest
from mongomock import MongoClient

from common import write_json
from expansion.new_england import facts_hash
from expansion.publish import record_hash
from national.load import load
from southeast.florida_crs import TRANSFORM
from southeast.publish import ACTIVE_RELEASE, apply_release, check_point, release_hash


def fixture_release():
    evidence = {"publisher": "Synthetic fixture", "url": "https://example.com/fixture", "artifact_sha256": "0" * 64,
                "locator": "row1", "source_date": None, "retrieved_at": "2025-01-01T00:00:00Z",
                "access_review": "Synthetic public example", "facts": "Fixture construction project"}
    source = {"_id": "fixture-source", "title": "Synthetic plan", "publisher": "Synthetic fixture",
              "authority": "state_government", "role": "project_plan", "landing_url": evidence["url"],
              "download_url": evidence["url"], "publication_date": None, "vintage": None,
              "retrieved_at": evidence["retrieved_at"], "sha256": evidence["artifact_sha256"],
              "public_status": "verified_public", "access_policy": "public_document", "import_status": "imported",
              "planning_region": None, "states": ["12"], "notes": ["Synthetic"], "project_count": 1}
    project = {"_id": "southeast:fixture:1", "source_id": source["_id"], "native_id": "fixture-1",
               "name": "Synthetic line", "owner": None, "other_owners": [], "planning_region": None,
               "states": ["12"], "counties": [], "geography_basis": "Synthetic fixture", "status": None,
               "status_group": "unknown", "in_service": {"raw": None, "value": None, "precision": "unknown"},
               "center": None, "location_review": "unlocated",
               "evidence": {"page": None, "sheet": None, "row": 1, "raw": {"source_evidence": [evidence]}}}
    event = {"id": "fixture-certification", "type": "certification", "date": "2025", "precision": "year",
             "native_project_link": project["native_id"], "description": "Synthetic certification", "evidence": [evidence]}
    release = {"schema_version": "southeast-release-v1", "release_id": "fixture-only", "producer": "producer",
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
                  "lat": 30, "lon": -84, "original_geometry": {"crs": "EPSG:4326", "type": "Point",
                                                               "coordinates": [-84, 30], "transform": "Identity"},
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


def test_atomic_deterministic_unlocated_history_and_candidate_isolation(tmp_path):
    base = {"sources": [], "projects": [], "coverage": {"other": "preserved"}}
    before = deepcopy(base)
    write_json(tmp_path / "data/southeast/batches/unapproved.json", fixture_release())
    assert apply_release(base, tmp_path) is base
    release = fixture_release()
    first = assemble(tmp_path, release, base)
    assert first == assemble(tmp_path, release, base)
    assert base == before
    assert first["projects"][0]["center"] is None
    assert first["projects"][0]["project_events"][0]["date"] == "2025"
    assert first["coverage"]["other"] == "preserved"
    with pytest.raises(ValueError, match="overwrite"):
        assemble(tmp_path, release, first)
    locate(release)
    located = assemble(tmp_path, release)
    assert located["projects"][0]["center"]["basis"] == "one"
    assert located["coverage"]["southeast"]["partial_endpoint_projects"] == 1


@pytest.mark.parametrize("case", ["self", "stale", "collision", "missing-row", "wrong-total", "unknown-total",
                                  "source-hash", "source-count", "bad-date", "native-link", "counts", "early-review"])
def test_invalid_release_never_mutates_base(tmp_path, case):
    release = fixture_release()
    if case == "self":
        release["identity_review"]["reviewer"] = "producer"
    elif case == "collision":
        release["projects"] *= 2
    elif case == "missing-row":
        release["acquisition"][0]["row_locators"] = []
    elif case in {"wrong-total", "unknown-total"}:
        release["acquisition"][0]["expected_source_rows"] = 2 if case == "wrong-total" else None
    elif case == "source-hash":
        release["sources"][0]["sha256"] = "1" * 64
    elif case == "source-count":
        release["sources"][0]["project_count"] = 2
    elif case == "bad-date":
        release["project_events"][0]["events"][0].update(date="2025-02-30", precision="day")
    elif case == "native-link":
        release["project_events"][0]["events"][0]["native_project_link"] = "other"
    elif case == "counts":
        release["expected_counts"]["new_projects"] = 2
    elif case == "early-review":
        release["identity_review"]["reviewed_at"] = "2024-01-01T00:00:00Z"
    approve(release)
    if case == "stale":
        release["coverage_notes"].append("Changed since review")
    base = {"sources": [], "projects": [], "coverage": {}}
    before = deepcopy(base)
    with pytest.raises(ValueError):
        assemble(tmp_path, release, base)
    assert base == before


@pytest.mark.parametrize("decision", ["insufficient", "rejected", "conflicting", "stale", "missing"])
def test_unapproved_geometry_stays_null(tmp_path, decision):
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
    project = assemble(tmp_path, release)["projects"][0]
    assert project["center"] is None
    assert project["location_review"] == ("rejected" if decision == "rejected" else "needs_review")


@pytest.mark.parametrize("case", ["self", "axes", "unsupported-crs", "stale-project", "duplicate-endpoint"])
def test_invalid_location_fails_release(tmp_path, case):
    release = fixture_release()
    locate(release)
    record = release["location_verifications"][0]
    if case == "self":
        record["reviews"][0]["reviewer"] = "producer"
    elif case == "axes":
        record["points"][0]["original_geometry"]["coordinates"] = [30, -84]
    elif case == "unsupported-crs":
        record["points"][0]["original_geometry"]["crs"] = "unknown"
    elif case == "stale-project":
        release["projects"][0]["name"] = "Changed"
    else:
        record["points"] *= 2
    approve(release)
    with pytest.raises(ValueError):
        assemble(tmp_path, release)


def test_independently_reproduced_dep_transform_and_axes():
    release = fixture_release()
    locate(release)
    point = release["location_verifications"][0]["points"][0]
    # Published DEP bytes and independent calculation are documented in the review report.
    point.update(lon=-84.3994653300266, lat=30.452223774750653)
    point["original_geometry"] = {"crs": "EPSG:6439", "type": "Point",
                                  "coordinates": [361673.80200000107, 716135.95380000025], "transform": TRANSFORM}
    check_point(point)
    point["original_geometry"]["coordinates"].reverse()
    with pytest.raises(ValueError):
        check_point(point)
    point["original_geometry"]["coordinates"].reverse()
    point["original_geometry"]["transform"] = "unspecified default datum"
    with pytest.raises(ValueError):
        check_point(point)


def test_event_deduplication_and_source_row_binding(tmp_path):
    release = fixture_release()
    locate(release)
    record = release["location_verifications"][0]
    record["events"] = deepcopy(release["project_events"][0]["events"])
    record["reviews"][0]["facts_sha256"] = record_hash(record)
    approve(release)
    result = assemble(tmp_path, release)
    assert len(result["projects"][0]["project_events"]) == 1
    record["events"][0]["date"] = "2024"
    record["reviews"][0]["facts_sha256"] = record_hash(record)
    approve(release)
    with pytest.raises(ValueError, match="conflicting duplicate"):
        assemble(tmp_path, release)
    release = fixture_release()
    release["projects"][0]["evidence"]["raw"]["source_evidence"][0]["locator"] = "other-row"
    approve(release)
    with pytest.raises(ValueError, match="locator"):
        assemble(tmp_path, release)


def test_existing_loader_preserves_prior_activation_on_southeast_write_failure(tmp_path, monkeypatch):
    release = fixture_release()
    locate(release)
    snapshot = assemble(tmp_path, release)
    db = MongoClient().gridbridge
    db.meta.insert_one({"_id": "national_active", "dataset": "prior"})
    db.national_projects.insert_one({"_id": "prior:fixture", "dataset": "prior"})

    def fail(*args, **kwargs):
        raise RuntimeError("Synthetic storage failure")

    with monkeypatch.context() as patch:
        patch.setattr(db.national_projects, "insert_many", fail)
        assert load(db, snapshot, "candidate") == 1
    assert db.meta.find_one({"_id": "national_active"})["dataset"] == "prior"
    assert db.national_projects.count_documents({"dataset": "prior"}) == 1
    assert load(db, snapshot, "candidate") == 0
    stored = db.national_projects.find_one({"dataset": "candidate"})
    assert stored["geo"]["coordinates"] == [-84, 30]
    assert stored["project_events"][0]["type"] == "certification"
    assert db.meta.find_one({"_id": "national_active"})["previous"] == "prior"
    assert load(db, snapshot, "candidate") == 0


def test_duplicate_native_project_cannot_hide_behind_distinct_internal_ids(tmp_path):
    release = fixture_release()
    second = deepcopy(release["projects"][0])
    second["_id"] = "southeast:fixture:second"
    second["evidence"]["raw"]["source_evidence"][0]["locator"] = "row2"
    release["projects"].append(second)
    release["sources"][0]["project_count"] = 2
    release["dispositions"].append({**release["dispositions"][0], "project_id": second["_id"], "locator": "row2"})
    release["acquisition"][0]["row_locators"].append("row2")
    release["acquisition"][0]["expected_source_rows"] = 2
    release["expected_counts"].update(new_projects=2, source_rows=2)
    approve(release)
    with pytest.raises(ValueError, match="duplicate primary native"):
        assemble(tmp_path, release)


@pytest.mark.parametrize("stale", [True, False])
def test_identity_review_must_postdate_unapproved_location_evidence(tmp_path, stale):
    release = fixture_release()
    locate(release)
    record = release["location_verifications"][0]
    record["points"][0]["geometry_evidence"] = deepcopy(record["points"][0]["geometry_evidence"])
    record["points"][0]["geometry_evidence"][0]["retrieved_at"] = "2025-03-01T00:00:00Z"
    if stale:
        record["reviews"][0]["facts_sha256"] = "0" * 64
    else:
        record["reviews"] = []
    release["expected_counts"]["confirmed_projects"] = 0
    approve(release)
    with pytest.raises(ValueError, match="identity review predates location evidence"):
        assemble(tmp_path, release)
