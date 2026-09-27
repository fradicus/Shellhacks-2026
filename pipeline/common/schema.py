from functools import cache
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from common.io import REPO_ROOT, load_json

SCHEMA_DIR = REPO_ROOT / "schemas"


class SchemaError(ValueError):
    pass


@cache
def _validator(schema_name: str) -> Draft202012Validator:
    schema = load_json(SCHEMA_DIR / f"{schema_name}.schema.json")
    Draft202012Validator.check_schema(schema)
    resources = [load_json(path) for path in SCHEMA_DIR.glob("*.schema.json")]
    registry = Registry().with_resources((item["$id"], Resource.from_contents(item)) for item in resources if "$id" in item)
    return Draft202012Validator(schema, format_checker=FormatChecker(), registry=registry)


def validate(obj: Any, schema_name: str) -> None:
    """Raise SchemaError listing every violation of `schemas/<schema_name>.schema.json`."""
    errors = sorted(_validator(schema_name).iter_errors(obj), key=lambda e: list(e.absolute_path))
    if errors:
        rid = obj.get("_id", "?") if isinstance(obj, dict) else "?"
        lines = [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in errors]
        raise SchemaError(f"{schema_name} {rid}: " + "; ".join(lines))
