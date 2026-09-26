"""Cosine similarity and top-K neighbors over embedding records. Pure Python; no dependencies."""

from __future__ import annotations

import math


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def top_k(records: list[dict], k: int = 10) -> list[dict]:
    """One neighbor record per input record: its k most similar other records, rank 1..k.

    Similarity is cosine over the stored vectors; ties break by ref_id for determinism.
    A record is never its own neighbor.
    """
    out = []
    for rec in records:
        scored = [
            (cosine(rec["vector"], other["vector"]), other)
            for other in records
            if other["_id"] != rec["_id"]
        ]
        scored.sort(key=lambda pair: (-pair[0], pair[1]["ref_id"]))
        neighbors = [
            {"ref_id": other["ref_id"], "kind": other["kind"], "score": round(score, 6), "rank": rank}
            for rank, (score, other) in enumerate(scored[:k], start=1)
        ]
        out.append({"ref_id": rec["ref_id"], "neighbors": neighbors})
    return out
