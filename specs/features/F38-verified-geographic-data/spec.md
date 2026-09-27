---
id: F38
name: Verified project data - Florida, Southeast, contiguous United States
lane: A
agent: data-researcher
phase: 7
depends_on: [F00, F30]
owns: [pipeline/expansion/, data/expansion/, reports/expansion/, tests/pipeline/test_f38_]
cut: never
---

# F38 Verified geographic project data

Status: specified; implementation and overnight launch pending. [C22](../../decisions/C22-verified-geographic-data.md)
authorizes this spec. Shared contracts and a recorded launch are prerequisites, even when dependency markers exist.
The [source research](sources.md) is a discovery starting point, not an ingestion allowlist or an acquired dataset.

## Refined request

Build a reproducible database of publicly documented electric transmission construction and upgrade projects,
including associated substations. Start with Florida, repair and expand Georgia, then cover the Southeast and the
48 contiguous states plus DC. Preserve documented historical work. Prioritize independently verified project
locations and useful project facts over raw record counts. Publish reviewable batches through PRs and the existing
Atlas load Action. Show exactly which sources, utilities, dates, states and location claims are covered or missing.
Make accepted points visible on the existing US maps with their evidence and honest counts. Defer frontend redesign.
Never invent a coordinate, project identity, date, contractor or claim of completeness.

## Scope and meaning of complete

- A project is an identified construction/upgrade effort. A substation, tower, generating unit, EIA utility,
  interconnection request or line in an asset inventory is not automatically a construction project. An asset
  can support a documented project-location link; do not inflate project counts with its poles or geometry vertices.
- Import planned, proposed and under-construction work first. Preserve in-service, cancelled and unknown records
  in distinct cohorts. A past planned service date never proves actual completion. "Current filing" is not "active job."
- Include historical versions and documented events encountered in these sources from the start. For each source,
  record the oldest/newest accessible vintage and actual imported period; do not promise all historical years.
  Obtain the latest eligible source and a prior comparable vintage where available before deeper archive backfill.
- "Fully populated" means every eligible row in a named, reviewed source universe has a recorded disposition,
  and every accepted field has evidence or an explicit unknown. It does not mean every real-world US project is
  publicly disclosed, every source covers all voltages, or every project can receive coordinates.
- Track source discovery completeness, extraction reconciliation, project identity, verified locations and
  status freshness separately. A reviewed registry can be complete while geographic coverage remains partial.
- For lifecycle freshness, record the source as-of date and reviewed refresh cadence separately from retrieval time.
  A fresh download of an old plan does not make its status current. Where cadence or status-as-of is unknown, do not
  claim verified current activity. Location confirmation alone cannot move a record into the current-work cohort.
- No minimum dot count permits weaker evidence. Do not call a state fully covered merely because one source or
  one located project exists there. Unknown statewide project denominators stay null.

## Geographic sequence and gates

| Stage | Scope | Exit evidence |
|---|---|---|
| 0 | Contract and source inventory | Accepted additive contracts, source roles/access/rights, exact batch boundaries, baseline counts and launch manifest |
| 1 | Florida pilot | One complete bounded source batch plus at least one independently confirmed project-location link, reproducible rejection cases, a verified Atlas read and a visible evidenced point on the existing map |
| 2 | Florida coverage and Georgia repair | Approved Florida source matrix reconciled; Georgia's existing records reused, unresolved locations investigated, new projects deduplicated; verified/missing counts by source and utility |
| 3 | Southeast | FL, GA, AL, MS, SC, NC, TN, KY, VA, WV, AR, LA; per-state source and verification ledgers, explicit cross-state records and unresolved gaps |
| 4 | Contiguous US + DC | All 48 states and DC assessed; regional and local source matrices reconciled, accessible approved sources processed, source-bounded coverage and verification measured |
| Stretch | Alaska, Hawaii | Separate source discovery and the same evidence gates after the contiguous-US priorities |

