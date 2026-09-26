from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .fetch import ARCHIVE_SHA256
from .geography import normalized_name


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_json_sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _unique(records: list[dict[str, Any]], label: str) -> None:
    ids = [record.get("id") for record in records]
    if not all(isinstance(value, str) and value for value in ids) or len(ids) != len(set(ids)):
        raise ValueError(f"{label} IDs must be non-empty and unique")


def _assert_counts(snapshot: dict[str, Any]) -> None:
    counts = snapshot["coverage"]["counts"]
    exact = {
        "sources": len(snapshot["sources"]),
        "utilities": len(snapshot["utilities"]),
        "utility_activities": len(snapshot["utility-activities"]),
        "service_territory_rows": len(snapshot["service-territory"]),
        "assertions": len(snapshot["assertions"]),
        "quarantine": len(snapshot["quarantine"]),
        "utilities_by_validation_status": dict(
            sorted(Counter(item["validation_status"] for item in snapshot["utilities"]).items())
        ),
        "service_territory_by_validation_status": dict(
            sorted(Counter(item["validation_status"] for item in snapshot["service-territory"]).items())
        ),
        "resolved_county_rows": sum(item["validation_status"] == "accepted" for item in snapshot["service-territory"]),
        "unresolved_county_rows": sum(item["validation_status"] == "unresolved" for item in snapshot["service-territory"]),
        "conflicting_county_rows": sum(item["validation_status"] == "conflicting" for item in snapshot["service-territory"]),
        "rejected_county_rows": sum(item["validation_status"] == "rejected" for item in snapshot["service-territory"]),
        "independently_corroborated_service_claims": sum(
            bool(item["independently_corroborated"]) for item in snapshot["assertions"]
        ),
        "comparable_field_conflicts": sum(item["reason"] == "comparable_field_conflict" for item in snapshot["quarantine"]),
        "unknown_utility_rows": sum(item["reason"] == "unknown_utility_number" for item in snapshot["quarantine"]),
        "county_identity_quarantine_rows": sum(
            item["reason"] in {"unresolved_county_identity", "ambiguous_county_identity"} for item in snapshot["quarantine"]
        ),
    }
    if counts != exact:
        raise ValueError("coverage counts do not equal recomputed record denominators")


def validate_snapshot(snapshot: dict[str, Any], geography: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "dataset",
        "generated_at",
        "sources",
        "utilities",
        "utility-activities",
        "service-territory",
        "assertions",
        "quarantine",
        "coverage",
    }
    if set(snapshot) != required or snapshot["schema_version"] != "verified-directory-v1":
        raise ValueError("verified snapshot top-level contract is invalid")
    if not isinstance(snapshot["generated_at"], str) or "T" not in snapshot["generated_at"]:
        raise ValueError("generated_at must be an explicit ISO date-time input")
    for key in ("sources", "utilities", "utility-activities", "service-territory", "assertions", "quarantine"):
        if not isinstance(snapshot[key], list):
            raise ValueError(f"{key} must be an array")
        _unique(snapshot[key], key)
    sources = {item["id"]: item for item in snapshot["sources"]}
    if set(sources) != {"eia-861-2024-final", "census-geography-reference"}:
        raise ValueError("verified source registry must contain the pinned EIA and Census references")
    if sources["eia-861-2024-final"]["content_sha256"] != ARCHIVE_SHA256:
        raise ValueError("EIA source hash does not match the reviewed final archive")
    census = sources["census-geography-reference"]
    if census["content_sha256"] != canonical_json_sha(geography) or "canonical normalized" not in census.get(
        "digest_semantics", ""
    ):
        raise ValueError("Census reference source must bind the canonical normalized geography value")
    utilities = {item["eia_utility_id"]: item for item in snapshot["utilities"]}
    if len(utilities) != len(snapshot["utilities"]):
        raise ValueError("EIA utility numbers must be unique within the 2024 Frame workbook")
    state_ids = {item["state_fips"] for item in geography["states"]}
    county_parent = {item["county_geoid"]: item["state_fips"] for item in geography["counties"]}
    territory_ids = {item["id"] for item in snapshot["service-territory"]}
    quarantine_ids = {item["record_id"] for item in snapshot["quarantine"]}
    expected_hash = sources["eia-861-2024-final"]["content_sha256"]
    for collection in (snapshot["utilities"], snapshot["utility-activities"], snapshot["service-territory"]):
        for item in collection:
            evidence = item.get("evidence")
            if not isinstance(evidence, dict) or evidence.get("source_sha256") != expected_hash:
                raise ValueError("EIA row evidence must bind the reviewed archive hash")
            if evidence.get("source_id") != "eia-861-2024-final" or not isinstance(evidence.get("row"), int):
                raise ValueError("EIA row evidence must bind a source, member, sheet and row")
    for activity in snapshot["utility-activities"]:
        reference = utilities.get(activity["eia_utility_id"])
        conflicts = []
        if reference:
            if normalized_name(reference["name"]) != normalized_name(activity["name"]):
                conflicts.append("name")
            if (
                activity["ownership"]
                and reference["ownership"]
                and normalized_name(reference["ownership"]) != normalized_name(activity["ownership"])
            ):
                conflicts.append("ownership")
        rejected = reference is None or bool(conflicts)
        if rejected != (activity["validation_status"] == "rejected"):
            raise ValueError("activity foreign-key status disagrees with the Frame utility registry")
        state = activity["state_fips"]
        if state is not None and state not in state_ids:
            raise ValueError("activity references an unknown Census state FIPS")
        if rejected and activity["id"] not in quarantine_ids:
            raise ValueError("unknown or conflicting utility activity must be preserved in quarantine")
    for territory in snapshot["service-territory"]:
        reference = utilities.get(territory["eia_utility_id"])
        conflicts = [] if reference and normalized_name(reference["name"]) == normalized_name(territory["name"]) else ["name"]
        state, county = territory["state_fips"], territory["county_geoid"]
        if state is not None and state not in state_ids:
            raise ValueError("service territory references an unknown Census state FIPS")
        if county is not None and (county not in county_parent or county_parent[county] != state):
            raise ValueError("service territory county must exist and belong to its resolved state")
        if territory["validation_status"] == "accepted" and (county is None or reference is None or conflicts):
            raise ValueError("accepted service territory requires a resolved county GEOID")
        if (territory["validation_status"] != "accepted" or reference is None or conflicts) and territory[
            "id"
        ] not in quarantine_ids:
            raise ValueError("non-accepted service territory must be preserved in quarantine")
    for assertion in snapshot["assertions"]:
        target = assertion["id"].removeprefix("assertion-")
        if target not in territory_ids:
            raise ValueError("assertion must bind a service-territory row")
        if assertion["upstream_lineages"] != ["eia-861-2024-final"] or assertion["independent_lineage_count"] != 1:
            raise ValueError("same-lineage EIA rows must not inflate independent corroboration")
        if assertion["independently_corroborated"]:
            raise ValueError("Census identity checks cannot corroborate utility service membership")
    _assert_counts(snapshot)
    content = {
        key: snapshot[key]
        for key in ("sources", "utilities", "utility-activities", "service-territory", "assertions", "quarantine", "coverage")
    }
    if snapshot["dataset"] != hashlib.sha256(_canonical(content)).hexdigest():
        raise ValueError("dataset hash does not match normalized content")


