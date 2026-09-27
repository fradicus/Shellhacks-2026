# C30 — Planning and History date windows

Status: proposed specification only, 2026-09-27. Implementation is deferred.
Tracking issue: [#170](https://github.com/fradicus/Shellhacks-2026/issues/170).

The user requested a spec, issue and PR and explicitly said **do not start work on this**.
This document does not authorize implementation, autonomous pickup, deployment, database changes or F37 completion.
No feature completion marker accompanies this proposal.

## Problem and existing contracts

Old filed milestones can extend the `/time` vertical axis back decades. F19 currently derives the axis origin
from the earliest drawn year; the Future/Historical/Tentative pair tabs do not bound the whole map population.
A bounded planning view should remain useful while older records stay accessible in a separate History view.

This proposal extends [C19](C19-history-view.md) and [F37](../features/F37-history-view/spec.md), which already
specify `/history` as a sibling of `/time`. It proposes replacing the earliest-record axis rule in
[F19](../features/F19-time-view/spec.md) and bounding the default display population described in
[C25](C25-main-demo-map.md). Those changes take effect only through a separately authorized implementation.
Existing feature specifications and shipped behavior are not rewritten by this draft.

## Storage and scope

Keep all existing legacy and national records in their current database and collections. Both routes read the
same records through application queries. No migration, historical collection, archival copy, record movement,
deletion, schema change, database writer, new provider or matching pipeline is required by this proposal.
Date windows control display and retrieval; they never rewrite source facts or lifecycle status.

National readers already accept `from`/`to` and dataset-scoped filters. Reuse these and existing indexes first.
Legacy readers need equivalent application-level date semantics. This is a query/UI change, not permission to
alter frozen shared readers without their owner. Additional indexes require measured query evidence and a
separate reviewed change; this spec makes no performance claim about the current query plan.

## Routes and defaults

Let Y be the year of the explicitly declared analysis date, not an independently advancing browser clock.
These are proposed product defaults, not sponsor distance/date requirements:

| View | Default inclusive window | Purpose |
|---|---|---|
| `/time` | January 1 of Y through December 31 of Y+5 | Current year plus five following years of planning milestones |
| `/history` | January 1 of Y-5 through December 31 of Y-1 | Previous five calendar years of filed milestones |

For analysis year 2026 these defaults are 2026–2031 and 2021–2025. Users can select other ranges, including
2001–2010. Both routes expose editable bounds and a reset-to-default control. A custom range can cross the
analysis date; route names do not manufacture a lifecycle classification.

Persist `from`/`to` and supported filters in the URL; navigation/back restores them. Reject malformed dates
and reversed ranges with a visible error. Use inclusive UTC calendar dates consistently on server and client.
Show the active range, dataset scope and **Analysis date**. Do not label a fixed analysis date “Today” or
silently recompute stored match classifications when the system clock advances.

## Date and status semantics

- Exact day: include when `from <= day <= to`.
- Month/year precision: use the full calendar interval, including leap years; include when that interval
  intersects the selected range. Keep original precision and evidence in every display.
- Unknown date: exclude from the dated scene and dated count; provide an explicitly labeled, bounded,
  paginated unknown-date grid using the same non-date filters. Never place it at a fabricated date.
- Located and unlocated records use the same date predicate. Unlocated dated records remain in the grid and
  have a separate count; they do not acquire invented coordinates to appear in the scene.
- Past target dates do not prove completion. A target interval wholly before the analysis date with planned,
  under-construction or unknown status remains discoverable in an overdue/unresolved-target grid. Preserve
  the source status and explain that this flag concerns a filed target, not observed construction progress.
- Unknown and overdue sections have explicit scopes and counts; do not add overlapping counts into a false
  unique total. A partial interval spanning the analysis date is not automatically overdue.

Use the same predicate across legacy and national adapters, maps, grids, pagination and counts. Preserve
existing source-confidence eligibility and geography/owner/status filters. No date filter upgrades candidate
coordinates or confirms an unknown status.

## Axis and interaction

The selected bounds determine the vertical date domain. Records outside that domain cannot extend it.
Auto-fit the selected span to the available scene height on initial load, range changes and reset; a minimum
pixels-per-year value must not prevent fitting. A manual scale override is allowed with visible units and reset.

For partial dates, draw only the intersecting portion and indicate continuation beyond a bound; evidence still
shows the complete original interval. Never clamp an out-of-range exact date onto a boundary to imply it occurred
there. Unknown dates appear in their list, not as dated pillars on the ground plane.

Keep the analysis-date plane only when it lies in the selected domain; otherwise show its date outside the
scene with a clear out-of-range indication. Preserve the existing 2D option, keyboard navigation, accessible
grid and source evidence. Empty ranges and unavailable data have explicit states.

## Pairs

Stored Future/Historical/Tentative tags, distances, exact day gaps and priority order remain unchanged.
The in-window pair list includes a stored pair only when both endpoints satisfy the date predicate. Disclose
how many retrieved pairs are excluded by the window and the retrieval scope; do not present a capped retrieval
as a complete database total. Unknown-date endpoints are not silently eligible for a dated pair list.

Changing the range clears a selection that is no longer eligible. A direct pair link with an out-of-window
endpoint offers an explicit action to expand the range to include the pair. It cannot silently stretch the axis.
This proposal adds no national pair generation, road-distance routing or new distance threshold.

## Retrieval and efficiency

Apply date/non-date filters on the server before returning scene points. Keep list pagination, bounded map
payloads and explicit truncation/coverage labels. Counts must declare whether they describe matching records,
located records, drawn points or retrieved pairs. Never treat the first grid page as the full map population.

For national data, resolve one active dataset per response and use it consistently for points, lists and counts.
Retain the existing legacy/national availability separation; one unavailable source does not erase the other.
Unknown and overdue sections use bounded queries with their declared date exceptions. Avoid fetching every
historical record into the browser just to filter it locally. Reuse the same normalized bounds within a request;
measure representative query timings and payload sizes before proposing extra caches or indexes.

## History scope and ownership

Initial historical browsing may show only existing **filed project milestones**. It must say so. Awards, actual
starts and actual completions require their own sourced evidence under F37; a target date is not an actual event.
This limited stage cannot satisfy the full F37 sourced-contract/event acceptance criteria.

After an explicit launch, coordinate F19 (time scene), F37 (History), F31 (national queries) and F06 (legacy
readers). Shared scene extraction, navigation and any frozen interfaces require an additive contract approved
through the technical-lead lane before implementation. Keep one renderer with route-specific configuration;
do not duplicate it or transfer ownership implicitly. This proposal assigns no worker and starts no feature.

## Acceptance for the later implementation

1. A dated 2001 record remains retrievable in History but cannot change a selected 2026–2031 planning axis.
2. Exact boundary days, leap day, month/year intersections, unknown dates, unlocated records and empty ranges
   produce consistent map/grid/count results; original precision is retained.
3. Old planned/unknown targets remain discoverable without becoming completed. Partial intervals crossing the
   analysis date are handled according to the interval rule.
4. URL reload/back, reset, range changes, out-of-window pair links and selection clearing behave as specified.
5. Stored match metrics, classifications and ranks remain identical; no new national matches appear.
6. Pagination/truncation and dataset consistency are verified on representative data, including source failures.
   Read-only checks confirm that both views reference existing record IDs without database writes or migration.
7. Fit behavior works on desktop/mobile with keyboard and 2D/grid fallbacks; required repository checks pass.
8. Record measured query/payload results and remaining F37 evidence gaps; do not claim full History completion.

## Delivery and reversal

This PR contains specification changes only. Keep #170 open for later delivery and leave F37 unstarted.
A separate explicit user launch is required before implementation. Later delivery may be staged as bounded
`/time` filtering and then History browsing, with full sourced events still governed by F37.
Reversal restores the previous application queries and view defaults; no data restoration or migration is needed.
