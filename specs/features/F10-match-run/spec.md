---
id: F10
name: Full-corpus overlaps and priority
lane: A
agent: geo-engineer
phase: 2
depends_on: [F09]
owns: [pipeline/match_run/, tests/pipeline/test_f10_, data/matches/, data/routes/]
cut: never
---

# F10 Match run

## Plan
1. Join active projects (F01, F02) with locations (F09); drop `rejected` endpoints. Compute centers **with `pipeline.matches.core.center`**.
2. Apply the C46 drive rule: route every `core.route_candidates` pair through `matches.routes.fetch_missing`
   (stored in `data/routes/routes.json`, schema `route`; only missing or stale pairs are requested), bind drives with
   `matches.routes.drives_for`, then run `core.overlaps(prepared, analysis_date, drives)` and `core.priority_sort`.
   Each match carries `drive_mi` and `route` (`matches.routes.route_summary`). The match run itself never calls a router.
3. **View:**
   - `future`: both dates exact and >= `analysis_date`, and both centers from high/medium locations
   - `historical`: a date before `analysis_date`
   - `tentative`: anything with a low-confidence location or an unknown date
4. Write `data/matches/matches.json` (schema `match`) and `data/matches/summary.json` (counts per view and band, pairs evaluated).
5. `review_state: needs_review` on every pair until F13 confirms it.

### Full-corpus adapter policy

- Recalculate the canonical parsed-JSON hashes for DESC projects, Georgia projects and the normalized OSM inventory,
  and require an exact match to F09's recorded semantic input fingerprints before using its locations.
- Bind every location to one active filing version by `project_id`, `source_id` and `project_key`, and to one actual
  filed endpoint by integer index and normalized name. Require complete slot coverage and globally unique location ids;
  duplicate slots, inactive or contradictory bindings, invalid coordinates and source-gated accepted locations fail
  the run rather than being dropped or deduplicated.
- Exclude unknown owners from cross-utility matching. Ignore any center already present on an input project and rebuild
  it only from accepted, finite, in-range location coordinates with `matches.core.center`.
- The summary distinguishes all active known-owner DESC×GPC combinations from centered pairs actually evaluated.
  It records spatial nonmatches, project exclusion reasons and overlap counts by view and band. Distances remain
  unrounded in stored data.

## Requirements
- **Don't reimplement any overlap rule.** Import `core` only. A rule change needs a `[C<n>]` PR from the contract owner.
- Sparse results are fine. Zero future overlaps is a valid answer, reported plainly.

## Validation
- `tests/pipeline/test_f10_*.py`: running the golden fixture through the full run path reproduces OVL_1..6 and the priority order from F00.
- Full-corpus replay from the committed inputs and stored routes must be byte-identical to the committed output. Do not
  assert fixed corpus counts (C46: corpora grow); every stored overlap stays `needs_review` pending F13.
- The summary counts routing candidates and route states (`ok`, `no_route`, `missing`, `stale`) so unknown drives are
  visible, never silently dropped.
- PR body: pairs evaluated, overlaps per view/band, and the top 10 with drive distance, straight-line distance and gap.

## Defaults
- A project with one located endpoint uses it as the center, with `center.basis: "one"`, and is never `future` unless that endpoint is high confidence.
