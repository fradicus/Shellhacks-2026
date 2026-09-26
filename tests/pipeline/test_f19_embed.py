"""F19 semantic search: text builders, cosine neighbors, offline-first runner with cache reuse."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from common import load_json, validate
from embeddings.neighbors import cosine, top_k
from embeddings.runner import run_batch
from embeddings.texts import brief_text, match_text, project_text

NOW = "2026-09-26T12:00:00Z"


def synth_project(key="DESC:1", utility="DESC", active=True) -> dict:
    """Clearly synthetic project; never real filing data."""
    return {
        "_id": f"{key}@test-source",
        "project_key": key,
        "utility": utility,
        "name": f"Synthetic project {key}",
        "active": active,
        "endpoints": [{"name": "Alpha Sub"}, {"name": "Beta Sub"}],
        "voltages_kv": [115],
        "in_service": {"date": "2028-06-01"},
        "description": "synthetic description",
        "source": {"source_id": "test-source"},
    }


def synth_match() -> dict:
    return {
        "_id": "DESC:1__GPC:2",
        "a": "DESC:1",
        "b": "GPC:2",
        "band": 0,
        "distance_mi": 3.032894,
        "time_gap_days": 1,
        "view": "historical",
        "review_state": "needs_review",
    }


def synth_brief(validation="passed") -> dict:
    return {
        "_id": "brief-1",
        "match_id": "DESC:1__GPC:2",
        "input_hash": "0" * 64,
        "model": "test",
        "prompt_version": "test",
        "generated_at": NOW,
        "supported_facts": [{"text": "The projects are 3.03 miles apart.", "fact_ids": ["f1"]}],
        "possible_shared_activities": [{"text": "Possible shared freight window.", "fact_ids": ["f1"]}],
        "questions": ["Can outage windows align?"],
        "limitations": [],
        "validation": validation,
    }


def fake_vectors(texts: list[str]) -> list[list[float]]:
    """Deterministic non-zero vectors derived from the text, 4 dims."""
    return [[float(len(t) % 5) + 1.0, float(len(t) % 3) + 1.0, 1.0, 0.5] for t in texts]


def make_root(tmp_path: Path, *, with_brief=True) -> Path:
    def write(rel: str, obj) -> None:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj))

    write("data/projects/desc.json", [synth_project()])
    write("data/projects/gpc.json", [synth_project("GPC:2", "GPC")])
    write("data/matches/matches.json", [synth_match()])
    if with_brief:
        write("data/briefs/briefs.json", [synth_brief()])
    return tmp_path


def test_project_text_lists_facts_and_unknowns():
    text = project_text(synth_project())
    assert "DESC:1 (DESC): Synthetic project DESC:1" in text
    assert "Alpha Sub, Beta Sub" in text and "115 kV" in text and "2028-06-01" in text
    bare = synth_project() | {"endpoints": [], "voltages_kv": [], "in_service": {"date": None}, "description": ""}
    text = project_text(bare)
    assert "unknown endpoints" in text and "unknown voltage" in text and "unknown in-service date" in text


def test_match_text_joins_both_sides():
    projects = {"DESC:1": synth_project(), "GPC:2": synth_project("GPC:2", "GPC")}
    text = match_text(synth_match(), projects)
    assert "3.03 miles apart" in text and "band 0" in text and "1 days apart" in text
    assert "Synthetic project GPC:2" in text
    missing = match_text(synth_match(), {})
    assert "unknown utility" in missing and "unnamed project" in missing


def test_brief_text_concatenates_grounded_sections():
    text = brief_text(synth_brief())
    assert "3.03 miles apart" in text and "freight window" in text and "outage windows" in text


def test_cosine_and_top_k():
    assert cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine([0.0, 0.0], [1.0, 1.0]) == 0.0
    records = [
        {"_id": "emb:match:a", "kind": "match", "ref_id": "a", "vector": [1.0, 0.0]},
        {"_id": "emb:match:b", "kind": "match", "ref_id": "b", "vector": [0.9, 0.1]},
        {"_id": "emb:project:c", "kind": "project", "ref_id": "c", "vector": [0.0, 1.0]},
    ]
    [na, nb, nc] = top_k(records, k=2)
    assert [n["ref_id"] for n in na["neighbors"]] == ["b", "c"]  # nearest first, never self
    assert na["neighbors"][0]["rank"] == 1 and na["neighbors"][0]["score"] > na["neighbors"][1]["score"]
    assert [n["ref_id"] for n in nb["neighbors"]] == ["a", "c"]
    assert nc["neighbors"][0]["ref_id"] in ("a", "b")


def test_offline_defers_and_writes_nothing(tmp_path):
    root = make_root(tmp_path)
    summary = run_batch(repo_root=root, live=False, now=NOW)
    assert summary["status"] == "deferred" and summary["reason"] == "live_execution_deferred"
    assert summary["needed"] == 4  # match + 2 projects + brief
    assert not (root / "data/embeddings/embeddings.json").exists()
    assert not (root / "data/neighbors/neighbors.json").exists()


def test_live_run_writes_schema_valid_outputs(tmp_path):
    root = make_root(tmp_path)
    summary = run_batch(repo_root=root, live=True, embed_fn=fake_vectors, now=NOW)
    assert summary["status"] == "ok" and summary["embedded"] == 4 and summary["neighbors"] == 4
    embeddings = load_json(root / "data/embeddings/embeddings.json")
    neighbors = load_json(root / "data/neighbors/neighbors.json")
    for rec in embeddings:
        validate(rec, "embedding")
        assert rec["dimensions"] == 4 and rec["model"] and rec["embedded_at"] == NOW
    for rec in neighbors:
        validate(rec, "neighbor")
    by_id = {rec["_id"]: rec for rec in embeddings}
    assert "emb:match:DESC:1__GPC:2" in by_id and "emb:brief:brief-1" in by_id
    assert by_id["emb:match:DESC:1__GPC:2"]["text"].startswith("Coordination pair DESC:1")
    assert {rec["_id"] for rec in neighbors} == {f"nbr:{rec['kind']}:{rec['ref_id']}" for rec in embeddings}


def test_rerun_reuses_cache_and_embeds_only_changes(tmp_path):
    root = make_root(tmp_path)
    run_batch(repo_root=root, live=True, embed_fn=fake_vectors, now=NOW)

    def boom(texts):
        raise AssertionError(f"unexpected embed call for {len(texts)} texts")

    again = run_batch(repo_root=root, live=True, embed_fn=boom, now=NOW)
    assert again["embedded"] == 0 and again["cached"] == 4

    matches = load_json(root / "data/matches/matches.json")
    matches[0]["distance_mi"] = 9.5  # changes the match's search text
    (root / "data/matches/matches.json").write_text(json.dumps(matches))
    seen = []

    def spy(texts):
        seen.extend(texts)
        return fake_vectors(texts)

    third = run_batch(repo_root=root, live=True, embed_fn=spy, now=NOW)
    assert third["embedded"] == 1 and third["cached"] == 3
    assert len(seen) == 1 and "9.50 miles apart" in seen[0]


def test_rejected_briefs_and_inactive_projects_are_excluded(tmp_path):
    root = make_root(tmp_path, with_brief=False)
    (root / "data/briefs/briefs.json").parent.mkdir(parents=True, exist_ok=True)
    (root / "data/briefs/briefs.json").write_text(json.dumps([synth_brief("rejected")]))
    projects = load_json(root / "data/projects/gpc.json")
    projects[0]["active"] = False
    (root / "data/projects/gpc.json").write_text(json.dumps(projects))
    summary = run_batch(repo_root=root, live=True, embed_fn=fake_vectors, now=NOW)
    embeddings = load_json(root / "data/embeddings/embeddings.json")
    kinds = sorted(rec["kind"] for rec in embeddings)
    assert kinds == ["match", "project"]  # no brief, no inactive project
    assert summary["corpus"] == 2
