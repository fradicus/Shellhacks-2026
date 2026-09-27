# C27: Publish approved Southeast sources and new project identities

Addresses [issue 146](https://github.com/fradicus/Shellhacks-2026/issues/146) for the explicitly launched C24/F39
Southeast scope. C23 remains unchanged: its fixed release updates existing national locations. This contract adds
new sources/projects without editing F38 outputs or relaxing independent location review.

## Fixed input and producer

The sole F39 activation file is `data/southeast/releases/active.json`, validated against
`schemas/southeast-release.schema.json`. Candidate/research directories are ignored. The existing `data/**` load
Action is the sole Atlas writer. No service, new collection, secret, database migration or scheduled crawler is added.
F39 owns a pure `southeast.publish.apply_release(snapshot, root)` hook; missing active.json returns the snapshot.
F30 invokes it after its validated base and C23 overlay, then recomputes source/aggregate coverage and validates the
assembled snapshot. F30 implements its hook in a separately claimed PR after its current claim is complete.

## Sources, projects and canonical identity

The release contains complete national-source and national-project records. Sources must be reviewed public project
plans/registers, `imported`, with matching pinned evidence hash and exact row/page locator for every project.
Reference layers support evidence; asset rows cannot become construction projects. New project IDs use `southeast:`
as a stable namespace and native publisher IDs. At least one supported state must belong to the twelve-state scope;
keep other evidenced states for cross-border projects. New IDs cannot conceal a known existing representation.

No source/project ID may collide with the assembled national corpus, and no duplicate IDs are allowed within a
release. This initial additive path never overwrites original source or project facts. Existing Georgia/DESC IDs
remain canonical; their new identity observations and location corrections need the existing owners' overlay path,
not a second Southeast project. Parent/component and cross-source duplicate decisions are explicit in dispositions.
If a new source repeats an existing project, record that row as duplicate pointing to its canonical ID. If it reports
an actual separate construction component, retain evidence establishing the distinction before accepting a new ID.

Each source has an `acquisition` entry binding its exact scope, acquired row locator set, independently known source
row total (null if unknown), complete/bounded_partial flag and hash-pinned enumeration evidence. For APIs use returned
ID sets and pagination/count responses; for tables use inspected page/sheet row boundaries and totals. The independent
reviewer verifies those underlying artifacts rather than trusting the producer's expected_counts. Disposition locators
must equal the acquisition row set exactly. A complete claim requires a known matching source total and evidence
that no pages/rows remain; bounded_partial stays visibly partial even when its acquired subset fully reconciles.
Do not silently define the acquired subset as the entire source. The whole-release review binds these ledgers too.

Each source row gets one unique `(source_id, locator)` disposition: accepted, duplicate, excluded or rejected, with
reason. Accepted/duplicate rows reference a release or existing canonical project; excluded/rejected rows have no
project ID. Each new project needs at least one accepted row in its primary source. Repeated evidence rows do not
inflate unique project counts. Source.project_count counts canonical projects whose primary source is that source,
not duplicate source observations. Unknown source-wide or statewide project denominators remain null in coverage.

All published fields require source locators or explicit unknowns. Preserve raw observations in project evidence;
publication time is not source/status time. `in_service` is a sourced milestone with original precision. Certification,
planned service, actual completion and cancellation remain distinct. Contradictory observations remain visible with
an explicit resolution or null normalized field. Preserve restricted-source exclusions and access decisions.

The independent `identity_review` binds the entire release except that field using C23's canonical hash encoding:
UTF-8 JSON, sorted keys, ensure_ascii=False, indent=2, allow_nan=False and trailing newline. Producer and reviewer
must differ; UTC review time cannot be future and cannot predate acquisition evidence being reviewed. Missing,
stale or self-review fails activation. This verifies acquisition reconciliation and canonical project interpretation;
it does not approve coordinates. A changed release needs a new review; retain previous decisions in F39 batch history.

## History independent of geometry

`project_events` groups typed C23 event records by new project ID independently of location_verifications. Validate
unique project/event IDs, native_project_link against that project's native_id, source evidence, and date precision.
Embed these as additive `national_projects.project_events`; the schema references the existing C23 event definition.
This allows unlocated projects to preserve certification, planned and actual historical events without a fabricated
coordinate. Keep location record events for backwards compatibility; duplicate event IDs across the two paths must
be byte-identical and are displayed once. F31's JSON read/export includes this field and its evidence; event display
is a separately owned additive integration, not a new History-page implementation. Whole-release identity review
binds these historical claims. A schema-valid event date still requires semantic precision/calendar validation.

## Location projection

Every input project starts with null center and `unlocated`, without embedded location_verification or project_events. Both are assembled only from the typed release fields. Optional
`location_verifications` use C23's exact verification schema, hash encoding, append-only review and event semantics.
They may reference only new projects in this release. Each record binds the exact pre-projection project facts.
Reuse the same review rules: no self-review, duplicate review IDs, future/unordered review time, stale facts,
unsupported CRS/transform, unlinked evidence, invalid endpoint roles or duplicate facilities. Derive a site point,
one evidenced endpoint (partial), or the arithmetic mean of two independently evidenced endpoints. No guessed
route/corridor vertex, administrative centroid, or facility-name-only match can qualify.

Unlike F38's initial implementation, Southeast validation must use the reviewed source geography and applicable
CRS; it must not apply New England bounds to southern projects. Bounds are error checks, not evidence of identity.
Document and independently reproduce each non-WGS84 transformation before allowing its CRS. Unknown accuracy stays
null; unknown feature meaning is not positional uncertainty. A plant label point cannot silently become a line terminal.
Do not weaken F38's validator or modify its files through this contract. F39 can reuse shared schemas and implement
its bounded checks; any later common-code extraction needs its owners' explicit integration.

Embed the verification record in the new national project. Only the latest independent `confirmed` decision with
current hashes permits non-null center. Unreviewed/stale/conflicting/rejected location records keep center null and
carry their explanatory state. Invalid structures/references fail the release rather than dropping rows silently.
An empty location_verifications array permits source-backed unlocated projects but never passes the Florida pilot
or any geographic delivery milestone. Publication of rows is separately counted from verified visible locations.

## Atomic assembly and reads

Validate schema, all source/project/row/review references, acquisition reconciliation and exact expected counts
before staging. Recompute new_sources/new_projects/confirmed_projects/source_rows and compare to expected_counts.
F39 attaches an additive `coverage.southeast` summary with source/state/status/complete/partial/unknown counts and
notes. F30 validates/recomputes final national coverage; preserve other producers' summaries. Embedding evidence in
national_projects keeps it under the same national_active pointer, retention and rollback as C23. Failed validation
or activation preserves the previous dataset. Deterministic repeated assembly must not mutate committed base files.

F31's C23 location_verification read/export/display path consumes the same shape for Southeast. F19's separately
owned national projection must include these projects, preserve names/time precision and deduplicate legacy IDs.
No source owner is forced into legacy enums and no new overlap pairs are invented. Live acceptance checks release
IDs, dataset/counts, RO reads, export and point selection on existing maps. This schema alone claims none of those.

## Validation and ownership

Contract PR owns only this decision, additive schema and frozen contract tests. No feature completion marker.
F39 implements adapter/reconciliation/promotion/release checks and approved data under its ownership. F30 implements
assembly and failed-load/rollback checks; F31/F19 retain API/UI integration. Preserve all currently active claims.
Schema checks are structural only; producer semantic gates remain mandatory. Test namespace/collision/source-hash failures, changed/self/stale reviews, out-of-scope records, malformed dates,
missing/duplicate row dispositions, candidate isolation, exact counts, history semantics, unlocated accessibility,
unchanged legacy matching, deterministic replay and failure preserving prior activation.

C27 authorizes the integration required by F39; it does not narrow its source coverage or geographic acceptance.
All twelve states remain incomplete until the F39 audit succeeds. Undo an activated release through the existing
previous dataset pointer and a reviewed release correction; never erase evidence or silently rewrite source history.
