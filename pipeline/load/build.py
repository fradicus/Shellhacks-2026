"""Pure half of the loader: read data/, validate, join locations into projects, stage per dataset. No database I/O."""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from briefs.facts import current_input_hash
from common import SchemaError, load_json, validate
from load.review_subjects import FINGERPRINT_VERSION, current_subjects, subject_hash, supporting_endpoints
from matches.core import center

# data/ prefix -> (collection, schema). Anything else under data/ (fixtures, osm, owners, summaries) is not loaded.
SOURCES: list[tuple[str, str, str]] = [
    ("data/sources/", "sources", "source"),
    ("data/projects/", "projects", "project"),
    ("data/locations/", "locations", "location"),
    ("data/matches/", "matches", "match"),
    ("data/briefs/", "briefs", "brief"),
    ("data/extraction/", "extractions", "extraction"),
    ("data/review/", "reviews", "review"),
    ("data/coverage/", "coverage", "coverage"),
    ("data/versions/", "version_changes", "version_change"),
    ("data/embeddings/", "embeddings", "embedding"),
    ("data/neighbors/", "neighbors", "neighbor"),
]
# Stored collections (locations are joined into projects rather than stored on their own).
COLLECTIONS = ["sources", "projects", "matches", "briefs", "extractions", "reviews", "coverage", "version_changes",
               "embeddings", "neighbors"]
CONFIDENCE_RANK = {"high": 0, "medium": 1, "low": 2}
# F13 audit verdict -> match.review_state. Any other verdict is kept as evidence but changes nothing.
PAIR_VERDICTS = {"confirmed": "confirmed", "downgraded": "rejected", "rejected": "rejected"}
# (match_id, staged records with joined projects) -> the hash of that match's current brief input facts, or None.
BriefHash = Callable[[str, dict[str, list[dict]]], str | None]


def _records_in(obj: Any) -> list | None:
    """A file holds a JSON array of records, or one record (an object with `_id`). Other objects (summaries) are
    skipped; non-object entries inside an array come back as-is so collect() reports them as errors."""
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict) and "_id" in obj:
        return [obj]
    return None


def collect(root: Path) -> tuple[dict[str, list[dict]], list[str], list[str]]:
    """Return (records by collection, validation errors, skipped files). Validates every record against its schema."""
    records: dict[str, list[dict]] = {name: [] for _, name, _ in SOURCES}
    errors: list[str] = []
    skipped: list[str] = []
    for prefix, coll, schema in SOURCES:
        base = root / prefix
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.json")):
            rel = path.relative_to(root).as_posix()  # same diagnostics on Windows workers
            try:
                recs = _records_in(load_json(path))
            except ValueError as e:
                errors.append(f"{rel}: invalid JSON ({e})")
                continue
            if recs is None:
                skipped.append(rel)
                continue
            for i, rec in enumerate(recs):
                if not isinstance(rec, dict):
                    errors.append(f"{rel}[{i}]: not a JSON object ({type(rec).__name__})")
                    continue
                if coll == "locations" and "_id" not in rec:
                    rec = {**rec, "_id": f"{rec.get('project_key')}#{rec.get('endpoint_index')}#{i}"}
                try:
                    validate(rec, schema)
                except SchemaError as e:
                    errors.append(f"{rel}[{i}]: {e}")
                    continue
                records[coll].append(rec)
    for coll, recs in records.items():
        seen: set[str] = set()
        for r in recs:
            if r["_id"] in seen:
                errors.append(f"{coll}: duplicate _id {r['_id']!r}")
            seen.add(r["_id"])
    records["locations"], bind_errors = bind_locations(records["projects"], records["locations"])
    errors += bind_errors
    # A filing version has at most two endpoints, one accepted location each; rejected candidates are kept as
    # evidence. core.center averages whatever it's given, so an extra accepted candidate would silently move the center.
    accepted: dict[tuple[str, int], list[str]] = {}
    for loc in records["locations"]:
        if loc["confidence"] == "rejected":
            continue
        if loc["endpoint_index"] not in (0, 1):
            errors.append(f"locations: {loc['_id']!r} is accepted with endpoint_index {loc['endpoint_index']}; "
                          "only 0 and 1 exist")
        accepted.setdefault((loc["project_id"], loc["endpoint_index"]), []).append(loc["_id"])
    for (pid, index), ids in sorted(accepted.items()):
        if len(ids) > 1:
            errors.append(f"locations: {len(ids)} accepted candidates for {pid!r} endpoint {index}: {sorted(ids)}")
    return records, errors, skipped