The Southeast list is this project's explicit working scope, not a claim about a government's regional definition.
Regional planning footprints cross state lines. Ingest a regional source once, associate supported states, and count
one cross-state project once nationally. State totals may overlap and must be labeled accordingly.
If the Florida pilot cannot confirm a location, record the missing evidence and continue independent source research;
do not declare its gate passed or scale the unproven location method. A blocked source does not block other eligible
sources within the authorized stage. Later-stage implementation waits for the preceding gate or an explicit decision.

## Pipeline and artifacts

Use the existing Python stack and file-to-PR-to-Atlas model. Build one bounded pipeline with source adapters, not a
new service or crawler platform. F38 owns its outputs; F30's committed snapshots and loader stay with their owner.

1. **Discover:** create a state/utility/planning-process matrix. Catalogue official plans, utility project pages,
   regulator dockets, siting/permit records and public government GIS. Record known scope exclusions and access
   failures. Source discovery is a task result, not project ingestion. Expand beyond investor-owned utilities to
   municipal, cooperative and federal providers where relevant public records exist.
2. **Acquire:** review each exact source before enabling it. Store publisher, URL, artifact identifier, publication
   date/vintage, retrieval UTC time, content hash, license/access restrictions, geographic and voltage scope, source
   role and parser version. Keep bounded raw caches ignored; commit only permitted evidence/extracts and manifests.
   Use time/size/page/request limits, retry limits and resumable checkpoints. Disallow arbitrary URLs from documents.
3. **Extract:** prefer deterministic tables/CSV/XLSX/GIS. OCR or model extraction may propose candidate facts with
   page/row evidence; it cannot approve its own output or generate missing coordinates. Preserve source text and
   date precision. Reconcile every eligible source row as accepted, duplicate, excluded or rejected with a reason.
4. **Resolve identity:** use publisher/native project IDs and explicit cross-source links. Preserve source observations
   and a stable canonical ID. Fuzzy names or nearby geometry create candidates only. Record parent programs and
   component projects, aliases, amendments, splits/merges and conflicts without double-counting their representations.
5. **Resolve location:** follow the evidence rules below, retaining rejected candidates and unresolved reasons.
6. **Verify:** an independent reviewer examines each location being promoted to confirmed and the evidence supporting
   its identity. Bind decisions to exact current source/project/location facts. Recompute numerical/CRS checks
   separately from the producer. A parser test passing or a second model agreeing is not location confirmation.
7. **Publish:** emit deterministic schema-valid batches, coverage and verification artifacts. The integration owner
   assembles the accepted national snapshot; only the existing load Action writes Atlas. Check the active dataset,
   expected counts and representative IDs through RO access after the load. Failed publication preserves the last
   valid snapshot and does not mark the batch loaded. File generation, merge and activation are distinct milestones.

Proposed F38 layout, finalized in the implementation contract:

- `pipeline/expansion/`: CLI, source adapters, normalization, candidate resolution and pure validation.
- `data/expansion/manifests/`: reviewed source catalog and pinned source/batch manifests.
- `data/expansion/batches/<source>/<vintage>/`: normalized project observations, candidate locations, events and
  append-only review decisions; partition large sources into stable documented shards when needed.
- `data/expansion/releases/`: deterministic release manifests referencing accepted batches and expected counts.
- `reports/expansion/`: source/state coverage, discrepancies, run checkpoints and final/resume reports.
- `tests/pipeline/test_f38_*`: adapter, reconciliation, location, history and release tests.

Do not create ignored raw caches until the owning contract establishes ignore rules. Private user files, credentials,
licensed exports and restricted source material must not enter the public repo. This feature does not import private
job histories; that remains F35. A local public file uses the same reviewed-source and provenance path as a download.

## Location evidence and verification

The goal is evidence about the actual project site/endpoints, not merely a point somewhere in its reported state.

### Acceptable evidence

