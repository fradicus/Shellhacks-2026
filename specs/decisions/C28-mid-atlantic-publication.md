# C28: Mid-Atlantic source and project publication

Addresses [issue 158](https://github.com/fradicus/Shellhacks-2026/issues/158). The user launched the next F38 cohort:
NY, NJ, PA, DE, MD and DC. VA/WV remain F39. Codex-local adopts the delegated technical-lead role for this contract.
This authorizes the integration needed to publish an actual reviewed batch; schema delivery alone is not acceptance.

## Reuse and fixed activation

`schemas/mid-atlantic-release.schema.json` reuses C27's property schemas for acquisition, row dispositions, counts,
whole-release identity review, typed events and C23 location records. It specializes only the schema version,
source/project namespace and project geography. [C27](C27-southeast-publication.md)'s acquisition, identity,
source evidence, history, review-hash and atomic-publication rules apply with F38 as producer and the paths below.
C27's Southeast source scope and F39 ownership do not transfer. The existing C23 New England release is unchanged.

The sole activation input is `data/expansion/mid-atlantic/releases/active.json`, version `mid-atlantic-release-v1`.
Research/candidate folders and arbitrary filenames cannot activate anything. F38 implements the pure
`expansion.mid_atlantic.apply_release(snapshot, root)` hook under its existing ownership. Missing active.json is a
no-op. Raw downloads remain outside the checkout; no crawler, dependency, new database collection or writer is added.
The existing `data/**` load Action remains the sole Atlas writer.

## Sources, identity and acquisition

Use reviewed public project plans/registers with imported national-source records and pinned original artifact
hashes. Reference inventories may support project-location evidence but cannot themselves become construction
projects. Source IDs use `mid-atlantic:`; project IDs use `mid-atlantic:<publisher>:<nativeID>`, retaining stable
publisher/native identifiers and original source identifiers in evidence. A vintage change does not invent a new
project identity. The national schemas and existing raw-evidence fields remain unchanged.

Each new project must have at least one evidenced state in NY/NJ/PA/DE/MD/DC (FIPS 36/34/42/10/24/11). Preserve all
other supported states on cross-border projects; a VA/WV-only project is outside this cohort. Shared planning regions
are not separate project universes. Check canonical identity against the entire assembled corpus, including F39 and
other producers. Any source/project ID collision fails; never overwrite another producer. Known repeated projects
are duplicate dispositions referring to their canonical IDs, not renamed additions. Parent/component distinctions,
aliases and cross-source duplicates require explicit evidence and reasons. Unsupported geography remains unknown.

Every source has C27's acquisition entry: exact bounded scope, acquired row-locator set, independently known source
row total or null, `complete`/`bounded_partial`, and pinned enumeration evidence. Dispositions must cover exactly that
set once each as accepted, duplicate, excluded or rejected with reasons. Accepted rows reference the correct primary
source/new project; duplicate rows reference a release or existing canonical project. Excluded/rejected rows have no
project ID. Every new project has an accepted primary-source row. Source.project_count counts primary canonical
projects, not observation rows. Unknown statewide/source-wide denominators stay null. A fully reconciled acquired
subset remains partial unless independent enumeration establishes the entire source universe.

The independent reviewer inspects original artifacts and enumeration boundaries, verifies acquisition and project
identity, and approves the exact whole release. `identity_review.facts_sha256` hashes the entire release excluding
only `identity_review`. Encoding is UTF-8 `json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
allow_nan=False) + "\n"`. Producer and reviewer differ. UTC review time is real, not future, and not earlier than
reviewed acquisition evidence. Missing, stale or self-review fails activation. Editing any source, project,
acquisition, disposition, location record, event, count or coverage note needs a new whole-release approval; retain
superseded decisions in F38 batch history. This approval does not replace the separate independent location review.

## Location and history

Every release input project has `center: null`, `location_review: unlocated`, and no embedded location_verification
or project_events. Only the separately typed release fields assemble those additions. Locations use C23's exact
record schema, pre-projection project facts hash, append-only review list and review hash excluding only `reviews`.
A location record may reference only a new project in this release. Apply the same identity, source-hash, timestamp,
reviewer, duplicate ID/facility, role, precision and stale-facts gates as C23/C27. Invalid structures/references fail
closed; structurally valid missing/stale/insufficient/conflicting/rejected confirmation leaves the center null with
an explanatory state. Only a current independent confirmed review may produce a site, single known endpoint
(partial), or arithmetic mean of two independently evidenced endpoints. Preserve unknown precision and uncertainty.

Use source geography and explicit applicable CRS checks for this cohort; do not reuse the New England-only bounds
or CRS allowlist indiscriminately. Bounds detect errors and never establish project identity. Keep original CRS,
axis order, geometry and conversion method. Each allowed non-WGS84 transform must be documented and independently
reproduced before activation. A CRS label or valid numeric bounds alone cannot justify a transform. State/county
centroids, route vertices, utility offices and name-only asset matches cannot supply missing project geometry.

C27's `project_events` field preserves typed C23 source-backed events for unlocated projects as well. Validate
native-project links, source evidence, real dates and original precision. Duplicate event IDs across project_events
and location records must be identical and consumed once. Source/status time, retrieval, proposed service,
certification and actual completion remain distinct. Location confirmation never changes construction status.

## Assembly, counts and consumers

F30 adds a separately claimed invocation after its validated base and existing accepted producers, including C23
and C27 when integrated. The hook receives the full assembled snapshot; it cannot substitute a private baseline.
Check all source/project/row/event references, review bindings, exact acquisition sets and expected_counts before
returning any additions. Recompute new_sources/new_projects/confirmed_projects/source_rows. Source hashes must match
the evidence attached to their projects. Derive centers only after review validation. Repeated assembly is
deterministic and does not mutate committed files. Applying a release twice to an already augmented snapshot cannot
silently duplicate or overwrite records; the normal replay path starts from the same base and producer sequence.

F38 adds `coverage.mid_atlantic` with release identity and source/state/status/location counts, complete/partial
endpoint coverage, unique confirmed projects, distinct canonical map positions and referenced facilities, unresolved
reasons, acquisition completeness and known gaps. Preserve existing producer summaries. F30 recomputes final national
coverage, validates the assembled snapshot and stages it under the same national_active pointer with existing
retention/rollback. Validation or staging failure preserves the prior active dataset; no partial project activation.

F31's existing optional location_verification, source evidence and bounded JSON export consume the same projection.
No new public route or client activation logic is required. JSON export retains project_events; any visual event
integration remains separately owned. F19 retains `/time` integration. Do not alter legacy IDs, matching, rankings,
ownership enums, statuses or milestone precision. No UI redesign is part of this contract.

## Required implementation and acceptance

The contract PR changes only this decision, its additive schema and frozen contract tests. F38 implements source
adapters, release validation, independent review binding and actual data under its current claim. F30 implements
its hook and assembly/failed-load tests separately. No F38/F39 data, C23/C27 schema or feature-owned code is changed
by this contract; no completion marker is created. Existing feature owners retain their assignments.

Implementation tests must reject namespace/collision/source-hash errors, out-of-scope geography, stale/self/future
reviews, wrong CRS/axes/transforms, mismatched counts, duplicate/missing dispositions and unsupported location links.
Test source-complete versus bounded-partial denominators, unknown fields, history semantics, unlocated accessibility,
all previous producers remaining intact, deterministic replay and failure preserving activation. Structural schema
validation is not independent acquisition or location review; these semantic gates are mandatory before staging.

For each actual batch, reconcile its source-bounded universe and report new/duplicate/rejected/unlocated/confirmed
counts. After merge and the existing load Action, verify active dataset, IDs, counts and exact evidence through RO
reads/export, then selected points and evidence on the existing map. Check default viewport/filter visibility and
site/complete/partial meaning, retaining overlapping state totals and shared-site counts. A schema, research list,
imported row count or successful load without new visible reviewed points does not complete geographic delivery.
Undo through the existing previous-dataset mechanism and a reviewed correction, preserving source/review history.