def bind_locations(projects: list[dict], locations: list[dict]) -> tuple[list[dict], list[str]]:
    """Each location is evidence for exactly one filing version (#47): its `project_id`, or `<project_key>@<source_id>`
    when only `source_id` is given. That version must exist and agree with the location's `project_key` (and
    `source_id`). A legacy location naming neither binds to the key's only active version; with zero or several active
    versions it can't be placed and is an error. Superseded filings never inherit the current filing's coordinates.
    Returns the bindable locations with `project_id` filled in, plus one error per location left out."""
    by_id = {p["_id"]: p for p in projects}
    active: dict[str, list[str]] = {}
    for p in projects:
        if p["active"]:
            active.setdefault(p["project_key"], []).append(p["_id"])
    out: list[dict] = []
    errors: list[str] = []
    for loc in locations:
        key, pid, sid = loc["project_key"], loc.get("project_id"), loc.get("source_id")
        if pid is None and sid is not None:
            pid = f"{key}@{sid}"
        if pid is None:
            versions = active.get(key, [])
            if len(versions) != 1:
                errors.append(f"locations: {loc['_id']!r} names no filing version and {key!r} has "
                              f"{len(versions)} active versions")
                continue
            pid = versions[0]
        p = by_id.get(pid)
        if p is None:
            errors.append(f"locations: {loc['_id']!r} is bound to unknown project {pid!r}")
        elif p["project_key"] != key or (sid is not None and sid != p["source"]["source_id"]):
            errors.append(f"locations: {loc['_id']!r} (project_key {key!r}, source_id {sid!r}) contradicts "
                          f"project {pid!r}")
        else:
            out.append({**loc, "project_id": pid})
    return out, errors


def join_projects(projects: list[dict], locations: list[dict]) -> list[dict]:
    """Attach each filing version's own endpoints (bind_locations); compute center (pipeline/matches/core.center),
    weakest used confidence and a GeoJSON point. Unbindable locations are dropped here; collect() reports them."""
    by_id: dict[str, list[dict]] = {}
    for loc in bind_locations(projects, locations)[0]:
        by_id.setdefault(loc["project_id"], []).append(loc)
    out = []
    for p in projects:
        eps = sorted(by_id.get(p["_id"], []), key=lambda e: (e["endpoint_index"], e["_id"]))
        joined = dict(p)
        # Parsers (F01/F02) emit filed endpoint names under `endpoints`; keep them apart from located endpoints.
        if "endpoints" in joined:
            joined["filed_endpoints"] = joined.pop("endpoints")
        if eps:
            joined["endpoints"] = eps
            joined["center"] = center(eps)
            used = [e["confidence"] for e in eps if e["confidence"] != "rejected" and e.get("lat") is not None]
            joined["location_confidence"] = max(used, key=CONFIDENCE_RANK.__getitem__) if used else None
        c = joined.setdefault("center", None)  # unlocated stays null and visible
        joined["geo"] = {"type": "Point", "coordinates": [c["lon"], c["lat"]]} if c else None
        out.append(joined)
    return out


def _utc(at: str) -> datetime | None:
    try:
        t = datetime.fromisoformat(at)
    except ValueError:
        return None
    return t if t.tzinfo else None


