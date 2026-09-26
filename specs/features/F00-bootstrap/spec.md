---
id: F00
name: Bootstrap - skeleton, contracts, matcher, golden test, CI, ownership gate
lane: B
agent: technical-lead
phase: 0
bootstrap: true
depends_on: []
owns: []            # bootstrap may touch anything (overnight.md §4)
cut: never
---

# F00 Bootstrap

Every other feature waits for this one. **Target: merged within 45 minutes.** Correctness beats polish, but
every contract below must exist, because other lanes can't change frozen files afterwards without a `[C<n>]` PR.

## Plan (task groups)
1. **Layout + deps.** Create the layout in `tech-stack.md`. `pipeline/pyproject.toml` with every package listed in tech-stack (plus `pytest`, `ruff`), `uv lock`. `web/` via `create-next-app` (TypeScript, App Router, ESLint, no Tailwind unless it's the default; either is fine, but pick one now), then add `maplibre-gl`, `mongodb`, `zod`, `@playwright/test`. Scripts: `lint`, `typecheck` (`tsc --noEmit`), `build`. Commit the lockfiles. **Pre-install everything any feature will need**, so nobody needs a contract PR for a common package.
2. **Schemas** (`schemas/*.schema.json`, JSON Schema 2020-12). Required fields below; everything else optional. `additionalProperties: true`, so features can add optional fields without a contract change.

   | Schema | Required fields |
   |---|---|
   | source | `_id, publisher, title, sha256, pages, public_status (public, public_with_banner, excluded)`, `url` or `local_path` |
   | project | `_id` (`<project_key>@<source_id>`), `project_key` (`DESC:6807B`, `GPC:20277`), `utility (DESC, GPC, unknown)`, `owner_code`, `native_id`, `name`, `source {source_id, page}`, `in_service {raw, date or null, precision (day, month, year, unknown)}`, `active` |
   | location | `project_key, endpoint_index, name, confidence (high, medium, low, rejected), evidence`; `lat`/`lon` required unless rejected |
   | match | `_id` (sorted keys joined by `__`), `a, b, distance_mi, time_gap_days (int or null), band (0 or 1), rule_version, rank_version, analysis_date, view (future, historical, tentative)` |
   | brief | `_id, match_id, input_hash, model, prompt_version, generated_at, supported_facts[], possible_shared_activities[], questions[], limitations[], validation (passed or rejected)` |
   | extraction | `_id, source_id, page, model, prompt_version, fields{}, comparison{}, accepted` |
   | review | `_id, record_id, verdict, reason, reviewer, at` |
   | run | `_id, stage, started_at, finished_at, status, counts{}` |
   | coverage | `_id (source_id), counts{}` |
   | version_change | `_id, project_key, from_source, to_source, field, old, new` |
3. **Pipeline common** (`pipeline/common/`): `load_json/write_json` (sorted keys, 2-space indent, trailing newline, so diffs stay stable), `validate(obj, schema_name)`, `norm_name(s)` (uppercase; strip SUB/SUBSTATION/PRIMARY/SS/TS/#n/parentheticals; collapse spaces).
4. **Canonical matcher** (`pipeline/matches/core.py`): `center(endpoints)`, `haversine_mi` (R = 3958.8, clamp h to [0,1]), `overlaps(projects, analysis_date)` returning match dicts per the mission rules, and `priority_sort` for `nearby-band-v1`. Pure functions, no I/O.
5. **Golden fixture + test.**
   - `data/fixtures/golden/projects.json` and `overlaps.json`, converted from `docs/Sperry-Tech-Challenge/Projects_Overlaps.xlsx`, with Excel serial dates converted (45809 = 2025-06-01, 45778 = 2025-05-01).
   - `tests/golden/test_golden.py`: exactly OVL_1..6 (the pairs DESC_2/GPC_1, DESC_3/GPC_2, DESC_3/GPC_3, DESC_1/GPC_1, DESC_5/GPC_2, DESC_5/GPC_3), distances 4.09, 5.65, 7.55, 8.01, 14.34, 14.81 at 2 dp, gaps 3074, 152, 517, 3074, 365, 730, and the other 19 excluded.
   - Boundaries: 24.999 mi in, 25.000 and 25.001 out, same-utility excluded, missing center excluded, month-precision date -> gap null.
   - Priority order on the sample: OVL_2, OVL_3, OVL_1, OVL_4, OVL_5, OVL_6.
6. **Fixtures for the UI** (`data/fixtures/`): projects, locations and matches from the golden sample (the real sample, labeled `view: historical`), plus one real `version_change`: DESC `0139 M,N`, in-service 2024-12-31 (2024–2028 filing, p. 3) -> 2026-05-31 (2025–2029 filing, p. 2). Other collections empty arrays. Validate all fixtures against the schemas in a test.
7. **Web shell.**
   - `web/lib/types.ts` mirroring the schemas.
   - `web/lib/data.ts`: `getProjects({bbox?, view?})`, `getMatches({view?, maxDistance?, limit?})`, `getPair(id)`, `getVersionChanges()`, `getCoverage()`, `getExtractions({source?})`. When `DATA_MODE=fixture`, it reads `data/fixtures`; otherwise it fetches the API routes below. On failure it returns a typed `{unavailable: true}`, never fixtures.
   - `app/layout.tsx` with `components/nav/` linking **all** routes: `/`, `/changes`, `/coverage`, `/gemini`, `/impact`.
   - Placeholder `page.tsx` for each route ("Coming soon", with the feature id) and for `/pair/[id]`.
   - Placeholder API route files returning 501 for `/api/projects`, `/api/matches`, `/api/pairs/[id]`, `/api/versions`, `/api/coverage`, `/api/extraction`, `/api/export`, `/api/health`.
   - `components/ui/` with a few primitives (Badge, Button, Table, EmptyState, ErrorState).
8. **Load stub.** `pipeline/load/__main__.py` exits 0 printing "not implemented" (F06 replaces it).
9. **CI and ownership.**
   - `.github/workflows/ci.yml`, job id **`ci`**, on `pull_request` and `push` to main: `uv sync`, `ruff`, `pytest`; `npm ci`, `lint`, `typecheck`, `build` with `DATA_MODE=fixture`; on PRs, `python3 scripts/check_ownership.py --title "$PR_TITLE" --base origin/$BASE`; plus `--lint-specs`.
   - `.github/workflows/load.yml`: on push to main touching `data/**`, run `cd pipeline && uv run python -m load` with `MONGODB_URI_RW` and `MONGODB_DB` from secrets.
   - A separate non-required job `e2e` (runs `tests/e2e` if present).
10. **`scripts/check_ownership.py`** (stdlib only, needs its own tests in `tests/golden/test_ownership.py`):
    - parses the YAML front matter of `specs/roadmap.md` and `specs/features/*/spec.md` (a minimal parser for the front matter subset used, or PyYAML if pinned)
    - `--lint-specs`: unique ids; every `depends_on` exists; no `owns` entry is a prefix of another feature's entry or of a frozen path
    - `--title T --base B`: reads `git diff --name-only B...HEAD` and applies the title-prefix rules in `overnight.md` §4 (including `[REVERT-<sha>]` reading `git show --name-only <sha>` and bootstrap `[F00]`); prints each offending file; exits 1
11. `.gitignore` (`.env*` except `.env.example`, `node_modules`, `.next`, `.venv`, caches) and `.env.example` listing every variable in tech-stack.

## Requirements
- Every frozen path in the roadmap exists at the end of F00.
- `pipeline/matches/core.py` is the **only** implementation of the overlap rules. Every other feature imports it.
- `DATA_MODE=fixture` works with no network and no secrets, and CI uses it.
- Don't add features beyond this list. Placeholders stay placeholders.

## Validation
- `cd pipeline && uv run pytest -q`: golden, boundary, fixture-schema and ownership tests pass. Paste the output.
- `cd web && npm run lint && npm run typecheck && DATA_MODE=fixture npm run build` passes.
- `python3 scripts/check_ownership.py --lint-specs` passes on the committed specs.
- Ownership self-test: a fake `[F05]` title with a changed file `pipeline/x.py` fails; `web/components/map/a.tsx` passes.
- PR title `[F00] Bootstrap`. After merge, confirm the `ci` check name exists (branch protection needs it).

## Defaults
- Next.js version: the current stable from `create-next-app`. Node 24.
- If a JSON Schema detail is unclear, make the field optional.
- If the 45-minute target slips, cut polish in the placeholders, never the golden test or the ownership gate.
