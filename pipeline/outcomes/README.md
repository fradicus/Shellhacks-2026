# Actual job outcomes

This module ships no production histories or model. It will not turn planned filings, contract dates, queue entry or in-service dates into construction duration. A model requires authorized actual construction records and an external deployment approval tied to the exact artifact bytes.

The versioned [import schema](schemas/import-v1.schema.json) accepts local UTF-8 JSON exports and explicit source manifests. Each job and event has a JSON Pointer into an export. Imported fields must equal the corresponding source object fields; export SHA256 values must match. The export may contain additional fields, but only the declared job/event fields are imported. A source records original publication, receipt and review times, publisher, upstream lineage and authorization reference. Do not backdate availability to make a backtest pass.

The importer requires features available before the decision, the decision no later than the actual construction start day, and exact actual start and physical completion dates on the same component. A review explicitly confirms physical construction semantics. Energization, substantial completion, contract closeout and demobilization dates are not substitutes. Elapsed duration uses calendar days. Ambiguous, conflicting, duplicate, unreviewed or late information is quarantined. All components/revisions sharing a project lineage are excluded rather than counted as independent outcomes.

A planned duration is optional. Its planned start and completion must be frozen, exact, source-backed and available before the decision. Revised plans must not overwrite earlier events; conflicting baselines require a new reviewed import rather than silent selection. Duration-overrun probability is distinct from in-service delay and remains null when a supported baseline is missing.

Run from `pipeline` with private absolute paths outside **every Git checkout**:

```text
uv run python -m outcomes /private/authorized-bundle.json --output /private/new-candidate-directory --training-cutoff 2023-01-01T00:00:00Z --calibration-cutoff 2024-01-01T00:00:00Z --evaluation-cutoff 2025-01-01T00:00:00Z
```

The dates above demonstrate argument syntax only. Choose cutoffs from the actual authorized history, before inspecting outcomes; the evaluation cutoff cannot be future and the resulting model expires after 180 days. Old example cutoffs intentionally cannot activate a current forecast.

The command creates a new private directory with `model.json`, quarantine reasons and the current schemas. It never overwrites an existing directory, commits histories, writes MongoDB or activates a model. Source files are capped at 16 MiB each/64 MiB total. Artifacts remain sensitive: company, geography, dates and lineage can identify contracts even when customer names are removed.

The fixed `empirical-cohort-v1` policy fits exact job-type/company/region cohorts with at least 30 training, 20 calibration and 20 later holdout outcomes. It uses an explicit temporal embargo and compares held-out error to a job-type median baseline. Interval width, coverage and error gates can withhold a forecast. The model never learns labels from its own answers and never retrains in a web request. See the F35 decision for numerical thresholds.

After an authorized reviewer approves a candidate, deployment configuration must supply both `OUTCOMES_MODEL_PATH` and `OUTCOMES_APPROVED_SHA256` (the reviewed file hash). A hash is an integrity and approval binding, not proof the source facts are true. Runtime independently recomputes metrics and support. Missing approval, wrong bytes, invalid dates, repeated lineage, failed evaluation or an expired model keep the service unavailable or cause abstention.

`GET /api/outcomes/status` exposes aggregate readiness only. `POST /api/outcomes/predict` accepts `job_type`, `company_id`, `region`, UTC `as_of`, and optionally `planned_duration_days` plus literal `planned_duration_confirmed_at_as_of: true`. No client-supplied paths. It echoes user baseline inputs, returns evaluated duration intervals only for supported cohorts, and returns null overrun probability outside the evaluated baseline domain. A returned empirical fraction includes numerator, denominator and a Wilson sampling interval; it is not a calibrated certainty.

The test fixture under `tests/web/outcomes` is labeled `synthetic_test_only` and rejected by the production loader. Tests temporarily simulate an authorized artifact in an isolated test process to exercise rejection and parity; their results are not real accuracy measurements.
