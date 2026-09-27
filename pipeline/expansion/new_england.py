"""Replay the approved ISO-NE source and prepare a non-publishable research cohort.

From pipeline: uv run python -m expansion.new_england --source /path/to/pinned.xlsx
Add --check to verify committed outputs without rewriting them. No network or Atlas writes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from common import REPO_ROOT, load_json
from national.iso_ne import SOURCE_ID, parse
from national.registry import entries

BATCH = Path("data/expansion/batches") / SOURCE_ID
COHORT_SIZE = 300
STATE_NAMES = {"09": "CT", "23": "ME", "25": "MA", "33": "NH", "44": "RI", "50": "VT"}
ACTIVE = {"planned", "proposed", "under_construction"}


def encode(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def facts_hash(project: dict) -> str:
    return hashlib.sha256(encode(project).encode()).hexdigest()


def artifacts(projects: list[dict], source: dict) -> dict[Path, str]:
    """Deterministic research prioritization, never a location or lifecycle approval."""
    ids = [p["_id"] for p in projects]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate project identities")
    for p in projects:
        if p["source_id"] != SOURCE_ID or p["evidence"]["source_sha256"] != source["sha256"]:
            raise ValueError("project evidence does not match the pinned source")
        if p["center"] is not None or p["location_review"] != "unlocated":
            raise ValueError("this source replay cannot approve coordinates")
        if set(p["states"]) - STATE_NAMES.keys():
            raise ValueError("state outside New England")
        if p["status_group"] not in ACTIVE | {"in_service", "cancelled"}:
            raise ValueError("unreviewed lifecycle status")
    active = sorted((p for p in projects if p["status_group"] in ACTIVE), key=lambda p: int(p["native_id"]))
    history = sorted((p for p in projects if p["status_group"] == "in_service"),
                     key=lambda p: int(p["native_id"]), reverse=True)
    if len(active) > COHORT_SIZE or len(active) + len(history) < COHORT_SIZE:
        raise ValueError("source no longer fits the reviewed 300-project selection")
    cohort = active + history[:COHORT_SIZE - len(active)]
    selected = {p["_id"] for p in cohort}
    dispositions = [{
        "project_id": p["_id"], "row": p["evidence"]["row"], "status_group": p["status_group"],
        "disposition": "selected_for_research" if p["_id"] in selected else "deferred",
        "reason": ("nonhistorical_source_status" if p["status_group"] in ACTIVE else "historical_research_cohort")
        if p["_id"] in selected else ("cancelled_cohort_deferred" if p["status_group"] == "cancelled"
                                     else "outside_first_300_research_cohort"),
    } for p in sorted(projects, key=lambda p: int(p["native_id"]))]
    summary = {
        "schema_version": "f38-research-v1", "publication_eligible": False,
        "source_id": SOURCE_ID, "source_sha256": source["sha256"], "source_url": source["url"],
        "source_status_as_of": "2026-06", "source_publication_at": source["published_at"],
        "source_retrieval_at": source["retrieved_at"],
        "selection": "All nonhistorical statuses, then in-service descending native ID; ID order is not chronology.",
        "source_rows_reconciled": len(projects), "cohort_count": len(cohort),
        "source_status_counts": dict(Counter(p["status_group"] for p in projects)),
        "cohort_status_counts": dict(Counter(p["status_group"] for p in cohort)),
        "cohort_state_counts": dict(Counter(STATE_NAMES[s] for p in cohort for s in p["states"])),
        "cohort_unknown_state_count": sum(not p["states"] for p in cohort),
        "deferred_count": len(projects) - len(cohort),
        "confirmed_location_count": 0, "distinct_confirmed_site_count": 0, "published_count": 0,
        "statewide_project_denominators": {state: None for state in STATE_NAMES.values()},
        "limitations": [
            "Source-backed records are not verified map points; every coordinate remains null.",
            "Status is reported as of June 2026, not independently verified current activity.",
            "Projected in-service month/year is not actual construction start or completion.",
            "PTF estimates are not total project cost, contract awards or actual spend.",
            "RSP component IDs do not establish distinct sites or deduplication across planning programs.",
            "Independent workbook review is separate from this deterministic parser replay.",
            "This is the existing pinned vintage; latest-source and prior-vintage comparison remain pending.",
        ],
    }
    bullets = ["# New England: 300 source-backed research bullets", "",
               "**Verified map points: 0. Published expansion records: 0.**", "",
               f"[ISO-NE June 2026 RSP workbook]({source['url']}); sheet `RSP_sortable`.", "",
               "All 46 planned/proposed/construction rows, then 254 historical in-service rows by descending native ID.",
               "ID order is a research priority, not a date. Status is as of June 2026. Dates below are projected milestones.",
               "Every bullet still needs project-linked location evidence and independent location review.", ""]
    for p in cohort:
        name = " ".join(p["name"].split()).replace("[", "\\[").replace("]", "\\]")
        state = ", ".join(STATE_NAMES[s] for s in p["states"]) or "state unknown"
        milestone = p["in_service"]["value"] or "unknown"
        bullets.append(f"- **{p['_id']} · {state} · {p['status']}** — {name} "
                       f"Owner: {p['owner']}. Projected in-service: {milestone}. "
                       f"[Source row {p['evidence']['row']}]({source['url']}). Location: unlocated.")
    return {
        BATCH / "research-cohort.json": encode({"summary": summary, "projects": cohort,
                                                "project_facts_sha256": {p["_id"]: facts_hash(p) for p in cohort}}),
        BATCH / "dispositions.json": encode(dispositions),
        Path("reports/expansion/new-england-bullets.md"): "\n".join(bullets) + "\n",
    }


def replay(source_path: Path, root: Path = REPO_ROOT) -> dict[Path, str]:
    source = entries(root)[SOURCE_ID]
    if source_path.stat().st_size > source["max_bytes"]:
        raise ValueError("source exceeds approved size")
    if hashlib.sha256(source_path.read_bytes()).hexdigest() != source["sha256"]:
        raise ValueError("source SHA-256 mismatch")
    projects = parse(source_path, load_json(root / "data/national/geography.json"), source["sha256"])
    baseline = [p for p in load_json(root / "data/national/projects.json") if p["source_id"] == SOURCE_ID]
    if sorted(projects, key=lambda p: p["_id"]) != sorted(baseline, key=lambda p: p["_id"]):
        raise ValueError("source replay differs from committed F30 records; investigate before proceeding")
    return artifacts(projects, source)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = replay(args.source)
    for relative, content in outputs.items():
        path = REPO_ROOT / relative
        if args.check:
            if not path.exists() or path.read_text() != content:
                raise ValueError(f"research artifact differs: {relative}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    print("Reconciled 1,024 source records; prepared 300 research records; 0 confirmed or published map points.")


if __name__ == "__main__":
    main()
