---
id: F46
name: Midwest project coverage from SPP and MISO with loose labeled locations
lane: A
agent: data-researcher
phase: 7
depends_on: [F00, F30]
owns: [pipeline/midwest/, data/midwest/, tests/pipeline/test_f46_]
cut: never
---

# F46: Midwest project coverage

## Scope

Iowa, Missouri, Kansas, Nebraska, North Dakota and South Dakota from SPP's Q3 2026 project tracking workbook and the
MISO rows F40 excluded, under [C43](../../decisions/C43-midwest.md). F38's source, identity and no-invention rules
apply. Do not edit other rollouts' artifacts or releases.

## Plan

1. `uv run python -m midwest.build fetch --cache <dir>` downloads the SPP appendix zip and OSM substations for the six
   states into a cache outside the checkout, with a hash manifest. Part 2 adds F40's pinned MISO workbook.
2. `build --cache <dir>` gives every row a locator and an accepted/excluded disposition, locates what it can, and
   writes `data/midwest/{projects,sources,dispositions,summary,osm-sources}.json` plus the pinned
   `releases/active.json`. `--check` proves the committed files reproduce.
3. `midwest.publish.apply_release` validates and appends the release inside F30's `load_snapshot`.
4. Ship in parts: `[F46] part 1: SPP`, `[F46] part 2: MISO`.

## Requirements

- IDs `<source>:<native id>`: SPP `UID`, MISO MTEP project ID. New IDs only.
- Reuse the C38 matcher (`california.caiso.match`), F40's name parser and Overpass helpers by import; do not fork
  their rules. SPP forms F40 does not read ("… Terminal Upgrade toward X", bus codes) are handled in `midwest`.
- A candidate is an exact normalized name match in one of the row's states, corroborated (operator/voltage) or
  unique there, and never another utility's facility. Unlocated rows keep the reason.
- Raw downloads stay outside the checkout. OSM use carries ODbL attribution. No access control is bypassed.

## Validation

Tech-stack checks plus `tests/pipeline/test_f46_*`: upgrade-name endpoint forms, status and date mapping, the operator
guard, and the committed release applied to the base snapshot (unreviewed only, located points inside one of their
states, counts equal to the release). Spot-check 10 located records per part against the workbook and report errors.
`changes/F46.md` only after part 2.
