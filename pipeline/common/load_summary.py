"""One structured summary per load run: what was staged, what is active, and the operational metrics around it.

Every load ends in exactly one named outcome, printed as a `<stage>: summary {...}` JSON line, appended to the GitHub
step summary when there is one, and written to `LOAD_METRICS_PATH` when that is set. Unknown values stay null.
"""

from __future__ import annotations

import json
import os
from typing import Any

# Wrote and activated a new release.
ACTIVATED = "activated"
# The requested release was already active; nothing written.
ALREADY_ACTIVE = "already_active"
# The requested release is intact in Atlas but another is active; nothing written, pointer unchanged.
RETAINED_INACTIVE = "retained_inactive"
# Pointer moved to an intact retained release (rollback or explicit activation); nothing re-staged.
REACTIVATED = "reactivated"
# The run receipt says this release loaded once, but retention pruned its documents; refused without --restage.
PRUNED_RECEIPT = "pruned_receipt"
# No write credentials: every record validated, nothing written.
VALIDATED_ONLY = "validated_only"
# Records failed validation; nothing written, pointer unchanged.
VALIDATION_FAILED = "validation_failed"
# A write or activation step failed; the previously active release is still served.
PUBLICATION_FAILED = "publication_failed"

SUCCESS = {ACTIVATED, ALREADY_ACTIVE, RETAINED_INACTIVE, REACTIVATED, VALIDATED_ONLY}


def source_freshness(sources: list[dict[str, Any]]) -> dict[str, Any]:
    """Oldest and newest `retrieved_at` over sources that record one; how many do not."""
    stamps = sorted(s["retrieved_at"] for s in sources if isinstance(s.get("retrieved_at"), str) and s["retrieved_at"])
    return {
        "sources": len(sources),
        "oldest_retrieved_at": stamps[0] if stamps else None,
        "newest_retrieved_at": stamps[-1] if stamps else None,
        "without_retrieved_at": len(sources) - len(stamps),
    }


def summary(
    stage: str,
    outcome: str,
    *,
    requested: str | None,
    staged: str | None,
    active: str | None,
    previous: str | None,
    counts: dict[str, Any],
    freshness: dict[str, Any] | None,
    quarantined: dict[str, Any] | None,
    failures: list[str] | None = None,
    detail: str | None = None,
) -> dict[str, Any]:
    return {
        "stage": stage,
        "outcome": outcome,
        "ok": outcome in SUCCESS,
        "release": {"requested": requested, "staged": staged, "active": active, "previous": previous},
        "counts": counts,
        "source_freshness": freshness,
        "quarantined": quarantined,
        "publication_failures": failures or [],
        "detail": detail,
    }


def sentence(s: dict[str, Any]) -> str:
    r = s["release"]
    staged = f"staged {r['staged']}" if r["staged"] else "staged nothing"
    active = f"active: {r['active']}" if r["active"] else "active: none"
    return f"{s['outcome']}: {staged}; {active}" + (f" (previous: {r['previous']})" if r["previous"] else "")


def emit(s: dict[str, Any]) -> None:
    line = json.dumps(s, sort_keys=True)
    print(f"{s['stage']}: {sentence(s)}")
    if s["detail"]:
        print(f"{s['stage']}: {s['detail']}")
    print(f"{s['stage']}: summary {line}")
    if path := os.environ.get("LOAD_METRICS_PATH"):
        with open(path, "w", encoding="utf-8") as out:
            out.write(line + "\n")
    if step := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(step, "a", encoding="utf-8") as out:
            out.write(f"### {s['stage']}: `{s['outcome']}`\n\n{sentence(s)}\n\n")
            if s["detail"]:
                out.write(f"{s['detail']}\n\n")
            out.write(f"```json\n{json.dumps(s, indent=2, sort_keys=True)}\n```\n\n")
