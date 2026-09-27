---
id: F47
name: SPP South project coverage (OK, NM, non-ERCOT TX) with loose labeled locations
lane: A
agent: data-researcher
phase: 7
depends_on: [F00, F30]
owns: [pipeline/sppsouth/, data/sppsouth/, tests/pipeline/test_f47_]
cut: never
---

# F47: SPP South project coverage

## Scope

Oklahoma, eastern New Mexico and non-ERCOT Texas from SPP's Q3 2026 project tracking workbook, under
[C47](../../decisions/C47-spp-south.md). F38's source, identity and no-invention rules apply. Do not edit other
rollouts' artifacts or releases.

## Plan

1. `uv run python -m sppsouth.build fetch --cache <dir>` downloads the SPP appendix zip and OSM substations for OK, NM
   and TX into a cache outside the checkout, with a hash manifest.
2. `build --cache <dir>` gives every row a locator and an accepted/excluded disposition, locates what it can, and
   writes `data/sppsouth/{projects,sources,dispositions,summary,osm-sources}.json` plus the pinned
   `releases/active.json`. `--check` proves the committed files reproduce.
3. `sppsouth.publish.apply_release` validates and appends the release inside F30's `load_snapshot`.

## Requirements

- IDs `spp-qpt-2026q3-south:<UID>`. New IDs only; a UID another rollout publishes is excluded.
- Reuse F46's SPP reader, name parser and locator by import (`midwest.build`); do not fork their rules. Owner codes
  new to this region get OSM operator fragments here.
- A candidate is an exact normalized name match in one of the row's states, corroborated (operator/voltage) or
  unique there, and never another utility's facility. Unlocated rows keep the reason.
- Raw downloads stay outside the checkout. OSM use carries ODbL attribution. No access control is bypassed.

## Validation

Tech-stack checks plus `tests/pipeline/test_f47_*`: scope and exclusion, operator keys for the new owners, and the
committed release applied to the base snapshot (unreviewed only, located points inside one of their states, counts
equal to the release). Spot-check 10 located records against the workbook and report errors. `changes/F47.md` last.
