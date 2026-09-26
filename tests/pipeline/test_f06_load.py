"""F06 loader: validation, locations->projects join, dataset staging, pointer flip, idempotence (mongomock)."""

import json
from pathlib import Path

import mongomock
import pytest

from common import REPO_ROOT, load_json
from load.__main__ import load
from load.build import collect, join_projects, stage

FIX = REPO_ROOT / "data/fixtures"


def write(root: Path, rel: str, obj) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj))


@pytest.fixture
def data_root(tmp_path):
    """A data/ tree built from the golden fixtures, in the folders the producing features own."""
    projects = [{k: v for k, v in p.items() if k not in ("center", "geo", "location_confidence")}
                for p in load_json(FIX / "projects.json")]
    write(tmp_path, "data/sources/sources.json", load_json(FIX / "sources.json"))
    write(tmp_path, "data/projects/desc.json", [p for p in projects if p["utility"] == "DESC"])
    write(tmp_path, "data/projects/gpc.json", [p for p in projects if p["utility"] == "GPC"])
    write(tmp_path, "data/locations/locations.json", [{k: v for k, v in loc.items() if k != "_id"}
                                                      for loc in load_json(FIX / "locations.json")])
    write(tmp_path, "data/matches/matches.json", load_json(FIX / "matches.json"))
    write(tmp_path, "data/matches/summary.json", {"pairs_evaluated": 25})
    write(tmp_path, "data/versions/versions.json", load_json(FIX / "version_changes.json"))
    write(tmp_path, "data/fixtures/matches.json", [{"not": "loaded"}])
    write(tmp_path, "data/osm/substations.json", [{"not": "loaded"}])
    return tmp_path


def test_collect_reads_owned_folders_only(data_root):
    records, errors, skipped = collect(data_root)
    assert errors == []
    assert skipped == ["data/matches/summary.json"]
    assert len(records["projects"]) == 10 and len(records["locations"]) == 20  # 2 endpoints x 10, incl. 4 unlocated
    assert len(records["matches"]) == 6 and len(records["version_changes"]) == 1


def test_join_recomputes_fixture_centers(data_root):
    records, _, _ = collect(data_root)
    joined = {p["project_key"]: p for p in join_projects(records["projects"], records["locations"])}
    for p in load_json(FIX / "projects.json"):
        j = joined[p["project_key"]]
        assert j["center"] == pytest.approx(p["center"]) if p["center"] else j["center"] is None
        assert j["geo"] == p["geo"]
        assert j["location_confidence"] == p["location_confidence"]
    one = joined["DESC:DESC_1"]  # Hooks Sub has no coordinates in the sample
    assert one["center"]["basis"] == "one" and len(one["endpoints"]) == 2


def test_invalid_record_reported(data_root):
    write(data_root, "data/matches/bad.json", [{"_id": "x", "a": "A", "b": "B", "distance_mi": 30}])
    _, errors, _ = collect(data_root)
    assert any("data/matches/bad.json[0]" in e for e in errors)


def test_duplicate_ids_reported(data_root):
    write(data_root, "data/versions/dup.json", load_json(FIX / "version_changes.json"))
    _, errors, _ = collect(data_root)
    assert any("duplicate _id" in e for e in errors)


def test_stage_namespaces_ids(data_root):
    records, _, _ = collect(data_root)
    staged = stage(records, "abc")
    m = staged["matches"][0]
    assert m["_id"].startswith("abc:") and m["id"] == m["_id"][4:] and m["dataset"] == "abc"
    assert "locations" not in staged


def test_load_flips_pointer_and_is_idempotent(data_root):
    db = mongomock.MongoClient().db
    records, errors, _ = collect(data_root)
    assert load(db, records, errors, "sha1") == 0
    snapshot = {c: sorted(d["_id"] for d in db[c].find()) for c in ("projects", "matches", "version_changes")}
    assert db.meta.find_one({"_id": "active"})["dataset"] == "sha1"
    assert load(db, records, errors, "sha1") == 0
    assert {c: sorted(d["_id"] for d in db[c].find()) for c in snapshot} == snapshot
    assert db.meta.find_one({"_id": "active"})["previous"] is None
    assert db.runs.find_one({"_id": "load:sha1"})["status"] == "ok"


