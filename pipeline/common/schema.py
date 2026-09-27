import hashlib
from functools import cache
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from common.io import REPO_ROOT, load_json

SCHEMA_DIR = REPO_ROOT / "schemas"


class SchemaError(ValueError):
    pass


# (schema_name, content digest) of records that already passed. Snapshot assembly re-validates every
# record after each overlay; unchanged records skip jsonschema. Failures are never cached.
# ponytail: unbounded per process (~50 bytes per distinct valid record); add an LRU if a long-lived process needs one.
_passed: set[tuple[str, bytes]] = set()


@cache
def _validator(schema_name: str) -> Draft202012Validator:
    schema = load_json(SCHEMA_DIR / f"{schema_name}.schema.json")
    Draft202012Validator.check_schema(schema)
    resources = [load_json(path) for path in SCHEMA_DIR.glob("*.schema.json")]
    registry = Registry().with_resources((item["$id"], Resource.from_contents(item)) for item in resources if "$id" in item)
    return Draft202012Validator(schema, format_checker=FormatChecker(), registry=registry)


def validate(obj: Any, schema_name: str) -> None:
    """Raise SchemaError listing every violation of `schemas/<schema_name>.schema.json`."""
    # repr, not json.dumps: it keeps tuple/list and True/1 apart, so equal keys mean equal JSON values.
    key = (schema_name, hashlib.blake2b(repr(obj).encode(), digest_size=16).digest())
    if key in _passed:
        return
    errors = sorted(_validator(schema_name).iter_errors(obj), key=lambda e: list(e.absolute_path))
    if errors:
        rid = obj.get("_id", "?") if isinstance(obj, dict) else "?"
        lines = [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in errors]
        raise SchemaError(f"{schema_name} {rid}: " + "; ".join(lines))
    _passed.add(key)
