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
    output = {"schema_version": "aef-point-v1", "generated_at": now, "records": [record]}
    if args.output.exists():
        previous = json.loads(args.output.read_text())
        if previous.get("schema_version") != "aef-point-v1":
            raise ValueError("Existing artifact has an unsupported schema")
        output["records"] = [r for r in previous["records"] if (r["point"], r["year"]) != (record["point"], record["year"])] + [
            record
        ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    schema = json.loads(Path(__file__).with_name("aef-point.schema.json").read_text())
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(output)
    temporary = args.output.with_suffix(".tmp")
    serialized = json.dumps(output, indent=2) + "\n"
    temporary.write_text(serialized, encoding="utf-8")
    temporary.replace(args.output)
    evidence.update(
        {
            "schema_version": "aef-read-evidence-v1",
            "retrieved_at": now,
            "snapshot_sha256": hashlib.sha256(serialized.encode()).hexdigest(),
        }
    )
    args.output.with_suffix(".evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "available",
                "samples": len(output["records"]),
                "bytes_read": evidence["bytes_read"],
                "requests": evidence["requests"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