def test_new_dataset_keeps_previous_and_drops_older(data_root):
    db = mongomock.MongoClient().db
    records, errors, _ = collect(data_root)
    for sha in ("s1", "s2", "s3"):
        assert load(db, records, errors, sha) == 0
    meta = db.meta.find_one({"_id": "active"})
    assert (meta["dataset"], meta["previous"]) == ("s3", "s2")
    assert sorted(db.matches.distinct("dataset")) == ["s2", "s3"]


def test_failed_validation_does_not_flip(data_root):
    db = mongomock.MongoClient().db
    records, errors, _ = collect(data_root)
    load(db, records, errors, "good")
    write(data_root, "data/matches/bad.json", [{"_id": "x"}])
    records, errors, _ = collect(data_root)
    assert load(db, records, errors, "bad") == 1
    assert db.meta.find_one({"_id": "active"})["dataset"] == "good"
    assert db.runs.find_one({"_id": "load:bad"})["status"] == "failed"
    assert db.matches.count_documents({"dataset": "bad"}) == 0


class FailingInserts:
    """Wraps a mongomock db; insert_many on `coll` raises, like a dropped connection mid-load."""

    def __init__(self, db, coll):
        self._db, self._coll = db, coll

    def __getattr__(self, name):
        return getattr(self._db, name)

    def __getitem__(self, name):
        c = self._db[name]
        if name != self._coll:
            return c

        class Broken:
            def __getattr__(self, attr):
                if attr == "insert_many":
                    def boom(*a, **k):
                        raise ConnectionError("simulated")
                    return boom
                return getattr(c, attr)

        return Broken()


def test_reloading_active_sha_is_a_no_op_even_if_writes_would_fail(data_root):
    db = mongomock.MongoClient().db
    records, errors, _ = collect(data_root)
    assert load(db, records, errors, "sha1") == 0
    before = db.sources.count_documents({"dataset": "sha1"})
    assert load(FailingInserts(db, "sources"), records, errors, "sha1") == 0
    assert db.sources.count_documents({"dataset": "sha1"}) == before > 0
    assert db.meta.find_one({"_id": "active"})["dataset"] == "sha1"


def test_write_failure_keeps_served_dataset(data_root):
    db = mongomock.MongoClient().db
    records, errors, _ = collect(data_root)
    assert load(db, records, errors, "sha1") == 0
    served = db.matches.count_documents({"dataset": "sha1"})
    assert load(FailingInserts(db, "sources"), records, errors, "sha2") == 1
    assert db.meta.find_one({"_id": "active"})["dataset"] == "sha1"
    assert db.matches.count_documents({"dataset": "sha1"}) == served
    run = db.runs.find_one({"_id": "load:sha2"})
    assert run["status"] == "failed" and "ConnectionError" in run["errors"][0]
    assert load(db, records, errors, "sha2") == 0  # a later retry of the failed sha still loads


def test_non_object_entries_are_errors_and_block_activation(data_root):
    write(data_root, "data/projects/mixed.json", [load_json(FIX / "projects.json")[0] | {"_id": "X@y"}, None])
    records, errors, skipped = collect(data_root)
    assert any("data/projects/mixed.json[1]: not a JSON object" in e for e in errors)
    assert "data/projects/mixed.json" not in skipped
    db = mongomock.MongoClient().db
    assert load(db, records, errors, "sha1") == 1
    assert db.meta.find_one({"_id": "active"}) is None


def test_filed_endpoints_kept_apart_from_locations(data_root):
    records, _, _ = collect(data_root)
    p = dict(records["projects"][0])
    p["endpoints"] = [{"name": "Queensboro", "raw": "Queensboro", "norm": "QUEENSBORO"}]
    [joined] = join_projects([p], [])
    assert joined["filed_endpoints"] == p["endpoints"] and "endpoints" not in joined
    [joined] = join_projects([p], [loc for loc in records["locations"] if loc["project_key"] == p["project_key"]])
    assert joined["filed_endpoints"][0]["name"] == "Queensboro"
    assert all("confidence" in e for e in joined["endpoints"])