def decide(reviews: list[dict], subjects: dict[tuple[str, str], dict]) -> dict[tuple[str, str], str]:
    """Apply the complete newest decision group only when every member is bound to the current subject.

    Equal-time decisions are one conservative group: any stale, missing, or unsupported binding makes the result
    needs_review regardless of input order. If every binding is current, a downgrade wins. Older evidence never
    substitutes for an invalid newest group. Other verdicts and undated reviews are ignored.
    """
    Decision = tuple[str, str | None, str | None]
    latest: dict[tuple[str, str], tuple[datetime, list[Decision]]] = {}
    for r in reviews:
        state, at = PAIR_VERDICTS.get(r["verdict"]), _utc(r["at"])
        if state is None or at is None:
            continue
        key = (r.get("subject_type", "pair"), r["record_id"])
        decision = (state, r.get("fingerprint_version"), r.get("subject_hash"))
        cur = latest.get(key)
        if cur is None or at > cur[0]:
            latest[key] = (at, [decision])
        elif at == cur[0]:
            cur[1].append(decision)

    decided: dict[tuple[str, str], str] = {}
    for key, (_, group) in latest.items():
        subject = subjects.get(key)
        current_hash = subject_hash(subject) if subject is not None else None
        if current_hash is None or any(version != FINGERPRINT_VERSION or value != current_hash
                                       for _, version, value in group):
            decided[key] = "needs_review"
        else:
            decided[key] = "rejected" if any(state == "rejected" for state, _, _ in group) else "confirmed"
    return decided


def apply_reviews(matches: list[dict], reviews: list[dict], subjects: dict[tuple[str, str], dict]) -> list[dict]:
    """Set each match's review_state from its decided pair review. A confirmation also needs every supporting endpoint
    (the located ones its centers rest on) to carry a current confirmed review; otherwise the pair stays
    needs_review. Matches with no current bound decision always need review, regardless of producer state."""
    decided = decide(reviews, subjects)
    out = []
    for m in matches:
        key = ("pair", m["_id"])
        state = decided.get(key, "needs_review")
        if state == "confirmed":
            eps = supporting_endpoints(subjects[key])
            if not eps or any(decided.get(("endpoint", e)) != "confirmed" for e in eps):
                state = "needs_review"
        out.append({**m, "review_state": state})
    return out


def check_briefs(briefs: list[dict], ready: dict[str, list[dict]], brief_hash: BriefHash | None) -> list[dict]:
    """A passed brief stays passed only if its input_hash equals the hash of its match's current facts. Otherwise it
    is stored as rejected with the reason (original verdict in `source_validation`), so no route shows it approved."""
    match_ids = {m["_id"] for m in ready.get("matches", [])}
    out = []
    for b in briefs:
        current = brief_hash(b["match_id"], ready) if brief_hash and b["match_id"] in match_ids else None
        if b["validation"] != "passed" or (current is not None and current == b["input_hash"]):
            out.append(b)
            continue
        if b["match_id"] not in match_ids:
            reason = "stale: match is not in this dataset"
        elif current is None:
            reason = "unverified: current input_hash could not be derived"
        else:
            reason = "stale: input facts changed since generation"
        out.append({**b, "validation": "rejected", "source_validation": "passed", "rejection_reason": reason})
    return out


def stage(records: dict[str, list[dict]], dataset: str,
          brief_hash: BriefHash | None = current_input_hash) -> dict[str, list[dict]]:
    """Documents as stored: `_id` = `<dataset>:<record _id>`, plus `id` and `dataset`. The API maps `id` back to `_id`.

    The default F12 callback verifies brief facts after joining locations and before dataset-prefixing ids. Passing
    None explicitly keeps the fail-closed unverified behavior available to callers and tests."""
    ready = dict(records)
    ready["projects"] = join_projects(records.get("projects", []), records.get("locations", []))
    ready["matches"] = apply_reviews(records.get("matches", []), records.get("reviews", []), current_subjects(ready))
    ready["briefs"] = check_briefs(records.get("briefs", []), ready, brief_hash)
    return {
        coll: [{**r, "_id": f"{dataset}:{r['_id']}", "id": r["_id"], "dataset": dataset} for r in ready.get(coll, [])]
        for coll in COLLECTIONS
    }
