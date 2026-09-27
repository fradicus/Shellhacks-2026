# Tech stack

Pin exact versions in the lockfiles created by the bootstrap feature (F00). Use the latest stable release at bootstrap
time; don't upgrade during the run. New dependencies only via a `[C<n>]` contract PR (see `overnight.md` §4).

| Layer | Choice |
|---|---|
| Agent runtime | Paperclip orchestration, local Claude Code + Codex, or disjoint hybrid assignments. All share root specs, feature worktrees and GitHub CI; choose in roadmap `execution_mode`. |
| Pipeline | Python 3.12, `uv`, `pdfplumber`, `openpyxl`, `google-genai`, `pymongo`, `jsonschema`, `pyyaml`, `mongomock`, `pytest`, `ruff` |
| Data | JSON files under `data/` committed to git (reviewable, diffable); JSON Schema in `schemas/` is the contract |
| Database | MongoDB Atlas (M0), database `gridbridge`. **Only the `load` GitHub Action writes to it**, on pushes to `main` touching `data/**` |
| Web | Next.js (App Router) + TypeScript strict, one app in `web/`; route handlers for the API; native `mongodb` driver; `zod` to validate query params |
| Map | `maplibre-gl` + OpenFreeMap tiles (no key). An accessible table must work if tiles fail |
| AI | Gemini via `google-genai`, **pipeline only** (batch). Model id in `GEMINI_MODEL`; the exact id, prompt version and schema version are stored with every output. The public site shows stored results; it never calls Gemini |
| Tests | `pytest` (pipeline, golden), `next build` + `tsc` (web), Playwright smoke (`tests/e2e`, non-blocking job) |
| CI | GitHub Actions: required check **`ci`** (spec/ownership checks; parallel Python/web validation for full changes) and `load` (Atlas upsert from `main`) |
| Hosting | Vercel project, root `web/`, production deploys from `main`, previews per PR |

## Repository layout (created by F00; the ownership globs in the feature specs refer to it)
```
AGENTS.md  CLAUDE.md  specs/  changes/  docs/(read-only)  plans/(read-only)
schemas/                         JSON Schemas: source, project, match, brief, extraction, review, run   [frozen]
scripts/check_ownership.py       ownership gate                                                      [frozen]
.github/workflows/ci.yml, load.yml                                                                    [frozen]
pipeline/pyproject.toml, uv.lock                                                                      [frozen]
pipeline/common/                 io, schema validation, ids                                          [frozen]
pipeline/matches/core.py         canonical center/haversine/overlap/gap/priority                     [frozen]
pipeline/<stage>/                one package per feature (extract_desc, extract_gpc, gemini_extract, locations, match_run, briefs, load)
tests/pipeline/test_<feature>.py per feature;  tests/golden/ (F00);  tests/e2e/ (QA)
data/fixtures/golden/            sample workbook as JSON (F00)
data/<area>/                     one folder per producing feature (see each spec's owns)
web/package.json, package-lock.json, lib/types.ts, lib/data.ts, app/layout.tsx, components/nav/   [frozen]
web/app/<route>/, web/components/<feature>/, web/app/api/<route>/   one owner each
reports/ release/ submission/    lane C
```

## Checks (change-scoped; referenced by AGENTS.md)

[C36](decisions/C36-fast-ci.md) replaces the full-suite requirement for every PR.
Run focused checks while editing. Before ready/merge, either run the applicable
commands below locally or link successful GitHub CI for the **exact PR revision**.
Successful CI is sufficient; do not repeat the full suite locally. Report failures
and optional browser job results honestly. Feature-specific acceptance still applies.

Classify the complete PR diff (commit changes first):
```bash
python3 scripts/ci_scope.py --base origin/main
```
Only root README/agent instructions and Markdown under `specs/`, `reports/`, or
`changes/` qualify as `docs`. Everything else, including mixed diffs and empty diffs,
requires `full`. Renames check both paths; a failed classification blocks validation.

For **every PR**, including docs:
```bash
python3 -m unittest discover -s tests/golden -p test_ci_scope.py
python3 scripts/check_ownership.py --lint-specs
python3 scripts/check_ownership.py --title "<your PR title>" --base origin/main
(cd pipeline && uv run pytest -c pyproject.toml ../tests/golden/test_ownership.py -q)
```
For **full** changes, also run (Python and web may run concurrently; [C39](decisions/C39-parallel-pytest.md) spreads pytest across CPUs):
```bash
(cd pipeline && uv run ruff check . && uv run pytest -q -n auto --durations=10)
(cd web && npm run lint && npm run typecheck && DATA_MODE=fixture npm run build)
```
CI additionally preserves the existing national, assistant and operations Node
checks and optional browser suites. Required `ci` aggregates the applicable jobs;
failed/cancelled prerequisites cannot pass. Main pushes always run full checks.

After edits or a rebase, classify and validate the new revision. Keep a passing
revision stable while CI finishes; rebase for conflicts, required branch protection,
or a known integration dependency rather than continuously chasing unrelated merges.
Before merge, inspect the diff for secrets, read-only paths and ownership violations.

## Read-only inputs
`docs/` (sponsor originals) and `plans/` (historical plans A–E). Never edit them.

