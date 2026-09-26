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
| CI | GitHub Actions: required check **`ci`** (ruff, pytest, lint, typecheck, build, ownership) and `load` (Atlas upsert from `main`) |
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

## Checks (every PR, from the repo root; referenced by AGENTS.md)
```bash
(cd pipeline && uv run ruff check . && uv run pytest -q)          # includes the golden test
(cd web && npm run lint && npm run typecheck && DATA_MODE=fixture npm run build)
python3 scripts/check_ownership.py --lint-specs
python3 scripts/check_ownership.py --title "<your PR title>" --base origin/main
```
Before F00 merges, only F00 runs, and it creates these tools.

## Read-only inputs
`docs/` (sponsor originals) and `plans/` (historical plans A–E). Never edit them.

## Environment variables
| Name | Where | Used by |
|---|---|---|
| `GEMINI_API_KEY`, `GEMINI_MODEL` | data runtime (local process); `GEMINI_API_KEY` also in Vercel for F20 query embedding | Gemini pipeline stages, `/api/search` query vectors |
| `GEMINI_EMBED_MODEL` | pipeline + Vercel | F20 embedding model id (default `gemini-embedding-001`, 768 dimensions) |
| `MONGODB_URI_RW` | GitHub Actions secret only | `load` workflow |
| `MONGODB_URI_RO`, `MONGODB_DB=gridbridge` | Vercel env; app/QA runtimes | web API, QA |
| `DATA_MODE=fixture` | CI and local dev without Atlas | web reads `data/fixtures` via `lib/data.ts`; **never in production** |
| `ANALYSIS_DATE` | Vercel env + pipeline | future vs historical split (default: `run_start` date) |

Production without Atlas shows an explicit "database unavailable" state. It never silently serves fixtures.

## C11 national extension
The same Python/Next.js/MapLibre/MongoDB stack serves `/explore`. Additive national schemas in `schemas/national-*.schema.json` and F30 snapshots under `data/national/` keep legacy project enums and data unchanged. Use separate dataset-scoped `national_sources`, `national_projects`, optional `national_utilities` and `national_service_territory`, plus `national_runs` and `meta.national_active`; the existing load Action remains the sole Atlas writer. `python -m national.load` validates only without RW credentials. Public reference geography is independent of project database availability. `NATIONAL_DATA_MODE=snapshot` explicitly enables the committed regional snapshot in local/CI environments, is rejected on production Vercel, and is never a silent database fallback. F32 remains a separate prototype; the existing pipeline-only Gemini rule still applies to the delivered app.

## Credentials before the run
Set `GEMINI_API_KEY` and a tested `GEMINI_MODEL` tonight for real F03/F12 extraction and briefs. Without them, offline coding/tests can proceed but Gemini integration remains incomplete. Atlas RW belongs only in GitHub Actions; RO goes to Vercel and the app/QA runtime before live integration. Offline CI needs no live Gemini/Atlas credentials. Local coding-tool authentication is separate from the product Gemini key. See [preflight.md](preflight.md) for the short checklist and both launch options.
