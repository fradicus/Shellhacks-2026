"""Reviewed download registry. Refresh accepts source ids, never caller-supplied URLs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from common import REPO_ROOT, load_json

DATA_DIR = REPO_ROOT / "data" / "national"
CACHE_DIR = DATA_DIR / "cache"
MANIFEST_PATH = DATA_DIR / "source-manifest.json"


def manifest(root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    return load_json(root / "data" / "national" / "source-manifest.json")


def entries(root: Path = REPO_ROOT) -> dict[str, dict[str, Any]]:
    values = manifest(root)
    by_id = {entry["id"]: entry for entry in values}
    if len(by_id) != len(values):
        raise ValueError("national source manifest has duplicate ids")
    return by_id


def cache_path(entry: dict[str, Any], root: Path = REPO_ROOT) -> Path:
    return root / "data" / "national" / "cache" / entry["cache_name"]
