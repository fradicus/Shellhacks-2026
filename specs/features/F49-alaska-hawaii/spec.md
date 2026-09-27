---
id: F49
name: Alaska and Hawaii project coverage from transcribed public documents
lane: A
agent: data-researcher
phase: 7
depends_on: [F00, F30]
owns: [pipeline/akhi/, data/akhi/, tests/pipeline/test_f49_]
cut: never
---

# F49: Alaska and Hawaii project coverage

## Scope

Transmission lines and substations in Alaska and Hawaii from public documents, under
[C49](../../decisions/C49-alaska-hawaii.md). F38's source, identity and no-invention rules apply. Generating
facilities, storage and program-level spending are out of scope. Do not edit other rollouts' artifacts or releases.

## Plan

1. `data/akhi/transcribed.json` lists the cited sources (URL, publisher, format) and each project with its facts,
   quotes and locators.
2. `uv run python -m akhi.build fetch --cache <dir>` downloads every cited document and the OSM substations for
   AK and HI into a cache outside the checkout, with a hash manifest.
3. `build --cache <dir>` checks every quote against its document's text, locates what it can, and writes
   `data/akhi/{projects,sources,dispositions,summary,osm-sources}.json` plus the pinned `releases/active.json`.
   `--check` proves the committed files reproduce.
4. `akhi.publish.apply_release` validates and appends the release inside F30's `load_snapshot`.

## Requirements

- IDs `<source>:<native id>` with a new source ID per cited document family; one project per real project, with
  several documents cited as evidence rather than duplicated records.
- Quotes are compared after collapsing whitespace and case; a missing quote fails the build.
- Reuse the C38 matcher (`california.caiso.match`) and the F40 Overpass helpers by import. Endpoint names are
  the facilities the document names; a description ("near", "a new substation") is not a facility.
- A released center lies inside its state, compared on `fit_west..fit_east_unwrapped` for Alaska.
- Raw downloads stay outside the checkout. OSM use carries ODbL attribution. No access control is bypassed.

## Validation

Tech-stack checks plus `tests/pipeline/test_f49_*`: the quote check, date precision, the antimeridian center check
(an Alaska point passes, a point outside fails), and the committed release applied to the base snapshot
(unreviewed only; located points inside their state; at least one located project in each of AK and HI). Report
record, located and dated counts per state honestly; no density target is set because the sources are thin.