- Prefer official coordinates/GIS with a stable facility, project, permit or certification identifier that can be
  linked to the project record. Store both the geometry evidence and the project-link evidence.
- Otherwise use documented site addresses, parcels, endpoint maps or siting documents with a reproducible location
  method and corroborating owner, voltage, county/project-area and endpoint identity where available. A geocoder
  result alone does not establish the project location. Two URLs copying the same data are not independent evidence.
- A single authoritative artifact can establish both identity and geometry if its identifiers and meaning are
  unambiguous; the independent reviewer must verify that linkage. Do not demand an arbitrary second source merely
  to count sources. Conversely, plausible matching names across several sources are insufficient by themselves.
- OSM and general asset inventories may propose candidates or corroborate an evidenced identity. Utility office
  addresses, service territories, municipality/county/state centers and utility-name matches cannot locate projects.
- Preserve original geometry type, CRS, positional precision, source date, method and any supported uncertainty.
  Transform to WGS84 reproducibly. Decimal places do not imply survey accuracy; unknown uncertainty remains null.
- Keep routes/corridors as referenced location evidence. A route vertex, bounding-box center or corridor centroid is
  not a substantiated facility endpoint. A public diagram is useful evidence but does not become precise GIS through
  visual guessing. Georeferencing requires documented control points and measured error before independent review.
- A proposed site can have a confirmed documented location while its construction remains proposed. Location review,
  project status, and actual completion are separate facts.

### Derived points and existing behavior

For a line, preserve its endpoints and derive the canonical center using the mission's arithmetic rule: two located
endpoints -> arithmetic mean; one -> that endpoint; none -> null. An independently confirmed one-endpoint location
must be labeled partial and counted separately from complete endpoint coverage. A standalone substation may have its
own authoritative site point. Never use these new facts to change legacy matching or ranking in F38.

New expansion records enter the published national `center` only with a current, valid independent confirmation of
all evidence used to derive that point. Unverified geometry stays in candidate evidence with a null published center.
Source-backed unlocated project records may still be imported and searched; they must not count as verified points.
Existing legacy/national candidates are grandfathered only as visibly unconfirmed historical inputs; do not silently
promote them. Coordinated corrections to old published locations remain with F09/F13/F30 and the contract owner.

### Explain each review state

| State / reason | Plain meaning and next action |
|---|---|
| Unlocated | No supportable coordinate has been found; retain available state/county evidence and research links |
| Needs review: no review | A candidate exists but no independent reviewer has checked it |
| Needs review: identity unresolved | The point may be a real facility, but the link to this project is not established |
| Needs review: conflicting evidence | Sources disagree; preserve both and resolve the specific conflict |
| Needs review: stale review | Reviewed facts changed; the previous decision no longer applies |
| Rejected candidate | This candidate is not accepted under the criteria; record whether it is contradicted or merely insufficient |
| Confirmed location | A current independent review supports this stated location/precision; construction status is separate |

Do not equate "rejected candidate" with "project does not exist". Retain exact reason, evidence references, reviewer,
review time, method and facts hash. A later correction appends a decision; it does not rewrite history. A review of
one coordinate cannot approve another filing, altered project identity or newly changed geometry.

## Visible geographic progress

The user-facing outcome is a US map gaining verified project locations after each release. Evidence eligibility is a
publication gate, not a badge applied afterward. A successful database load with unchanged map coverage is not a
completed geographic delivery. Existing records and newly verified expansion records must remain distinguishable.

- Report before/after unique confirmed projects, distinct physical locations, states/counties supported, lifecycle
  cohorts, complete/partial endpoint coverage and records still lacking geometry. Several projects can share a site;
  neither stacked coordinates nor zoom clustering should make underlying project counts ambiguous.
- Demonstrate the pilot and each newly covered state in the existing map, with a selected point opening the same
  source/review facts exported from the active dataset. Check default filters and viewport framing do not hide the
  new cohort; preserve historical/planned distinctions rather than changing statuses to make points visible.
