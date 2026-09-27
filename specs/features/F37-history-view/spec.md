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

Status: part 1 (the page over documented events already in the active datasets) started at the user's explicit
request on 2026-09-27 ([decision](../../decisions/F37-history-part-1.md)). Contract/award discovery remains a
separate, unmet requirement (see *Delivery parts*). The user chose a separate, visually rich Three.js page that
looks and behaves very similarly to the main time view. Follow [C19](../../decisions/C19-history-view.md), F19's
time semantics and F21's shared visual direction.

## Purpose

From a planned project, find relevant past work, inspect its documented events and open the original source
record. `/time` remains the primary planning surface; `/history` is its sibling. The existing Historical pair tab
means a past filed milestone, not verified completion or an awarded contract.

**The one idea.** `/time` answers *when will it be built, above where*. `/history` answers *what was actually
built, when, and how that compared with the plan*: every located project stands where it is, its documented
events stacked at their dates, and a movable year plane lets you watch the record accumulate.

## What the datasets already document

Measured on 2026-09-27 from the committed assembly (`national.build.load_snapshot()` on `origin/main` at `1d1eb4a`),
which is what the load Action publishes. These are the same records `/time` and `/explore` read.

| Source | Located, confirmed | Documented events |
|---|---|---|
| PJM construction register (`mid-atlantic:pjm-construction`) | 263 | per-row `project_events`: `ActualInServiceDate` (typed `in_service`, 235 rows), and `ProjectedInServiceDate`, `RequiredDate`, `RevisedInServiceDate`, `ISAInServiceDate` (typed `planned_milestone`) |
| ISO-NE RSP June 2026 (`iso-ne-rsp-2026-06`) | 345 | the register's status (e.g. "In-service") and its *projected* in-service month: a plan value, not an actual date |
| Florida DEP, NYPSC | 4 | certification events, "not a construction or in-service date" as sourced |
| Legacy DESC/GPC filings | per the legacy dataset | the filed in-service milestone; F14 filing revisions (old → new date between two filings) |

No public award/contract record with an evidenced project link exists in these datasets.

## Delivery parts

1. **Part 1: the page.** `/history` over the documented events above. A read-only adapter in `web/lib/history/`
   derives events from the active national records (`project_events`, register status, stored in-service value)
   and legacy filings (filed milestone, F14 revisions). No new storage, importer, writer, schema or record copy.
   Production reads Atlas through the existing national/legacy loaders; fixture and snapshot modes behave exactly
   as those loaders do, and say so on screen.
2. **Part 2: contract/award discovery (deferred, unmet).** Verify a small public source set with an explicit
   project-to-award link and add it additively through the contract owner. Until then the page states "No contract
   or award evidence in this dataset". A working scene cannot close this requirement.

## Visual grammar: longitude, latitude, time

Longitude and latitude are the map; the vertical is time, later always higher, exactly as on `/time`. History adds:

