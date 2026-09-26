"""F06 loader: embedding and neighbor records (F19) — collect, stage, load, vector-index safety."""

from __future__ import annotations

import json
from pathlib import Path

import mongomock

from load.__main__ import ensure_vector_index, load
from load.build import collect, stage


def write(root: Path, rel: str, obj) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj))


def embedding_record(ref_id: str = "DESC:1__GPC:2", kind: str = "match", dims: int = 4) -> dict:
    return {
        "_id": f"emb:{kind}:{ref_id}",
        "kind": kind,
        "ref_id": ref_id,
        "text": "synthetic search text",
        "text_hash": "0" * 64,
        "vector": [0.1] * dims,
        "model": "test-embed",
        "dimensions": dims,
        "embedded_at": "2026-09-26T12:00:00Z",
    }


def neighbor_record(ref_id: str = "DESC:1__GPC:2") -> dict:
    return {
        "_id": f"nbr:match:{ref_id}",
        "ref_id": ref_id,
        "model": "test-embed",
        "computed_at": "2026-09-26T12:00:00Z",
        "neighbors": [{"ref_id": "DESC:3__GPC:4", "kind": "match", "score": 0.9, "rank": 1}],
    }


def test_collect_reads_embeddings_and_neighbors(tmp_path):
    write(tmp_path, "data/embeddings/embeddings.json", [embedding_record()])
    write(tmp_path, "data/neighbors/neighbors.json", [neighbor_record()])
    records, errors, skipped = collect(tmp_path)
    assert errors == []
    assert [r["_id"] for r in records["embeddings"]] == ["emb:match:DESC:1__GPC:2"]
    assert [r["_id"] for r in records["neighbors"]] == ["nbr:match:DESC:1__GPC:2"]
    assert skipped == []


def test_invalid_embedding_record_blocks_activation(tmp_path):
    bad = embedding_record() | {"vector": ["not-a-number"] * 4}
    write(tmp_path, "data/embeddings/embeddings.json", [bad])
    records, errors, _ = collect(tmp_path)
    assert any("data/embeddings/embeddings.json[0]" in e for e in errors)
    assert records["embeddings"] == []
    db = mongomock.MongoClient().db
    assert load(db, records, errors, "bad") == 1
    assert db.meta.find_one({"_id": "active"}) is None


def test_stage_namespaces_embedding_and_neighbor_ids(tmp_path):
    write(tmp_path, "data/embeddings/embeddings.json", [embedding_record()])
    write(tmp_path, "data/neighbors/neighbors.json", [neighbor_record()])
    records, errors, _ = collect(tmp_path)
    assert errors == []
    staged = stage(records, "abc")
    assert staged["embeddings"][0]["_id"] == "abc:emb:match:DESC:1__GPC:2"
    assert staged["embeddings"][0]["id"] == "emb:match:DESC:1__GPC:2"
    assert staged["neighbors"][0]["dataset"] == "abc"


def test_load_stores_embeddings_and_prunes_old_datasets(tmp_path):
    write(tmp_path, "data/embeddings/embeddings.json", [embedding_record()])
    write(tmp_path, "data/neighbors/neighbors.json", [neighbor_record()])
    db = mongomock.MongoClient().db
    for sha in ("s1", "s2", "s3"):
        records, errors, _ = collect(tmp_path)
        assert load(db, records, errors, sha) == 0
    assert sorted(db.embeddings.distinct("dataset")) == ["s2", "s3"]
    assert sorted(db.neighbors.distinct("dataset")) == ["s2", "s3"]


def test_vector_index_helper_never_breaks_mongomock_loads(tmp_path, capsys):
    write(tmp_path, "data/embeddings/embeddings.json", [embedding_record()])
    db = mongomock.MongoClient().db
    records, errors, _ = collect(tmp_path)
    assert load(db, records, errors, "sha1") == 0
    assert db.meta.find_one({"_id": "active"})["dataset"] == "sha1"
    assert "vector index" in capsys.readouterr().out  # warned, did not fail
    ensure_vector_index(db)  # direct call is safe too
