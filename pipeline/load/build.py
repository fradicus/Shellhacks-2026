"""Pure half of the loader: read data/, validate, join locations into projects, stage per dataset. No database I/O."""

from pathlib import Path
from typing import Any

from common import SchemaError, load_json, validate
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
]
# Stored collections (locations are joined into projects rather than stored on their own).
COLLECTIONS = ["sources", "projects", "matches", "briefs", "extractions", "reviews", "coverage", "version_changes"]
CONFIDENCE_RANK = {"high": 0, "medium": 1, "low": 2}


def _records_in(obj: Any) -> list[dict] | None:
    """A file holds a JSON array of records, or one record (an object with `_id`). Anything else isn't loadable."""
    if isinstance(obj, list) and all(isinstance(r, dict) for r in obj):
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
            rel = str(path.relative_to(root))
            try:
                recs = _records_in(load_json(path))
            except ValueError as e:
                errors.append(f"{rel}: invalid JSON ({e})")
                continue
            if recs is None:
                skipped.append(rel)
                continue
            for i, rec in enumerate(recs):
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
    return records, errors, skipped


def join_projects(projects: list[dict], locations: list[dict]) -> list[dict]:
    """Attach endpoints; compute center (pipeline/matches/core.center), weakest used confidence and a GeoJSON point."""
    by_key: dict[str, list[dict]] = {}
    for loc in locations:
        by_key.setdefault(loc["project_key"], []).append(loc)
    out = []
    for p in projects:
        eps = sorted(by_key.get(p["project_key"], []), key=lambda e: (e["endpoint_index"], e["_id"]))
        joined = dict(p)
        if eps:
            joined["endpoints"] = eps
            joined["center"] = center(eps)
            used = [e["confidence"] for e in eps if e["confidence"] != "rejected" and e.get("lat") is not None]
            joined["location_confidence"] = max(used, key=CONFIDENCE_RANK.__getitem__) if used else None
        c = joined.get("center")
        joined["geo"] = {"type": "Point", "coordinates": [c["lon"], c["lat"]]} if c else None
        out.append(joined)
    return out


def stage(records: dict[str, list[dict]], dataset: str) -> dict[str, list[dict]]:
    """Documents as stored: `_id` = `<dataset>:<record _id>`, plus `id` and `dataset`. The API maps `id` back to `_id`."""
    ready = dict(records)
    ready["projects"] = join_projects(records.get("projects", []), records.get("locations", []))
    return {
        coll: [{**r, "_id": f"{dataset}:{r['_id']}", "id": r["_id"], "dataset": dataset} for r in ready.get(coll, [])]
        for coll in COLLECTIONS
    }