def load_published_snapshot(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root = repo_root / "data" / "verified"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    snapshot: dict[str, Any] = {
        "schema_version": manifest["schema_version"],
        "dataset": manifest["dataset"],
        "generated_at": manifest["generated_at"],
    }
    for name in ("sources", "utilities", "utility-activities", "service-territory", "assertions", "quarantine"):
        path = root / f"{name}.json"
        data = path.read_bytes()
        expected = manifest["files"][path.name]
        if hashlib.sha256(data).hexdigest() != expected["sha256"]:
            raise ValueError(f"published artifact hash mismatch: {path.name}")
        envelope = json.loads(data)
        if any(envelope[key] != manifest[key] for key in ("schema_version", "dataset", "generated_at")):
            raise ValueError(f"published artifact envelope mismatch: {path.name}")
        snapshot[name] = envelope["records"]
    coverage_path = root / "coverage.json"
    coverage_bytes = coverage_path.read_bytes()
    if hashlib.sha256(coverage_bytes).hexdigest() != manifest["files"]["coverage.json"]["sha256"]:
        raise ValueError("published coverage hash mismatch")
    coverage = json.loads(coverage_bytes)
    snapshot["coverage"] = {key: value for key, value in coverage.items() if key not in {"dataset", "generated_at"}}
    geography = json.loads((repo_root / "data" / "national" / "geography.json").read_text(encoding="utf-8"))
    return snapshot, geography


def validate_published(repo_root: Path) -> None:
    snapshot, geography = load_published_snapshot(repo_root)
    validate_snapshot(snapshot, geography)
    records = [
        record
        for key in ("sources", "utilities", "utility-activities", "service-territory", "assertions", "quarantine")
        for record in snapshot[key]
    ]
    validate_records_schema(records, repo_root / "data" / "verified" / "schemas" / "domain-record.schema.json")


def validate_schema(instance: Any, schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    issues = sorted(validator.iter_errors(instance), key=lambda issue: list(issue.path))
    if issues:
        raise ValueError("; ".join(issue.message for issue in issues[:5]))


def validate_records_schema(records: list[dict[str, Any]], schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for record in records:
        issues = sorted(validator.iter_errors(record), key=lambda issue: list(issue.path))
        if issues:
            raise ValueError(f"record {record.get('id', '<missing>')}: {issues[0].message}")
