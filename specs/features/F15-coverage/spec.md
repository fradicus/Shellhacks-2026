---
id: F15
name: Coverage view (data quality)
lane: B
agent: technical-lead
phase: 3
depends_on: [F06, F10]
owns: [pipeline/coverage/, tests/pipeline/test_f15_, data/coverage/, web/app/coverage/, web/components/coverage/]
cut: allowed
---

# F15 Coverage view

Sperry's AI team hires for extraction + validation. This page shows ours, with denominators.

## Plan
1. `pipeline/coverage/`: compute per source the rows seen, parsed, flagged, with 2/1/0 endpoints, endpoints located by confidence, active projects, projects in any match, and the extraction accuracy (from F03's `eval.json`). Write `data/coverage/coverage.json` (schema `coverage`).
2. `/coverage` page: a source table (sha256 prefix, filing date, public status, pages), coverage bars per source (plain CSS), the unlocated project list, quality flags, the extraction accuracy table, and the last `runs` entry.

## Validation
- `tests/pipeline/test_f15_*.py` on small synthetic inputs with known counts. lint, typecheck, build, and a screenshot.

## Defaults
- A missing input (e.g. F03 unavailable) shows as "not available", never as 0%.
