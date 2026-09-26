# F17 validation — 2026-09-26

Implementation verified against main `906e85f` (F34). Node 24.13.0; Python 3.12.13.

## Required checks

- `cd pipeline && uv run ruff check . && uv run pytest -q`: passed; 386 passed, 1 skipped.
- `cd web && npm run lint && npm run typecheck && DATA_MODE=fixture npm run build`: passed.
  Existing Big Shoulders fallback-font warning remains; the font downloads and build succeed.
- `python3 scripts/check_ownership.py --lint-specs`: passed, 29 features.
- `python3 scripts/check_ownership.py --title '[F17] Model matting mobilization and idle rental costs' --base origin/main`: passed.
- `git diff --check`: passed. Reviewed changes against main; only F17-owned paths and permitted spec/marker files.

## Feature checks

- `node --test web/components/impact/model.test.mjs`: 3 passed. Covers blanks, invalid input, explicit zero,
  negative results, cents, count/amount limits, overflow, optional holding costs, break-even and UTC date gaps.
- Fixture-mode optimized server on port 3017; from `web/`,
  `node_modules/.bin/playwright test -c components/impact/playwright.config.ts`: 4 passed across desktop/mobile.
  Covers scenario entry, holding costs, negative outcome, invalid input, date assumptions, reset, full print
  notes, pair selection, missing pair, horizontal overflow and no browser console/page errors.
- Separate server on port 3018 with DATA_MODE and MongoDB credentials unset: explicit unavailable states,
  no fixture substitution, standalone user-entered zero-cost calculation passed.
- Screenshots inspected: [empty desktop](empty-desktop.png), [filled desktop](filled-desktop.png),
  [empty mobile](empty-mobile.png), [filled mobile](filled-mobile.png).
  Entered amounts are labeled synthetic test inputs, not supplier quotes or real project estimates.

## Scope of this evidence

These checks establish local implementation behavior. They do not establish a live Atlas connection, a Vercel
production deployment, observed PM acceptance, actual equipment availability or realized financial savings.
The feature does not fetch soil properties or estimate timber-mat decay.
