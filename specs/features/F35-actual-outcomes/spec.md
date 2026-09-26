---
id: F35
name: Actual outcome import and evaluated estimates
lane: B
agent: technical-lead
phase: 6
depends_on: [F00]
owns: [pipeline/outcomes/, web/lib/outcomes/, web/app/api/outcomes/, tests/pipeline/test_f35_, tests/web/outcomes/]
cut: never
---

# F35 Actual outcomes only

Build a local authorized-history import, evidence validation, versioned model/evaluation artifact and read-only prediction/status API using C15. Do not commit private histories or derive construction duration from existing planned filings. Jobs have explicit source-native identity/component/project lineage, job type/company/region known at decision time and append-only dated planned/actual events with source evidence and publication/as-of times. Record authorization/review metadata without secrets. Quarantine conflicts, repeated lineage, impossible/future events, missing actual anchors and coarse/ambiguous dates.

Exact actual construction start and completion on the same scope are required for construction duration. A frozen original planned baseline, known before the outcome, is required for delay labels. Other lifecycle intervals retain separate names and cannot be pooled. Company effects are associative, not causal ratings. No LLM-created labels or silent self-training; every retrain records dataset/model/config hashes, cutoff and comparative evaluation.

Use a deterministic empirical cohort model with chronological, project-lineage-separated evaluation against a simple job-type baseline. Predeclare minimum support, evaluation/calibration holdouts, error/interval limits and abstention criteria. Return intervals/support/evaluation and no numerical prediction when support, freshness, lineage, calibration or accuracy gates fail. No high-accuracy claim without held-out evidence. Unseen company/type, invalid as-of, missing model or unresolved source conflict abstains. No private row-level API output or arbitrary model file path from a request.

Tests must cover leakage across revisions, post-cutoff outcomes/features, future events, planned/actual confusion, duplicates, forged artifact counts/metrics, poor backtest/coverage, no-model production behavior and a clearly named synthetic test-only cohort. Such a test is not real accuracy evidence. Full repository checks and independent review required. Live training remains dependent on authorized actual records; code completion does not mean a fitted operational model exists.
