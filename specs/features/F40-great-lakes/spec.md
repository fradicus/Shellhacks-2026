---
id: F40
name: Great Lakes project coverage with labeled candidate locations
lane: A
agent: data-researcher
phase: 7
depends_on: [F00, F30]
owns: [pipeline/greatlakes/, data/greatlakes/, reports/greatlakes/, tests/pipeline/test_f40_]
cut: never
---

# F40: Great Lakes project coverage

## Scope

MN, WI, MI, IL, IN, OH, PA and NY, in that order, per [C26](../../decisions/C26-great-lakes-candidates.md). The user's
target is ~5,000 map points; it is a target, not a quota. F38's source, identity, history and no-invention rules apply;
its location bar is relaxed only through C26's labeled candidate tier and, from part 4, C33's labeled unique-name
tier and HIFLD fallback ([F40-hifld-c33](../../decisions/F40-hifld-c33.md)). Do not edit F38/F39 artifacts or releases.

## Plan

1. Per state, record a source ledger: public project registers (state biennial/ten-year plans, regulator dockets,
   ISO/RTO lists), facility geometry sources, access failures (e.g. MISO 403) and rights. A link list is not coverage.
2. Parse each reviewed register deterministically into national-project records with a source locator per row.
   Every row gets accepted/duplicate/excluded disposition with a reason.
3. Extract facility names the source text names as sites or endpoints. Match them to public facility geometry under
   C26's rules. Publish the center as an unverified candidate or leave it null with the unresolved reason.
4. Ship one state per PR (`[F40] part N: <state>`), with per-state totals: projects, candidate-located, partial
   (one endpoint), unlocated by reason, status cohorts.

## Requirements

- Output `data/greatlakes/projects.json` (national-project schema, `_id` `<source>:<native id>`, new IDs only) and
  `data/greatlakes/sources.json` (publisher, URL, vintage, retrieval UTC, SHA-256, rights).
- A transmission owner's own public project-map coordinate for a named project (e.g. AEP Transmission's state maps)
  is also a candidate: `basis: source_point`, evidence naming the map file and marker, precision unstated. It is
  stronger than a name match but still unreviewed, never `confirmed`.
- Candidate centers use `location_review: "unreviewed"` and an additive `location_candidate` field with facility
  ID(s), dataset, normalized name, corroborating fields and endpoint role. Never `confirmed`.
- Raw downloads stay outside the checkout. OSM use carries ODbL attribution. Do not bypass access controls.
- A project that also appears in another corpus (e.g. an MTEP number already imported) is linked, not duplicated.

## Validation

Tech-stack checks, plus `tests/pipeline/test_f40_*`: parser replay against the pinned source hash; matcher rejects
substring/fuzzy names, out-of-state and ambiguous same-name facilities; centers follow the mean/partial rule; every
record validates against the national schema. Spot-check at least 10 candidates per state against the source text and
map, and report the sample and any errors. `changes/F40.md` only after all eight states have ledgers and published data.

## Part 5: Pennsylvania construction register

Use the browser-saved, SHA-256-pinned PJM XML through the strict existing F38 reader. Import only explicit
PA rows and exclude already-published PJM native IDs plus source-described distribution-only work. Preserve
a disposition for every row, raw owner codes and separate milestone dates. An unresolved site-equipment
circuit label stays unlocated; the shared line candidate policy remains unchanged. Publish inside the existing
Great Lakes release, with no new loader folder. See [F40-pjm-pa](../../decisions/F40-pjm-pa.md).
