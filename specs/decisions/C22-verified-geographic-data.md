# C22: Verified geographic project coverage

Status: specification delivery. [Issue 132](https://github.com/fradicus/Shellhacks-2026/issues/132).
The user authorizes a new spec and roadmap for data expansion, incremental PRs and a prospective overnight run.
The later clarification makes the desired outcome explicit: verified project locations visibly filling the US map.
This decision does not launch ingestion, autonomous workers, a scheduler or an overnight run.

## Decision

Add [F38](../features/F38-verified-geographic-data/spec.md), assigned to codex-local in the data-researcher role.
Florida is the pilot, then Georgia, a named Southeast scope, and the 48 contiguous states plus DC. Alaska/Hawaii
are stretch. Prioritize transmission construction and upgrade projects with associated substations. Preserve source
observations, historical events and unresolved candidates, but count verified project locations separately.

A project's presence in a spreadsheet, a named state, a correct database connection or a plausible OSM candidate
cannot establish a verified point. Each new accepted location needs explicit project linkage and a current independent
review of its evidence and precision. Unknowns remain unknown. Measure source-bounded coverage; do not promise that
an overnight run discovers every US project or gives every record a coordinate.

Each published batch must reach the existing user-facing US map and retain clickable evidence. Minimal data wiring
and honest counts through F19/F31's owners are required delivery work. Defer redesign and new map/history interactions.
Keep raw project, distinct project, point, endpoint and event counts separate; aliases or coincident geometry must not
inflate coverage. The existing unconfirmed legacy points must not be presented as newly verified expansion results.

## Why the earlier audit matters

The [F13 report](../../reports/audit/summary.md) recorded insufficient county/project-area evidence for 14 endpoint
records, with zero confirmations in that reviewed scope. A downgraded candidate is not proof that the project is false.
It means that exact coordinate-to-project relationship was not established by that audit. Current effective states
must still be recomputed against current facts; do not reinterpret a historical report as a live database check.
F38 requires actionable reasons (missing review, identity unresolved, conflict, stale evidence, contradicted candidate)
and separates location validity from project lifecycle status.

## Boundaries and prerequisites

- Specifications only in this PR; no F38 completion marker or imported-data claim.
- Before implementation, freeze additive evidence/review/history/release schemas and the loader/API/map compatibility
  contract in a separately claimed contract PR. Do not change legacy enums, IDs or sponsor matching semantics.
- F38 owns the new pipeline and batch artifacts; F30/F06 own existing ingestion/read integration, F19/F31 own their
  map consumers, and F37 retains its History implementation and evidence requirements. No ownership is transferred.
- A later explicit launch must record its actual timing, worker/reviewer, scope, budget and gates. The original run's
  elapsed gates are historical for this spec task. Root STOP and main-red rules remain binding on a launched run.
- Existing D2 Georgia handling, D15 source exclusion, public-source restrictions, RO app access and sole Action writer
  remain intact. Regional expansion does not silently authorize restricted source processing.

## Alternatives and undo

Importing infrastructure inventories as projects would increase dots without establishing construction work. Automatically
geocoding names would repeat the unresolved-identity problem. A nationwide one-shot import would make bad joins harder to
review. Use complete, bounded source batches with independent verification and measured coverage instead.

Undo by deferring F38 in the roadmap; existing data and production behavior are unchanged by this spec. Later published
batches must support the accepted dataset rollback path and retain their source/review evidence.
