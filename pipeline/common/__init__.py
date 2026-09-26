"""Shared pipeline helpers: stable JSON I/O, schema validation, ids and name normalization. Frozen after F00."""

from common.ids import match_id, project_id
from common.io import REPO_ROOT, load_json, write_json
from common.names import norm_name
from common.schema import SchemaError, validate

__all__ = ["REPO_ROOT", "SchemaError", "load_json", "match_id", "norm_name", "project_id", "validate", "write_json"]
