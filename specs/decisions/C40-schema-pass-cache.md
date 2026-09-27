# C40: skip re-validating records that already passed

The user asked for the snapshot-test speedup C39 left open, on 2026-09-27. Claude local
takes it in the technical-lead role. Feature ownership is unchanged.

## Evidence

After [C39](C39-parallel-pytest.md), the slowest tests each assemble the national
snapshot (15–50s each). Profiling
`test_f30_snapshot.py::test_cross_record_validator_rejects_invalid_bindings[invalid_cross_state_county]`
(36s) put 28s in `common.schema.validate`, over 31,283 calls. `national.build.load_snapshot`
re-validates every record after each of six producer overlays, so an unchanged record
passes jsonschema 7+ times per call, and again in every test that calls it.

## Contract

- `common.schema.validate` remembers `(schema_name, blake2b(repr(record)))` for records
  that passed, and returns early when it sees the same pair again.
- Failures are never remembered: an invalid record is validated and reported in full
  every time, with the same `SchemaError` text as before.
- The key uses `repr`, not `json.dumps`. `repr` keeps tuple/list, True/1 and int/float
  apart, so two records share a key only if they are the same JSON value. A differing
  repr (for example, key order) only misses the cache.
- Correct because `_validator` is already cached per schema name for the process, so a
  schema can't change under a remembered pass. The set lives for one process and is
  never persisted.
- No call site, schema, dataset or validation rule changes. `tests/golden/test_schema_cache.py`
  covers a changed record, JSON-equal non-JSON values, and a pass under another schema.

## Options

- Validate only the final assembled snapshot in `load_snapshot`: similar saving, but it
  edits F30's code and loses per-overlay failure attribution. Rejected.
- Share one assembled snapshot across the heavy tests via fixtures: edits five
  features' tests, and later tests would lean on shared mutable state. Rejected.
- Cache in `national.build.validate_records` only: F30-owned, and misses the other
  producers' calls. Rejected.

Remaining cost after this is mostly `copy.deepcopy` inside producer `apply_release`
functions. That code belongs to the producers' owners.

## Undo

Revert this PR; `validate` goes back to running jsonschema on every call.
