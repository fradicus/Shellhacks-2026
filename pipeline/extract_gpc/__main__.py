from __future__ import annotations

import json

from .parser import build_outputs, write_outputs


def main() -> None:
    outputs = build_outputs()
    write_outputs(outputs)
    summary = outputs["summary"]
    print(
        json.dumps(
            {
                "ambiguous_rows": summary["ambiguous_rows"],
                "rows": summary["rows_emitted"],
                "rows_per_owner_code": summary["rows_per_owner_code"],
                "rows_per_zone": summary["rows_per_zone"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
