import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_json(path: str | Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str | Path, obj: Any) -> None:
    """Sorted keys, 2-space indent, trailing newline: reruns produce byte-identical files, so diffs stay reviewable."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")
