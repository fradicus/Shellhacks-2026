---
name: "GridBridge"
description: "Public utility overlap evidence and coordination roadmap for four ShellHacks tracks."
owner: "technical-lead"
---

# GridBridge project charter

This is the self-contained build contract for the imported company. Plan B is the preferred foundation. The human must authorize kickoff; import does not start the build. Source docs are read-only and implementation files belong under `plans/plan-E/implementation/`. Do not read Plan D.

## Seed dependency graph

Dependencies in task bodies are the portable source of truth. CEO resolves the following slugs to imported issue IDs and creates native blocked-by relationships at kickoff. Tasks may exchange reviewed intermediate artifacts, but downstream completion still requires accepted prerequisites. At most three assignments are active. `deploy` has an early preparation phase and a later publication gate; record acceptance and human authorization before publishing even though preparation starts early.

| Task | Owner | Prerequisites |
|---|---|---|
| `kickoff` | `ceo` | Human kickoff approval |
| `contracts` | `technical-lead` | `kickoff` |
| `source-audit` | `data-researcher` | `kickoff` |
| `golden-reference` | `qa-verifier` | `kickoff` |
| `gemini-extraction` | `gemini-engineer` | `contracts`, `source-audit` |
| `extract-register` | `data-researcher` | `gemini-extraction` |
| `resolve-locations` | `geo-engineer` | `extract-register` |
| `match-pairs` | `geo-engineer` | `resolve-locations`, `golden-reference`, `contracts` |
| `atlas-api` | `technical-lead` | `contracts` |
| `map-ui` | `frontend-engineer` | `contracts` |
| `gemini-briefs` | `gemini-engineer` | `match-pairs`, `gemini-extraction` |
| `filing-diff` | `data-researcher` | `source-audit`, `extract-register` |
| `integrate` | `technical-lead` | `atlas-api`, `map-ui`, `match-pairs`, `gemini-briefs`, `filing-diff` |
| `acceptance` | `qa-verifier` | `integrate` |
| `deploy` | `release-engineer` | `contracts` |
| `live-check` | `qa-verifier` | `acceptance`, `deploy` |
| `submission` | `ceo` | `live-check` |

## Build contract

## 2. Scope roadmap — ambitious, with a buildable first release

The goal is a planning intelligence product, not just a six-pair map. Treat the 36-hour release as its first credible milestone. Plan B supplies the product direction; the stages below explain what we promise, what we aim for, and what needs more time or evidence. Stage targets are not claims that these features already exist.

| Stage | Experience / ambition | Dependency and release gate | Owner |
|---|---|---|---|
| **R0 — Trust the result, hours 0–8** | A judge can trace the exact sample results back to endpoints and dates. Approved source manifest, owner mappings, contracts, Atlas and first Gemini extraction work. | Six exact matches, 19 exclusions; no ambiguous pages enter Gemini; Atlas read/write and model call succeed. | Lead + QA + data |
| **R1 — Competition core, hours 8–20** | Browse two utilities, find geographic overlaps, inspect source evidence, see grounded Gemini work and export a coordination card. Public corpus extends beyond the sample. | Core definition of done, reviewed featured records, source coverage ledger, current/historical separation. | Geo + Gemini + frontend |
| **R2 — Ambitious hackathon target, hours 14–24** | A **plan-change watchlist** shows the verified DESC date change and whether changed inputs alter a pair's priority. A **coordination scenario drawer** lets a planner choose alternative in-service milestones, preview resulting day gaps and compare optional sourced mobilization assumptions without overwriting the published plan. A **coverage explorer** reveals where missing locations prevent analysis. | R1 integrated by hour 18; QA validates original vs scenario labels, version attribution and deterministic recomputation. New UI freezes at hour 24. | Data + geo + frontend, lead integrates |
| **R3 — Exceptional stretch, only if R2 passes by hour 22** | Add a third verified utility from approved public tables and compare every selected cross-utility pair; group pairwise opportunities into a meeting agenda. Show an on-demand refresh preview with added/changed/removed project versions. | Owner/source review completed; no changes to the canonical pair rule; bounded workload and QA available before freeze. At hour 22 choose at most one stretch feature. | CEO selects; data + lead + QA |
| **R4 — Product after the event** | Scheduled filing monitoring, a user-approved notification digest, corridor geometry alongside sponsor centers, actual construction-window evidence, resource compatibility and multi-project schedule/cost optimization. Planners review changes and collaborate with an audit trail. | Reliable ingestion over multiple refreshes; public geometry and real schedule/resource evidence; account/permission model; validated assumptions and user research. | Future roadmap; not seeded as hackathon tasks |

### What makes the ambition useful

- **Changes should change decisions.** The watchlist ties a source revision to the affected project, stored matches and ranking. A verified old/new date is useful even when the example is historical; no claim of a current delay or coordination opportunity is implied.
- **Scenarios should be reversible and visibly hypothetical.** Published dates stay immutable. A planner-entered hypothetical milestone recomputes the same absolute day-gap formula, with an “Assumption” label and reset control. This tests sensitivity; it does not propose an achievable construction schedule. Optional dollar arithmetic uses only the stated impact formula and sourced/user-entered inputs.
- **Scale should expose uncertainty.** More utilities and documents increase the opportunity set, but unresolved ownership, CEII status and locations remain in the coverage ledger. The watchlist must not quietly turn extraction guesses into accepted facts.
- **A meeting agenda is not proof of joint feasibility.** A group of related pairwise matches may contain projects more than 25 miles apart from each other. Show every supporting pair and its own distance; never imply all members qualify as one geographic overlap.

