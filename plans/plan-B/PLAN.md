# Utility construction overlap detector — Paperclip implementation plan

Prepared 26 September 2026. This is a plan for the full project. No application, demo, cloud resources, or running Paperclip company has been created by this document.

## 1. Recommended approach

Build **GridBridge**, a working name for a utility planning dashboard. Compare Georgia Power with Dominion Energy South Carolina, starting with the sponsor materials already in this repository. Show their projects on an interactive map, identify nearby work, compare schedules, and rank opportunities to coordinate crews, equipment, and freight.

Use eight Paperclip agents: a CEO and seven specialists. Use Claude Code as the common development runtime, Gemini in the application for document extraction and evidence-based coordination briefs, and MongoDB Atlas for project records and spatial queries. Deploy one Node web service, with a React frontend, on Render and connect a qualifying GoDaddy Registry domain.

The agents build the application. The finished application runs independently of Paperclip. Paperclip keeps its own operational database; Atlas stores the project's utility data.

### Repository findings that affect implementation

The repository originally contained reference documents, with no application code. Plan A is maintained separately in `plans/plan-A/`. This plan belongs to `plans/plan-B/`. Keep each effort inside its own folder and share the original repository `docs/` directory. Source paths beginning `docs/` in this document are relative to the repository root.

Read these files before implementation:

- `docs/Sperry-Tech-Challenge/ShellHacks_Challenge_Gridlock.docx`: challenge and required outputs.
- `docs/Sperry-Tech-Challenge/Finding_Real_Locations_Guide.docx`: endpoint matching, center calculation, distance threshold, and confidence rules.
- `docs/Sperry-Tech-Challenge/Projects_Overlaps.xlsx`: example project and overlap tables.
- `docs/Sperry-Tech-Challenge/Project Listings/Dominion Energy/2024-2028-2million-and-above-project-descriptions.pdf`: 44 project cards.
- `docs/Sperry-Tech-Challenge/Project Listings/Georgia Power/2025 IRP Volume 3 PUBLIC DISCLOSURE.pdf`: 668 pages, including the Georgia ITS expansion plan.
- `docs/context/hackathon-prizes.md` and `docs/context/transcript.txt`: track requirements and resource coordination context.

**Three concrete data issues:**

1. Some starter records have 2023–2025 in-service dates. They are useful historical examples, but cannot automatically be described as future work in September 2026.
2. Georgia's expansion tables contain multiple organization codes, including GPC, GTC, and SAV. Preserve the original owner/sponsor code. Verify each mapping before labeling a row Georgia Power.
3. Some Georgia PDF pages carry both PUBLIC DISCLOSURE and confidential CEII markings. Have the data owner resolve the public status of the relevant pages before sending them to Gemini or republishing excerpts. Use an unambiguously public alternative where status remains unresolved. The sponsor explicitly excludes CEII.

