# C23: Publish independently reviewed F38 locations through the national snapshot

Closes the contract portion of [issue 136](https://github.com/fradicus/Shellhacks-2026/issues/136).
The user's renewed instruction is to deliver actual points. Codex-local adopts the technical-lead contract role
for this isolated contract; no feature ownership transfers. F38 remains the data producer, F30 the national
assembly/loader owner, F31 the explorer/API owner, F19 the time-view owner. Each implementation uses its own claim.

## Bounded contract

Use `schemas/expansion-release.schema.json`. The sole activation input is the fixed path
`data/expansion/releases/active.json`. No folder glob, filename from a document, remote URL or candidate batch is an
activation request. Research cohorts remain ignored. Raw public downloads stay outside the checkout; no new cache
ignore path is necessary. `data/**` already triggers the existing sole-writer load Action.

A release embeds source evidence, project-to-facility links, original geometry, independent decisions and optional
typed events. Sources identify publisher, HTTPS URL, artifact hash, exact locator, source time, retrieval UTC,
access/rights review and supported facts. A retrieval date does not advance status freshness. Unknown source dates,
accuracy and precision remain null. Location records identify native facilities; project identity comes from the
original project plus explicit evidence, not fuzzy name matching. Owner/voltage/place checks are documented in each
identity rationale. Routes/corridors are preserved as evidence; a vertex/centroid cannot substitute for an endpoint.

A record binds to the complete original national project with `project_facts_sha256`. Every review binds to a
`facts_sha256` over the record excluding its `reviews` list. Hash encoding is UTF-8 JSON with Python
`json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\\n"`.
No review may be its own producer. The last appended review controls; timestamps must be ordered and real UTC.
Only `confirmed` with a matching current facts hash can publish. Missing/stale/conflicting/insufficient/rejected
reviews leave the project unlocated; malformed references fail the release. A change needs a new appended review.

Location kind `site` requires exactly one point with role `site`; `line` allows roles `a` and/or `b`, each once.
The published center is the site point, the single known endpoint (partial), or arithmetic mean of two known
endpoints. Exact original CRS/coordinates, conversion method and supported uncertainty accompany each point.
Only WGS84 output coordinates are published. Independent reviewers recompute the transform and center.
Multiple projects may share facilities; count unique projects and distinct evidence-backed facility sites separately.
A multi-site program without individually substantiated endpoints cannot masquerade as a standalone site.

## Projection, history and activation

F30 validates the unchanged base snapshot, then calls F38's pure `apply_release(snapshot, root)` hook. Missing
`active.json` means no expansion. Existing project IDs are updated in memory, never duplicated. Only `center`,
`location_review` and additive `location_verification` change. Original project observations, status and milestone
precision remain intact. Unknown IDs, duplicate release IDs, mismatched original hashes or malformed evidence fail
closed before database staging. Existing non-null centers cannot be silently replaced by this initial contract.
F30 recomputes coverage and validates the assembled snapshot before staging. F38 adds release/count details to
coverage; legacy matching and ranking do not consume these changes.

Optional events distinguish observed source status, planned milestones, certification, award, construction start,
completion, in-service and cancellation. Every event has source evidence and native project linkage; partial dates
retain their precision. No contractor is inferred from equipment owner, and PTF estimates are not awards/spend.
No historical backfill is required merely to publish an evidenced current source location.

Store accepted evidence and review records inside each `national_projects` document through the additive
`location_verification` field. This keeps evidence, geometry and project facts under the same `national_active`
pointer without extra collections/indexes. The existing two-dataset retention and previous pointer remain the
rollback mechanism. A failed validation/write leaves the active pointer intact. Re-running a dataset is idempotent.
Read/export uses existing `/api/national` and `/api/national/export` scoped to the active dataset; F31 includes
location evidence and partial/site meaning in the selection panel and JSON export. Do not replace CSV silently.

`/explore` already renders non-null national centers. F31 exposes source/reviewer evidence and verifies matching
map/table/counts. F19 separately consumes the approved national projection in `/time`, preserves owner names and
original milestone precision, deduplicates legacy IDs and creates no invented overlap pairs. F38 is not complete
until both map consumers and RO live acceptance work. No renderer fork or frontend redesign is authorized.

## Acceptance and delegation

F38: bounded public acquisition, source/identity/location evidence and independent reviews, release validation,
rejection cases, documented coverage and release counts. F30: hook and assembly/rollback tests. F31: additive type,
evidence display/export and local/live map check. F19: separately claimed minimal time-view integration by its owner.
These dependencies are implementation tasks of this launch, not reasons to stop after another research list.
Independent source/reviewer sessions may run with disjoint assignments; only the F38 integrator writes active.json.

Validate stale hashes, self-review, changed project facts, missing and rejected reviews, duplicate IDs, wrong CRS,
partial endpoints, count reconciliation, unmodified original facts, idempotency and failed activation. A schema pass
never proves geographic truth. Each accepted site must be independently inspected against its actual source.