- A state with only state-level records remains a research gap for precise locations. Do not color it as fully
  populated or place projects at its centroid. A snapshot of a filled basemap is not geographic acceptance.
- No quota forces uniform density: actual public project coverage is uneven. Record the evidence gap and next source
  for sparse states. A selected historical cohort may add past projects only with their sourced temporal meaning.

## History and roadmap integration

F37 already specifies a future `/history` page. F38 prepares reusable public project evidence while that UI stays
pending. Keep filing observations, planned milestones, permitting/certification, award, actual start, actual completion,
in-service status and cancellation distinct. Partial dates stay partial. A certification proves certification; an
in-service status may be sourced without establishing an exact completion date. Record that limit.

Use canonical project IDs and an accepted additive event contract shared with F37. Store event source locators and
explicit project links. Separate estimated cost, contract award value and actual spend. Contractor names require
contract/award evidence; utility owners cannot be substituted. Preserve unknowns and conflicting observations.
This does not authorize a procurement crawler, outcome-model training, private-history publication, or edits to F37.

## Shared contracts and ownership prerequisites

Before implementation, a separate `[C<n>]` PR by the technical-lead contract owner must freeze:

1. Additive schemas for source observations, project identity links, candidate/accepted location evidence,
   facts-bound independent reviews, typed historical events and coverage/release manifests. Specify field-level
   evidence references, source-time semantics, precision, reason codes and validity rules; retain existing enums/IDs.
2. The national compatibility projection and deduplication rules: how F38 observations merge with F30's current
   corpus without duplicate IDs, silent overwrites, loss of older sources, or historical records presented as active.
3. The national-loader hook for assembly/validation/activation of projects plus their evidence, reviews and events,
   with one dataset pointer and rollback semantics. If extra collections are necessary, their names, indexes,
   retention and dataset-scoped read/export contract must be explicit. No separate Atlas writer.
4. Workflow triggers for approved `data/expansion/` releases, offline replay/validation commands, cache ignores and
   compatibility tests. Preserve the existing supported-source loader; unknown folders are not automatically imports.
5. A read-only audit/export path for all accepted fields and evidence, using the existing national API owner where
   applicable; and minimal existing-map integration by F19/F31. The main `/time` view must consume the approved
   national project projection as well as legacy projects without duplicate representations, forcing new owners into
   legacy utility enums, or inventing new overlap pairs. `/explore` must show the same accepted location evidence.
   Source-backed unlocated rows remain accessible. New endpoints, source points and canonical centers retain their
   meaning; do not plot a project multiple times merely because it has several evidence records. Shared type/renderer
   adjustments require their owner and a contract review; avoid a renderer fork or redesign.

F30/F06/F19/F31/F37 owners implement changes in their paths through separately claimed PRs. The coordinator cannot assume
that schema additions alone make their loaders consume these records. Never give two sessions ownership of a feature.
F38's spec-only delivery does not create a completion marker or claim that these contracts are implemented.

## Incremental PRs and overnight operation

- Default to one local F38 implementation worker in its own worktree, with independent reviewer sessions at review
  checkpoints. Paperclip/hybrid execution is optional through the existing preflight assignment rules. Separate
  research/review tasks may run concurrently only with explicit disjoint assignments; one integrator writes releases.
- Use `[F38] part N: <source/state/batch>`; one open F38 implementation PR at a time. Aim for a tested, independently
  reviewable batch every 30–60 minutes, but readiness gates decide publication. Never merge an incomplete batch to
  satisfy a timer. Large sources may span sequential PRs; intermediate parts cannot claim the source complete.
- Every PR includes source IDs/vintages/locators, eligible-row reconciliation, unique projects added/updated, duplicates,
  status cohorts, newly confirmed locations, partial endpoint coverage, unresolved/rejected reasons, historical events,
  complete validation output, actual coordinate precision and the before/after count of verified projects visible
  on the existing map, broken down by state and lifecycle status. Publish active dataset evidence after loading in a
  subsequent checkpoint; do not pretend an unmerged PR is already in Atlas.
