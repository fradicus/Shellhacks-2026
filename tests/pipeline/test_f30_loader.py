import mongomock

from national.load import ensure_indexes, load, stage


def snapshot():
    return {
        "sources": [{"_id": "source", "title": "Source"}],
        "projects": [
            {
                "_id": "project",
                "states": ["25"],
                "counties": [],
                "planning_region": "iso-ne",
                "owner": "Owner",
                "status_group": "planned",
                "in_service": {"value": "2028-12"},
                "center": {"lat": 42.1, "lon": -71.2, "basis": "one", "evidence": "reviewed"},
            }
        ],
        "coverage": {"schema_version": "national-coverage-v1", "projects_total": 1},
    }


def test_stage_adds_dataset_identity_and_geo_without_mutating_public_record():
    value = snapshot()
    records = stage(value, "sha")
    project = records["national_projects"][0]
    assert project["_id"] == "sha:project" and project["id"] == "project" and project["dataset"] == "sha"
    assert project["geo"] == {"type": "Point", "coordinates": [-71.2, 42.1]}
    assert "geo" not in value["projects"][0]


def test_load_activates_national_only_and_is_idempotent():
    db = mongomock.MongoClient().gridbridge
    db.meta.insert_one({"_id": "active", "dataset": "legacy"})
    assert load(db, snapshot(), "sha") == 0
    assert db.meta.find_one({"_id": "active"})["dataset"] == "legacy"
    assert db.meta.find_one({"_id": "national_active"})["dataset"] == "sha"
    assert db.national_projects.count_documents({"dataset": "sha"}) == 1
    assert db.national_runs.find_one({"_id": "national-load:sha"})["coverage"]["projects_total"] == 1
    before = list(db.national_projects.find({}))
    assert load(db, snapshot(), "sha") == 0
    assert list(db.national_projects.find({})) == before


def test_failed_project_write_never_moves_national_pointer(monkeypatch):
    db = mongomock.MongoClient().gridbridge
    db.meta.insert_one({"_id": "national_active", "dataset": "previous"})

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic write failure")

    monkeypatch.setattr(db.national_projects, "insert_many", fail)
    assert load(db, snapshot(), "candidate") == 1
    assert db.meta.find_one({"_id": "national_active"})["dataset"] == "previous"
    run = db.national_runs.find_one({"_id": "national-load:candidate"})
    assert run["status"] == "failed" and run["errors"] == ["write failed: RuntimeError"]


def test_previous_success_can_be_reactivated_after_pointer_moves():
    db = mongomock.MongoClient().gridbridge
    assert load(db, snapshot(), "first") == 0
    assert load(db, snapshot(), "second") == 0
    assert db.meta.find_one({"_id": "national_active"})["dataset"] == "second"
    assert load(db, snapshot(), "first") == 0
    assert db.meta.find_one({"_id": "national_active"})["dataset"] == "first"
    assert db.national_projects.count_documents({"dataset": "first"}) == 1


def test_run_evidence_failure_never_promotes_candidate(monkeypatch):
    db = mongomock.MongoClient().gridbridge
    db.meta.insert_one({"_id": "national_active", "dataset": "previous"})

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic run failure")

    monkeypatch.setattr(db.national_runs, "replace_one", fail)
    assert load(db, snapshot(), "candidate") == 1
    assert db.meta.find_one({"_id": "national_active"})["dataset"] == "previous"


def test_final_status_failure_is_noncritical_after_ready_coverage_and_activation(monkeypatch):
    db = mongomock.MongoClient().gridbridge
    original = db.national_runs.replace_one
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("synthetic final status failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(db.national_runs, "replace_one", fail_second)
    assert load(db, snapshot(), "candidate") == 0
    assert db.meta.find_one({"_id": "national_active"})["dataset"] == "candidate"
    assert db.national_runs.find_one({"_id": "national-load:candidate"})["status"] == "ready"


def test_active_snapshot_repairs_missing_run_but_rejects_incomplete_records():
    db = mongomock.MongoClient().gridbridge
    assert load(db, snapshot(), "candidate") == 0
    db.national_runs.delete_many({})
    assert load(db, snapshot(), "candidate") == 0
    assert db.national_runs.find_one({"_id": "national-load:candidate"})["status"] == "ok"
    db.national_projects.delete_many({})
    assert load(db, snapshot(), "candidate") == 1
    assert db.meta.find_one({"_id": "national_active"})["dataset"] == "candidate"


def test_retention_cleanup_failure_is_noncritical_after_activation(monkeypatch):
    db = mongomock.MongoClient().gridbridge
    original = db.national_sources.delete_many

    def fail_cleanup(query):
        if isinstance(query.get("dataset"), dict):
            raise RuntimeError("synthetic cleanup failure")
        return original(query)

    monkeypatch.setattr(db.national_sources, "delete_many", fail_cleanup)
    assert load(db, snapshot(), "candidate") == 0
    assert db.meta.find_one({"_id": "national_active"})["dataset"] == "candidate"
    assert db.national_runs.find_one({"_id": "national-load:candidate"})["status"] == "ok"


def test_indexes_are_separate_for_array_filters():
    db = mongomock.MongoClient().gridbridge
    ensure_indexes(db)
    indexes = db.national_projects.index_information().values()
    keys = {tuple(index["key"]) for index in indexes}
    assert (("dataset", 1), ("states", 1)) in keys
    assert (("dataset", 1), ("counties", 1)) in keys
    assert (("dataset", 1), ("states", 1), ("counties", 1)) not in keys
    assert (("dataset", 1), ("in_service.value", 1)) in keys
    assert (("dataset", 1), ("geo", "2dsphere")) in keys
