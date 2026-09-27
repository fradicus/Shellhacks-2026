---
id: F50
name: Interior West project coverage (WY, NV, UT, ID, MT) with loose labeled locations
lane: A
agent: data-researcher
phase: 7
depends_on: [F00, F30]
owns: [pipeline/interiorwest/, data/interiorwest/, tests/pipeline/test_f50_]
cut: never
---

# F50: Interior West project coverage

## Scope

Wyoming, Nevada, Utah, Idaho and Montana under [C50](../../decisions/C50-interior-west.md): WestConnect TPPL Wyoming
rows, then 2026 WECC Annual Progress Report transcriptions. F38's source, identity and no-invention rules apply. Do not
edit other rollouts' artifacts or releases.

## Plan

1. `uv run python -m interiorwest.build fetch --cache <dir>` downloads the pinned sources and OSM substations for the
   five states into a cache outside the checkout, with a hash manifest.
2. `build --cache <dir>` gives every source row an accepted/excluded disposition, locates what it can, and writes
   `data/interiorwest/{projects,sources,dispositions,summary,osm-sources}.json` plus the pinned `releases/active.json`.
   `--check` proves the committed files reproduce.
3. `interiorwest.publish.apply_release` validates and appends the release inside F30's `load_snapshot`.
4. Ship in parts: `[F50] part 1: Wyoming TPPL`, `[F50] part 2: WECC progress reports`.

## Requirements

- New IDs only; a project another rollout publishes is excluded with the reason.
- Reuse F45's TPPL reader and locator and F46's C33 locator by import; do not fork their rules.
- Transcribed rows carry page and verbatim quote; the build fails if a quote or facility name is not on its page.
- Raw downloads stay outside the checkout. OSM use carries ODbL attribution. No access control is bypassed.

## Validation

Tech-stack checks plus `tests/pipeline/test_f50_*`: scope, the ProjectName fallback, quote verification, and the
committed release applied to the base snapshot (unreviewed only, located points inside one of their states, counts
equal to the release). Spot-check located records per part and report errors. `changes/F50.md` only after part 2.
