---
id: F51
name: California municipal-utility project coverage from WECC progress reports
lane: A
agent: data-researcher
phase: 7
depends_on: [F00, F30, F50]
owns: [pipeline/camunis/, data/camunis/, tests/pipeline/test_f51_]
cut: never
---

# F51: California municipal utilities

## Scope

LADWP, IID, SMUD, TANC, TID and MID projects from their 2026 WECC Annual Progress Reports, under
[C51](../../decisions/C51-california-munis.md). F38's source, identity and no-invention rules apply. Do not edit other
rollouts' artifacts or releases.

## Plan

1. `uv run python -m camunis.build fetch --cache <dir>` downloads the six reports and OSM substations for CA, UT and NV
   into a cache outside the checkout, with a hash manifest.
2. `build --cache <dir>` verifies every transcribed row on its page, gives it an accepted/excluded disposition, locates
   what it can, and writes `data/camunis/{projects,sources,dispositions,summary,osm-sources}.json` plus the pinned
   `releases/active.json`. `--check` proves the committed files reproduce.
3. `camunis.publish.apply_release` validates and appends the release inside F30's `load_snapshot`.

## Requirements

- Reuse F50's progress-report reader (`interiorwest.apr`) by import; do not fork its verification or placement rules.
- New IDs only; a project F44, F45 or F50 publishes is excluded with the reason.
- Raw downloads stay outside the checkout. OSM use carries ODbL attribution. No access control is bypassed.

## Validation

Tech-stack checks plus `tests/pipeline/test_f51_*`: scope and exclusions, operator keys, and the committed release
applied to the base snapshot (unreviewed only, located points inside one of their states, counts equal to the
release). Spot-check located records and report errors. `changes/F51.md` last.
