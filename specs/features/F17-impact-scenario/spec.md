---
id: F17
name: Impact scenario (stretch)
lane: B
agent: technical-lead
phase: 3
depends_on: [F11]
owns: [web/app/impact/, web/components/impact/]
cut: allowed
---

# F17 Impact scenario

## Plan
1. `/impact?pair=<id>`: the pair summary, then an editable scenario:
   `potential = avoided_mobilizations × unit_mobilization_cost − coordination_cost`.
   Every input starts **empty** and is labeled "user scenario". Low/base/high columns. The output is null until all inputs are entered. Negative results are shown as negative.
2. Show the contractor anecdote ($1.5M freight on one $5M job) as context text, **not** as a default ratio. Label the result "modeled potential, not realized savings".
3. Hypothetical milestone: the user enters alternative in-service dates, and the page recomputes the day gap with the same formula, labeled "Assumption", with a reset button. Published data is never changed.

## Sponsor-tailored follow-on

The user explicitly authorized finishing this feature on 2026-09-26 after reviewing the sponsor context.
See [F17 decision](../../decisions/F17-mobilization-scenario.md). This is a bounded follow-on to the original run.

- Frame the worksheet around transferring a mat or equipment package between jobs. User-entered coordination
  costs include extra transfer freight, handling, cleaning, inspection and administration, without default rates.
- An optional holding-cost switch extends the formula by subtracting `extra_idle_days × daily_package_cost`.
  These are additional chargeable days and the rate for the whole package, not a rate per mat. When disabled,
  holding costs are explicitly excluded. Enabling the switch requires both inputs before computing a result.
- Show the maximum whole idle days before potential becomes negative when a positive daily rate and a
  nonnegative pre-holding margin make that calculation meaningful. This is arithmetic under fixed assumptions.
- All numeric inputs start blank. Zero must be entered explicitly; invalid, nonfinite, negative or oversized
  inputs do not calculate. Counts/days are whole numbers; money has at most two decimals. Calculate in integer
  cents and reject unsafe combined totals. Negative modeled potential remains visible.
- Low/base/high represent independently entered scenarios, not statistical confidence. Warn if completed
  modeled results are not ordered low/base/high; never silently sort or rewrite assumptions.
- The existing pair-card link and global Impact link enter this route. A GET picker offers up to 100 available
  pairs. Preserve the pair's source references, filed date precision, classification and effective review state.
  Rejected/unreviewed pairs must not become validated opportunities because a scenario is positive.
- Standalone scenarios work without a pair or database. Missing IDs and database failures are explicit;
  fixture mode is visibly labeled. Changing pair opens a fresh worksheet.
- Add a package description, quote references/open questions, a user-marked verification checklist, print/PDF
  handoff and reset. Notes print in full. No persistence, credentials, API writes, booking or AI calls.
- Hypothetical dates remain separate from holding days and from source records. No inference of construction
  windows, equipment release dates, truck distance, soil suitability or timber-mat service life.

## Validation
- lint, typecheck, build; a screenshot showing empty inputs and one filled scenario.
- `node --test web/components/impact/model.test.mjs`: missing/invalid/zero/negative inputs, money arithmetic,
  opt-in holding cost, break-even, bounds and UTC milestone gaps.
- From `web/`, against a fixture-mode server on port 3017:
  `node_modules/.bin/playwright test -c components/impact/playwright.config.ts`.
  Check desktop/mobile inputs, negative results, date assumptions, reset, pair picker, missing pair, print
  notes and no horizontal overflow. Screenshot amounts are explicitly synthetic test inputs, not quotes.
- Complete all repo-wide checks before ready; separately report live deployment and observed PM use.

## Defaults
- Pure client-side math; no persistence.
