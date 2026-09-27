---
id: F45
name: Southwest project coverage from WestConnect with loose labeled locations
lane: A
agent: data-researcher
phase: 7
depends_on: [F00, F30]
owns: [pipeline/southwest/, data/southwest/, tests/pipeline/test_f45_]
cut: never
---

# F45: Southwest project coverage

## Scope

Arizona, New Mexico and Colorado from the WestConnect TPPL workbook; a few Nevada and Utah lines from WestTEC,
under [C42](../../decisions/C42-southwest.md). F38's source, identity and no-invention rules apply. Do not edit
other rollouts' artifacts or releases.

## Plan

1. `uv run python -m southwest.build fetch --cache <dir>` downloads the TPPL workbook, the WestTEC planned layer and
   OSM substations for the five states into a cache outside the checkout, with a hash manifest.
2. `build --cache <dir>` gives every row a locator and an accepted/excluded disposition, locates what it can, and
   writes `data/southwest/{projects,sources,dispositions,summary,osm-sources}.json` plus the pinned
   `releases/active.json`. `--check` proves the committed files reproduce.
3. `southwest.publish.apply_release` validates and appends the release inside F30's `load_snapshot`.

## Requirements

- IDs `<source>:<native id>`: the TPPL `projectid`, the WestTEC line-name slug. New IDs only; never a WestTEC
  feature F42 already published.
- Reuse the C38 matcher (`california.caiso.match`) and Overpass helpers by import. Endpoint names come from the
  Origin and Termination cells only, cleaned of voltages, equipment words and "(formerly …)". Descriptions such as
  "near the existing…", "TBD" or "a new or existing substation" are not facilities.
- A candidate is an exact normalized name match in the row's state, corroborated (operator/voltage) or unique in
  the state, and never another utility's facility. Unlocated rows keep the reason.
- Raw downloads stay outside the checkout. OSM use carries ODbL attribution. No access control is bypassed.

## Validation

Tech-stack checks plus `tests/pipeline/test_f45_*`: endpoint cleaning, year and status mapping, the operator guard,
and the committed release applied to the base snapshot (unreviewed only; located points inside their state;
≥100 located with a dated event and ≥100 located not in service or cancelled across the five states). Spot-check 12
located records against the workbook and report errors.
