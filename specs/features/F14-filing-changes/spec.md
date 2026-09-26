---
id: F14
name: Filing-change view
lane: B
agent: frontend-engineer
phase: 3
depends_on: [F01, F06]
owns: [web/app/changes/, web/components/changes/]
cut: allowed
---

# F14 Filing-change view

## Plan
1. `/changes`: the list of `version_change` records (from `getVersionChanges`), grouped by project. Each shows the old value, the new value, both filings' names and pages (DESC public PDF links `#page=N`), and whether the project appears in any match.
2. Highlight the verified example `DESC:0139 M,N`: in-service 2024-12-31 -> 2026-05-31. Label historical items as historical (both dates are before the analysis date) and make no claim of a current delay.
3. Filter by field (in-service, cost, status). Show an empty state if there are no changes.

## Validation
- lint, typecheck, build; a fixture-mode screenshot showing the 0139 M,N change.

## Defaults
- Show at most 200 changes, with a count of the total.