The executable acceptance scope is R0–R1 plus the verified filing comparison. R2 is the desired competition finish, with explicit gates; R3 is one optional stretch. R4 supplies the larger product story. The hour-by-hour plan protects a usable release while giving the team a concrete ambitious target.

## 3. What the judges use

### Four screens, one coherent workflow

**Overview:** utility selectors, explicit analysis date, future/historical toggle, source versions and coverage counts. Default production view requires two verified owners, reviewed locations and exact in-service dates on or after the analysis date. Unknown-date and tentative-location records remain available under clearly labeled filters. Historical fixture mode is separate and conspicuous.

**Map and ranked list:** two utility colors, project centers, selected pair connector, mileage and date-gap columns. Map selection and table selection stay synchronized. A connector represents center-to-center distance, not a transmission route. Filters narrow existing geographic overlaps; they never turn distant projects into overlaps. An accessible table works when map tiles fail.

**Evidence drawer:** original names, native IDs, raw owner codes, both endpoints, accepted/rejected location evidence, source document/page, raw date text, precision, project versions and supersession. Unknowns read “Not published” or “Needs review.” Show one-endpoint centers explicitly. Review decisions include author, reason and time.

**Coordination card:** deterministic pair facts, Gemini's supported summary, source-linked possible shared activities and unanswered questions. Export projects and overlaps as CSV plus a printable card. Optional impact inputs are labeled user scenarios, never claimed realized savings. A compact old/new filing comparison lives in the drawer, not a separate large product.

### Definition of done

- Map and list compare real records from at least two verified utilities, including DESC and Georgia Power when approved GPC evidence is available.
- The untouched sample produces exactly OVL_1–OVL_6, their distances and gaps; all other 19 cross-utility pairs are excluded.
- Production records preserve real owner codes. A GPC PDF containing SAV or GTC records does not make those projects Georgia Power.
- Every featured non-sample pair is independently reviewed from approved public evidence. Sparse results are acceptable; fabricated results are not.
- Atlas is the active database behind the deployed UI. Gemini performs real extraction and visible coordination work.
- CSV, evidence, empty states, service failure states and the main keyboard flow work.
- Human confirms the event's final rules and domain eligibility, obtains the domain, and authorizes publication/submission. HTTPS and track evidence are then checked during implementation.

## 4. Source policy and research scope

Read the challenge, location guide, workbook, both supplied utility PDFs, intern listing, `docs/context/hackathon-prizes.md` and `docs/context/transcript.txt`. They remain read-only. Plans A/B/C inform design; none supplies authoritative utility facts.

The Georgia PDF has 668 pages and a December 2024 planning snapshot. Some relevant pages have both PUBLIC DISCLOSURE and CONFIDENTIAL CEII markings. **Quarantine mixed-marking pages before model upload, extraction into the product, or excerpt publication.** A publicly accessible URL does not override the sponsor's CEII exclusion. Use unambiguously public utility/SERTP alternatives; the human source owner resolves any ambiguous permission. Do not reverse redactions or infer private infrastructure. The sample itself is the sponsor-authorized regression fixture, not proof that every referenced PDF page may be uploaded.

Research order:

