# F00 decisions (bootstrap)

Each entry: context, choice, how to undo.

1. **View classification lives in `core.view`.** F10 defines the three views but can't edit the frozen core, so F00
   implements them there: `historical` if either exact date is before `analysis_date`; `future` if both exact dates are
   on/after it and both projects' `location_confidence` is high/medium; otherwise `tentative`. A pair with one past date
   and one unknown date is `historical` (the past date is the stronger fact). Undo: `[C<n>]` changing `core.view`.
2. **Project input to `core` carries `center`, `in_service`, `utility`, `location_confidence`.** `center()` skips
   `rejected` endpoints and anything without both lat and lon, and averages all remaining (normally two).
3. **Sample fixture ids.** Sample projects use `project_key` `DESC:DESC_1` / `GPC:GPC_1`, source id `sperry-sample`.
   `owner_code` is null with `owner_basis: "utility column of the sponsor sample"` (the workbook gives the utility, not
   an owner code). Sample coordinates get confidence `high` with the workbook row/column as evidence; missing sample
   coordinates are `rejected` location records ("No coordinates in the sponsor sample") so the UI shows them as unknown.
4. **Version-change fixture source ids** are `desc-2024-2028` and `desc-2025-2029`. F01 should use the same ids for the
   two DESC filings so the fixture and real data line up. The 2024–2028 side (p. 3, `12/31/2024`) was checked in the
   PDF; the 2025–2029 side comes from the spec (that PDF isn't in `docs/`).
5. **`data.ts` in API mode fetches this app's own `/api/*`** (spec). Server-side base URL: `SITE_URL`, else the
   production domain (`VERCEL_PROJECT_PRODUCTION_URL`) in production, else `VERCEL_URL`, else localhost. The unique
   deployment URL is skipped in production because Vercel deployment protection can 401 it. Fetches use
   `cache: "no-store"`, so data pages render per request instead of freezing an "unavailable" state at build time.
   Undo: point `data.ts` at `web/lib/server/` directly via `[C<n>]`.
6. **`MatchRow` / `PairDetail` response shapes** are fixed in `types.ts`: `/api/matches` returns matches with
   `project_a`/`project_b` joined (no endpoints); `/api/pairs/[id]` returns `{match, a, b, brief, version_changes}` with
   endpoints joined and only a `passed` brief.
7. **No web unit-test runner.** Only Playwright (non-required `e2e` job). F11's CSV injection check goes in its PR body
   or a Playwright spec. The e2e job builds in fixture mode, serves on :3000, sets `BASE_URL`, and runs
   `playwright test -c tests/e2e` (so F07's config lives at `tests/e2e/playwright.config.ts`).
8. **Styling: plain CSS + CSS modules**, no Tailwind. Shared tokens (utility colours, bands) in `globals.css`;
   primitives and display formatters (`fmtMiles`, `gapText`, `bandLabel`) in `components/ui/`. No web fonts, so the
   build needs no network.
9. **Ruff rule set** pinned in `pipeline/pyproject.toml` (`E,F,W,I,B,UP`) so a developer's global ruff config can't
   change CI results.
10. **Repo settings not applied**: the account running F00 has push but not admin, so branch protection and auto-merge
    are still off (human pre-flight §2, `fradicus`). Until then `ci` is not enforced; agents must wait for a green `ci`
    before `gh pr merge --squash`.
