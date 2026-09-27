"""Activate only exact proposed records with independently supplied hash-bound approvals.

Writes the fixed release atomically after schema and all current-project checks pass.
"""

from __future__ import annotations

import argparse
import os
import tempfile
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from common import REPO_ROOT, load_json, validate
from expansion.new_england import encode
from expansion.publish import ACTIVE_RELEASE, check_record, record_hash


def approved_release(records: list[dict], approvals: list[dict], projects: list[dict], release_id: str) -> dict:
    by_id = {p["_id"]: p for p in projects}
    accepted = {}
    for item in approvals:
        if item["project_id"] in accepted:
            raise ValueError("duplicate final approval")
        accepted[item["project_id"]] = item["review"]
    if len({r["project_id"] for r in records}) != len(records):
        raise ValueError("duplicate proposal")
    if set(accepted) != {r["project_id"] for r in records}:
        raise ValueError("final approvals must match the exact proposal set")
    result = deepcopy(records)
    for record in result:
        approval = accepted[record["project_id"]]
        if approval["decision"] != "confirmed" or approval["facts_sha256"] != record_hash(record):
            raise ValueError("approval does not confirm these exact current location facts")
        record["reviews"].append(approval)
    release = {
        "schema_version": "expansion-release-v1", "release_id": release_id,
        "created_at": datetime.now(UTC).isoformat(),
        "scope": "Existing ISO-NE project/component IDs in six New England states; independently reviewed facility "
                 "sites or named line endpoints. Source lifecycle status and milestone precision unchanged.",
        "records": result,
        "coverage_notes": [
            "Confirmed means independently reviewed documented facility/site or endpoint linkage, not survey accuracy.",
            "NOAA/CZM geometry is a 2013 planning-scale dataset digitized at 1:40000; uncertainty in metres is unknown.",
            "Vermont sites use official utility-submitted/E911 records; numerical transformation does not imply survey accuracy.",
            "June 2026 project statuses remain source observations; location review does not certify current construction.",
            "A one-endpoint line center is partial. Several project components can share a facility; site counts are separate.",
            "No municipality centers, utility offices, geocoder guesses, cancelled projects or inventory-only assets were added.",
        ],
    }
    validate(release, "expansion-release")
    for record in result:
        if record["project_id"] not in by_id:
            raise ValueError("unknown project id")
        if by_id[record["project_id"]]["status_group"] == "cancelled":
            raise ValueError("cancelled records are outside this release cohort")
        if check_record(record, by_id[record["project_id"]]) != "confirmed":
            raise ValueError("final release contains an unconfirmed location")
    return release


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposals", type=Path, required=True)
    parser.add_argument("--approvals", type=Path, action="append", required=True)
    parser.add_argument("--release-id", required=True)
    args = parser.parse_args()
    approvals = [item for path in args.approvals for item in load_json(path)]
    release = approved_release(load_json(args.proposals), approvals,
                               load_json(REPO_ROOT / "data/national/projects.json"), args.release_id)
    path = REPO_ROOT / ACTIVE_RELEASE
    if path.exists():
        raise ValueError("existing release requires a reviewed superseding release; this initial CLI will not overwrite it")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".release-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as output:
            output.write(encode(release))
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    print(f"Validated and wrote {len(release['records'])} reviewed project locations; Atlas publication remains a separate step.")


if __name__ == "__main__":
    main()
