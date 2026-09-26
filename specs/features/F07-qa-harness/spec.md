---
id: F07
name: QA harness - independent golden check + e2e smoke
lane: C
agent: qa-verifier
phase: 1
depends_on: [F00]
owns: [tests/e2e/, reports/qa/]
cut: allowed
---

# F07 QA harness

## Plan
1. **Independent golden check** (`reports/qa/golden.md` plus a script under `tests/e2e/golden_independent.py`): read the xlsx directly with `openpyxl`, recompute the centers, haversine and gaps **without importing `pipeline.matches.core`**, and compare against both the workbook's overlap sheet and F00's `core` output. Report any difference, however small.
2. **Playwright smoke** (`tests/e2e/smoke.spec.ts`, run by CI's non-required `e2e` job against `DATA_MODE=fixture npm run build && npm start`): every nav route returns 200 with no console errors; the home list shows 6 rows in fixture mode; clicking the first row opens `/pair/...`.
3. **Post-merge audit loop** (the rest of the run, between other work): for each newly merged PR, skim the diff for rule violations (overlap logic outside `core`, fixtures served in production, secrets, invented data). File issues labeled with the owning lane.

## Validation
- The golden script exits 0 and prints the 6 pairs. The smoke test passes locally in fixture mode; paste the output.

## Defaults
- A smoke failure caused by an unfinished placeholder route is not a bug. Skip it with a note until that route's feature is done.
