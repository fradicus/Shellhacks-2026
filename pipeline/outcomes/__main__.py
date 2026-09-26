"""Import an authorized export into an externally stored, reviewed model candidate."""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from outcomes.contracts import Artifact, Bundle, Cutoffs
from outcomes.importer import read_bounded, strict_json, validate_bundle
from outcomes.model import build_artifact, validate_artifact

REPO = Path(__file__).resolve().parents[2]


def external_path(value: str) -> Path:
    path = Path(value).resolve()
    if not Path(value).is_absolute() or path.is_relative_to(REPO):
        raise ValueError("private inputs/outputs must be absolute paths outside this Git worktree")
    # Other linked worktrees are private-data hazards too.
    for parent in [path.parent, *path.parents]:
        if (parent / ".git").exists():
            raise ValueError("private input/output cannot be inside any Git checkout")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", help="authorized import JSON path outside any Git checkout")
    parser.add_argument("--output", required=True, help="new private candidate directory (must not already exist)")
    parser.add_argument("--training-cutoff", required=True)
    parser.add_argument("--calibration-cutoff", required=True)
    parser.add_argument("--evaluation-cutoff", required=True)
    args = parser.parse_args()
    try:
        source_path, output = external_path(args.bundle), external_path(args.output)
        bundle = Bundle.model_validate(strict_json(read_bounded(source_path)))
        for source in bundle.sources:
            external_path(source.local_path)
        cutoffs = Cutoffs(training=args.training_cutoff, calibration=args.calibration_cutoff, evaluation=args.evaluation_cutoff)
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        if cutoffs.evaluation > now:
            raise ValueError("future evaluation cutoff")
        rows, quarantine = validate_bundle(bundle, as_of=cutoffs.evaluation)
        artifact = build_artifact(rows, cutoffs, purpose=bundle.purpose)
        validate_artifact(artifact, now=now)
        output.mkdir(parents=True, exist_ok=False)
        raw = (artifact.model_dump_json(indent=2) + "\n").encode("utf-8")
        (output / "model.json").write_bytes(raw)
        (output / "quarantine.json").write_text(json.dumps(quarantine, indent=2) + "\n", encoding="utf-8")
        contracts = {"import": Bundle.model_json_schema(), "model": Artifact.model_json_schema()}
        (output / "contracts.json").write_text(json.dumps(contracts, indent=2) + "\n", encoding="utf-8")
        sha = hashlib.sha256(raw).hexdigest()
        print(
            json.dumps(
                {
                    "accepted": len(rows),
                    "quarantined": len(quarantine),
                    "artifact_sha256": sha,
                    "passing_cohorts": sum(e["passed"] for e in artifact.evaluation.values()),
                    "activation": "External artifact-hash approval is required; this command does not activate a model.",
                }
            )
        )
    except (ValueError, OSError) as error:
        # CLI is local/private; do not forward these diagnostics through public APIs.
        parser.exit(2, f"Import failed: {error}\n")


if __name__ == "__main__":
    main()
