from __future__ import annotations

import json

from .parser import build_outputs, write_outputs


def main() -> None:
    outputs = build_outputs()
    write_outputs(outputs)
    summary = {
        "records": len(outputs["projects"]),
        "sources": {
            source_id: sum(
                record["source"]["source_id"] == source_id for record in outputs["projects"]
            )
            for source_id in ("desc-2024", "desc-2025")
        },
        "unparsed": len(outputs["unparsed"]),
        "version_changes": len(outputs["version_changes"]),
    }
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
