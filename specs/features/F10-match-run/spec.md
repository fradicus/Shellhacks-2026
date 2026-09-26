---
id: F10
name: Full-corpus overlaps and priority
lane: A
agent: geo-engineer
phase: 2
depends_on: [F09]
owns: [pipeline/match_run/, tests/pipeline/test_f10_, data/matches/]
cut: never
---

# F10 Match run

## Plan
1. Join active projects (F01, F02) with locations (F09); drop `rejected` endpoints. Compute centers **with `pipeline.matches.core.center`**.
2. Run `core.overlaps` over all DESC × GPC pairs where both utilities are known and different. Apply `core.priority_sort`.
3. **View:**
   - `future`: both dates exact and >= `analysis_date`, and both centers from high/medium locations
   - `historical`: a date before `analysis_date`
   - `tentative`: anything with a low-confidence location or an unknown date
4. Write `data/matches/matches.json` (schema `match`) and `data/matches/summary.json` (counts per view and band, pairs evaluated).
5. `review_state: needs_review` on every pair until F13 confirms it.

## Requirements
- **Don't reimplement any overlap rule.** Import `core` only. A rule change needs a `[C<n>]` PR from the contract owner.
- Sparse results are fine. Zero future overlaps is a valid answer, reported plainly.

## Validation
- `tests/pipeline/test_f10_*.py`: running the golden fixture through the full run path reproduces OVL_1..6 and the priority order from F00.
- PR body: pairs evaluated, overlaps per view/band, and the top 10 with distance and gap.

## Defaults
- A project with one located endpoint uses it as the center, with `center.basis: "one"`, and is never `future` unless that endpoint is high confidence.
