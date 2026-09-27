---
id: F44
name: California project coverage from CAISO with loose labeled locations
lane: A
agent: data-researcher
phase: 7
depends_on: [F00, F30]
owns: [pipeline/california/, data/california/, tests/pipeline/test_f44_]
cut: never
---

# F44: California project coverage

## Scope

California under [C37](../../decisions/C37-california.md), using C33's location tiers plus C37's operator guard.
F38's source, identity and no-invention rules apply. Do not edit other rollouts' artifacts or releases.

## Plan

1. `uv run python -m california.caiso fetch --cache <dir>` downloads the CAISO Transmission Development Forum
   workbooks and the OSM California substations into a cache outside the checkout, with a hash manifest.
2. `build --cache <dir>` parses every row with a sheet/row locator and an accepted/duplicate/excluded disposition,
   locates what it can, and writes `data/california/{projects,sources,dispositions,summary,osm-sources}.json` plus
   the pinned `releases/active.json`. `--check` proves the committed files reproduce.
3. `california.publish.apply_release` validates and appends the release inside F30's `load_snapshot`.

## Requirements

- IDs `<source>:<CAISO project/upgrade ID>`; rows without an ID use their name slug. New IDs only.
- Reuse the F40 matcher (`greatlakes.match`) and Overpass helpers by import; the California pre-pass only extracts
  names (`<Name> NN kV …`, `(X Substation)`, `… Line (A – B)`, leading line codes).
- A candidate is an exact normalized name match in California, corroborated (operator/voltage) or unique in the
  state, and never another utility's facility. Unlocated rows keep the reason.
- Raw downloads stay outside the checkout. OSM use carries ODbL attribution. No access control is bypassed.

## Validation

Tech-stack checks plus `tests/pipeline/test_f44_*`: name forms, unique-name and operator-conflict rules, typo dates,
status mapping, and the committed release applied to the base snapshot (unreviewed only, ≥100 located with events,
≥100 located not in service or cancelled). Spot-check 12 located records against the source text and report errors.
