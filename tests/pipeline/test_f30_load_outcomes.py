"""National loader outcomes: every run names what was staged and what is active; rollback uses the previous pointer."""

import json

import mongomock

from common import load_summary
from national import load as national_load
from national.load import load_release, rollback


def snapshot(failures=None):
    return {
        "sources": [{"_id": "source", "title": "Source", "retrieved_at": "2026-09-20T00:00:00Z"},
                    {"_id": "other", "title": "Other"}],
        "projects": [{"_id": "project", "states": ["25"], "counties": [], "planning_region": "iso-ne", "owner": "Owner",
                      "status_group": "planned", "in_service": {"value": "2028-12"},
                      "center": {"lat": 42.1, "lon": -71.2, "basis": "one", "evidence": "reviewed"}}],
        "coverage": {"schema_version": "national-coverage-v1", "projects_total": 1, "failures": failures or []},
    }


def test_activation_and_repeat_are_named_with_releases_and_metrics():
    db = mongomock.MongoClient().gridbridge
    first = load_release(db, snapshot(failures=[{"source": "x"}]), "A")
    assert first["outcome"] == load_summary.ACTIVATED
    assert first["release"] == {"requested": "A", "staged": "A", "active": "A", "previous": None}
    assert first["source_freshness"] == {"sources": 2, "oldest_retrieved_at": "2026-09-20T00:00:00Z",
                                         "newest_retrieved_at": "2026-09-20T00:00:00Z", "without_retrieved_at": 1}
    assert first["quarantined"] == {"failed_sources": 1}
    again = load_release(db, snapshot(), "A")
    assert (again["outcome"], again["release"]["staged"]) == (load_summary.ALREADY_ACTIVE, None)


def test_rollback_uses_the_previous_pointer_and_refuses_an_incomplete_release():
    db = mongomock.MongoClient().gridbridge
    for sha in ("A", "B"):
        load_release(db, snapshot(), sha)
    back = rollback(db)
    assert back["outcome"] == load_summary.REACTIVATED
    assert (back["release"]["active"], back["release"]["previous"]) == ("A", "B")
    db.national_projects.delete_many({"dataset": "B"})
    refused = rollback(db)
    assert refused["outcome"] == load_summary.PRUNED_RECEIPT and not refused["ok"]
    assert db.meta.find_one({"_id": "national_active"})["dataset"] == "A"
    assert rollback(mongomock.MongoClient().gridbridge)["outcome"] == load_summary.PUBLICATION_FAILED


def test_validation_only_run_is_explicit(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("MONGODB_URI_RW", raising=False)
    monkeypatch.setenv("GIT_SHA", "national-validation")
    monkeypatch.setenv("LOAD_METRICS_PATH", str(tmp_path / "m.json"))
    monkeypatch.setattr(national_load, "load_snapshot", lambda root: snapshot())
    assert national_load.main([]) == 0
    summary = json.loads((tmp_path / "m.json").read_text())
    assert summary["outcome"] == load_summary.VALIDATED_ONLY and summary["release"]["active"] is None
    assert "national load: validated_only: staged nothing; active: none" in capsys.readouterr().out
