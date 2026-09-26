"""Run with `uv run python -m gemini_extract`; add --live only for an authorized API run."""

import argparse
import json
import sys

from .runner import ExistingExtractionsError, run_batch
from .sources import SourceError


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Enable real API calls using GEMINI_API_KEY and GEMINI_MODEL")
    args = parser.parse_args()
    try:
        _, report = run_batch(live=args.live)
    except (SourceError, ExistingExtractionsError) as exc:
        print(json.dumps({"status": "failed", "reason": str(exc)}))
        return 1
    except Exception:
        # Never log SDK/OS exception bodies or local credentials. No success artifact on failure.
        print(json.dumps({"status": "failed", "reason": "extraction_pipeline_failed"}))
        return 1
    print(json.dumps({key: report[key] for key in ("status", "reason", "corpus_pages", "pages_processed", "live_calls")}))
    return 0 if not args.live or report["status"] == "complete" else 1


if __name__ == "__main__":
    sys.exit(main())