The [dated context notes](context/README.md) under `specs/context/` capture product feedback separately from source
inputs. They inform decisions; they do not alter the authority or interpretation of source records. Keep their
historical observations stable and append explicit corrections or later answers.

## Evidence and freshness semantics

Follow the [shared vocabulary](vocabulary.md): source publication/vintage, retrieval/check time, observed change
time and project milestones describe different facts. Preserve unknown values and original date precision.
A refresh success is not evidence that a publisher changed a project. Changes need comparable old/new source
evidence; failed refreshes preserve the last valid dataset and disclose the failed attempt separately.

These are acceptance requirements for the [PM follow-up](followup.md), not a claim that all history fields already
exist. Any missing shared fields require an additive contract through their owner. Keep the current stack and
sole-writer/deployment boundaries; this documentation update introduces no migration, provider or scheduled job.

## Environment variables
| Name | Where | Used by |
|---|---|---|
| `GEMINI_API_KEY`, `GEMINI_MODEL` | data runtime only (Paperclip env or local process) | Gemini pipeline stages |
| `MONGODB_URI_RW` | GitHub Actions secret only | `load` workflow |
| `MONGODB_URI_RO`, `MONGODB_DB=gridbridge` | Vercel env; app/QA runtimes | web API, QA |
| `DATA_MODE=fixture` | CI and local dev without Atlas | web reads `data/fixtures` via `lib/data.ts`; **never in production** |
| `ANALYSIS_DATE` | Vercel env + pipeline | future vs historical split (default: `run_start` date) |

Production without Atlas shows an explicit "database unavailable" state. It never silently serves fixtures.

## C11 national extension
The same Python/Next.js/MapLibre/MongoDB stack serves `/explore`. Additive national schemas in `schemas/national-*.schema.json` and F30 snapshots under `data/national/` keep legacy project enums and data unchanged. Use separate dataset-scoped `national_sources`, `national_projects`, optional `national_utilities` and `national_service_territory`, plus `national_runs` and `meta.national_active`; the existing load Action remains the sole Atlas writer. `python -m national.load` validates only without RW credentials. Public reference geography is independent of project database availability. `NATIONAL_DATA_MODE=snapshot` explicitly enables the committed regional snapshot in local/CI environments, is rejected on production Vercel, and is never a silent database fallback. F32 remains a separate prototype; the existing pipeline-only Gemini rule still applies to the delivered app.

## C15 field operations extension
F33/F34/F35 maintain domain-owned versioned JSON schemas and Zod contracts inside their exclusive prefixes for reference artifacts, provider responses and actual job outcomes. Their public API contracts are frozen by `specs/decisions/C15-verified-operations.md`; cross-feature changes require a contract review. No existing national or legacy schema is renamed. F36 consumes these APIs from a separate `/operations` page. Approved public reference artifacts may be committed; raw private job history, credentials, provider tokens, Google route responses and downloaded caches must not be committed. No new database writer is introduced. The optional pinned Python `environment` extra installs Rasterio for bounded public AEF COG sampling; normal web/CI use does not require live raster reads. Tests use explicitly named fixtures and never return them as production data. Live APIs are requested only from server-side adapters with fixed hosts, bounded requests, freshness/coverage checks and clear failure states. Existing live-service credential deferral remains in effect for this worker.

Operations environment names are `NWS_USER_AGENT` (identifying contact), `GOOGLE_ROUTES_API_KEY` and `GOOGLE_LVR_ENABLED=true` (both required; LVR provisioning must also exist), and `OUTCOMES_MODEL_PATH` plus `OUTCOMES_APPROVED_SHA256` (optional local model artifact and its external deployment approval pin; both required for activation). No `NEXT_PUBLIC_` credential is allowed. AEF uses a reviewed public GCS index/object, with no invented asset version. Provider-specific operational freshness thresholds are implementation policy, displayed and tested, not claims that a provider guarantees accuracy. Google route content must not be rendered on MapLibre; use a separate attributed route-only presentation. See C15's official documentation links.

F35 activation also requires `OUTCOMES_APPROVED_AT`, an externally recorded UTC approval timestamp bound to the approved artifact hash. A request cannot be backdated before approval. It is server-only deployment configuration and never supplied by the browser; absence means forecasts are unavailable. Private model files must be provisioned outside Git checkouts and are not copied into public deployment assets by this repository.

NWS does not require an API key. The server identifies itself by default as `GridBridge (https://github.com/fradicus/Shellhacks-2026/issues)`; deployments may override that public identifying contact with `NWS_USER_AGENT`. Weather remains usable without supplying a secret. Provider availability still depends on successful requests and valid current source responses.

## Credentials before the run

Set `GEMINI_API_KEY` and a tested `GEMINI_MODEL` tonight for real F03/F12 extraction and briefs. Without them, offline coding/tests can proceed but Gemini integration remains incomplete. Atlas RW belongs only in GitHub Actions; RO goes to Vercel and the app/QA runtime before live integration. Offline CI needs no live Gemini/Atlas credentials. Local coding-tool authentication is separate from the product Gemini key. See [preflight.md](preflight.md) for the short checklist and both launch options.
