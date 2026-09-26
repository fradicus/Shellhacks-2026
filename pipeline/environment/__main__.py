"""Explicit public-network sampler; never overwrite a previously accepted artifact on failure."""

import argparse
import hashlib
import json
import multiprocessing
from datetime import UTC, datetime
from pathlib import Path

import jsonschema

from environment.aef import worker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--index-sha256", required=True)
    parser.add_argument("--lat", required=True, type=float)
    parser.add_argument("--lon", required=True, type=float)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--allow-public-network", action="store_true")
    args = parser.parse_args()
    if not args.allow_public_network:
        parser.error("Explicit --allow-public-network is required; no calls made")
    parent, child = multiprocessing.Pipe(duplex=False)
    process = multiprocessing.Process(target=worker, args=(child, args))
    process.start()
    child.close()
    try:
        if not parent.poll(50):
            result = {"ok": False, "reason": "AEF process deadline exceeded"}
        else:
            try:
                result = parent.recv()
            except EOFError:
                result = {"ok": False, "reason": "AEF worker exited without evidence"}
    finally:
        if process.is_alive():
            process.terminate()
        process.join(3)
        parent.close()
    if not result["ok"]:
        print(json.dumps({"status": "unavailable", "reason": result["reason"], "artifact_preserved": True}))
        return 1
    record, evidence = result["result"]
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    publish(record, evidence, args.output, now)
    print(json.dumps({"status": "available", "bytes_read": evidence["bytes_read"], "requests": evidence["requests"]}))
    return 0


def publish(record, evidence, destination, now):
    """Preserve each older sample's actual retrieval and range evidence."""
    destination = Path(destination)
    output = {"schema_version": "aef-point-v1", "generated_at": now, "records": [record]}
    evidence_records = []
    if destination.exists():
        previous_text = destination.read_text()
        previous = json.loads(previous_text)
        previous_evidence = json.loads(destination.with_suffix(".evidence.json").read_text())
        if previous_evidence.get("schema_version") != "aef-read-evidence-v2":
            raise ValueError("Existing evidence version unsupported")
        if previous_evidence.get("snapshot_sha256") != hashlib.sha256(previous_text.encode()).hexdigest():
            raise ValueError("Existing snapshot/evidence binding mismatch")
        if previous.get("schema_version") != "aef-point-v1":
            raise ValueError("Existing artifact has an unsupported schema")
        output["records"] = [r for r in previous["records"] if (r["point"], r["year"]) != (record["point"], record["year"])] + [
            record
        ]
        evidence_records = [
            r for r in previous_evidence["records"] if (r["point"], r["year"]) != (record["point"], record["year"])
        ]
    destination.parent.mkdir(parents=True, exist_ok=True)
    schema = json.loads(Path(__file__).with_name("aef-point.schema.json").read_text())
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(output)
    temporary = destination.with_suffix(".tmp")
    serialized = json.dumps(output, indent=2) + "\n"
    temporary.write_text(serialized, encoding="utf-8")
    evidence = {**evidence, "retrieved_at": now, **{k: record[k] for k in ("point", "year", "sample_sha256")}}
    evidence_records.append(evidence)
    manifest = {
        "schema_version": "aef-read-evidence-v2",
        "snapshot_sha256": hashlib.sha256(serialized.encode()).hexdigest(),
        "records": evidence_records,
    }
    evidence_temp = destination.with_suffix(".evidence.tmp")
    evidence_temp.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    evidence_temp.replace(destination.with_suffix(".evidence.json"))
    temporary.replace(destination)


if __name__ == "__main__":
    raise SystemExit(main())
