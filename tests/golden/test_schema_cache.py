"""C40: skipping already-passed records must never let a different record through."""
from copy import deepcopy

import pytest

from common.io import REPO_ROOT, load_json
from common.schema import SchemaError, validate


def project():
    return deepcopy(load_json(REPO_ROOT / "data/national/projects.json")[0])


def test_a_passed_record_that_changes_is_validated_again():
    record = project()
    validate(record, "national-project")
    validate(record, "national-project")  # cached pass
    record["states"] = "not a list"
    with pytest.raises(SchemaError):
        validate(record, "national-project")
    with pytest.raises(SchemaError):  # failures are never cached
        validate(record, "national-project")


def test_json_equal_but_non_json_values_are_not_conflated():
    record = project()
    validate(record, "national-project")
    record["states"] = tuple(record["states"])  # json.dumps would match the passed list
    with pytest.raises(SchemaError):
        validate(record, "national-project")


def test_a_pass_under_one_schema_does_not_cover_another():
    record = project()
    validate(record, "national-project")
    with pytest.raises(SchemaError):
        validate(record, "national-source")
