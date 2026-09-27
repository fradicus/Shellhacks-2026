---
id: F48
name: Precomputed provisional national nearby pairs
lane: B
agent: technical-lead
phase: 7
depends_on: [F30, F31, F19]
owns: [pipeline/national_pairs/, data/national_pairs/, tests/pipeline/test_f48_, web/lib/national-pairs/, web/app/api/national-pairs/, tests/web/national-pairs/]
cut: never
---

# F48 National nearby pairs

Implement [C48](../../decisions/C48-national-candidate-pairs.md). This user-assigned
Codex session owns generation, explicit utility identities, bounded dataset-pinned
reads and tests. F30 publication and F19 rendering follow as separate owned PRs.

## Validation
- Focused Python generator tests, brute-force equivalence and real snapshot report.
- Node query/API tests under `tests/web/national-pairs/` with the existing TS loader.
- Repo change-scoped checks and ownership review before merge.

## Defaults
Use standard-library spatial buckets and existing MongoDB/Zod clients. No new
packages, routing requests or public-site computation of cross-project distances.
Unresolved owners stay excluded with a reason; tentative facility locations remain
eligible with their visible uncertainty. No data quotas or invented dates.

## C55 search

Implement [C55](../../decisions/C55-candidate-search.md)'s optional `q` read API
and focused tests before F19 uses it. Search preserves the published matching
rule and stored rank; it never re-generates pairs or guesses owner identities.
