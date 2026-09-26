"""Validate source bytes and exact JSON-pointer values before accepting actual outcomes."""

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

from outcomes.contracts import Bundle, Observation, Source, day, timestamp

MAX_SOURCE_BYTES = 16 * 1024 * 1024


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def strict_json(raw: bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError(f"nonfinite JSON: {value}")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def read_bounded(path: Path) -> bytes:
    with path.open("rb") as stream:
        raw = stream.read(MAX_SOURCE_BYTES + 1)
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError("source exceeds 16 MiB budget")
    return raw


def pointer(document, path: str):
    value = document
    for part in path[1:].split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not key.isdecimal() or str(int(key)) != key:
                raise ValueError("invalid array pointer")
            value = value[int(key)]
        else:
            value = value[key]
    return value


def available(source: Source) -> str:
    return max(source.published_at, source.received_at, source.reviewed_at)


def validate_bundle(bundle: Bundle, *, as_of: str, allow_test: bool = False) -> tuple[list[Observation], list[dict]]:
    timestamp(as_of)
    if bundle.purpose != "authorized_actual_history" and not allow_test:
        raise ValueError("synthetic test histories cannot create operational models")
    sources = {}
    documents = {}
    source_bytes = 0
    for source in bundle.sources:
        if source.id in sources:
            raise ValueError("duplicate source id")
        if not source.published_at <= source.received_at <= source.reviewed_at <= as_of:
            raise ValueError("source publication, receipt and review are out of order or future")
        source_path = Path(source.local_path)
        if not source_path.is_absolute() or source_path.suffix.lower() != ".json":
            raise ValueError("source must be an absolute local JSON export path")
        raw = read_bounded(source_path)
        source_bytes += len(raw)
        if source_bytes > 64 * 1024 * 1024:
            raise ValueError("source bundle exceeds aggregate 64 MiB budget")
        if hashlib.sha256(raw).hexdigest() != source.sha256:
            raise ValueError("source hash mismatch")
        documents[source.id] = strict_json(raw)
        sources[source.id] = source

    def check(row):
        evidence = row.evidence
        if evidence.source_id not in sources:
            raise ValueError("unknown evidence source")
        expected = row.model_dump(exclude={"evidence"})
        actual = pointer(documents[evidence.source_id], evidence.pointer)
        if not isinstance(actual, dict) or any(actual.get(key) != value for key, value in expected.items()):
            raise ValueError("imported values differ from their source pointer")
        return sources[evidence.source_id]

    id_counts = Counter(job.id for job in bundle.jobs)
    lineage_counts = Counter(job.project_lineage for job in bundle.jobs)
    event_counts = Counter(event.id for event in bundle.events)
    event_index = {}
    for event in bundle.events:
        event_index.setdefault(event.job_id, []).append(event)
    reviews = {}
    for review in bundle.reviews:
        reviews.setdefault(review.job_id, []).append(review)
    accepted, quarantine = [], []
    for job in sorted(bundle.jobs, key=lambda row: row.id):
        try:
            if id_counts[job.id] != 1 or lineage_counts[job.project_lineage] != 1:
                raise ValueError("duplicate job or project lineage; revisions/components cannot cross folds")
            review_rows = reviews.get(job.id, [])
            if len(review_rows) != 1 or review_rows[0].decision != "accepted":
                raise ValueError("missing, rejected, repeated or unresolved review")
            review = review_rows[0]
            if review.reviewed_at > as_of:
                raise ValueError("future review")
            feature_source = check(job)
            features_available = max(available(feature_source), job.features_known_at)
            if features_available > job.decision_at or job.decision_at > as_of:
                raise ValueError("features were not available at decision time")
            events = event_index.get(job.id, [])
            grouped = {}
            evidence_sources = [feature_source]
            for event in events:
                if event_counts[event.id] != 1 or event.component_id != job.component_id:
                    raise ValueError("duplicate event identity or component mismatch")
                source = check(event)
                evidence_sources.append(source)
                if event.precision != "day" or event.date is None:
                    raise ValueError("coarse or missing date is not an exact actual/planned anchor")
                day(event.date)
                if event.known_at > as_of or event.known_at < source.published_at:
                    raise ValueError("event knowledge timestamp contradicts source publication")
                if event.actuality == "actual" and event.date > min(as_of[:10], source.published_at[:10], event.known_at[:10]):
                    raise ValueError("actual event was reported before it happened or is in the future")
                grouped.setdefault((event.actuality, event.kind), []).append((event, source))

            def one(actuality, kind, grouped=grouped):
                rows = grouped.get((actuality, kind), [])
                if len(rows) != 1:
                    raise ValueError("missing or conflicting construction anchor")
                return rows[0]

            start, start_source = one("actual", "construction_start")
            end, end_source = one("actual", "construction_complete")
            if job.decision_at > f"{start.date}T00:00:00Z":
                raise ValueError("decision occurred after construction started")
            duration = (date.fromisoformat(end.date) - date.fromisoformat(start.date)).days
            if not 0 < duration <= 3650:
                raise ValueError("impossible or unsupported construction duration")
            observed = max(available(start_source), available(end_source), start.known_at, end.known_at, review.reviewed_at)
            planned_duration, planned_available = None, None
            if any(key[0] == "planned" for key in grouped):
                pstart, ps = one("planned", "construction_start")
                pend, pe = one("planned", "construction_complete")
                planned_available = max(available(ps), available(pe), pstart.known_at, pend.known_at)
                planned_duration = (date.fromisoformat(pend.date) - date.fromisoformat(pstart.date)).days
                if planned_available > job.decision_at or not 0 < planned_duration <= 3650:
                    raise ValueError("planned duration was not a valid frozen pre-decision baseline")
            accepted.append(
                Observation(
                    job_id=job.id,
                    project_lineage=job.project_lineage,
                    component_id=job.component_id,
                    job_type=job.job_type,
                    company_id=job.company_id,
                    region=job.region,
                    decision_at=job.decision_at,
                    features_available_at=features_available,
                    actual_start=start.date,
                    actual_complete=end.date,
                    available_at=observed,
                    duration_days=duration,
                    planned_duration_days=planned_duration,
                    planned_available_at=planned_available,
                    evidence_hashes=sorted({s.sha256 for s in evidence_sources}),
                )
            )
        except (ValueError, KeyError, IndexError, TypeError) as error:
            quarantine.append({"job_id": job.id, "reason": str(error)})
    known_jobs = {job.id for job in bundle.jobs}
    for event in bundle.events:
        if event.job_id not in known_jobs:
            quarantine.append({"job_id": event.job_id, "reason": "orphan event"})
    return accepted, quarantine
