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

## Validation
- lint, typecheck, build; a screenshot showing empty inputs and one filled scenario.

## Defaults
- Pure client-side math; no persistence.
