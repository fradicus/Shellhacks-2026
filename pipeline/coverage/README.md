# Coverage ledger

From `pipeline/`, run:

```text
uv run python -m coverage
```

The offline command validates committed inputs and writes `data/coverage/coverage.json`. It performs no network or
database access. `--repo-root PATH` targets a different repository root for isolated validation.

Each record is keyed by source id. Counts use filing versions and explicit match bindings; F06 staging derives current
review states without changing producer data. `data/extraction/eval.json` and `reports/audit/evidence.json` are optional:
their metrics are `null` when unavailable.
