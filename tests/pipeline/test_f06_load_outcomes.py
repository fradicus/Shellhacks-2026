"""F06 loader outcomes: an active release, an intact retained release, a pruned receipt and a real activation stay
distinct; rollback uses meta.active.previous; every run names what was staged and what is active (mongomock)."""

import json

import mongomock
import pytest

from common import REPO_ROOT, load_json, load_summary
from load import __main__ as loader
from load.__main__ import load_release, rollback
from load.build import collect

FIX = REPO_ROOT / "data/fixtures"


@pytest.fixture
def records(tmp_path):
    def write(rel, obj):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj))

    projects = [{k: v for k, v in p.items() if k not in ("center", "geo", "location_confidence")}
                for p in load_json(FIX / "projects.json")]
    write("data/sources/sources.json", load_json(FIX / "sources.json"))
    write("data/projects/desc.json", [p for p in projects if p["utility"] == "DESC"])
    write("data/projects/gpc.json", [p for p in projects if p["utility"] == "GPC"])
    write("data/locations/locations.json",
          [{k: v for k, v in loc.items() if k != "_id"} for loc in load_json(FIX / "locations.json")])
    write("data/matches/matches.json", load_json(FIX / "matches.json"))
    write("data/versions/versions.json", load_json(FIX / "version_changes.json"))
    recs, errors, _ = collect(tmp_path)
    assert errors == []
    return recs


def active(db):
    meta = db.meta.find_one({"_id": "active"})
    return meta["dataset"], meta["previous"]


def test_new_release_is_staged_and_activated(records):
    db = mongomock.MongoClient().db
    first = load_release(db, records, [], "A")
    assert first["outcome"] == load_summary.ACTIVATED
    assert first["release"] == {"requested": "A", "staged": "A", "active": "A", "previous": None}
    again = load_release(db, records, [], "A")
    assert (again["outcome"], again["release"]["staged"], again["release"]["active"]) == (load_summary.ALREADY_ACTIVE, None, "A")


def test_reloading_a_pruned_release_is_refused_then_restaged_on_request(records):
    db = mongomock.MongoClient().db
    for sha in ("A", "B", "C"):
        assert load_release(db, records, [], sha)["outcome"] == load_summary.ACTIVATED
    assert db.matches.count_documents({"dataset": "A"}) == 0 and db.runs.find_one({"_id": "load:A"})["status"] == "ok"
    pruned = load_release(db, records, [], "A")
    assert pruned["outcome"] == load_summary.PRUNED_RECEIPT and pruned["ok"] is False
    assert pruned["release"] == {"requested": "A", "staged": None, "active": "C", "previous": "B"}
    assert "--restage" in pruned["detail"]
    assert active(db) == ("C", "B") and db.matches.count_documents({"dataset": "A"}) == 0
    restaged = load_release(db, records, [], "A", restage=True)
    assert restaged["outcome"] == load_summary.ACTIVATED and restaged["release"]["staged"] == "A"
    assert active(db) == ("A", "C")
    assert sorted(db.matches.distinct("dataset")) == ["A", "C"]


def test_an_intact_retained_release_is_reported_not_silently_skipped(records):
    db = mongomock.MongoClient().db
    for sha in ("A", "B"):
        load_release(db, records, [], sha)
    retained = load_release(db, records, [], "A")
    assert retained["outcome"] == load_summary.RETAINED_INACTIVE and retained["ok"] is True
    assert retained["release"] == {"requested": "A", "staged": None, "active": "B", "previous": "A"}
    assert active(db) == ("B", "A")
    served = load_release(db, records, [], "A", activate=True)
    assert served["outcome"] == load_summary.REACTIVATED and active(db) == ("A", "B")


def test_rollback_serves_the_previous_release_and_refuses_when_it_is_gone(records):
    db = mongomock.MongoClient().db
    for sha in ("A", "B"):
        load_release(db, records, [], sha)
    back = rollback(db)
    assert back["outcome"] == load_summary.REACTIVATED and active(db) == ("A", "B")
    assert rollback(db)["outcome"] == load_summary.REACTIVATED and active(db) == ("B", "A")
    db.matches.delete_many({"dataset": "A"})  # retention or a manual prune removed it
    refused = rollback(db)
    assert refused["outcome"] == load_summary.PRUNED_RECEIPT and not refused["ok"] and active(db) == ("B", "A")
    assert rollback(mongomock.MongoClient().db)["outcome"] == load_summary.PUBLICATION_FAILED


def test_failures_and_metrics_are_structured(records, capsys):
    db = mongomock.MongoClient().db
    bad = load_release(db, records, ["data/matches/x.json[0]: invalid"], "A", skipped=["data/matches/summary.json"])
    assert bad["outcome"] == load_summary.VALIDATION_FAILED and bad["publication_failures"] == ["data/matches/x.json[0]: invalid"]
    assert bad["quarantined"] == {"invalid_records": 1, "skipped_files": 1}
    ok = load_release(db, records, [], "A")
    assert ok["counts"]["projects"] == len(records["projects"])
    assert ok["source_freshness"]["sources"] == len(records["sources"])
    load_summary.emit(ok)
    out = capsys.readouterr().out
    assert "load: activated: staged A; active: A" in out
    line = next(x for x in out.splitlines() if x.startswith("load: summary "))
    assert json.loads(line.removeprefix("load: summary "))["outcome"] == "activated"


def test_validation_only_run_has_an_explicit_outcome(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("MONGODB_URI_RW", raising=False)
    monkeypatch.setenv("GIT_SHA", "validation-sha")
    metrics = tmp_path / "metrics.json"
    monkeypatch.setenv("LOAD_METRICS_PATH", str(metrics))
    monkeypatch.setattr(loader, "collect", lambda root: ({"projects": [{"_id": "p"}], "sources": []}, [], []))
    assert loader.main([]) == 0
    summary = json.loads(metrics.read_text())
    assert summary["outcome"] == load_summary.VALIDATED_ONLY
    assert summary["release"] == {"requested": "validation-sha", "staged": None, "active": None, "previous": None}
    assert "validated_only: staged nothing; active: none" in capsys.readouterr().out
    monkeypatch.setattr(loader, "collect", lambda root: ({"projects": []}, ["bad record"], []))
    assert loader.main([]) == 1
    assert json.loads(metrics.read_text())["outcome"] == load_summary.VALIDATION_FAILED
