---
id: F42
name: Pacific Northwest project coverage with loose labeled locations
lane: A
agent: data-researcher
phase: 7
depends_on: [F00, F30]
owns: [pipeline/pnw/, data/pnw/, reports/pnw/, tests/pipeline/test_f42_]
cut: never
---

# F42: Pacific Northwest project coverage

## Scope

WA, OR, ID and MT under [C33](../../decisions/C33-pacific-northwest.md). F38's source, identity and no-invention rules
apply; its location bar is replaced by C33's labeled tiers. Do not edit F38/F39/F40/F41 artifacts or releases.

## Plan

1. Record a source ledger: public project registers (regional plans such as NorthernGrid, BPA and utility plans,
   state siting/regulator lists), facility geometry sources, access failures and rights. A link list is not coverage.
2. Parse each register deterministically into national-project records with a source locator per row. Every row gets
   an accepted/duplicate/excluded disposition with a reason.
3. Locate each project with the strongest C33 tier that holds; otherwise leave it unlocated with the reason.
4. Ship in parts (`[F42] part N: <source or state>`) with per-state totals by tier and status cohort.

## Requirements

- Output `data/pnw/projects.json` (national-project schema, `_id` `<source>:<native id>`, new IDs only) and
  `data/pnw/sources.json` (publisher, URL, vintage, retrieval UTC, SHA-256, rights).
- Candidate centers carry an additive `location_candidate` block (facility IDs, dataset, normalized name,
  corroboration or `unique_in_state`, endpoint role).
- **User amendments, 2026-09-27:** publish only work dated 2025-2035 (completed, cancelled, older waiver-list rows and
  out-of-window in-service dates are excluded with the reason), and **no county dots**: C33's county-reference tier
  is not used. A named county is kept only as `counties` GEOIDs for filtering; such a project stays unlocated.
- Reuse the F40 matcher and shared helpers by import; do not fork their rules.
- Raw downloads stay outside the checkout. OSM use carries ODbL attribution. Do not bypass access controls.
- A project listed by two sources is linked, not duplicated.

## Validation

Tech-stack checks, plus `tests/pipeline/test_f42_*`: parser replay against the pinned source hash; the loosened
unique-name rule rejects names with two in-state facilities, out-of-state facilities and contradicting
voltage/county; no record carries `approximate_location`; every record validates against the national schema. Spot-check 10 located projects per state against
the source text and report the sample and any errors. `changes/F42.md` only after all four states have ledgers and
published data.
