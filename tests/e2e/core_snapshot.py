"""Adapter for the system under test; the independent reference never imports core."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipeline"))

from matches.core import center, overlaps, priority_sort  # noqa: E402

projects = json.load(sys.stdin)
for project in projects:
    project["center"] = center(project["endpoints"])
json.dump(
    {"centers": {p["project_key"]: p["center"] for p in projects}, "matches": priority_sort(overlaps(projects, "2026-09-26"))},
    sys.stdout,
)
