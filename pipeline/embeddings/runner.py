"""Build the embedding corpus, embed what changed, write data/embeddings/ + data/neighbors/.

Offline-first (like F12 briefs): without live=True every needed-but-missing vector defers the
run — nothing is written, the summary says why. Cached vectors are reused whenever a record's
text_hash and model still match, so reruns cost zero API calls.
"""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path

from common import load_json, validate, write_json
from embeddings.embed import EmbedFn, embed_texts
from embeddings.neighbors import top_k
from embeddings.texts import brief_text, match_text, project_text

DEFAULT_MODEL = os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-001")
DIMENSIONS = 768  # keep in sync with pipeline/load VECTOR_DIMENSIONS and web/app/api/search
NEIGHBOR_K = 10


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def collect_corpus(root: Path) -> list[dict]:
    """{kind, ref_id, text} for every match, active project and passed brief under data/."""
    corpus: list[dict] = []
    projects = []
    projects_dir = root / "data/projects"
    if projects_dir.is_dir():
        for path in sorted(projects_dir.rglob("*.json")):
            projects.extend(load_json(path))
    active_by_key = {p["project_key"]: p for p in projects if p.get("active")}

    matches_path = root / "data/matches/matches.json"
    if matches_path.exists():
        for match in load_json(matches_path):
            corpus.append({"kind": "match", "ref_id": match["_id"], "text": match_text(match, active_by_key)})
    for project in projects:
        if project.get("active"):
            corpus.append({"kind": "project", "ref_id": project["_id"], "text": project_text(project)})
    briefs_path = root / "data/briefs/briefs.json"
    if briefs_path.exists():
        for brief in load_json(briefs_path):
            if brief.get("validation") == "passed":
                corpus.append({"kind": "brief", "ref_id": brief["_id"], "text": brief_text(brief)})
    return [entry for entry in corpus if entry["text"].strip()]


def run_batch(
    *,
    repo_root: Path,
    live: bool,
    embed_fn: EmbedFn | None = None,
    model: str = DEFAULT_MODEL,
    dimensions: int = DIMENSIONS,
    k: int = NEIGHBOR_K,
    now: str | None = None,
) -> dict:
    """Embed the corpus and write both output files. Returns a summary dict (see __main__)."""
    embedded_at = now or datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    corpus = collect_corpus(repo_root)

    cache: dict[tuple[str, str], dict] = {}
    existing_path = repo_root / "data/embeddings/embeddings.json"
    if existing_path.exists():
        for rec in load_json(existing_path):
            cache[(rec["kind"], rec["ref_id"])] = rec

    stale, fresh = [], []
    for entry in corpus:
        hit = cache.get((entry["kind"], entry["ref_id"]))
        if hit and hit["text_hash"] == _text_hash(entry["text"]) and hit["model"] == model:
            fresh.append(hit)
        else:
            stale.append(entry)

    summary = {
        "status": "ok",
        "reason": None,
        "model": model,
        "dimensions": dimensions,
        "corpus": len(corpus),
        "cached": len(fresh),
        "embedded": 0,
        "neighbors": 0,
    }
    if stale and not live:
        summary.update(status="deferred", reason="live_execution_deferred", needed=len(stale))
        return summary

    if stale:
        vectors = (embed_fn or (lambda texts: embed_texts(texts, model=model, dimensions=dimensions)))(
            [entry["text"] for entry in stale]
        )
        if len(vectors) != len(stale):
            raise ValueError(f"embedder returned {len(vectors)} vectors for {len(stale)} texts")
        for entry, vector in zip(stale, vectors, strict=True):
            fresh.append(
                {
                    "_id": f"emb:{entry['kind']}:{entry['ref_id']}",
                    "kind": entry["kind"],
                    "ref_id": entry["ref_id"],
                    "text": entry["text"],
                    "text_hash": _text_hash(entry["text"]),
                    "vector": [float(v) for v in vector],
                    "model": model,
                    "dimensions": len(vector),
                    "embedded_at": embedded_at,
                }
            )
        summary["embedded"] = len(stale)

    fresh.sort(key=lambda rec: rec["_id"])
    for rec in fresh:
        validate(rec, "embedding")

    kind_by_ref = {rec["ref_id"]: rec["kind"] for rec in fresh}
    neighbors = [
        {
            "_id": f"nbr:{kind_by_ref[n['ref_id']]}:{n['ref_id']}",
            "ref_id": n["ref_id"],
            "model": model,
            "computed_at": embedded_at,
            "neighbors": n["neighbors"],
        }
        for n in top_k(fresh, k)
    ]
    for rec in neighbors:
        validate(rec, "neighbor")

    write_json(repo_root / "data/embeddings/embeddings.json", fresh)
    write_json(repo_root / "data/neighbors/neighbors.json", neighbors)
    summary["neighbors"] = len(neighbors)
    return summary