- Validate every row and every confirmed location. Independently re-extract a reproducible stratified sample of other
  fields (every source, parser variant, status/date form and source edge case). Record sample size and denominator.
  Any sampled systematic error quarantines its affected batch until all affected rows are checked and corrected.
- Before an overnight launch, commit a run manifest containing actual start/deadline, runtime/model, worker/reviewer,
  allowed states/source batches, prior gate evidence, observable budget, request/retry limits and stop/resume rules.
  Default requested run length is eight hours, starting when explicitly launched, not the historical roadmap date.
- Apply `specs/overnight.md`: honor root STOP, main-red handling, claims, checks and budget gates. This follow-on uses
  its recorded new deadline; at 75% of its observed budget stop new work, at one hour before deadline start no new
  source, and at 30 minutes before deadline finish validation/reporting only. Stop by the deadline. Do not clear STOP
  or reopen another worker's feature. No scheduler or overnight process is started by merging this spec.
- Checkpoint about every 30 minutes in F38-owned reports/batches, recording remaining source/verification work.
  End with exact merged/loaded/pending totals and a resume command/task. Report observed throughput to estimate the
  next run. One overnight run is a bounded coverage increment, not a promise of complete national verification.

## Validation and acceptance

Run every command in `specs/tech-stack.md` plus these meaningful checks:

- Source replay is deterministic; eligible rows reconcile; changed headers, IDs, pagination, truncated downloads and
  duplicate shards fail closed. Preserve last valid data when acquisition or parsing fails.
- Deduplication preserves distinct same-name projects and amendments; cross-state and multi-source records do not
  inflate nationwide totals. Parent/component counts are explicit. Unknown dates/owners/costs remain unknown.
- Same-name facilities in different counties, wrong owners/voltages, reversed axes, wrong CRS, service-territory
  substitution, state/county centroids and unsupported endpoint links cannot become confirmed locations.
- Every newly published non-null center has a current confirming review of its exact inputs; missing, stale,
  conflicting and rejected reviews cannot activate candidate coordinates. Preserve source-backed unlocated projects.
- History tests distinguish past plans from actual events, status from event date, certification from completion,
  owners from contractors, and award value from total project cost.
- Before/after comparisons preserve existing legacy IDs, dates and matching behavior. Release validation covers
  cross-collection references, per-state/status/location counts, replay idempotency, failed activation and rollback.
- Florida's pilot must demonstrate primary-source project -> independently verified location -> PR -> Action ->
  RO Atlas read/export -> visible point on the existing US map -> source evidence, all with matching IDs/dataset.
  Record a browser check and screenshot of this bounded journey; comprehensive frontend redesign/testing is outside F38.
- Each state release includes both location yield and a public-source coverage ledger with gaps. Broader publication
  must not reduce verification standards. If zero new points qualify, report zero and keep the milestone unmet.
- Completion requires the approved source universe and geographic milestones to be reconciled and the accepted
  batches published with live read evidence and the corresponding points visible on the existing maps. If coverage
  remains blocked, keep F38 incomplete or explicitly amend scope through a reviewed decision; never treat a list of state names as nationwide completion.

## Defaults

Transmission and associated-substation projects only; generation/distribution inventories are reference-only unless
separately scoped. Current work gets acquisition priority; history is retained as evidence permits. Florida precedes
Georgia. Unknowns are useful research tasks, not permission to guess. No frontend redesign, provider change, vector-search
work, paid-data subscription, direct local Atlas writes or bypass of source access restrictions is included.
Existing Georgia D2 table-only handling and SERTP D15 exclusion remain effective until their owner explicitly resolves
them. A public-looking filename or "Non-CEII" label alone does not override conflicting markings in source contents.
