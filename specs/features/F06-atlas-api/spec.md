---
id: F06
name: Atlas loader + read API
lane: B
agent: technical-lead
phase: 1
depends_on: [F00]
owns: [pipeline/load/, tests/pipeline/test_f06_, web/app/api/projects/, web/app/api/matches/, web/app/api/pairs/, web/app/api/versions/, web/app/api/coverage/, web/app/api/extraction/, web/app/api/sources/, web/app/api/briefs/, web/app/api/runs/, web/lib/server/]
cut: never
---

# F06 Atlas loader + read API

The `load` GitHub Action is the **only writer** to Atlas (tech-stack). This feature implements what it runs.

## Plan
1. **Loader** (`pipeline/load/__main__.py`):
   - read every `data/**/*.json` that matches a schema (sources, projects + locations joined into projects' `endpoints` and `center`, matches, briefs, extractions, reviews, coverage, version changes)
   - validate each record against its schema
   - upsert by `_id` into a **staging** dataset (`dataset: <git sha>` field), then flip the `meta.active_dataset` pointer only when every collection validates
   - write a `runs` document either way
   - idempotent: loading the same sha twice changes nothing
2. **Indexes:** `projects.center` 2dsphere; `{utility:1, active:1}`; `matches {view:1, band:1, time_gap_days:1, distance_mi:1}`; `briefs.match_id`; unique `_id` everywhere.
3. **Read routes** (Node runtime, one cached `MongoClient` in `web/lib/server/db.ts`, `MONGODB_URI_RO`), shapes exactly as `web/lib/types.ts`:
   - `GET /api/projects?bbox=w,s,e,n&view=`: `$geoWithin` `$box` when bbox is given; null-center projects included only when no bbox is given
   - `GET /api/matches?view=&maxDistance=&limit=`: priority order as stored
   - `GET /api/pairs/[id]`: the match, both projects with endpoints and evidence, the brief (if passed), version changes for either project
   - `GET /api/versions`, `GET /api/coverage`, `GET /api/extraction?source=`, `GET /api/sources` (added by C3), `GET /api/briefs` (all, passed and rejected) and `GET /api/runs` (latest run or null; public Run fields only) (added by C5)
4. **Audit subjects** (`pipeline/load/review_subjects.py`, added by C7 for #57): pure `endpoint_subject`, `pair_subject`
   and `subject_hash` (SHA-256 of canonical JSON, `fingerprint_version: audit-subject-v1`). Staging recomputes every
   match's and accepted location's hash before dataset-prefixing; a review's `subject_hash` must equal it for its
   verdict to apply, a pair confirmation also needs current confirmed reviews for its supporting endpoints, and a
   review without a binding (or with a stale one) leaves `review_state` at `needs_review`. Location records bind to one
   filing version via `project_id` / `source_id` (#47). F13 reuses only the projection and hash.
5. Validate every query param with `zod`: bbox within +/-180/90, limit <= 500, enums checked. Unknown params -> 400. Only read the active dataset.
6. Atlas unreachable -> 503 `{unavailable: true}`. Never serve fixtures in production.

## Requirements
- No write routes. No raw operators from the request. The connection string is never logged.

## Validation
- `tests/pipeline/test_f06_*.py`: the loader's validation, join and pointer-flip logic run with `mongomock` if it's pinned, otherwise against pure functions split from the I/O (keep the I/O thin).
- Manual check with `MONGODB_URI_RO` on the lane B machine: `curl` each route against Atlas after the first `load` run on main. Paste the status codes and counts.
- CI builds in fixture mode, so the routes must compile without env vars.

## Defaults
- If the `load` action fails on main because a secret is missing, log a decision and open an issue labeled `human-morning`. The UI shows unavailable in production.
