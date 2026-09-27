# GridBridge / Common Ground — judge-readiness audit

27 September 2026. Final submission pass against the user-supplied production URL: https://shellhacks2026-mu.vercel.app/.

## Executive Summary & Health Score (out of 100)

**Live presentation readiness: 70/100. The deployed application is usable as an evidence-discovery demonstration, but it is not accepted as the complete product requested in Plan B and the later Google/contract-upload amendments.** Four bounded fixes were implemented and tested during this pass. Production still reports a different, unmapped code revision. The deployment owner must publish the reviewed, green main revision to the existing Vercel project and verify the resulting URL before calling those fixes delivered to judges.

This score is an architectural/QA assessment, not measured test coverage or a certification. The rubric is availability/reliability 16/20, data/provenance 18/25, complete user workflows 15/25, usability 10/15, and release/test evidence 11/15. The older audit's 78/100 concerned a different local integration branch. Its contract-upload, coordinated-publication and Google-map implementation claims do **not** describe the current deployment or current main.

### Exact release boundary

| Evidence | Verified result |
|---|---|
| Public origin | `https://shellhacks2026-mu.vercel.app` |
| Full release check at 2026-09-27T12:00:13Z | Valid HTTPS, home HTTP 200, health HTTP 200, database up, eight homepage client bundles scanned without the verifier's configured credential markers. |
| Code reported by production | `4b30678aadee6f96c25a19d17d94179f23256b36`; this revision could not be resolved in the reviewed GitHub repository. Do not infer its source contents from main. |
| Active legacy dataset at that check | `9548c28191b2ac4eb703ec9283c31e364a911bce`. Earlier in this pass it was `490820091216c212879a58dd514ae6fe79cd527b`; data publication is continuing independently of frontend deployment. |
| Check against merged main `1fbcb5d97369a651d8853753aca4caeda1b4638f` at 11:59:39Z | Failed: deployed code revision did not match. A changing database identifier is not evidence that new application code was deployed. |
| Vercel access | The configured authenticated account/team cannot access this exact deployment or alias; the lookups returned 404. No replacement project or unrelated URL was created. |
| Custom domain | No qualifying custom domain was supplied or verified. |
| Production mutations | No production data was edited. Only the explicitly scoped Git changes below were published. |

The release verifier and health contract supporting these checks are `release/verify-deployment.mjs:58` and `web/app/api/health/route.ts:72`. The dated receipt is in `release/deploys.md:1`. A marker scan is limited to the eight discovered homepage bundles and the configured patterns; it is not a complete security audit.

### Code changes prepared for this release