1. Hash and inventory supplied inputs, page numbering conventions and public-status decisions.
2. Review the full supplied DESC list and the newer 2025–2029 public list. Track stable native IDs across versions; never double-count them.
3. For Georgia, inventory all approved expansion-table rows first. Prioritize projects explicitly mentioning Augusta, Evans, Savannah, McIntosh, Purrysburg, Goshen or the SC border; retain the full denominator so this bounded search cannot be sold as exhaustive statewide coverage.
4. Verify owner-code mappings against the source legend or an official public owner record. Unknown owners remain unresolved. The sample labels remain unchanged for golden regression; a separate production attribution table records corrections. In particular, sample GPC_2/GPC_3 have SAV-prefixed names.
5. Locate endpoint candidates using official public maps and public OSM features; assess name, voltage, county, owner and nearby landmarks together. Never accept coordinates from a name-only search or Gemini assertion. Keep source feature IDs, retrieval dates and rejected candidates.
6. Seek approved newer Georgia data through the [Georgia Power IRP page](https://www.georgiapower.com/about/company/filings/irp.html) and [SERTP reference library](https://www.southeasternrtp.com/reference_library.cshtml). A newer DESC Hooks–Modoc card (`6809 G`, page 11, December 31, 2027) is a research lead, not an asserted match.

If approved current Georgia sources cannot be found by hour 12, flag this to the human and narrow to available approved records. Retain the historical sample as a labeled demonstration of calculations. Report the unresolved two-utility future-data requirement rather than imply success.

No automated public Nominatim dependency. Respect [its usage policy](https://operations.osmfoundation.org/policies/nominatim/) for any manual assistance; cache permitted lookups. No restricted grid datasets are needed. No arbitrary public upload or URL-fetch endpoint.

## 5. Exact calculations and ranking

### Sponsor overlap rules — version `sperry-center-v1`

An endpoint is located only when both its latitude and longitude are accepted. With two located endpoints, center = arithmetic mean latitude and arithmetic mean longitude. With one, center = that endpoint. With none, center is unknown and the record cannot enter spatial matching. This GA/SC midpoint convention reproduces the sponsor sheet; it is not a route geometry algorithm.

For centers in radians:

```text
h = sin²((lat2-lat1)/2) + cos(lat1) * cos(lat2) * sin²((lon2-lon1)/2)
distance_mi = 2 * 3958.8 * asin(sqrt(clamp(h, 0, 1)))
overlap = different verified utilities AND known centers AND distance_mi < 25
time_gap_days = abs(date2 - date1).days       # exact in-service calendar dates only
```

Use unrounded distance for classification and sorting; round only display/export to two decimals. Exactly 25 miles is excluded. Missing dates do not remove a geographic overlap. Missing or month/year-only dates produce a null exact day gap and retain their raw text and precision. Do not impute January 1 or December 31. A future filter requires exact dates for its confirmed view; uncertain dates get a separate review view. In-service milestones are not construction intervals.

For the initial corpus, calculate every cross-utility pair after filtering active project versions. Atlas's spatial index supports map queries and future candidate acceleration, but cannot substitute its own distance convention for this golden calculation. This avoids candidate-query rounding or radius differences losing edge cases. Sort project IDs canonically and include input versions, analysis date and rule version in each stored match key.

### Product priority — version `nearby-band-v1`

No invented probability or weighted composite score. First select the user's view (reviewed future, historical or tentative). For eligible geographic pairs, sort by:

1. Distance band: 0 for under 10 miles, 1 for 10 to under 25 miles.
2. Exact in-service gap ascending; unknown gaps last within their band.
3. Unrounded distance ascending, then canonical pair ID.

Ten miles is an explicit product prioritization assumption; it does not change the sponsor's 25-mile rule. The band makes geography primary while allowing time to distinguish similarly local projects. Display both drivers so a planner can disagree. A separate “distance order” control reproduces the sheet's presentation.

### Optional impact

Potential mobilization saving = `avoided_mobilizations * sourced_unit_mobilization_cost - coordination_and_transfer_cost`. Each input needs a user-entered scenario label or an actual cited estimate; absent inputs produce null dollars. Negative results remain negative. Every sample row returns null because the workbook supplies none of these inputs. The contractor's $1.5M freight on one $5M job is an anecdote, not a transferable ratio. No copying a known DESC cost into an unknown GPC field. If credible inputs are unavailable, ship qualitative shared-activity questions and explain the missing cost data.

### Executed sample output

The independent plan verifier reads the XLSX directly, including mixed string and Excel-serial dates, recomputes centers and all 25 pairs, and checks the workbook's pair IDs, labels, overlap counts, rounded distances and exact gaps.

| Workbook ID | Project A | Project B | Miles | Gap in days | Product priority |
|---|---|---|---:|---:|---:|
| OVL_1 | DESC_2 | GPC_1 | 4.09 | 3074 | 3 |
| OVL_2 | DESC_3 | GPC_2 | 5.65 | 152 | 1 |
| OVL_3 | DESC_3 | GPC_3 | 7.55 | 517 | 2 |
| OVL_4 | DESC_1 | GPC_1 | 8.01 | 3074 | 4 |
| OVL_5 | DESC_5 | GPC_2 | 14.34 | 365 | 5 |
| OVL_6 | DESC_5 | GPC_3 | 14.81 | 730 | 6 |

All six impact estimates are null. Golden mode keeps supplied utility labels and dates intact; it does not promote fixture coordinates or historical milestones into independently verified future opportunities. Actual run details are in the repository Plan E verification report.

## 6. Architecture and data contract

```text
Approved PDF page manifest --> Gemini extraction --> schema validation --> human/QA review
Public endpoint evidence -----------------------------------------------> location review
                                              |
Python batch pipeline: centers, exact haversine, day gaps, versioned pairs
                                              |
MongoDB Atlas: sources / projects / matches / runs / reviews / briefs
                                              |
Next.js server routes + native MongoDB driver + server-side Gemini briefs
                                              |
React UI + MapLibre + OpenFreeMap --> HTTPS application + qualifying domain
```

**One Next.js application**, TypeScript and schema validation; **one Python batch pipeline** for PDF processing and deterministic matching. This retains B's contracts and workflow while avoiding a separate Express deployment and leveraging A's PDF approach. Shared JSON Schemas and canonical fixtures bridge Python and TypeScript; one canonical Python matcher produces stored results, and the browser never independently decides eligibility. The technical lead owns schema and lockfile changes. Pin tested dependencies during implementation.

Use the supported Google Gen AI SDK in each environment that calls Gemini. Choose an available stable model with tested PDF and structured-output support, store its exact ID in `GEMINI_MODEL`, and record prompt/schema/model versions per run. No speculative model name is embedded in the package. [Gemini document processing](https://ai.google.dev/gemini-api/docs/document-processing), [structured output](https://ai.google.dev/gemini-api/docs/structured-output).

| Collection | Essential fields and indexes |
|---|---|
| `sources` | Publisher, URL/local path, SHA256, published/retrieved dates, page numbering, public-status decision, supersedes ID; unique hash. |
| `projects` | Stable owner/native ID, source version, original name, owner code/mapping evidence, type/voltage if published, status/as-of, endpoints and evidence, center, date raw/value/precision/kind, optional cited cost, review state; unique stable ID + version. |
| `matches` | Canonical project IDs and versions, rule/rank version, analysis date, unrounded distance, exact gap or null, band, evidence refs; unique inputs/settings key. |
| `runs` | Source hashes, model/prompt/schema versions, started/completed state, extracted/rejected counts, retry/failure log, active dataset version. |
| `reviews` | Record/field, old/new value, evidence, reviewer, reason, timestamp; append-only decisions. |
| `briefs` | Pair input hash, model/prompt version, structured output, cited fact IDs, review result, generated time; invalidate when inputs change. |

GeoJSON is `[longitude, latitude]`; omit unknown geometry, never store `(0,0)` as a missing value. Use a `2dsphere` center index for viewport queries plus ordinary owner/date/version indexes. Null-location records remain searchable through ordinary table queries. [Atlas connection](https://www.mongodb.com/docs/atlas/driver-connection/), [geospatial index](https://www.mongodb.com/docs/manual/core/indexes/index-types/geospatial/2dsphere/).

Stage each ingestion run and switch the active dataset pointer only after validation. Repeated source hashes and stable project versions upsert idempotently. Preserve old versions for the filing comparison; do not merge two unrelated projects because their normalized names resemble each other.

Minimum routes: read-only projects, matches, pair detail and CSV; protected server-side brief generation using stored approved pair IDs. Reject arbitrary source URLs, raw database operators and unbounded queries. Bound pagination, validate filters and escape CSV formula prefixes. The public deployment serves cached reviewed briefs; live regeneration is operator-only and rate limited. A local operator CLI sends `OPERATOR_API_TOKEN` in the Authorization header to the protected route; the browser only reads the resulting approved brief. Compare tokens safely, reject missing/invalid tokens, and never log the header. MongoDB credentials and Gemini keys never enter client bundles. Use a pooled server connection; run batch ingestion outside HTTP requests. Gemini failure leaves the deterministic results usable; Atlas failure shows an explicit unavailable state rather than silently claiming cached data is live.

Deployment target: one Vercel project with the Next.js directory as its root; Python ingestion runs on the operator's machine. Configure Atlas network access for the actual runtime egress before release; if the selected Vercel plan cannot offer an acceptable route, release engineer selects a documented host with fixed outbound IP and validates it by hour 4. Do not make `0.0.0.0/0` the default. Hosting network feasibility is a real launch gate. [Next.js hosting](https://vercel.com/docs/frameworks/full-stack/nextjs), [Atlas access list](https://www.mongodb.com/docs/atlas/security/ip-access-list/).

## 7. Gemini work judges can inspect

**Extraction:** source researcher first approves page ranges. Gemini engineer renders or segments those pages, preserves original page mappings and asks Gemini for schema-constrained projects with field-level source references. Preserve raw quotes and nulls; the model cannot invent locations, owner mappings or costs. Validate types, evidence snippets, IDs and dates; quarantine mismatches for review. Retry transient failures with bounded backoff and a maximum of two retries; persistent failures become review items. No unrestricted PDF chat.

**Coordination briefs:** provide only accepted project evidence and the deterministic match object. Structured output has `supported_facts`, `possible_shared_activities`, `questions`, `limitations`, and citations to supplied fact IDs. Reject new numbers, unsupported owner/date claims and missing citations. Label suggestions as possibilities. Review every brief featured in judging. Treat document text as data, never as instructions to tools.

**Evaluation:** build a reviewed reference set of 12 approved project rows spanning both utilities, missing fields and different table/card layouts. Report counts of correct values and supported citations by field with denominators; preserve failures. Compare extraction against human labels, not the model's own self-score. Test a prompt-injection passage, a bad citation and a service failure. These are future implementation acceptance checks; they were not run for this plan.

A judge sees the original approved page, the actual Gemini response and its accepted/rejected fields, then clicks a pair to read a source-linked brief. Capture model ID, timestamp and request/result metadata without the key. Stored results are labeled with their generation time.

## 8. Agents, jobs and skills

Keep B's eight roles. All seven specialists report to the CEO; the technical lead controls integration and contracts. QA remains independent. Eight configured agents means at most three active assignments and one run per agent.

```text
CEO / Product Lead
  ├── Technical Lead / Backend & Atlas
  ├── Utility Data Researcher
  ├── Gemini / Document Engineer
  ├── Geospatial / Matching Engineer
  ├── Frontend / UX Engineer
  ├── QA / Data Verification
  └── Release / Submission Engineer
```

All agents receive `gridlock-rules`, `paperclip-work`, and `git-delivery`. Each is a real local SKILL.md in the package. Additional skills and ownership:

| Slug / job | Owned work and handoff | Additional skills | Suggested agent budget |
|---|---|---|---:|
| `ceo` | Scope, dependency links, resource limits, track acceptance, human decisions; releases ready tasks only. | `track-submission` | $10 |
| `technical-lead` | Contracts, Atlas/API, dependencies, integration; publish fixtures early to unblock UI and pipeline. | `atlas-api`, `overlap-analysis`, `qa-acceptance` | $25 |
| `data-researcher` | Public-source manifest, owner mappings, reviewed rows, current filings and version diff. | `source-audit`, `pdf-extraction`, `location-review` | $20 |
| `gemini-engineer` | Approved-page extraction, schema/citation validation, model evaluation and briefs. | `pdf-extraction`, `gemini-evidence` | $20 |
| `geo-engineer` | Endpoint decisions, centers, matcher, priority and impact scenario. | `location-review`, `overlap-analysis` | $20 |
| `frontend-engineer` | Map/list/detail, visible Gemini work, CSV interaction, accessibility and failure states. | `map-workbench` | $20 |
| `qa-verifier` | Independent golden checks, featured-record audit, integration/service/security checks; blocks false claims. | `source-audit`, `gemini-evidence`, `overlap-analysis`, `atlas-api`, `map-workbench`, `qa-acceptance` | $15 |
| `release-engineer` | Hosting/network/secrets, domain handoff, CI/release smoke tests, rollback and submission artifacts. | `release-domain`, `track-submission`, `qa-acceptance` | $10 |

Budgets total **$140**, an example ceiling subject to the operator's chosen spend limit, not a purchase authorization. Reserve a separate proposed $10 application Gemini cap; provider billing is separate from Paperclip's agent budget. Hosting/domain costs require actual quotes and human selection. Paperclip budgets are monthly; using a new company isolates this event's recorded spend. Monitor provider quotas and subscription accounting separately. Reduce scope at 75% of the chosen ceiling. [Paperclip costs](https://docs.paperclip.ing/guides/day-to-day/costs/).

The lead's combined API/integration load is controlled by shipping the contract first, using native driver operations, and delegating all infrastructure and release work. No agent adds frameworks or changes shared schemas without the lead's review.

### Work ownership in the future build

Use `plans/plan-E/implementation/` under the repository worktree. No implementation files are created now.

| Owner | Directory |
|---|---|
| Lead | `web/app/api/`, `schemas/`, dependency manifests/lockfiles, integration notes |
| Frontend | `web/app/` excluding `api/`, `web/components/` |
| Data | `data/manifests/`, `data/review/`, `data/versions/` |
| Gemini | `pipeline/extract/`, `web/lib/gemini/` |
| Geo | `pipeline/locations/`, `pipeline/matches/` |
| QA | `tests/`, `reports/` |
| Release | `release/`, `submission/` |
| CEO | `decisions/` |

Agents use separate worktrees/branches when available; otherwise enforce the ownership table and one integration writer. Issue handoffs contain exact file/commit references, test commands/results and next owner. During this planning task no branches or commits are created.

## 9. Accounts, API keys and configuration

An account is not automatically an API key. No keys are included in this package. Store actual secrets in Paperclip's secret store and hosting environment, never Markdown, issue comments, prompts, screenshots or browser variables. [Paperclip secrets](https://docs.paperclip.ing/reference/deploy/secrets/).

| Account / variable | Required? | Where and how to obtain | Who uses it / scope |
|---|---|---|---|
| Paperclip local board account | Yes | Install and onboard; save local operator login. | Human manages company. Runtime supplies agent-scoped `PAPERCLIP_API_KEY` and context; do not invent a shared admin key. |
| Claude Code auth; `ANTHROPIC_API_KEY` if API billing | One supported authentication method required; API key optional with supported logged-in subscription | Follow [Claude Code quickstart](https://code.claude.com/docs/en/quickstart); authenticate the host CLI or create an Anthropic API key through that account. | All eight coding agents through `claude_local`; choose and test an available model. This is separate from product Gemini. |
| Google AI Studio account and `GEMINI_API_KEY` | Yes for Gemini track | Create a project/key through [Gemini key setup](https://ai.google.dev/gemini-api/docs/api-key); enable required billing/quota. | Gemini engineer's extraction process and protected web server. QA examines redacted logs; no key needed for frontend or CEO. |
| `OPERATOR_API_TOKEN` | Required for protected live generation/mutation routes | Human generates a random application secret using a password manager (at least 32 random bytes); no provider account needed. | Server validates a bearer token; lead tests protection and the operator invokes generation from a local CLI. Never embed it in the public UI or export it in a URL. |
| Atlas account, cluster and `MONGODB_URI_RW` | Yes | Create Atlas project/cluster, database user restricted to this app database, permitted network route, then obtain driver connection URI. [Connection guide](https://www.mongodb.com/docs/atlas/driver-connection/) | Lead and controlled ingestion process. Used to load records and persist briefs/reviews. URI includes database password; it is a secret, not an Atlas management key. |
| `MONGODB_URI_RO` | Yes for production reads and QA | Separate database user with read access only to this database, same connection setup. | Web read routes and QA; release operator binds it to host. Use RW only for protected mutations. |
| GitHub account and repo access; `GH_TOKEN` | Repo access required; token optional if host CLI/SSH already authenticated | Repository settings or GitHub fine-grained token settings; restrict to this repository and needed contents/PR permissions. | Lead merges/pushes only after build authorization. Release reads deployment source. Other agents can deliver local diffs without tokens. No workflow/admin permission by default. |
| Hosting account; `VERCEL_TOKEN` | Hosting account required to publish; CLI token optional | Human signs in to Vercel and connects the repository or deploys through UI; create token only for automated deployment. | Release engineer only. App secrets are configured on the host separately from agent inputs. |
| Registrar account and qualifying domain | Required for domain track; **no registrar API key needed** | Human checks [MLH prizes](https://www.mlh.com/events/prizes) and [GoDaddy Registry offer](https://mlh.link/GoDaddyRegistry), confirms ShellHacks eligibility and obtains qualifying domain through the stated registrar. | Human purchases/redeems, controls DNS and confirms registration evidence. Release supplies exact DNS records from host. |
| MLH/Devpost/event submission account | Yes for submission | Human uses ShellHacks' actual submission link and selects eligible tracks. | Human submits team/project and accepts terms. No Devpost automation token needed. |
| MapLibre / OpenFreeMap | No key | Follow [OpenFreeMap quick start](https://openfreemap.org/quick_start/); preserve attribution. | Browser basemap; no paid map API required. |
| Cloudflare, MapTiler, geocoding vendor, OpenAI, Atlas Admin API | No | Not part of the baseline. | Add only if a concrete need is approved; none is needed to satisfy the requested tracks. |

Plain configuration: `GEMINI_MODEL`, `MONGODB_DB=gridbridge`, `SOURCE_DOCS_DIR` pointing to repo `docs`, `ANALYSIS_DATE`, host-selected coding model, and deployment URL. `PAPERCLIP_*` runtime context is supplied by Paperclip. Do not manually share another agent's credential. The portable sidecar declares only role-specific inputs; machine paths, secret bindings and model selection are configured after import.

## 10. Full Paperclip setup for this repository

These steps are for the future build launch; they were not executed now. Format was checked against the official [Agent Companies repository](https://github.com/paperclipai/companies), its [pinned authoring reference](https://raw.githubusercontent.com/paperclipai/companies/514503bf4f0ca88ebf16d5dc648e085d587f268f/skills/company-creator/references/companies-spec.md), [normative specification](https://agentcompanies.io/specification), and [Paperclip vendor specification](https://raw.githubusercontent.com/paperclipai/paperclip/master/docs/companies/companies-spec.md).

### 10.1 Install and authenticate

1. Human supplies Node.js **24.11+**, Python 3, Git and a supported local OS. Install Claude Code using its official quickstart; run it once as the same ordinary OS user who runs Paperclip. Verify model access and tool execution. Do not run the agent host as root.
2. From the checked-out repository, record `git status`, the base revision, Node/Python/Claude versions and the selected Paperclip package version. Preserve uncommitted Plan E files. For the later build, create an isolated branch/worktree only after ensuring it contains this package; do not assume an untracked plan appears in a new worktree.
3. Install/start Paperclip with the official onboarding command. For repeatable subsequent runs, pin the package version that passed the import preview. On later restarts, use the documented run command. [Installation](https://docs.paperclip.ing/guides/getting-started/installation/).

```sh
node --version
python3 --version
claude --version
npx paperclipai onboard --yes
# Later restart, after onboarding has completed:
npx paperclipai run
```

Run onboarding and the restart command at different times, not as two competing server processes. Keep the service private to the operator during setup.

### 10.2 Preview and import

In a second terminal at the repository root, with the server running and board CLI authentication configured:

```sh
npx paperclipai company import ./plans/plan-E/paperclip --target new --dry-run
npx paperclipai company import ./plans/plan-E/paperclip --target new --yes
```

Inspect the preview before the second command: expect **1 company, 8 agents, 13 skills, 1 project and 17 seed tasks**. Stop on missing skills, unknown sidecar fields or unexpected counts. The CLI supports a local directory as a positional source and imports all five groups by default. Imported timer heartbeats are disabled. [Import command reference](https://docs.paperclip.ing/reference/cli/company/).

The package uses `schema: agentcompanies/v1`, local skill shortnames, project owner and task assignee/project slugs. `.paperclip.yaml` carries `schema: paperclip/v1`, `claude_local` adapter types and portable env input declarations. It contains no live secret values, machine IDs or absolute workspaces. Task dependencies are explicit in task bodies; kickoff turns them into native blocked-by relationships. This avoids guessing unsupported portable dependency fields. Written skills are original procedures; none depends on a missing external skill folder.

### 10.3 Bind workspace, secrets and runtime limits

1. Open project **GridBridge** and set its workspace to the absolute path of this checkout or chosen worktree, with repository URL `https://github.com/fradicus/Shellhacks-2026`. Set agents to use that workspace. Keep all build edits under `plans/plan-E/implementation/`; the shared `docs/` is input only. Configure `SOURCE_DOCS_DIR` as the actual absolute `docs` path. [Workspaces](https://docs.paperclip.ing/guides/projects-workflow/workspaces/).
2. Keep agents paused while setting up. Bind every required env input from the secret store; optional Claude API keys may remain unbound when host login works. Put app deployment secrets on the host as well. Bind no DB or Gemini keys to frontend/CEO. Validate Atlas access with a minimal authenticated read/write against the app database and remove the test record during the future setup.
3. Choose the available Claude model in each adapter's configuration, record its identifier and run **Test Environment** for every agent. Verify the installed runtime exposes the agent's written skills and Paperclip coordination tools. Set maximum one concurrent run per agent; CEO releases no more than three assignments at a time. Use a bounded run duration (suggested 20 minutes) and keep timer heartbeats off. [Claude adapter](https://docs.paperclip.ing/reference/adapters/claude-code/), [company skills](https://docs.paperclip.ing/how-to/write-a-company-skill/).
4. Set the operator-approved company/agent monthly budgets in the UI, using the $140 allocation only if accepted. Set provider/application caps separately. Confirm paused agents do not run just because tasks were imported. Do not turn on recurring schedules for this 36-hour build.
5. Recheck all 17 tasks, their owners and project. Leave downstream tasks blocked until kickoff records prerequisite links. If import preview fails, correct only the package fields identified by the running version and rerun preview; do not silently skip skills or tasks.

### 10.4 Kickoff

Human explicitly starts `kickoff` after accounts, source handling, scope and spend are settled. CEO creates dependency links from PROJECT.md, logs the analysis date and limits, then releases `contracts`, `source-audit` and `golden-reference`. Frontend and Gemini work start from approved contracts/fixtures without waiting for all geolocation. The technical lead reviews interface changes; QA signs off independent evidence. CEOs and specialists use the supplied `paperclip-work` procedure for checkout, progress, blockers and completion.

The app must keep serving after Paperclip is stopped; Paperclip is the build manager. Its own operational database is separate from the application's required Atlas database.

## 11. Thirty-six-hour execution schedule

Hours are elapsed from authorized kickoff. An hour row is a milestone, not an instruction to run all eight agents simultaneously. CEO queues no more than three active assignments; human account/DNS work can proceed independently.

| Hour | Primary work and exit evidence |
|---:|---|
| 0–1 | Human tests runtimes, import, secrets and budget; CEO records kickoff and dependency links. |
| 1–2 | Lead publishes first contract; data audits source classifications; QA independently calculates golden fixture. |
| 2–3 | Lead finalizes schemas/fixtures; data maps owners; QA confirms six pairs and 19 nonmatches. |
| 3–4 | Release checks host-to-Atlas networking and domain eligibility; Gemini starts approved-page extraction; frontend scaffolds fixture map/table. |
| 4–5 | Data builds approved page manifest; Gemini validates first schema outputs; frontend detail drawer. |
| 5–6 | Lead creates Atlas schema/index/load path; data labels reference rows; geo starts endpoint candidate review. |
| 6–7 | Lead read API against Atlas; geo records accepted/rejected candidates; Gemini extraction retries/citation validation. |
| 7–8 | Data reviews extraction; frontend connects read API; geo resolves prioritized border endpoints. |
| 8–9 | Geo implements canonical matcher; Gemini produces evaluation counts; lead checks idempotent versioned loads. |
| 9–10 | Frontend displays ranked pairs; data expands real public corpus; QA checks extraction failures. |
| 10–11 | Geo verifies centers/precision; Gemini builds grounded briefs; release prepares protected deployment settings. |
| 11–12 | Data inventories newer sources; lead connects brief storage; CEO reviews current two-utility coverage gate. |
| 12–13 | Human resolves any CEII/owner source questions; geo reviews non-sample candidates; frontend shows unknown states. |
| 13–14 | Data links old/new DESC ID; Gemini validates briefing fact IDs; QA audits first featured pair. |
| 14–15 | Frontend adds filing diff and review evidence; lead tests API bounds; geo publishes match/rank driver records. |
| 15–16 | QA reviews candidate pairs independently; Gemini fixes observed extraction/citation failures; data closes coverage ledger. |
| 16–17 | Frontend implements CSV/print card; lead integrates; release performs first authorized staging deployment. |
| 17–18 | QA tests historical/future separation and failure states; geo optional transparent impact inputs; data resolves high-value gaps. |
| 18–19 | Frontend makes Gemini input/output and scenario labels visible; lead fixes integration defects; release tests TLS/domain configuration. |
| 19–20 | QA tests complete page-to-pair-to-export flow; Gemini runs bounded live-call rehearsal; CEO drafts supported track claims. |
| 20–21 | Data/geo finalize chosen opportunities; frontend accessibility pass; lead confirms stable active dataset promotion. |
| 21–22 | QA checks all featured facts/owners/citations; release verifies secrets are absent from client output; CEO applies cut order. |
| 22–23 | Fix blocking correctness bugs; rehearse source-page and filing-change interactions; preserve redacted evidence logs. |
| 23–24 | Integrated acceptance candidate; CEO confirms scope. **Feature freeze at hour 24.** |
| 24–25 | QA regression on locked feature set; data only fixes reviewed factual defects; release prepares rollback artifact. |
| 25–26 | Live Atlas queries and real Gemini call captured; frontend fixes usability blockers only. |
| 26–27 | Domain/HTTPS smoke checks; human confirms registration eligibility and submission access. |
| 27–28 | QA signs off data version; publish final coverage counts. **Data freeze at hour 28.** |
| 28–29 | Release deploys accepted candidate with authorization; QA verifies deployed routes, exports and evidence. |
| 29–30 | Rehearse two-minute pitch and fallback recording; check exact deployed revision. **Release freeze at hour 30.** |
| 30–31 | CEO/release assemble four-track evidence; human checks claims and team details. |
| 31–32 | QA repeats only deployed critical path; fix release-blocking defects with explicit retest. |
| 32–33 | Capture final short video/screenshots with source versions and model timestamps visible. |
| 33–34 | Human submits early; confirm links and selected tracks. |
| 34–35 | Rehearse answers on CEII, owner mapping, dates, Atlas and Gemini value. |
| 35–36 | Deadline buffer and final availability check; preserve release and dataset version. |

### Cut order and protected core

At hour 12, cut wide-area research beyond the defined border inventory if quality is slipping. At hour 20, cut R3 stretch first, then optional cost scenarios, then hypothetical-date controls, then cosmetic animations, then expanded diff UI (retain the verified old/new card). At hour 24, stop all new features. Live Gemini regeneration may fall back to a labeled previously generated result, but actual Gemini extraction/brief work and its evidence remain required. Never cut the golden checks, source/owner review, strict overlap rule, Atlas-backed reads, usable map/list, two-utility evidence, visible Gemini work or required domain/submission tasks. A missing core item is an open requirement, not a successful cut.

## 12. Human tasks and risk handling

| Human responsibility / risk | Timing and response |
|---|---|
| Accounts, payment terms, model access and spend | Before kickoff; operator alone supplies secrets and accepts charges. Agents can prepare configurations. |
| Mixed CEII/public pages and uncertain owners | Source review by hour 2; resolve by hour 12 or use approved alternatives. Never upload a disputed page while waiting. |
| Eligible domain, redemption/purchase, DNS control | Start by hour 3; exact name is chosen from available qualifying names. Working brand is GridBridge; no availability or trademark clearance is asserted. |
| Permission to deploy and submit | Human authorizes during implementation after concrete release evidence; this plan itself authorizes neither purchase nor publication. |
| No current overlaps | Report exact zero and coverage; show historical fixture separately. Do not relabel old dates or reduce threshold discipline. |
| Incomplete or conflicting endpoints | Show candidate/review status and one-endpoint approximation. Unreviewed locations cannot become featured confirmed opportunities. |
| Atlas network or hosting mismatch | Resolve by hour 4, choose permitted fixed-egress host if needed; recheck connection and TLS after deployment. |
| Gemini quota/errors or unsupported output | Model smoke test early, cache accepted outputs, bounded retries, explicit failure state; no fabricated substitute result. |
| Agent contention / integration delay | One contract owner, separate worktrees or owned paths, three active assignments, frontend fixtures early, QA independent. |
| Evolving Paperclip package format | Run server preview before import; inspect counts and resolve errors. Static validation in this delivery is not an import test. |
| Stale public plans and competition rules | Show analysis date/source dates; human confirms current event rules. Local track text is the project brief, not proof of award eligibility. |

## 13. Two-minute pitch and track evidence

**0:00–0:20:** “Utilities publish years of construction plans, but nearby work can remain invisible to the people coordinating crews and equipment. GridBridge turns those public plans into a shortlist a planner can audit.”

**0:20–0:45:** Open both utilities on the map and a reviewed pair. “This distance comes from the sponsor's endpoint-center rule. These are in-service milestones, not promised construction windows. Here are the original pages and the location evidence.” Show real counts from the finished build; never replace this with an invented opportunity count.

**0:45–1:05:** Switch to the labeled sample comparison. “The closest pair is 4.09 miles apart, but its milestones differ by 3,074 days. This 5.65-mile pair has a 152-day gap. We preserve both facts instead of treating every nearby project as equally useful.”

**1:05–1:30:** Show an approved page and Gemini's structured extraction, then the coordination brief. “Gemini reads the plan and drafts the questions a planner should ask. The distances and dates come from deterministic code, and every factual claim links back to evidence.”

**1:30–1:50:** Show filing change and card export. “Plans change, so Atlas preserves document versions, reviewed projects and match results. This card gives both planners the evidence and unanswered questions they need for a useful conversation.”

**1:50–2:00:** Point to the qualifying domain and close. “We help utilities find where coordination is worth investigating, with enough evidence to trust the next step.”

| Track | Evidence to capture from the future build |
|---|---|
| Sperry Gridlock | Two verified utilities, exact six-pair regression, real public inventory and non-sample review outcomes, map/list/card, honest gaps and source links. |
| Gemini | Actual approved-page extraction, structured response and validation, model/request metadata, visible grounded brief, redacted logs and failure handling. |
| Atlas | Real cluster/collection/index configuration, redacted query trace behind a UI interaction, persisted versions/matches; no static JSON masquerading as database use. |
| GoDaddy Registry domain | Eligible registration confirmation, chosen qualifying suffix/registrar under current event terms, DNS and live HTTPS app; generic hosting URL alone is insufficient. |
