---
id: F37
name: 3D History page and sourced project/contract events
lane: B
agent: frontend-engineer
phase: 6
depends_on: [F19]
owns: [web/app/history/, web/components/history/, web/lib/history/, web/app/api/history/, pipeline/history/, data/history/, tests/web/history/, tests/pipeline/test_f37_]
cut: allowed
---

# F37 History

Status: specified; implementation and evidence acquisition pending. The user chose a separate, visually rich
Three.js page that looks and behaves very similarly to the main time view. Follow
[C19](../../decisions/C19-history-view.md), F19's time semantics and F21's shared visual direction.

## Purpose

From a planned project, find relevant past work, inspect its documented events and open supporting contract
or contractor records where available. `/time` remains the primary planning surface; `/history` is its sibling.
The existing Historical pair tab means a past filed milestone, not verified completion or an awarded contract.

## Plan and integration prerequisites

1. Verify a small set of public historical sources and explicit project-to-event/contract links. Record actual
   coverage, missing fields and unavailable sources before claiming contract discovery.
2. Agree a separate additive contract PR for shared scene modules, ownership, event schemas, navigation and
   loader integration. Reuse F19's MapLibre/Three.js foundation; F37 must not copy the renderer or edit F19's
   files without the owning lane's coordinated change. Use existing dependencies and accepted F21 tokens.
3. Build a bounded evidence importer/adapter and read-only history API in F37's paths. If C15/F35 outcome types
   have merged, consume their accepted public evidence representation where applicable; do not create a
   competing outcome model or expose private job histories. New storage/schema wiring belongs to the contract
   owner. Production retains Atlas reads and the existing load Action as sole Atlas writer.
4. Implement the scene, event list, evidence drawer and context-preserving navigation. Coordinate the
   `/time` entry action through its owner and the History nav item through the contract owner.
5. Verify the real research journey and visual/accessibility fallbacks before adding `changes/F37.md`.

## Visual and interaction requirements

- Preserve map navigation, camera gestures, utility colors, selection feedback, typography and evidence-drawer
  conventions. Inherit F21's dark glass surfaces, readable figures and visible unknown states. Use restrained
  warmer neutral highlights and archival labels to distinguish History without changing utility color meaning.
- Keep the vertical time axis: later dates are always higher. Label the axis origin and scale explicitly.
  A selected historical date range frames the scene. A draggable year plane and keyboard date controls scrub
  that period; the selected period and event types filter the map and list consistently.
- Distinguish the scrub cursor from the fixed, labeled analysis-date reference. The cursor is a time filter,
  not a reconstruction of what was known on that date. Publication and retrieval dates remain visible in
  evidence; an actual "as known then" replay requires a separately accepted versioned evidence contract.
- A project pillar may carry distinct shapes and text labels for filed in-service, award, actual construction
  start and actual completion events, but only when those events are documented. No synthetic lifecycle.
  Exact dates are points; month/year dates are spans with their original precision. Unknown dates remain in
  an explicit list section. A span intersects the selected range if any part overlaps; never impute a day.
- Selecting a project highlights its documented sequence and opens the evidence drawer. Lines between event
  markers show chronology only; they must not suggest uninterrupted construction or a known duration.
- Scrubbing lights up events in the selected period. Any playback is user-initiated, bounded and stoppable;
  no ambient loops or automatic camera flights. Reduced motion uses immediate state changes.
- Include a 2D toggle and a keyboard-accessible project/event list carrying the same facts. Unlocated projects
  stay searchable in that list and are never placed at a utility office, county center or guessed coordinate.
  WebGL/tile failure retains filters, records and source access. Support desktop and 390 px layouts.
- Provide year/date range, utility, region, event type and literal-text search. Expose work-type and contractor
  filters only for supported fields, with unknowns visible. Count projects separately from events/contracts;
  a project with several events must not inflate the project count.
- "Find similar past work" on `/time` opens History with a stable origin-project identifier and only supported
  context filters. Explain matching fields such as evidenced location or documented work type. Similarity is
  a research aid and does not alter canonical overlap/ranking or imply contractor suitability. Preserve the
  origin selection on return; selected range, filters and project survive reload and browser back/forward.

## Evidence requirements

- Every event has stable source/native identity, project linkage evidence, event type, planned/actual meaning,
  raw date and precision, and a source URL plus page/row/document locator. Retain publication/as-of metadata
  when known and retrieval evidence. An unknown publication date stays null.
- Distinguish the utility/project owner from the awarded contractor. A contract may cover multiple projects
  or only one component; represent the documented scope and links explicitly. Similar names or proximity alone
  cannot establish a project-contract link. Preserve conflicting claims for review rather than silently choosing.
- Preserve contractor names, scope, award date and amount only when sourced. Estimated project cost, awarded
  contract value and actual expenditure are separately labeled with currency and scope. An amendment does not
  become a second job or an unexplained total. No inferred savings or performance ratings.
- A past planned milestone does not prove award, construction or completion. Actual status and event dates
  require their own evidence. Do not interpret an in-service milestone as a construction window.
- Keep nulls and partial coverage visible. "No contract evidence in this dataset" must remain distinct from
  "no contract existed." Label synthetic fixtures and exclude them from real coverage and demonstration claims.
- Bound API filters, pagination and downloads; use dataset-scoped reads and explicit unavailable states.
  No arbitrary URL fetching, database queries or silent production fixture fallback.

## Validation and acceptance

- Run every tech-stack check plus meaningful history adapter and browser checks. Verify planned/actual
  separation, partial/unknown dates, date-range boundaries, duplicate/amended contracts, ambiguous links,
  conflicting sources, missing locations, exact filtered counts and bounded API/export behavior if exported.
- Capture desktop and 390 px evidence of overview, scrubbed period, selected event with source and 2D/failure
  states. Check keyboard scrub/selection, visible focus, reduced motion and map/list consistency. Record actual
  scene size and measured performance on the tested device; do not claim an unmeasured frame rate.
- Regression-check `/time` selection and pair links, stored distances/gaps and canonical golden tests after
  any shared scene extraction. Confirm both pages retain the same axis direction and utility identity colors.
- Demonstrate planned project → History with explained context → selected past event → original source.
  Contract-discovery acceptance additionally requires at least one verified public award/contract record with
  an evidenced project link. If none is available, record that requirement as unmet; a scene prototype cannot
  close it. Missing fields within a verified record remain explicitly unknown.
- This spec PR adds no completion marker. F37 closes only after the page, applicable integration and evidence
  acceptance pass, or a later approved scope change explicitly records any cut.

## Defaults

- Public sourced history only for this page. Private histories, predictive outcomes and operational planning
  remain with their separate owners and authorization boundaries.
- Reuse existing source identifiers and evidence components through narrow adapters. Start with a small
  verified corpus; do not build a universal procurement crawler or introduce another graphics framework.
- Label the route **History**. Keep `/time` primary and its current Historical pair filter intact. The page
  remains a 3D sibling; a horizontal timeline may be secondary detail, not the replacement main visualization.