- **Event glyphs by evidence meaning, never by colour.** Identity colours keep `/time`'s meaning.
  - Solid bead: a documented *actual* event (PJM `ActualInServiceDate`).
  - Hollow ring: a documented *plan* (projected, required, revised, ISA dates; a filed legacy milestone).
  - Square tick: another documented event (certification), with its sourced description verbatim.
  - Frosted column with open ends: a month/year value over its whole span; no day picked (F19's rule).
- **Plan → actual thread.** When a project documents both a plan date and an actual date, a thin thread joins them
  on its pillar. Selecting the project turns it into a drafting bracket labelled with the day difference between
  the two *documented* dates and names both fields ("actual 412 days after RequiredDate"). The thread shows
  chronology only, never construction duration or cause. Legacy F14 revisions draw the same way (old filed date →
  new filed date between two named filings).
- **The year plane.** A warm, engraved glass plane at a chosen date; the analysis date stays a separate, fixed,
  labelled tick. Events at or below the plane are lit, events above it are ghosted. It is a time filter, not an
  "as known then" replay; that needs a versioned evidence contract.
- **Ground ripples.** When the plane passes upward over a documented *actual* in-service event during user-initiated
  playback or scrubbing, a ring expands once on the ground at that project. Never ambient. None under reduced motion.
- **The ledger.** A secondary 2D strip under the scene: documented events per year, actual and plan stacked
  separately, the plane's year marked, and a draggable selected range. It is the date-range filter and a second,
  keyboard-accessible scrubber. It is detail, not a replacement for the 3D scene.
- **Playback.** "Play the record" moves the plane from the range start to its end in a few seconds with a counter
  ("214 documented actual in-service dates by 2014"). User-initiated, stoppable, off under reduced motion.
- **Palette.** F21 dark glass with warm parchment/amber for History's own chrome (plane, ledger, overline), so the
  sibling reads as an archive rather than a forecast. The default camera bearing mirrors `/time`'s so the pages are
  distinguishable at a glance; axis direction, controls and layout do not change.

## Interaction requirements

- Preserve map navigation, camera gestures, selection feedback, typography and evidence-drawer conventions.
- Selecting a project highlights its documented sequence, frames it and opens the evidence drawer: every event in
  date order with type, planned/actual meaning, raw value and precision, publisher, locator, retrieval time and a
  link to the original source. Unknown source dates stay visibly unknown.
- A 2D toggle and a keyboard-accessible project list carry the same facts. The list shows projects with an event in
  the selected range; located projects with no dated event are in an explicit section; unlocated records are
  counted and linked to the national explorer, never placed at a guessed coordinate.
- Filters: date range (ledger), event meaning (actual / plan / other), source, literal text. Counts show projects
  and events separately; a project with several events counts once.
- Range semantics: an exact date is in range when inside the inclusive range; a month/year span when any part of it
  overlaps. Unknown dates are never imputed.
- **From `/time`.** `/history?origin=<project key>` opens with the origin marked (a white ghost pillar at its stored
  center) and a "Near this project" list: located past projects within 25 miles of the origin's stored center,
  nearest first. The straight-line distance is labelled as a research aid computed from stored centers; it does
  not alter canonical overlaps or rankings and implies no contractor suitability. The `/time` entry link belongs
  to F19's owner; the nav item is a contract change.
- URL state (`origin`, `project`, `from`, `to`, `at`, filters) survives reload and browser back/forward.
- WebGL or tile failure keeps filters, list, ledger and evidence working and says so in one sentence. Desktop and
  390 px layouts.

## Evidence rules

- Every drawn event has a stable id, project linkage, type, planned/actual meaning, raw date and precision, and a
  source URL plus locator wherever the record provides one.
- A past planned milestone does not prove award, construction or completion. An ISO-NE "In-service" register status
  is the publisher's status with its projected month, not an actual in-service date.
- Distinguish owner from contractor; estimated cost, contract value and actual spend stay separately labelled. No
  inferred savings, performance ratings, contractor, date or location.
- "No contract evidence in this dataset" stays distinct from "no contract existed". Synthetic fixtures are labelled
  and never counted as real coverage.
- Bounded reads through the existing loaders; no arbitrary URL fetching or new database queries.

## Validation and acceptance (part 1)

- Every tech-stack check. A unit check on the adapter: planned/actual separation, month/year range intersection,
  unknown dates, plan→actual difference only when both dates are exact, project vs event counts.
- Desktop and 390 px evidence of overview, a scrubbed plane, a selected project with its bracket and source, 2D and
  failure states. Keyboard scrub and selection, visible focus, reduced motion.
- No F19 file edited by this part; both pages keep the same axis direction and identity colours.
- Contract-discovery acceptance remains unmet until part 2.

## Defaults

- Public sourced history only. Private histories, predictive outcomes and operations stay with their owners.
- Import F19's pure time math (`web/components/time/timeScale.ts`). History's glyphs, threads, plane and ripples
  are a scene F19's layer does not draw, so F37 keeps a small history layer in its own paths instead of editing or
  forking F19's renderer. A later contract may extract a shared base once both pages settle.
- No new dependency or graphics framework, no universal procurement crawler, no history API or export until
  something consumes one.
- Label the route **History**. Keep `/time` primary and its Historical pair filter intact.

## Quiet overview (2026-09-27)

Match `/time`'s quiet overview ([F19 quiet overview](../../decisions/F19-quiet-overview.md)): at national zoom an
unfocused project draws as a dim, thin stem with a dimmer glyph and no halo, by the shared `calmAt(zoom)` ramp
(0.25 at zoom ≤2.5, 0.4 at 4.2, 1 at ≥6.5). Hovered and selected projects stay fully lit; nothing is hidden and no
date, glyph meaning, color or count changes. Validation: headless screenshots at 1440 and 390 on live data.
