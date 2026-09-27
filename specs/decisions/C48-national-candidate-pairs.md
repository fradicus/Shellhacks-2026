# C48 — Precomputed national nearby candidates

## Authority and ownership
The user assigned this Codex session specification, implementation and delivery on
2026-09-27. They clarified: **provisional, simple 25-mile circles for now**.
Codex adopts technical-lead for this contract and F48, then the existing F30 and
F19 roles for sequential integration PRs. Original overnight gates are historical
for this bounded task. STOP, ownership and CI gates still apply.

F47 already belongs to SPP South on main. F48 below is a distinct claim. Draft
C46/#241's national driving-route proposal is not a prerequisite for this release.
This release neither changes legacy matching nor claims road-distance eligibility.

## Product
The Three.js map keeps its scope control. The default pair panel is **Nearby
candidates**, showing the nationwide ranked list and total. Region, state, grid
plan and pin scopes filter pairs with **both centers/projects inside the scope**.
Load 50 rows at a time. Each row shows both names, straight-line miles and location
uncertainty. Selecting it reuses the two-point highlight, circles and comparison;
full source/location evidence loads on demand. A separate Legacy pairs choice
preserves the existing filed pair views and evidence links.

Visible wording: “Provisional · under 25 miles straight-line. Driving routes and
construction schedules have not been checked.” A milestone gap is not a work window.
Only the selected or hovered pair gets a connection; never draw all pair lines.

## Matching contract
- Work from the assembled national snapshot. Exclude legacy projections (already
  represented in the legacy list), in-service/cancelled records, missing/invalid
  centers, county/area-only tiers and rejected/needs-review/unlocated records.
  Accept confirmed, official and tentative facility centers with their labels.
  Unknown lifecycle/milestone remains visible and does not become a future claim.
- Resolve every reported owner and co-owner through a cited, explicit alias ledger.
  Unknown/unmapped owners are excluded and counted. Group known related aliases
  conservatively; shared identities/co-owners cannot produce a cross-utility pair.
  No fuzzy owner inference, source-publisher substitution or duplicate A–B/B–A.
- Reuse canonical haversine (R=3958.8 miles), exact-date gap and priority logic.
  Distance is strictly <25 miles, classified before rounding. Spatial buckets are
  a conservative neighbor prefilter; exact haversine makes the final decision.
- Rank by <10-mile band, exact gap ascending (unknown last), unrounded distance,
  then stable canonical pair ID. All results remain provisional discovery leads.
- Record rule/identity versions, dataset, IDs, raw distance, nullable gap, rank,
  tier, shared state/region/plan scope fields and both center points.

## Publication and API
F48 owns generation, ledger, pair types/query/API and tests. F30's national loader
calls the generator after snapshot assembly and stages `national_candidate_pairs`
with projects/sources **before** activating `meta.national_active`. Generation or
pair-write failure preserves the previous dataset. Retain the same two datasets.
The existing load Action remains the only Atlas writer; explicitly dispatch it
once after integration, then every data publication regenerates pairs.

`GET /api/national-pairs?dataset=...&scope=...&offset=...` returns <=50 ranked
records, a total and the matching compact project summaries for that page.
Optional `id` loads a shared selection. Require the page's dataset; a changed
active pointer returns 409 with refresh guidance. Invalid query 400, unavailable
503, missing selection 404. Do not silently return an empty list on failure.
Reads have limits/timeouts; client requests are abortable and stale responses
cannot overwrite the current scope. No browser-side all-pairs calculation.

## Delivery
1. F48 generator/identity ledger/read API, tests and measured counts/runtime.
2. F30 atomic publication hookup, loader failure tests, load Action receipt.
3. F19 scoped paged list, selection/evidence, desktop/mobile browser checks.
F48's own completion marker covers its backend part; the user task is complete
only after all three parts merge and the real publication is verified.

## Validation / rollback
Test spatial prefilter against brute force, exact boundary, duplicate IDs, shared
owners, ambiguous aliases, null/partial dates, county/rejected exclusions, stable
ranking and scopes. Test atomic failure, dataset mismatch, pagination, query
validation, stale UI requests and map selection. Report accepted/excluded project
counts, pair counts by tier, generation duration and page size. No nationwide
completeness or construction/drive feasibility claim. Revert F19 to legacy panel;
remove F30 hook to stop generating pairs without changing source data.