| Pull request | Problem and resulting behavior | Validation / delivery |
|---|---|---|
| [#301 — F06](https://github.com/fradicus/Shellhacks-2026/pull/301) | An optional brief read could make the whole pair unavailable. Deterministic pair/source evidence now survives that specific failure; cancellation and mandatory-evidence failures still propagate. | Exact-revision CI, four focused cases; merged as `bda19d8`. `web/lib/server/queries.ts:118`; `tests/web/legacy/optional-brief.test.ts:1`. |
| [#302 — F11](https://github.com/fradicus/Shellhacks-2026/pull/302) | The pair-card CSV exported the whole view and could misrepresent the selected evidence. It now exports exactly the displayed pair, including review, version, source-page and precision context. Rejected pairs and filed owner codes have accurate labels. | Exact-revision CI; CSV/label tests; browser card and impact handoff; merged as `b21c4fb`. `web/components/pair/pairCsv.ts:35`; `CoordinationCard.tsx:36`; `evidenceLabels.ts:3`. |
| [#303 — F31](https://github.com/fradicus/Shellhacks-2026/pull/303) | Clicking the already-active explorer view cleared a selected project. That action is now a no-op and keeps the drawer open. | Exact-revision CI/e2e and manual production-build check; merged as `1fbcb5d`. `web/components/national/NationalExplorer.tsx:1`; `tests/web/national/explorer.spec.ts:1`. |
| [#304 — F19](https://github.com/fradicus/Shellhacks-2026/pull/304) | Focus could scroll the entire scene under the fixed header; on short screens the masthead squeezed the pair rows behind Projects. The scene no longer focus-scrolls, and the list retains space and independent scrolling. | Exact code revision passed full CI; latest rerun and merge status recorded in the final delivery note below. Pointer selection and evidence navigation passed at 1280×720 and 390×844. `web/components/time/time.module.css:49`, `:159`, `:233`, `:1019`. |

The local integrated test revision is `14d4071`, based on main `4908200`. The newer main `9548c2` changed only the California data/parser lane; those changes were preserved. No data, routing geometry, TimeView controller, schema, dependency, or shared loading files were included in these four patches. An independent reviewer found no concrete high/medium defect in the patches. Existing work by the nationwide-data and OSRM agents was not stopped, overwritten or merged speculatively.

### What this pass examined

Plans B/E, the transcript and current specs; the existing audit and its branch boundary; Git changes and open ownership claims; producers, loaders, readers, API routes and UI consumers; all navigation destinations by HTTP; live Overlaps, Gemini and Field planning interactions; and focused production-build explorer/pair/impact workflows. Graphify was used for cross-file navigation and refreshed after the code edits. The final code graph contains 7,385 nodes and 13,075 relationships.

This is not a claim that every source PDF page, device, input combination, button, provider jurisdiction, or production write path was independently accepted. Unperformed checks are called out below. No video or MP4 was created.

## Critical & High-Priority Vulnerabilities (Immediate fix required)

No new exploitable critical security issue was established in the scoped patches. The high-priority items here are release, integrity and functional gaps with concrete evidence.

### R1 — The judges' URL does not serve the reviewed fixes — HIGH, open

The health endpoint reports code `4b30678a…`, while the reviewed fixes have different merged Git revisions. The release verifier correctly fails against the target revision. During the pass, the dataset advanced from `4908200…` to `9548c2…` without the code changing. A working database and successful HTML response are insufficient release acceptance. Evidence: the timestamped checks above; `web/app/api/health/route.ts:72`; `release/verify-deployment.mjs:65`; `.github/workflows/load.yml:29` and `:39`.

**Required action:** the owner of the existing Vercel project must deploy current green main with project root `web`, preserve its existing environment bindings, then run the exact-revision verifier. The configured account here cannot perform that deployment. Do not replace the judges' URL or migrate the database just to bypass missing hosting access.

### R2 — Requested Google maps and actual truck-road visualization are not delivered across the app — HIGH, open

Current source still initializes MapLibre on Project map, National explorer, History and Field planning: `web/components/map/MapView.tsx:3`, `web/components/national/NationalMap.tsx:3`, `web/components/history/HistoryView.tsx:3`, `web/components/operations/WorksiteMap.tsx:3`. The live Overlaps page visibly attributes OpenFreeMap/OpenMapTiles/OpenStreetMap. The later provider policy explicitly reserves OSRM for Overlaps and requires Google on the other map surfaces (`specs/decisions/C53-provider-routing-and-upload.md:8`). The earlier audit branch's Google adapters are not equivalent to a deployment of that policy.

There is a server Google truck-route adapter, but it requires a key and separately provisioned LVR access and returns an unavailable state otherwise (`web/lib/operations/providers.ts:142`). Its private encoded polyline is sampled on the server for environmental evidence (`web/lib/operations/service.ts:80`); this does not establish that users see an accepted truck route on a Google map. A center-to-center proximity connector or passenger-car route must not be presented as a verified truck path.

**Required action:** allow the map/routing owner to finish the isolated implementation, then verify an attributed real route, verified entrances, explicit vehicle constraints, provider coverage, and clear errors in the deployed UI. This pass did not trigger paid route calls or claim route safety. Ordinary imagery, AlphaEarth embeddings and Earth/3D tiles are separate capabilities; an AEF reference field does not satisfy a Google Earth visual-map requirement (`web/lib/operations/aef.ts:11`, `:61`).

### R3 — Full Plan B filtering/recomputation and export synchronization remain incomplete — HIGH, open

Plan B asks users to choose utilities, an analysis date and a planning horizon (`plans/plan-B/PLAN.md:38`). Current Overlaps uses stored collection/view classifications and an illustrative time sheet (`web/components/time/TimeView.tsx:129`, `:160`). Moving the sheet does not recompute eligible records or prove a construction window. The selected-pair CSV is fixed, but general legacy export only accepts type/view and caps rows at 5,000 without a complete shared-filter contract (`web/app/api/export/route.ts:11`, `:74`).

**Required action:** implement a single validated query model and dataset binding for the required controls, lists and exports. Test analysis-date boundaries, unknown precision, zero results, source revisions and truncation explicitly. Preserve the current deterministic under-25-mile rule until its owner ships an approved rule change; do not substitute road distance silently.

### R4 — Uploading a new contract through the complete analysis is absent from the current release — HIGH, open

Current navigation contains no contract intake destination (`web/components/nav/Nav.tsx:10`), and the current judge/main checkout has no contract intake package, API or page. The older audit branch contains a bounded private intake implementation, but it was not merged into this release. Even that implementation requires exact-quote human review and does not establish general multi-project OCR, semantic reconciliation or automatic verified enrichment.

This is a later user amendment; original Plan E disallowed arbitrary public uploads (`plans/plan-E/PLAN.md:143`). The current amendment requires authorization/receipt, extraction, review, analysis and publication acceptance (`specs/decisions/C53-provider-routing-and-upload.md:22`). Software schema “contracts” are not document-upload functionality.

**Required action:** deliver an authenticated upload workflow with one authorized real document, inspect extraction errors, approve citations and duplicates, then show the new reviewed records consistently in maps, evidence and exports. Do not hurriedly copy the old branch's incompatible publication system into a running database.

### R5 — Real extraction, featured-opportunity acceptance and operational outcomes are incomplete — HIGH, open

The live Gemini workbench explicitly shows **0 of 91 DESC cards processed**. The committed extraction ledger records zero extraction calls/accepted/processed pages (`data/extraction/eval.json:4`). A separate committed brief-generation run produced 15 passing stored briefs (`data/briefs/summary.json:3`), and the live Briefs tab exposes 15. Stored structured-output validation is not independent model accuracy or proof of extraction performance.

The live Overlaps display has zero future legacy pairs, 16 historical and three tentative in the observed session; its first historical example is explicitly not confirmed by audit. These are candidate/evidence records, not accepted savings opportunities. The operational duration model also reports no current externally approved model (`web/lib/outcomes/model.ts:197`, `:269`).

**Required action:** keep the demo claims limited to evidence discovery. To close the full goal, perform a real source-grounded extraction/evaluation, independent review of the featured pair, and a separately approved actual-history model if predictions are shown. Filing dates do not establish crew availability, construction duration, equipment transfer windows or realized savings. Plan requirements: `plans/plan-B/PLAN.md:57`, `plans/plan-E/PLAN.md:121`; transcript motivation: `docs/context/transcript.txt:26`, `:42`, `:48`.

### R6 — Cross-page publication is still split — HIGH, open in current release

The loader workflow invokes legacy and national publications separately (`.github/workflows/load.yml:29`, `:39`). Legacy readers select `meta.active` (`web/lib/server/db.ts:26`); national publication advances `meta.national_active` (`pipeline/national/load.py:181`). The active-dataset health field covers the legacy pointer, not a unified manifest binding every page, reference artifact and model result. The old audit branch's coordinated `meta.release` migration is not in current main.

**Required action:** explicitly verify both published datasets and their intended relationship in the release receipt; handle a partial load visibly. A coordinated-pointer migration requires its own staged/readback/rollback acceptance. Until then, do not claim every surface uses one atomic publication merely because each API works.

## Medium & Low-Priority Improvements

| Priority | Finding and evidence | Action |
|---|---|---|
| Medium | Large live payloads: approximately 22.17 MB for Explore HTML, 10.44 MB for Time HTML, about 6 MB for History, and about 19.5 MB for one national API response during this pass. These are observed response-body sizes, not a controlled performance benchmark. Current national API serializes its explorer payload (`web/app/api/national/route.ts:20`). The deployed SHA is unmapped, so current-source line numbers must not be treated as proof of its exact implementation. | After deploying current compact-read work, measure again on a normal connection; page the ledger, keep map payloads compact, and load detail/source text on selection. |
| Medium — fixed in candidate | Pair evidence actions could become unreachable; short-screen list rows competed with the Projects control. `web/components/time/time.module.css:49`, `:159`, `:233`, `:1019`. | Deploy #304; repeat the exact laptop and phone click sequence on production. |
| Medium — fixed in main | Active view clicks discarded national selection. `web/components/national/NationalExplorer.tsx:1`; `tests/web/national/explorer.spec.ts:1`. | Deploy #303. This fix does not add URL persistence for every selection/filter. |
| Medium — fixed in main | Whole-view CSV from one pair and misleading reviewed-owner language. `web/components/pair/CoordinationCard.tsx:36`, `pairCsv.ts:35`, `evidenceLabels.ts:3`. | Deploy #302. Preserve exact file/source versions and review state; separately address general export filters/caps. |
| Medium — fixed in main | Optional brief errors hid mandatory pair facts. `web/lib/server/queries.ts:118`. | Deploy #301; retain cancellation and mandatory-read failures. |
| Medium | Windows newline conversion invalidates committed artifact digests. No root `.gitattributes` enforces the relevant bytes. The reviewed worktree initially had 311 converted files; all were restored to exact HEAD bytes without data changes. A F39 mutation test still hashes translated text differently on Windows (`tests/pipeline/test_f39_dense.py:78`). | Add owner-approved LF/binary artifact attributes and byte-based test hashing. Do not re-publish data to conceal checkout conversion. Linux CI passed. |
| Low | Field planning returns reference counties as long FIPS-number lists. Live search for Duke returned six actual records, but identifying counties requires additional lookup. `web/components/operations/OperationsDesk.tsx:71`; reference rendering and source semantics are in that component. | Show verified state/county names alongside codes, with expandable lists; preserve the warning that reference service rows are not project locations. |
| Low | The previous README said no production URL had been verified. `README.md:7` before this documentation pass. | Corrected with the actual URL, dated receipts, exact code mismatch and owner action. Keep volatile counts in receipts rather than undated marketing claims. |

The long Overlaps and History controllers remain candidates for incremental separation after the presentation deadline. Extracting view state, selection, provider layers and accessibility behavior should follow regression evidence rather than a rushed rewrite. No new complexity or leak claim was inferred solely from file length.

### Status of the original assigned audit items

| Original item | Current release interpretation |
|---|---|
| H1 — stale match/source facts | The old audit branch has stronger integrity/review-binding work. This pass did not re-certify or port all of it to current main. Current lead labels must remain conservative; no reviewed-opportunity acceptance is claimed. |
| H2 — mixed publication | Open in current release; see R6. Do not import the old “fixed locally” status as deployed. |
| H3 — contract intake | Open in current release; see R4. |
| H6 — real-data/model/deployment acceptance | HTTPS/DB availability and real EIA directory search are now observed. Extraction, featured-opportunity review and current-code deployment remain incomplete. |
| H7 — reproducible hashes | The working checkout was corrected without changing data. Cross-platform fixture/attribute remediation remains owner work. |
| M1 — national coordination | Current main has a separate national candidate path, while the observed deployed `/api/national-pairs` returned 404. The older audit's stricter matcher is a different implementation and is not claimed here. |
| M2 — selected-project field planning | The live page accepts manual worksites and exposes real references. This pass did not establish the full selected-project/publication handoff from every national surface. |
| M3 — Overlaps layout | Reproduced and fixed through #304; laptop/phone acceptance passed locally, production acceptance awaits deployment. |

## Positive Highlights (What is built well)

- Source citations, date precision, uncertainty and explicit unavailable states are present throughout the data model. The live Gemini page tells the user that extraction has not run instead of inventing model output (`web/components/gemini/Workbench.tsx:1`; `data/extraction/eval.json:4`).
- The real EIA directory is usable in the deployed UI. Searching Duke returned six named utilities with EIA IDs, vintage and evidence state; it did not replace an unknown worksite with a county centroid (`web/lib/verified/server.ts:12`, `:32`).
- Database reads are bounded and shared through the repository layer, with cancellation/deadline infrastructure (`web/lib/server/repository.ts:15`, `:21`). The optional-brief change is narrowly isolated.
- Export serialization preserves source context, quotes CSV fields, guards formula-like text, and limits the selected-pair artifact to the displayed pair (`web/components/pair/pairCsv.ts:1`; `tests/web/export/pairCsv.test.ts:1`).
- The separate pipeline/web/e2e/ownership CI gates caught integration problems without disabling them. The release verifier refuses a mismatched code revision (`release/verify-deployment.mjs:65`).
- The app separates user scenario assumptions from filed evidence. The impact worksheet does not silently promise savings when input costs or durations are unknown (`web/components/impact/ImpactWorksheet.tsx:47`, `:51`, `:103`).

## Actionable Roadmap (Step-by-step remediation plan)

### Before sending the link to judges

1. **Deploy the reviewed code in the existing Vercel project.** The owning account should deploy the latest main revision whose required CI is green, including #301–#304, with root `web` and its existing production bindings. No database migration is required by these four fixes.
2. **Verify the actual deployed SHA.** Run `node release/verify-deployment.mjs --commit <full deployed Git SHA> --url https://shellhacks2026-mu.vercel.app`. The command must pass against the intended revision, not simply the previously observed one. Record the health dataset and national publication receipt separately.
3. **Repeat the short demo path on that URL.** Home → National explorer → select a project → click the active view and retain selection → Overlaps → select a pair with the mouse → Open evidence → selected-pair CSV → Impact inputs. Repeat pair access at 390×844. Confirm the CSV contains that pair and one data row using a browser that exposes downloads.
4. **Use truthful presentation wording.** Demonstrate public-filing discovery, evidence comparison, review status, the real EIA directory, and an explicitly user-entered impact scenario. Do not present rejected/historical pairs as approved future savings opportunities; do not claim all Google maps, truck-route geometry, contract upload, live extraction or duration prediction are complete.
5. **Keep the live checks visible.** If the deployment owner cannot publish the code before submission, the existing site can still demonstrate the observed research/reference workflows, but the release is not accepted as fully ready and the known live layout/selection/export problems remain.

### After the immediate release

6. Finish the existing owners' Google/OSRM work and verify actual provider geometry with attribution and vehicle/entrance constraints. Keep the requested Overlaps provider exception.
7. Reconcile legacy, national and verified-reference publication identities with an accepted atomic-release design or explicit split-release guarantees; test partial-load rollback/readback.
8. Implement Plan B's shared utility/date/horizon query and synchronized exports, then test date precision and revision changes.
9. Ship authenticated contract intake as a separately accepted workflow using one authorized real document and reviewed citations; keep private source bytes out of Git and public exports.
10. Run and evaluate real Gemini extraction; independently review featured opportunities and actual-history models. Treat unknowns and failed corroboration as visible evidence states.
11. Complete performance measurement and incremental controller cleanup after the version deployed to judges is stable.

### Page-by-page functional report

| Surface | Verified now | Remaining delivery boundary |
|---|---|---|
| Home `/` | Live HTTPS and HTTP 200; navigation destinations available; eight discovered client bundles pass the configured marker scan. | A landing animation is not proof of downstream workflow acceptance; some branding differs between the deployed code and current source. |
| Overlaps `/time` | Live map, dates, source counts, pair lists and selected-pair evidence summary. The candidate build fixes focus/list layout and reaches its evidence card by pointer at both reviewed sizes. | Current live code still has the clipped-action behavior. Zero future legacy pairs is an honest data result. No verified truck route is established by a straight proximity connector. |
| Project map `/map` | HTTP 200 and current-source MapLibre implementation. | Full Google replacement and every interaction were not accepted live. |
| National explorer `/explore` | Live HTTP 200/data response; local project drawer and active-view retention verified. | Large deployed payload; no claim of complete nationwide verified project locations. Production must receive #303. |
| History `/history` | Live HTTP 200; current source has a separate history map/ledger. | Google map amendment, actual job histories, and exhaustive interaction acceptance remain incomplete. An in-service filing is not a measured job outcome. |
| Pair evidence `/pair/...` | Live pair API returned evidence; local deterministic card, unavailable-brief state, selected-pair export action and impact handoff work. | Local CSV serialization is tested; the in-app browser did not emit a download event, so an actual downloaded file was not accepted through that UI. Production needs #301/#302/#304. |
| Field planning `/operations` | Live form opens; blank submission shows “Worksite label is required”; reference section opens; Duke search returns six real EIA records. | Live Google/LVR paid routes, map geometry, worksite-provider coverage, and selected-project context from every page were not accepted. No approved duration model. |
| Filing changes `/changes` | HTTP 200 and corresponding API data. | No exhaustive record-by-record diff review or unified-publication acceptance. |
| Coverage `/coverage` | HTTP 200; committed coverage artifacts remain available. | Coverage counts do not establish independent location/owner corroboration. |
| Gemini `/gemini` | Source text/deterministic fields visibly load, explicit 0/91 extraction status, Extraction and Briefs(15) controls usable. | Real extraction/evaluation remains unavailable; no new model request was made. |
| Impact `/impact` | HTTP 200; local selected-pair handoff carries both projects; editable worksheet and explicit unknown inputs. | Not a validated economic prediction. Native print dialogue and a downloaded browser artifact were not verified. |
| Contract upload | No current main/live intake destination. | Full amended workflow is missing; see R4. |
| Health/data APIs | Health, projects, pair, sources, coverage, briefs, national/reference and legacy CSV read endpoints responded in this pass. | `/api/national-pairs` was absent on the observed deployed revision. No production write/upload path was exercised. |

### EIA and data validation: what is real and what it means

The reference corpus is **EIA-861 2024 final**, stored as reviewed, hash-checked artifacts; it is not a fresh EIA network call on every page. The release contains 3,413 utility records: 3,380 accepted and 33 needing review. It contains 11,866 utility/county service rows: 11,818 accepted, 37 unresolved and 11 conflicting; 51 records are quarantined. Evidence: `data/verified/coverage.json:1`; reproducible allowlisted refresh/check entry point `pipeline/verified/__main__.py:10`; hash-checked application reads `web/lib/verified/server.ts:12`, `:32`.

The live Duke search returned the accepted IDs 15470, 19446, 3046, 3542, 5416 and 6455 from reference dataset `3e63e1037b9c76681bcc73b4a41acb080f20172b664457f07419aa14fbee0bf7`. This confirms a functional deployed reference lookup. Census verifies geographical identity; it does not independently prove utility service membership. Independent service corroboration remains zero in the recorded corpus. These rows do not supply construction schedules, road entrances, crew availability or independently verified ownership of every transmission project.

The live map observed 2,863 located records in its displayed scope, with 2,784 national records not yet in service, 1,195 national records already in service available in History and 4,263 unlocated national records. Its displayed location classes were 46 confirmed, 270 owner-published and 2,468 tentative among those not yet in service. These are one observed UI snapshot while other agents are publishing; they are not an undated canonical national total and were not hand-edited by this pass.

The local browser build deliberately used `DATA_MODE=fixture` and `NATIONAL_DATA_MODE=snapshot`. Its 10 legacy projects/six legacy pairs and 1,286-record base national snapshot are local test data scopes, not a substitute for the production inventory or proof that the newest regional release is fully visible.

### Pipeline and database review boundary

The current checkout contains 29 pipeline packages. Their roles and acceptance boundaries are:

| Packages | Role | Verified boundary / remaining gap |
|---|---|---|
| `extract_desc`, `extract_gpc` | Deterministic parsing of the source filings. | Schema/golden checks run in CI; raw date/owner uncertainty must remain visible. Entry points: `pipeline/extract_desc/__main__.py:8`, `pipeline/extract_gpc/__main__.py:8`. |
| `osm`, `locations` | Cached geographic evidence and review tooling. | Matching a place name is not verified ownership or a truck entrance. `pipeline/locations/__main__.py:11`. |
| `matches`, `match_run` | Canonical proximity/date/rank calculation and run artifacts. | Plan B/E facts remain deterministic; illustrative time controls do not rerun them. `pipeline/match_run/__main__.py:15`. |
| `gemini_extract`, `briefs` | Optional source-grounded extraction and stored narrative briefs. | Zero extraction acceptance; 15 recorded passing briefs. `pipeline/gemini_extract/__main__.py:11`, `pipeline/briefs/__main__.py:12`, ledgers cited above. |
| `coverage`, `common` | Coverage summaries and shared validation/publication helpers. | Coverage is a statement of known and unknown records, not source corroboration. `pipeline/coverage/__main__.py:15`. |
| `load` | Versioned legacy publication to the database. | Shared read-only web access; separate publication pointer. `pipeline/load/__main__.py:84`; `web/lib/server/db.ts:26`. |
| `national`, `national_pairs` | National snapshot assembly/load and nearby candidate generation. | Separate national pointer; candidate delivery differs between main and live. `pipeline/national/load.py:98`, `:181`; `pipeline/national_pairs/build.py:1`. |
| `akhi`, `california`, `camunis`, `expansion`, `greatlakes`, `interiorwest`, `midwest`, `pnw`, `southeast`, `southwest`, `sppsouth`, `texas` | Regional source ingestion and publication artifacts. | Other agents' additions were preserved. Linux pipeline CI passed for the reviewed changes; this pass did not independently reread every regional filing or certify every location. Release manifests and source ledgers remain the evidence for each region. |
| `verified` | EIA/Census utility and geographical reference artifacts. | Hash-checked real reference data; service/ownership limitations above. `pipeline/verified/__main__.py:10`. |
| `environment`, `weather_history` | Environmental context and historical weather evidence. | Provider/year/point coverage is bounded; an annual embedding is not current weather or a construction safety decision. `pipeline/weather_history/__main__.py:77`; `web/lib/operations/aef.ts:11`. |
| `outcomes` | Authorized actual-history import and model artifacts. | No current externally approved live model established. `pipeline/outcomes/__main__.py:27`; `web/lib/outcomes/model.ts:269`. |

The web application's database identity remains read-only; the GitHub load workflow is the designated writer. Current legacy and national loaders are separate. Reference JSON remains separately hash-checked on disk. The observed health response proves a reachable configured database at the probe time; it does not certify every collection, index, source receipt or cross-page revision join. No missing live credentials were invented or copied from unrelated locations.

### Validation and Git ledger

| Check | Result and limits |
|---|---|
| Exact PR CI | #301, #302, #303 and #304 code revisions passed checks, web, pipeline, e2e and aggregate CI. PR metadata changes caused an additional #304 run; its final state is recorded below. |
| Local production build | Passed on Node 24, including TypeScript. Fixture/snapshot modes were explicitly enabled. A nonfatal font fetch used the configured fallback. |
| Local web verification | Full ESLint passed; 91 Node tests passed, zero failed/skipped. Focused optional-brief, CSV and owner-label cases passed. |
| Local pipeline verification | Ruff passed. Initial Windows failures exposed missing Bash and CRLF artifact conversion. After fixing only the local environment/bytes, 693 previously passing cases plus 49 rerun cases passed; the F39 mutation/hash test still fails on Windows. A filename-newline golden test is incompatible with Windows and was excluded from that rerun. Do not describe the full local Python run as green. The exact PR Linux pipeline CI passed. |
| Spec/ownership | 43 feature specs passed lint; ownership checks passed in CI. No ownership gate was weakened. |
| Browser acceptance | Project selection survives active-view click. Pair pointer selection and Open evidence work at 1280×720 and 390×844; phone document width equals viewport width. Impact handoff loads the selected projects. |
| Browser limitations | No confirmation of a downloaded CSV file from the in-app browser event; no native print-dialog verification; no fresh paid Google/Gemini call. Serializer tests and button navigation are separate evidence. |
| Live release verifier | Observed revision passes infrastructure/bundle scan; intended merged revision fails code match. Both facts are recorded, not collapsed into “production passed.” |
| Git files | Four feature patches affect 13 source/test files, +296/-15 at integrated `14d4071`. No committed data, `.env`, `.local`, routing-controller or schema changes. A scoped credential-pattern review found no credentials in those patch files. |
| Data checkout integrity | 311 files displayed as modified after byte restoration; every one matched its HEAD blob. Refreshing the index with conversion disabled cleared the stale status, with no staged data diff. No data rewrite was committed. |
| Knowledge graph | AST update completed after edits; ignored generated graph files were not added to the feature PRs. |

### Agent roles and non-interference

The root owned Git integration, live browser acceptance and this report. A principal-architecture reviewer (`gpt-6-astra`, high reasoning) independently checked the patches and Git hygiene. A source/workflow reviewer (`gpt-6-astra`, high reasoning) owned the bounded F06/F11 implementation and plan/evidence checks. A frontend QA implementer (`gpt-5.6-sol`, high reasoning) handled the isolated F31/CSS fixes and release documentation. File ownership was exclusive. The external data and OSRM workers were left running; their branches and shared files were not reset, force-pushed or overwritten.

### Final delivery note — 2026-09-27, 12:08 UTC

All four fixes are merged: #301 `bda19d8`, #302 `b21c4fb`, #303 `1fbcb5d`, and #304 `040d98f`. Both #304 CI runs completed successfully before its merge. The main revision after that merge is `040d98ff650d41c09e47618f0be793277da13760`; its integration CI is running at this checkpoint. The separate owner's intervening overview-fit change #306 is preserved. Production deployment of these fixes is still unverified and the configured hosting account cannot update the target URL.

The report is also saved locally at the requested `docs/audit-report.md`. The repository copy is kept under the existing release owner's `release/` directory so sponsor originals and ownership gates remain intact. The README and deployment ledger now identify the actual live origin and its code mismatch. No video or MP4 was produced.