The [public DESC project PDF](https://www.scrtp.com/assets/pdfs/home/2024-2028-2million-and-above-project-descriptions.pdf) is accessible. Check the [Georgia Power IRP page](https://www.georgiapower.com/about/company/filings/irp.html) and [SERTP public planning library](https://www.southeasternrtp.com/) for updates. SERTP announced preliminary 2026 ten-year plans; project freshness and utility attribution still require review.

## 2. Product behavior and acceptance criteria

### Required experience

1. Choose the two utilities, an analysis date, and a planning horizon.
2. See both utilities on a map, with a synchronized project table.
3. Open a project to see its original name, owner, date, location evidence, confidence, and source page.
4. See nearby pairs and a ranked coordination list.
5. Filter by distance, schedule relationship, project type, and location confidence.
6. Open a pair to inspect both source records, distance, schedule comparison, and a Gemini coordination brief.
7. Export the filtered project and overlap records as CSV, including source and uncertainty fields.

Use the sponsor's rule for the default **Nearby opportunities** view: project centers less than 25 miles apart. Time is a secondary ranking signal. Also provide a separate **Timeline matches** view to satisfy the request to flag projects scheduled around the same time even when they are not nearby. Label each result `nearby`, `timeline`, or `both`; a remote timeline match must not masquerade as a local resource-sharing opportunity.

Use a proposed 180-day proximity threshold for in-service dates, editable in the UI and explicitly labeled as a product assumption. This threshold is not supplied by the sponsor.

### Completion criteria

- Both utilities have real, cited project records and their owner mappings have been checked.
- Every accepted record has a document version and source page. Missing values stay missing.
- Map, ranked list, filters, detail view, and CSV export work together.
- Spatial results follow the sponsor's center-based rule and pass independent distance checks.
- In-service proximity is distinguished from an actual overlapping construction window.
- Gemini performs real extraction and produces source-grounded briefs. A failed Gemini call does not erase deterministic match results.
- Atlas actually stores and serves the records and supports indexed spatial queries.
- At least one opportunity has an editable, transparent impact scenario.
- Published application works over HTTPS on the registered domain.
- All four requested tracks have an evidence section in the submission draft.

Do not manufacture a minimum number of overlaps. Report the number found, the number inspected, and location/date coverage. If current data yields no nearby matches, show that result honestly and offer explicitly dated historical examples separately.

## 3. Agent organization and jobs

All seven specialists report to the CEO. The technical lead owns shared interfaces and integration; the CEO owns priorities and task assignment. QA reviews work independently of its author.

| Agent | Job and deliverables | Main handoff |
|---|---|---|
| **CEO / Product Lead** | Own scope, issue dependencies, budgets, acceptance criteria, track coverage, and final submission narrative. Keep decisions and blockers in Paperclip. | Assign bounded issues to specialists; send integration decisions to technical lead. |
| **Technical Lead / Backend & Atlas Engineer** | Own data/API contracts, Node API, Atlas collections/indexes, shared types, dependency choices, and integration branch. Review and merge accepted changes. | Contracts to all builders; complete API to frontend and QA. |
| **Utility Data Researcher** | Audit public sources, find current plan versions, verify owner codes, inventory document pages, create reviewed examples, and maintain source provenance. | Approved page manifest and reference records to Gemini and geospatial engineers. |
| **Gemini / Document Engineer** | Implement document segmentation, structured extraction, schema validation, retries, extraction evaluation, and coordination briefs. | Validated records to backend; cited brief format to frontend. |
| **Geospatial / Matching Engineer** | Resolve endpoints, retain candidate evidence, calculate project centers, distance and time relationships, deterministic ranking, and impact scenarios. | Versioned match records and explanation fields to backend and QA. |
| **Frontend / UX Engineer** | Build map, table, filters, pair details, timeline treatment, data quality states, accessibility, and exports. | Integrated user flows and screenshots to QA. |
| **QA / Data Verification Engineer** | Independently verify sampled extraction and every prominently featured opportunity; check geometry, dates, security boundaries, and end-to-end behavior. | Reproducible defects or acceptance evidence to technical lead and CEO. |
| **Release / Submission Engineer** | Own deployment configuration, secrets wiring, health checks, domain/DNS instructions, rollback steps, and track evidence package. | Release candidate to QA; submission package to CEO. |

Eight configured agents does not mean eight simultaneous runs. Start with no more than three active assignments and one run per agent. The CEO can manage that limit through assignment order if the installed Paperclip version lacks a global concurrency setting.

### File ownership

All paths below are relative to this idea's future implementation directory:

| Owner | Files |
|---|---|
| Technical lead | `server/`, `shared/`, root package manifest and lockfile |
| Data researcher | `data/sources/`, `data/review/`, source inventory |
| Gemini engineer | `pipeline/extract/`, `pipeline/briefs/`, extraction prompts |
| Geospatial engineer | `pipeline/locations/`, `pipeline/matches/` |
| Frontend engineer | `client/` |
| QA | `tests/`, evaluation reports |
| Release engineer | deployment settings, CI, `docs/release/`, `docs/submission/` |
| CEO | project plan, issue descriptions, decision log |

Coordinate changes to shared types and dependencies with the technical lead. Do not let multiple agents rewrite one lockfile concurrently.

## 4. Skills required by each agent

Skills are reusable written procedures; tools, API access, and model credentials must be configured separately. The names beginning `gridbridge-` below are **proposed custom skills to author**, not existing downloadable packages.

All agents need Paperclip's bundled coordination skill and `gridbridge-project-rules`. Agents editing files also need `gridbridge-git-workflow`.

| Custom skill | Required procedure and output | Assigned agents |
|---|---|---|
| `gridbridge-project-rules` | Read the challenge, honor folder boundaries, distinguish evidence from inference, preserve unknowns, protect secrets, and follow the definition of done. Output a task-specific completion checklist. | Everyone |
| `gridbridge-git-workflow` | Work on the assigned branch/worktree; inspect changes; run relevant checks; attach commit/diff and verification to the issue; never overwrite another idea's files. | Everyone writing files |
| `gridbridge-delivery` | Break milestones into issues with owner, dependencies, inputs, output, acceptance test, and budget; review blockers before assigning more work. | CEO, technical lead |
| `gridbridge-public-source-audit` | Record publisher, URL, local checksum, publication date, public status, page range, owner code, and freshness. Reject unresolved source classification for external processing. | Researcher, QA |
| `gridbridge-gemini-extraction` | Segment approved PDFs, request schema-constrained output, validate citations and values, deduplicate, retry transient errors, and route uncertainty to review. | Gemini engineer, QA |
| `gridbridge-location-matching` | Match endpoint names against public features using owner, voltage, county, and neighboring landmarks; save accepted/rejected candidates and reasons. | Geospatial engineer, researcher, QA |
| `gridbridge-overlap-analysis` | Implement center distance, date uncertainty, the separate match categories, deterministic ranking, pair deduplication, and explicit impact assumptions. | Geospatial engineer, technical lead, QA |
| `gridbridge-atlas-api` | Use native MongoDB driver, GeoJSON, indexes, idempotent imports, bounded queries, validation, server-only credentials, and stable response contracts. | Technical lead, QA |
| `gridbridge-map-ux` | Synchronize map/list selection; explain uncertainty; support keyboard/table alternatives; display source citations, attribution, and empty/error states. | Frontend engineer, QA |
| `gridbridge-verification` | Maintain reviewed reference cases, test boundary conditions, verify featured claims, and document actual outcomes with reproduction steps. | QA; builders for their checks |
| `gridbridge-release-tracks` | Deploy the reviewed commit, verify health/DNS/TLS, rehearse rollback, and gather evidence for Sperry, Gemini, Atlas, and domain tracks. | Release engineer, CEO |

### Authoring and attaching the skills

Create `paperclip/skills/<skill-name>/SKILL.md` in this idea folder during setup. Each file needs a clear name and description, required inputs, numbered workflow, expected output, and checks. Put the relevant sections of this plan in supporting references rather than copying the entire plan into every skill.

Import that directory into the company skill library, then attach the appropriate returned skill keys to each agent. Paperclip documents `POST /api/companies/{companyId}/skills/import` with a `source` path and `POST /api/agents/{agentId}/skills/sync` with `desiredSkills` plus `mode: "add"`. Use the returned canonical keys; inspect the next heartbeat to confirm installation. [Paperclip company skill guide](https://docs.paperclip.ing/how-to/write-a-company-skill/)

Do not assume skills installed in this Codex session automatically exist in Paperclip. Install or author them explicitly for the chosen runtime.

## 5. Common instructions and role prompts

Use this as the common instruction text for all agents:

> You work on GridBridge, the utility overlap detector, within this idea's assigned directory. Read the approved implementation plan and your assigned Paperclip issue before editing. Use the supplied sponsor documents as reference data. Do not modify the other idea's files or the original sponsor files. Preserve public-source provenance and uncertainty. Do not infer missing coordinates, dates, owners, or costs as facts. Check out the assigned issue through Paperclip before work. Keep a durable record of decisions, changed files, checks, and remaining blockers. End each run with the next concrete step. Continue only within the issue's scope and available budget.

Append the appropriate role prompt:

- **CEO:** “Own the acceptance criteria and the dependency graph in this plan. Delegate bounded work to the seven configured specialists. Resolve routine scope choices. Track the Gemini, Atlas, and domain requirements explicitly. Mark the project complete only after QA has accepted the integrated release and submission evidence.”
- **Technical lead:** “Own shared schemas, API behavior, Atlas, and integration. Publish contracts before dependent implementation starts. Review branch changes and accept them after relevant checks. Keep package versions pinned and the architecture limited to the documented components.”
- **Researcher:** “Deliver a public-source manifest and reviewed project examples for DESC and GPC. Resolve stale dates, multi-owner tables, duplicate versions, and mixed disclosure markings. Record the exact page and evidence for every decision. Make location ambiguities explicit.”
- **Gemini engineer:** “Implement Gemini extraction and briefs from approved inputs. Return structured validated data with original page references. Measure extraction against reviewed examples. Make all numerical match claims come from the deterministic matching result.”
- **Geospatial engineer:** “Follow the sponsor's center calculation and strict distance threshold. Keep inferred endpoint matches separate from accepted locations. Distinguish in-service milestones from construction intervals. Produce reproducible matches, ranks, and editable impact scenarios.”
- **Frontend engineer:** “Build an interactive map and ranked list that expose source evidence and uncertainty. Make timeline-only matches clearly recognizable. Preserve usability when locations or dates are missing, when there are zero matches, and when Gemini is unavailable.”
- **QA:** “Check results independently against original documents and reference calculations. Verify every opportunity featured in the submission. Test boundaries, missing data, stale records, duplicate pairs, and failed services. Report measured outcomes and blockers.”
- **Release engineer:** “Deploy the accepted commit, wire production secrets, validate domain and HTTPS, and document rollback. Assemble evidence of actual Gemini calls, Atlas queries, and the qualifying domain. Draft submission material from verified project behavior.”

## 6. Architecture

```text
Approved public PDFs + source manifest
             |
       Gemini extraction
             |
  Schema validation + data review
             |
Public location evidence --> accepted endpoint locations
             |
 Deterministic distance/time matching
             |
 MongoDB Atlas: projects, sources, matches, runs
             |
 Node/Express API ---- Gemini coordination briefs
             |
 React/Vite UI + Leaflet map
             |
 Render service + qualifying custom domain
```

Recommended components:

- **TypeScript** across frontend, backend, and pipeline to share validation and types.
- **React + Vite** for the UI, **Leaflet** for map interaction, MapTiler for a hosted basemap.
- **Node + Express**, serving both API and built frontend from one origin.
- **MongoDB native driver** and a schema validator such as Zod.
- **Google's `@google/genai` SDK**. Select an available stable Gemini model supporting the required PDF/structured output features, test it, and record the exact ID in `GEMINI_MODEL`.
- **Node's test runner** for core logic and **Playwright** for the essential browser flows.

Use an operator-run batch ingestion command for the initial release. Public users browse stored records; ingestion and Gemini batch processing do not depend on keeping an HTTP request open. No public upload or arbitrary URL-fetch endpoint is required.

Future directory structure, entirely within this idea folder:

```text
paperclip/       role instructions and custom skills
client/          React UI
server/          API and static serving
shared/          schemas and match contracts
pipeline/        extraction, location resolution, matching, loading
data/            manifests and reviewed small fixtures
tests/           calculation, extraction, API, browser checks
docs/            decisions, release instructions, track evidence
```

Raw sponsor inputs stay in the shared repository `docs/` directory. Configure an absolute `SOURCE_DOCS_DIR` when running pipeline commands so execution from a worktree does not depend on fragile relative paths.

## 7. Data contracts and provenance

| Collection | Minimum fields |
|---|---|
| `sources` | ID, utility/publisher, original URL, repository path, checksum, publication/retrieval dates, public-status review, page numbering convention, superseded source ID |
| `projects` | Stable ID, utility ID, raw owner code, raw name, normalized type, voltage, status and status-as-of, endpoints, center, location confidence, dates/precision, cost if published, source/page references, record version |
| `matches` | Sorted project IDs, their versions, analysis date, rule version, distance, schedule relationship, uncertainty, match category, rank drivers, brief and brief provenance |
| `runs` | Run ID, source hashes, extraction prompt/model/schema versions, processing counts, failures, timestamps, completion state |

Each endpoint stores name, optional GeoJSON Point, public feature ID/URL, evidence, match method, and reviewer decision. Store coordinates as `[longitude, latitude]`. Omit an unknown geometry; do not insert `(0,0)`.

Index project centers with `2dsphere`, and add ordinary indexes for utility/status/date queries. Geospatial indexes omit missing locations, so temporal-only discovery must use a separate ordinary query. [MongoDB geospatial documentation](https://www.mongodb.com/docs/manual/core/indexes/index-types/geospatial/2dsphere/)

Use a unique source checksum and a stable utility/project key. Preserve repeated project versions rather than silently replacing conflicting dates. Give matches a unique key over sorted IDs, input versions, analysis settings, and rule version. Reprocessing the same source must not duplicate records.

Date records contain the raw text, precision (`day`, `month`, `year`, `unknown`), date kind (`in_service`, `construction_start`, `construction_end`), and normalized bounds. Use UTC date arithmetic. A year-only date is a year-long uncertainty range, not a known December 31 deadline.

## 8. Matching and ranking rules

### Geography

- Two accepted endpoints: use their midpoint as described in the sponsor guide. For this GA/SC dataset, use the arithmetic mean of latitudes and longitudes, matching the starter workbook convention.
- One accepted endpoint: use it as the representative center and label the limited coverage.
- Neither endpoint accepted: keep the project searchable in the table but exclude it from confirmed spatial matches.
- Calculate haversine distance between centers with a documented Earth radius and convert consistently to miles.
- Default condition: **distance < 25 miles**, equivalent to **40,233.6 meters**. Exactly 25 miles is excluded under the guide's “under 25” wording. Record this boundary interpretation in the test cases.
- Atlas generates nearby candidates; apply the documented distance calculation for final classification and comparison with workbook values.

Center distance is the required approximation. It does not prove that long transmission corridors intersect or share right-of-way. Geometry-based corridor comparisons can be a later extension with a separate label.

### Time

For two exact in-service dates, compute the absolute day difference. A gap of at most the selected 180-day default is a timeline match. Label this “nearby in-service dates.”

For actual construction intervals, use inclusive interval overlap: the later start must be no later than the earlier end. Display overlapping days only when bounds are adequately known.

For month/year precision, calculate possible gap bounds. Classify as definite, possible, or not within the selected threshold. Missing dates remain unknown. Do not invent construction duration by subtracting an arbitrary number of months from commissioning.

### Combining and ranking

Candidates must belong to different verified utilities and have distinct stable project IDs. Default list order:

1. Verified nearby pairs with a definite time relationship.
2. Verified nearby pairs with unknown or distant schedules.
3. Tentative nearby pairs, visibly marked for review.

Within each group, sort by distance, then schedule gap when comparable, then a documented type compatibility rule and stable ID. Keep timeline-only results in their separate view. This produces explainable ranking without suggesting an unvalidated probability or dollar benefit.

### Future versus historical

Make `analysisDate` visible and reproducible. Current mode uses future or confirmed ongoing work. A source's old “in progress” status with a past planned date requires a freshness warning or updated confirmation. Keep historical results available under an explicit snapshot date. Never automatically roll dates forward.

## 9. Gemini implementation and evaluation

Gemini has two core responsibilities:

1. **Document extraction:** convert approved utility project pages into the shared schema, including names, owner codes, voltage, schedule, published costs, and supporting source references.
2. **Coordination briefs:** explain an already-computed pair using its verified evidence, possible shared resources, uncertainty, and questions a planner should resolve.

Select relevant page ranges first, preserve original page mapping, and process bounded chunks. Validate the selected model's document limits before uploading. Gemini supports document understanding and schema-constrained output, but schema compliance does not establish factual accuracy. Validate the values and citations separately. [Document processing](https://ai.google.dev/gemini-api/docs/document-processing), [structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)

Treat document text as data. Prompts embedded in a PDF must not become instructions or tool calls. Never allow an extracted URL to trigger an unrestricted fetch.

Cache by source hash, page range, model, prompt, and schema version. Retry rate-limit/transient failures with bounded backoff; preserve partial progress. Leave invalid records in a review queue with reasons.

Build a manually reviewed evaluation set spanning both utilities, multiline tables, missing dates, redacted costs, and owner ambiguity. Propose 20–30 representative project records, expanding if errors cluster. Report precision/recall for project detection and field accuracy separately. Suggested release target: at least 95% accuracy on name/owner/date for the reviewed set, and 100% source review for featured opportunities. These are targets to measure, not achieved results.

Brief generation receives immutable computed distance/time fields. Verify every numerical claim against them. On Gemini failure, render a deterministic explanation and show the brief as unavailable.

## 10. Atlas and API implementation

Create an Atlas project and appropriately sized cluster, a dedicated database, and separate database users for imports and the deployed read API. The importer can write required collections; the web service should read prepared records. Add write privileges only if an actual server feature needs them.

Configure network access for the development host and deployment egress addresses. Copy the driver connection URI and store it as a secret. Atlas management API keys are not required for ordinary driver access. [Atlas driver connection guide](https://www.mongodb.com/docs/atlas/driver-connection/)

Proposed routes:

| Route | Purpose |
|---|---|
| `GET /api/projects` | Paginated/filterable records; optional map bounding box |
| `GET /api/projects/:id` | Project details and provenance |
| `GET /api/matches` | Ranked matches with distance/time/category filters |
| `GET /api/matches/:id` | Both records, computed reasons, prepared brief, impact scenario |
| `GET /api/coverage` | Counts, location/date coverage, source freshness, exclusions |
| `GET /api/export` | Same filtered results as CSV, with formula-injection protection |
| `GET /healthz` | Service health without exposing credentials |

Bound pagination, radius, date range, and export size. Validate query inputs and whitelist sort fields. Reuse the database connection pool. Keep all database and Gemini credentials on the server or batch worker.

## 11. Paperclip setup on this repository

These steps are instructions for a later setup run. This planning task does not install services or start agents.

### A. Install and verify the local runtime

Use Node 24.11 or later to satisfy the current Paperclip installation guide. Install Claude Code and run onboarding as a normal user:

```sh
node --version
brew install --cask claude-code
claude --version
npx paperclipai onboard --yes
```

Open `http://localhost:3100`. After setup, `npx paperclipai run` starts the instance again. Record the tested Paperclip and runtime versions so later changes are deliberate. [Paperclip installation](https://docs.paperclip.ing/guides/getting-started/installation/), [Claude Code setup](https://code.claude.com/docs/en/quickstart)

### B. Create company, project, and workspace

- Company: `GridBridge — ShellHacks 2026`.
- Goal: deliver the accepted utility overlap product and evidence for the four requested tracks.
- Project: `GridBridge implementation`.
- Git remote: `https://github.com/fradicus/Shellhacks-2026.git`.
- Base branch: `main` after verifying the actual remote.
- Repository checkout: `/Users/ericzhang/VSCODE Proejcts/Hackathons/shellhacks-2026`.
- Agent working directory: `plans/plan-B/` within its assigned checkout/worktree. For this checkout, use `/Users/ericzhang/VSCODE Proejcts/Hackathons/shellhacks-2026/plans/plan-B`.

Keep Paperclip installation/state outside the application repository. Keep `docs/Sperry-Tech-Challenge/` shared and unchanged. Commit the reviewed plan and setup instructions before creating implementation worktrees; worktrees cannot inherit uncommitted files.

Use isolated Git worktrees per implementation issue. Current Paperclip exposes these through its experimental Isolated Workspaces setting. Verify a test issue lands in a distinct directory/branch before parallel work. If unavailable in the installed release, create conventional Git worktrees and set each agent's `cwd` explicitly. [Execution workspaces](https://docs.paperclip.ing/guides/projects-workflow/workspaces/)

A working directory is not a filesystem security boundary. Scope runtime permissions separately, especially for a local headless adapter. Do not share personal credentials broadly among agents.

### C. Create the CEO, then the seven reports

Use the Agents UI. Set name, role, reporting manager, adapter, instructions, and budget. Use the exact titles in section 3. The CEO reports to the human board. All seven specialists report to that CEO. [Paperclip agents guide](https://docs.paperclip.ing/guides/org/agents/)

Common adapter settings:

| Setting | Proposed value |
|---|---|
| Adapter | `claude_local` |
| `cwd` | Absolute path to this idea's directory in the selected worktree |
| Model | An available Claude coding model from the adapter picker; pin the tested ID |
| `timeoutSec` | 1200 |
| `graceSec` | 15 |
| `maxTurnsPerRun` | 30 initially |
| Provider env | `ANTHROPIC_API_KEY` bound to a Paperclip secret |
| Instructions | Common text plus role prompt from section 5 |
| Scheduled wakeups | Disabled initially |
| Work wakeups | Assignment/manual invocation; mentions only when useful |

Use the same tested model initially. Upgrade the technical lead for difficult review only if needed. Run **Test Environment** for every agent to verify command, directory, authentication, and model. Secret references are supported in the adapter configuration. [Claude adapter reference](https://docs.paperclip.ing/reference/adapters/claude-code/)

Create roles directly as the board during initial setup; there is no need to have the CEO repeatedly request these same hires. Start with a single read-only smoke issue asking the CEO to identify its directory, plan, and next issue. Confirm it can update the Paperclip issue before assigning implementation.

### D. Attach skills and secrets

Author/import the section 4 skills and attach only the relevant set. Bind application development credentials only to agents performing live integrations. Give the frontend engineer example responses and a restricted map key, not an Atlas admin credential.

Store credentials in Paperclip's secret store for agent runs and the hosting platform's secret environment for the deployed app. Back up the Paperclip instance and its encryption key together. [Paperclip secrets](https://docs.paperclip.ing/reference/deploy/secrets/)

### E. Budgets and heartbeat policy

Illustrative development-agent allocation, **not spending authorization or a cost forecast**:

| Agent | Example budget |
|---|---:|
| CEO | $8 |
| Technical lead | $18 |
| Researcher | $10 |
| Gemini engineer | $18 |
| Geospatial engineer | $14 |
| Frontend engineer | $14 |
| QA | $12 |
| Release engineer | $6 |
| **Total** | **$100** |

Set an appropriate company/agent budget in Paperclip. Start with assignment-driven work and review spend after the first complete task. A 30–60 minute CEO check can be added during active development; avoid repeatedly waking idle workers. Paperclip records agent costs and exposes budget controls. [Costs and budgets](https://docs.paperclip.ing/guides/day-to-day/costs/)

Application Gemini calls, hosting, domain registration, and map usage have separate billing. Provider quotas and alerts need separate configuration; an alert alone is not a guaranteed hard spending cap.

## 12. API keys, credentials, and permissions

For the recommended setup, obtain **two private API keys, a MongoDB connection credential, and a restricted browser map key**. GitHub and hosting authentication are also needed, but can use account-based authorization instead of manually created API tokens.

| Credential | Required for | Where to get it | Who receives it |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Recommended API-billed Claude agent runtime | Anthropic Console API keys | Paperclip agent runtime only |
| `GEMINI_API_KEY` | Actual product extraction and briefs | Google AI Studio API keys | Gemini engineer, controlled integration jobs, production only if it makes Gemini calls |
| `MONGODB_URI` | Atlas application database connection | Atlas Connect → Drivers, with dedicated database user | Backend/import integration; appropriate read-only URI in deployed service |
| `VITE_MAPTILER_KEY` | Chosen hosted basemap | MapTiler account keys | Frontend build; restrict allowed origins |
| GitHub login / fine-grained `GH_TOKEN` | Push branches and create/review PRs | GitHub CLI login or repository-scoped token | Agents performing GitHub operations |
| Render GitHub connection | Deploy repository | Render dashboard authorization | Release operator |
| `RENDER_API_KEY` | Optional automated deployment management | Render account API keys | Release agent only, if automation is chosen |
| Domain registrar account | Register qualifying domain and edit DNS | MLH's GoDaddy Registry offer | Human domain owner; API key unnecessary for dashboard setup |
| Paperclip run credential | Agent issue coordination | Supplied/managed by Paperclip | Assigned agent runtime; never application frontend |

Google recommends keeping Gemini keys out of browser code and source control. Use `GEMINI_API_KEY` only in the server/batch environment. [Gemini key setup](https://ai.google.dev/gemini-api/docs/api-key)

The MapTiler key is intentionally used in the browser and should be restricted to the local development and published application origins. It is not a substitute for keeping private keys server-side. [MapTiler key restrictions](https://docs.maptiler.com/guides/credentials/api-key/)

Use GitHub permissions limited to this repository: contents and pull requests for builders, issues only if GitHub issue operations are used. Add workflow permissions only to the role that edits CI. Paperclip issues remain the primary task tracker.

**Not required:** a GoDaddy API key for manual registration/DNS, an Atlas administration API key for driver access, a paid geocoding key for reviewing cached public infrastructure features, or a separate cloud credential merely to call Gemini through AI Studio.

Claude subscription authentication is an alternative to the Anthropic API key when supported by the installed adapter/account. Choose and test one runtime auth method. The application still needs its Gemini credential.

Example future environment template, containing placeholders only:

```dotenv
# Private server / ingestion settings
GEMINI_API_KEY=<secret>
GEMINI_MODEL=<tested-available-model-id>
MONGODB_URI=<secret-driver-uri>
MONGODB_DB=gridbridge
SOURCE_DOCS_DIR=<absolute-path-to-shared-docs>

# Public frontend setting
VITE_MAPTILER_KEY=<origin-restricted-map-key>

# Ordinary configuration
ANALYSIS_DATE=2026-09-26
DISTANCE_THRESHOLD_MI=25
DATE_GAP_DAYS=180
PORT=3000
```

Keep actual `.env` files out of Git. Paperclip agent secrets do not automatically populate Render; bind deployment values separately. Never put Gemini, Atlas, GitHub, or runtime provider credentials in a `VITE_` variable.

## 13. Location data workflow

Start with the sponsor's named endpoints and known example coordinates, treating workbook locations as candidates to verify. Query/cache public OSM power features in the relevant region. Match on name plus owner, voltage, county, and topology clues. Preserve the feature ID, retrieval date, and license attribution.

Review every location featured in the final top opportunities. Ambiguous names should produce multiple candidates or an unresolved record. A town centroid is a regional estimate, not a confirmed substation.

Use cached regional data and bounded Overpass requests. Handle timeouts and missing operator tags. Avoid one external lookup per project per page load.

The sponsor guide mentions public Nominatim. If chosen for occasional manual lookups, its policy requires identifiable requests, caching, attribution, and an absolute maximum of one request per second; bulk and recurring use have stricter limits, and client autocomplete is prohibited. This plan does not depend on automated public Nominatim geocoding. [Nominatim policy](https://operations.osmfoundation.org/policies/nominatim/)

## 14. Impact scenario

Use one editable mobilization/freight scenario for an accepted pair:

`estimated avoided cost = avoided mobilizations × assumed cost per mobilization − extra coordination/transfer costs`

Display each input, units, provenance, and low/base/high assumptions. If evidence does not support sharing labor or equipment, say what would need confirmation before applying the scenario. Temporal proximity may mean competition for the same resources rather than savings.

The supplied transcript explains why freight and crew sequencing matter, but its anecdotes are not measured costs for the matched projects. Do not apply a quoted percentage to every project. Do not estimate shared land acreage from center distance alone.

## 15. Paperclip issue sequence

Create these as issues, retaining dependencies. Each issue should include owner, inputs, expected files/artifact, acceptance check, and a bounded work scope.

| ID | Issue | Owner | Depends on | Acceptance |
|---|---|---|---|---|
| P01 | Confirm source versions, disclosure status, and owner mapping | Researcher | — | Approved source manifest and explicit unresolved items |
| P02 | Freeze schemas, API contract, and folder ownership | Technical lead | — | Versioned contracts covering unknowns and date precision |
| P03 | Scaffold this idea's application and CI | Technical lead | P02 | Build/lint/basic test commands run |
| P04 | Create independent reference records and distance/date cases | QA | P01, P02 | Reviewed fixtures with source locations and expected results |
| P05 | Implement Gemini extraction with validation | Gemini engineer | P01–P04 | Both utilities parsed; evaluation report and review queue |
| P06 | Resolve endpoint locations | Geospatial engineer | P05 | Evidence-backed locations plus unresolved list |
| P07 | Implement spatial/time matches, ranking, and impact inputs | Geospatial engineer | P04, P06 | Boundary tests pass; deterministic results |
| P08 | Atlas collections, imports, indexes, API | Technical lead | P03, P05 | Idempotent load and indexed query evidence |
| P09 | Build map/list/detail UI against contract | Frontend engineer | P02, P03 | Essential flows work with clearly marked test fixtures |
| P10 | Produce cited Gemini briefs | Gemini engineer | P07, P08 | Computed claims preserved; failures handled |
| P11 | Integrate real data, filters, exports, coverage | Frontend engineer | P07–P10 | Real API drives every visible result |
| P12 | Independent data and end-to-end verification | QA | P11 | Featured pairs verified; blocking failures resolved |
| P13 | Deployment and qualifying domain | Release engineer | P03; release requires P12 | Reviewed commit deployed; DNS/TLS/health checked |
| P14 | Live QA and release evidence | QA | P13 | Public URL verified on desktop/mobile |
| P15 | Submission package for all four tracks | CEO + release engineer | P14 | Accurate write-up, architecture, evidence, attribution |

Domain availability and event eligibility checks can begin early while implementation proceeds. Registration and paid hosting remain actions for the later execution phase, under the user's then-authorized account and spending scope.

Suggested work order for a hackathon: first establish data viability and contracts, then extraction/location/matching, then integration, and reserve the final quarter of available time for verification and release. Remove optional chat, route optimization, vector search, and extra utilities before cutting provenance or correctness.

## 16. Verification checklist

- Recompute the starter workbook's pairs from its coordinates and dates; compare within an explicitly chosen rounding tolerance. Investigate discrepancies rather than treating every supplied derived value as infallible.
- Test 24.999, 25.000, and 25.001 miles; zero distance; missing endpoints; reversed coordinates; and same-utility exclusions.
- Test month/year-only dates, leap years, missing dates, reversed intervals, and historical status handling.
- Confirm every pair appears once and an unchanged re-import is idempotent.
- Ensure an unknown location remains in temporal/table views and is absent from confirmed spatial results.
- Test malformed Gemini output, nonexistent citations, rate limits, and a complete Gemini outage.
- Verify owner codes from Georgia ITS tables, especially records not explicitly labeled GPC.
- Verify map/table selection, filters, export agreement, keyboard use, loading/error/empty states, and small screens.
- Check secrets are absent from Git, browser bundles, API responses, and ordinary logs.
- Measure query and map response time on the actual imported dataset and report counts and conditions.
- Use a held-out set for extraction evaluation after prompt tuning. Verify all submission examples manually.

## 17. Deployment and domain

Deploy one Render Node web service rooted at this idea's application directory. The implementation should provide `npm ci`, `npm run build`, and `npm start`; these scripts are planned and do not yet exist. The server must bind to the hosting-provided `PORT` and serve the built client. Keep ingestion a separate operator command.

Connect Render to the repository, select the reviewed branch/commit, configure environment variables, and check `/healthz`. Add Render's published outbound addresses to the Atlas network access list. Keep deploy logs free of secret values. [Render Node deployment](https://render.com/docs/deploy-node-express-app), [outbound IP addresses](https://render.com/docs/outbound-ip-addresses)

Choose a memorable domain through the event's qualifying GoDaddy Registry offer. `GridBridge` is only a working brand; availability and eligibility have not been checked. A domain sold by the GoDaddy registrar does not by itself establish eligibility for a GoDaddy Registry promotion.

Follow the [MLH prize page's GoDaddy Registry link](https://www.mlh.com/events/prizes) and confirm the current event offer, eligible extensions, redemption terms, and renewal price. Add the purchased domain to Render, copy its exact DNS instructions to the registrar, and verify HTTPS and the canonical URL. [Render custom domains](https://render.com/docs/custom-domains)

Retain the last accepted deployment and dataset version. Rollback consists of redeploying that commit and selecting the corresponding data version; do not run destructive imports during a web deployment.

## 18. Track evidence and submission plan

| Track | Product contribution | Evidence to prepare |
|---|---|---|
| **Sperry Tech** | Two utility plans, primary geographic matching, meaningful schedule comparison, interactive map, ranked opportunities, optional impact scenario | Named sources, reviewed pair examples, rules, data coverage, screenshots, reproducible calculations |
| **Gemini API** | PDF understanding/structured extraction and cited coordination briefs | Actual API integration, model/prompt versions, input/output examples, extraction evaluation, failure handling |
| **MongoDB Atlas** | Persistent project/provenance records and geospatial discovery | Atlas deployment, `2dsphere` index, query/explain evidence, real API responses with credentials hidden |
| **GoDaddy Registry** | Memorable qualifying domain hosting the usable application | Registration/offer eligibility evidence, resolving domain, HTTPS, branding explanation |

Using an AI coding agent alone does not demonstrate the application's Gemini feature. Merely opening an Atlas account does not demonstrate database integration. Prepare evidence of actual product behavior.

The local prize document and public MLH page can differ in prize descriptions. Treat ShellHacks staff and the event-specific redemption/submission rules as the authority for eligibility. Do not promise credits, free registration, or a particular prize without confirming them.

For background, FERC Order 1920 addresses long-term regional transmission planning and cost allocation. Describe this application as a coordination discovery tool; do not claim it certifies regulatory compliance. [FERC transmission information](https://ferc.gov/electric-transmission)

## 19. First CEO assignment

Paste this after the company, agents, instructions, skills, and credentials have been set up:

> Read this implementation plan and the shared sponsor challenge and location guide. Verify your working directory belongs to this idea. Create P01–P15 as Paperclip issues with the documented owners, dependencies, and acceptance checks. Assign P01 and P02 first. Require an approved public-source manifest before any document upload to Gemini. Establish the analysis date and keep historical examples labeled. Do not change the other idea's files. Report the initial issue graph, source blockers, selected runtime/model versions, and available budget before starting dependent implementation.

This document completes planning. Installation, skill authoring/import, cloud account configuration, domain purchase, and application implementation are the next execution phase.
