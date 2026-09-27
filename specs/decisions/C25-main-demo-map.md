# C25: Fill the main demo map with accepted project data

Status: specification for implementation handoff; no map implementation or data activation claimed.

## Intent and authority

The user requested a proper specification for filling the main demo map while four data agents research sources.
The main demo is `/time` (mission/F21). This decision defines its integration acceptance, building on
[F38](../features/F38-verified-geographic-data/spec.md), the pending
[C23 publication contract](https://github.com/fradicus/Shellhacks-2026/pull/137), and
[the F19 handoff](https://github.com/fradicus/Shellhacks-2026/issues/139).
It does not change research assignments, launch more workers, or edit another feature's spec.
C23 must be accepted and its producer/loader/read support implemented before live acceptance below.

The gap is concrete: at main revision `a0cfee7`, `web/app/time/page.tsx` reads legacy `getProjects()` and
`getMatches()` only. Loading national projects does not make them visible on that page.

## Outcome

Opening `/time` shows accepted national project locations alongside the existing legacy projects, using the
existing MapLibre/Three.js scene. A visitor can find a project, select its point, inspect the source and location
review, and distinguish its filed milestone from actual construction. Source-backed projects without accepted
coordinates remain searchable. Success means a reviewed release is visible in the deployed demo, not merely
that a source was found, a JSON file exists, or Atlas accepted a write.

## 1. Data-agent handoff and publication

- Each producer delivers its existing feature-owned batch with stable project/source IDs, source locators and
  vintage, raw milestone text and precision, lifecycle evidence, candidate location evidence and review disposition.
  Follow C23's accepted schema for publication; this document creates no competing payload or evidence format.
- Candidate geometry, unresolved identities, stale reviews and research-only artifacts cannot enter the confirmed
  map layer. Every new non-null published center requires a current independent review bound to its exact inputs.
- One assigned release integrator assembles approved batches, preserving provenance and resolving documented identity
  links. Four research agents do not independently write to the active database. Only the existing load Action writes
  Atlas. A failed validation/load preserves the prior active release.
- Record batch -> accepted release -> active dataset -> deployed read separately, with revision, timestamp,
  expected unique-project counts and representative IDs. Keep rejected/unlocated dispositions and coverage gaps.
- Coordinates, IDs, utility names, dates and contractor facts must come from accepted evidence. Source inventories,
  asset-only records, office addresses and administrative centroids are not project dots.

## 2. Read model and identity

F30/F31 provide the accepted national projection; F19 consumes it alongside the legacy read model.

| Concern | Required behavior |
|---|---|
| Dataset consistency | Capture the national active dataset once per result set; points, totals, pagination and evidence use that dataset. A changed/expired dataset requires an explicit refresh, never mixed pages. |
| Legacy identity | Preserve current legacy selection keys, pair IDs, source facts and stored pair metrics. |
| National identity | Preserve native national IDs and actual owner labels; do not cast national owners into DESC/Georgia enums. Use an internal namespace if renderer keys could collide. |
| Cross-corpus duplicates | Suppress a national legacy mirror only through its explicit identity mapping. Name similarity or nearby coordinates cannot merge projects. Retain additional evidence without drawing the same canonical project twice. |
| Coincident projects | Distinct projects at one site remain distinct selectable records. Offer a list for coincident points; do not jitter coordinates or call one site several physical locations. |
| Completeness | Honor bounded API reads. Page through results or use the owner's bounded viewport contract; never silently present the first page or a fixed limit as the whole dataset. Display loaded/total and any truncation. |
| Unlocated records | Retain in All projects with a reason and evidence access; omit from spatial matching and point geometry. |

The minimal presentation adapter must carry identity, dataset/source namespace, name, owner, accepted center and
its site/complete-endpoints/partial-endpoint meaning, location review state, milestone value/raw text/precision,
lifecycle status and evidence reference. Optional absent facts remain null. Exact shared types and any additive API
changes belong to their existing owners under the accepted contract; do not invent a second schema in the renderer.

## 3. Main map behavior

- Keep the current scene, 2D toggle, keyboard list and pair selection. Extend the existing renderer and detail
  presentation; no parallel map implementation or frontend redesign is required.
- Default to all imported lifecycle cohorts with status labels, including unknown status. Do not hide a newly
  accepted point because its milestone is missing or in the past. A current filing is not proof of active construction.
- Fit the initial overview to drawable projects in the selected scope. Provide a visible reset/fit action and region
  or state scope so sparse national coverage and dense regional batches can both be inspected. Selection and refresh
  must not repeatedly reset a user's camera. If no points qualify, show the empty reason and searchable records.
- Plot one canonical center per project. Lines use the mission's endpoint mean rule, one located endpoint is labeled
  partial, and substations use an accepted site point. Endpoints and evidence geometries are not extra project counts.
- New national markers show their confirmed review state. Existing legacy/unconfirmed inputs remain visibly distinct
  with their stored effective review state; never upgrade them through a new color or legend. Do not imply that every
  visible legacy point meets the new confirmation gate.
- National owners use a neutral expansion palette with text labels, or a stable existing palette extension. Color
  alone must not convey owner, review state or selection. Do not reuse the two legacy utility labels for new owners.
- Marker selection opens project details even when no overlap pair exists. Coincident selection and the searchable
  list must reach every project. Include ID, actual owner if known, status, source vintage, raw milestone, location
  meaning, review/reason, source locator/link and dataset. Unknown fields say unknown.
- Search by name and ID across located and unlocated records. List, map and counts use the same filter semantics;
  geometry eligibility is stated separately. Filters expose scope and can be cleared.

## 4. Time and pair semantics

- Height means filed in-service milestone only. Exact dates use the existing bead; month/year precision uses its
  full interval. Unknown or unsupported milestone precision stays on the ground with a readable unknown label.
  Never substitute retrieval, publication, permit, award or review dates as project height.
- Past planned dates do not imply actual completion. Historical event playback remains F37's `/history` scope.
- The intro, scrubber and booth mode must include compatible national records without relabeling milestone counts
  as construction/completion counts. Unknown dates cannot disappear from project totals.
- National points do not automatically create overlap pairs, rings, ranks or coordination savings. Existing pairs
  retain stored distance/gap/rank and the mission's strict cross-utility distance rule. Adding national matching is
  separate work requiring the canonical matcher and its own evidence/acceptance.
- With no existing pairs in a selected geographic scope, show the projects and an honest no-pairs state. The legacy
  pair tour remains available without implying the national dataset has been matched.

## 5. Counts, unavailable states and performance

Show clearly scoped counts: unique projects in the filtered dataset, projects with drawable locations, newly
confirmed national projects, unlocated projects and legacy/unconfirmed drawable projects. Keep physical-site counts
separate if available; never infer them merely by counting markers. Counts must reconcile through explicit disjoint
categories, with out-of-viewport, pagination and time-filter effects identified. State coverage is source-bounded;
no uniform density quota and no nationwide completeness claim.

Legacy and national availability are independent. A failed national read shows an explicit national-data warning
while usable legacy data remains available; the reverse preserves usable national projects. Both unavailable shows
an error. An empty valid dataset shows zero, not a service error. Never use production fixtures or cached research
candidates to conceal an outage. Show dataset identity and freshness semantics without exposing credentials.

Measure the accepted real batch on the demo laptop at its recorded resolution, preserving F19's target of no
sustained drop below 50 fps. Record project count, browser and observed frame rate. Avoid per-point HTML labels at
national scale; use the existing layer and selected/hover labels. If aggregation or bounded viewport loading is
needed, disclose it and preserve access to every underlying record. A low frame rate is an unresolved acceptance
issue, not permission to silently drop points. Reduced motion disables animation; missing tiles/WebGL leaves the
project list, evidence and pair facts usable on desktop and at 390px width.

## 6. Delivery sequence and ownership

1. **Producers/reviewers:** research and review their assigned cohorts; publish only accepted artifacts in their own
   prefixes. Research-only checkpoints can continue while integration is pending.
2. **F30/F31 owners:** implement accepted release activation and dataset-consistent reads/evidence/counts. Demonstrate
   one real approved batch through the existing Action and RO API. Shared frozen changes use a contract PR.
3. **F19 owner:** claim issue 139 and implement the presentation adapter, existing-scene support, project selection,
   counts, filters and independent error states in `web/app/time/` and `web/components/time/`.
4. **Validation:** the owning feature records automated and live evidence; independent review checks the actual
   point-to-project source link and the deployed workflow. Coordinate cross-owner fixes through separate claims.

This spec assigns no second writer to F19/F30/F31 and does not authorize editing their specs in this PR. The
implementation owner references C25 in its own follow-up spec/PR. The original overnight clock is historical for
this bounded specification request; STOP, main-red and normal implementation gates remain in force. No feature
completion marker is added for writing this spec. Roll back by reverting the consumer change or activating the
previous accepted dataset through the existing publication mechanism, retaining audit evidence.

## 7. Acceptance checklist

Run all repo checks from `specs/tech-stack.md`, plus focused adapter/interaction checks:

- Accepted national point is rendered/selectable; unreviewed, stale, rejected and null-center national records
  cannot become confirmed dots. A partial endpoint is labeled partial.
- Explicit legacy mirror draws once; two same-name distinct projects remain distinct; coincident projects are both
  selectable. Native IDs and arbitrary real owner labels survive the adapter.
- Exact/month/year/unknown milestone behavior is correct; unknown status is visible; past plans never imply completed
  work. Legacy golden overlap results, ranks, links and pair selection remain unchanged.
- More than one result page reconciles to the declared total. Dataset change mid-pagination cannot mix releases.
  Search/filter/reset, project selection without a pair, keyboard navigation and evidence access work.
- National-only outage, legacy-only outage, both unavailable, valid-empty data, tile failure, WebGL failure and reduced
  motion produce the specified states. Check desktop and 390px layouts and record performance on the real batch.

Live completion requires a recorded journey: approved source/project/location review -> merged release -> successful
load Action -> active RO API response -> visible `/time` point -> matching source/review details. Record deploy URL,
commit, dataset ID, time, representative project IDs, before/after scoped counts and screenshots of overview,
selected evidence, unknown-date and unlocated states. Verify `/explore` agrees on the same project's coordinates,
review and dataset. Record unavailable services or pending gates explicitly; fixture screenshots prove UI behavior
only. No required dot quota overrides evidence. If zero new locations qualify, report zero and keep map-population
acceptance pending.
