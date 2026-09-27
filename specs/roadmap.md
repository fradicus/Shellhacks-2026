---
run_start: "2026-09-26T04:45:00-04:00"
analysis_date: "2026-09-26"
execution_mode: local               # paperclip | local | hybrid
contract_owner: technical-lead
reporting_agent: ceo
lanes:
  A: { name: data,    agents: [data-researcher, gemini-engineer, geo-engineer] }
  B: { name: app,     agents: [technical-lead, frontend-engineer] }
  C: { name: quality, agents: [qa-verifier, release-engineer, ceo] }
# Ignored in paperclip mode. In hybrid mode, keep only locally assigned features here.
local_workers:
  claude-local: [F00, F05, F11, F14, F16, F19, F21, F40]
  codex-local: [F01, F02, F03, F04, F06, F07, F08, F09, F10, F12, F13, F15, F17, F18, F30, F31, F32, F33, F34, F35, F36, F37, F38, F39, F41]
frozen_paths:
  - schemas/
  - scripts/
  - .github/
  - azure-pipelines.yml
  - ci/
  - pipeline/pyproject.toml
  - pipeline/uv.lock
  - pipeline/common/
  - pipeline/matches/
  - tests/golden/
  - data/fixtures/
  - web/package.json
  - web/package-lock.json
  - web/tsconfig.json
  - web/next.config
  - web/eslint.config
  - web/lib/types.ts
  - web/lib/data.ts
  - web/app/layout.tsx
  - web/app/globals.css
  - web/components/nav/
  - web/components/ui/
  - AGENTS.md
  - CLAUDE.md
gates:
  - { at: "0:00", only: [F00, F18] }
  - { at: "5:00", no_new_phase: 2 }
  - { at: "6:30", freeze: true, allow: [F18] }
  - { at: "7:30", report: true }
  - { at: "8:00", hard_stop: true }
stretch: [F17]
---

# Roadmap: GridBridge overnight build

Each phase leaves a working, deployable product on `main`. The gates in the front matter assume an **8-hour run**.
For a shorter run, scale every `at` value proportionally in the pre-flight commit (a 6-hour run is 0.75×).

## Execution options
- **Paperclip:** agents use their named role/lane assignments; the local worker map is ignored.
- **Local:** Claude Code and Codex use `local_workers`, adopting each feature's named role/lane. One implementation feature per session; the F18 owner also handles short reporting checkpoints in a separate worktree.
- **Hybrid:** local sessions own only IDs listed in `local_workers`; Paperclip owns the remaining features through the existing role/lane assignments. Trim the local map before launch. Pause the old owner before any reassignment.

The launch split gave Claude the bootstrap and the app (F00, F05, F06, F11, F14, F16), and Codex the data, QA, release and reporting. After the user confirmed the Claude worker had stopped, C8 transferred remaining F06 corrections to Codex in the same technical-lead role; the original F06 delivery remains credited to its author. No extra agents or scheduler are required for local mode. See [preflight.md](preflight.md).

## Phase 0: bootstrap (lane B alone)
Skeleton, contracts, fixtures, the canonical matcher and golden test, CI, the ownership gate, placeholder routes. After this, everyone works in parallel without touching shared files.

## Phase 1: parallel foundations
Real DESC and Georgia registers, Gemini extraction, an OSM inventory, a map and list on fixtures, the Atlas loader and API, the QA harness, deploy verification.

## Phase 2: the real product
Reviewed locations, full-corpus overlaps and priority, the evidence drawer and coordination card, grounded briefs, independent data audit.

## Phase 3: differentiators
Filing-change view, coverage view, Gemini workbench. Stretch: impact scenario.

## Phase 4: acceptance
Continuous status reports, final acceptance, submission draft, `STOP`.

## Features

| ID | Feature | Lane | Agent | Phase | Depends on | Cut |
|---|---|---|---|---|---|---|
| F00 | Bootstrap: skeleton, contracts, matcher, golden, CI | B | technical-lead | 0 | none | never |
| F01 | DESC register (both filings, versions, source manifest) | A | data-researcher | 1 | F00 | never |
| F02 | Georgia register (Ten-Year Plan tables, owner codes) | A | data-researcher | 1 | F00 | never |
| F03 | Gemini extraction of DESC cards + evaluation | A | gemini-engineer | 1 | F01 | never |
| F04 | OSM power-infrastructure inventory | A | geo-engineer | 1 | F00 | allowed |
| F05 | Map + ranked list (fixtures, then API) | B | frontend-engineer | 1 | F00 | never |
| F06 | Atlas loader + read API | B | technical-lead | 1 | F00 | never |
| F07 | QA harness: independent golden + e2e smoke | C | qa-verifier | 1 | F00 | allowed |
| F08 | Release: deploy, health, domain verification | C | release-engineer | 1 | F05 | never |
| F09 | Endpoint locations with evidence + confidence | A | geo-engineer | 2 | F01, F02, F04 | never |
| F10 | Full-corpus overlaps + priority | A | geo-engineer | 2 | F09 | never |
| F11 | Evidence drawer + coordination card + CSV/print | B | frontend-engineer | 2 | F05, F06 | never |
| F12 | Grounded Gemini briefs | A | gemini-engineer | 2 | F10 | never |
| F13 | Independent data audit (locations, featured pairs) | C | qa-verifier | 2 | F10 | allowed |
| F14 | Filing-change view | B | frontend-engineer | 3 | F01, F06 | allowed |
| F15 | Coverage view | B | technical-lead | 3 | F06, F10 | allowed |
| F16 | Gemini workbench | B | frontend-engineer | 3 | F03, F06 | allowed |
| F17 | Impact scenario (stretch) | B | technical-lead | 3 | F11 | allowed |
| F18 | Status, acceptance, submission draft, STOP | C | ceo | 4 | none | never |
| F19 | Time view (Three.js), added after run 1 by the human | B | frontend-engineer | 3 | F05, F06 | allowed |
| F21 | Visual system and frontend pass, added by the human after sponsor reviews | B | frontend-engineer | 5 | F19 | allowed |
| F30 | Trusted national sources, Census geography, regional imports | A | data-researcher | 5 | F00 | never |
| F31 | National explorer with state/county/region filters | B | frontend-engineer | 5 | F00 | never |
| F32 | Optional AI app controls, separate prototype branch | B | gemini-engineer | 5 | F31 | allowed |
| F37 | 3D History page and sourced project/contract events (spec only; implementation pending) | B | frontend-engineer | 6 | F19 | allowed |
| F33 | Verified EIA directory and evidence reconciliation | A | data-researcher | 6 | F00 | never |
| F34 | Environmental evidence, current conditions and truck route adapters | A | geo-engineer | 6 | F00 | never |
| F35 | Actual job outcomes, evaluated duration and delay estimates | B | technical-lead | 6 | F00 | never |
| F36 | Field operations planning desk | B | frontend-engineer | 6 | F33, F34, F35 | never |
| F38 | Verified geographic project data: Florida to contiguous US (spec only; launch pending) | A | data-researcher | 7 | F00, F30 | never |

## Authorized follow-on: national discovery

The user's 2026-09-26 follow-on authorizes C11/F30/F31 and a separate F32 branch after the first run. Read [C11](decisions/C11-national-follow-on.md) for the boundary: Plans B/D guide traceability and interaction, the existing sponsor math stays canonical, and Census geography is not nationwide project coverage. The original elapsed gates and run start remain historical; they do not cancel this new request. F30 and F31 may proceed in separate delegated worktrees against the frozen national schema contract; F31 cannot claim integrated data delivery until F30's validated snapshot is available. The root coordinator reviews shared integration and leaves the independent MongoDB/search/embedding worker's files alone. Old F08/F18 drafts remain paused.

## Authorized follow-on: verified field operations

The user's later sponsor Q&A transcript and board photo authorize C15/F33–F36 after the original run gates. [C15](decisions/C15-verified-operations.md) governs source reconciliation, EIA scope, annual AlphaEarth context, current conditions, truck restrictions, and real outcome evaluation. F33/F34/F35 may build their independent modules concurrently against C15; F36 starts after their exported types and completion markers exist. Integrated acceptance requires all applicable artifacts and honest unavailable states. The root owns C15/shared integration and F35. F33 is the data researcher, F34 the geospatial engineer, F36 the frontend engineer. Each uses a separate worktree and independent review. Existing F06/F12/F19/F20 and C13/C14 work on other computers remains with its current owners. F32 remains an optional separate branch. Credentials and actual completed-job data are prerequisites for live results, not permission to invent them.

F18 starts at 0:00 alongside F00 and merges
status updates as `[F18] status HH:MM` parts. At the user's expedited-completion request, F18 may publish its final report, `STOP` and `changes/F18.md` before the scheduled `report` gate once all non-stretch implementation features and core corrections are verified complete (or an allowed cut is explicitly recorded), the final integration checks pass, and deferred live services are stated clearly. Otherwise the scheduled report gate remains the deadline. F18 itself is the final reporting step; optional F17 need not start. This does not waive merge checks or permit an unresolved core defect to be called complete.

## Sponsor-feedback follow-up: PM investigation

[C16](decisions/C16-sponsor-context.md) integrates the sponsor panel and demo feedback into the mission and
[PM acceptance scenario](followup.md). It authorizes this documentation reconciliation after the original run;
it does not start a new autonomous feature run. Existing implementation assignments, C11/F30/F31, the separate
F32 prototype and the operations claim in issue 97 retain their own boundaries.

Next product milestone: a PM investigates one real project, checks nearby work, changes and evidence, and exports
a useful follow-up packet. Required sequence: clarify claims, investigate a bounded location sample, expose useful
freshness/history, verify the assembled deployed workflow, and observe a PM doing the task. Existing feature
owners handle their paths after any gaps are explicitly scoped and claimed; no blanket reopening is implied.

Treat equipment rental/subleasing, automatic dispatch, a new field-account product, predictive claims and a separate
civic workflow as [potential work](followup.md#potential-work-do-not-implement), not ready features. The notes are
context, not implementation permission. Record reason, decision and acceptance when promoting an idea.

Feature completion markers continue to identify merged implementation. Reporting must separately show automated
checks, live integration and user-task evaluation against a named revision. Check job-level CI conclusions; a
successful workflow can contain a failed non-blocking browser job. See [documentation upkeep](context/README.md#keep-context-and-specs-aligned).

## Specified follow-on: 3D historical research

The user's 2026-09-26 request authorizes C19 specification delivery, including its issue, worktree, PR and merge.
[F37](features/F37-history-view/spec.md) defines `/history` as a close Three.js sibling of the main `/time` view:
shared map interaction and visual language, a historical year plane, documented event sequences and contract
evidence. See [C19](decisions/C19-history-view.md) and [issue 104](https://github.com/fradicus/Shellhacks-2026/issues/104).
F37 is reserved to codex-local for later implementation; it is not eligible for autonomous pickup until the
user starts that work and the shared-scene/data integration contract is accepted. Existing F19/F21 and proposed
C15/F33–F36 ownership remain intact. A merged specification does not satisfy F37's completion criteria or claim
that historical contracts have been acquired. Original run gates remain historical for this bounded spec task.

## Specified follow-on: verified geographic expansion

[C22](decisions/C22-verified-geographic-data.md) and [F38](features/F38-verified-geographic-data/spec.md) capture the
user's data-first request: verified project locations visibly filling the existing US map, beginning in Florida,
then repairing/expanding Georgia, then the defined Southeast, then the 48 contiguous states plus DC. Alaska/Hawaii
are stretch. Preserve current and documented historical work with distinct lifecycle/status evidence. A count of
imported records or a list of regional sources does not satisfy location coverage.

This authorizes specification delivery only. F38 is reserved to codex-local and is not eligible for autonomous pickup
until the additive evidence/loader/API/map compatibility contract is accepted and the user explicitly launches the
work. Its later run uses a newly recorded start/deadline, budget, source scope, independent reviewer and incremental
PR checkpoints; the original run clock is historical. No overnight worker is started by this spec. Existing feature
owners retain F06/F09/F13/F19/F30/F31/F37 paths, and root STOP/main-red rules remain binding.

Data acquisition and independent identity/location verification are the main work. Minimal integration into existing
maps is required so accepted points actually appear; redesign and new History interactions remain deferred. F37 still
owns `/history`; F38's sourced observations/events may feed its accepted contract later. The F38 completion marker
requires its source-bounded coverage and visible publication acceptance, not just an importer or a nationwide basemap.

## Original run critical path
F00 → F01 + F02 (+F04) → F09 → F10 → F12, with F05 → F11 and F06 in parallel. If F09 is late at 4:30, geo
narrows to the border-area projects (see F09 Defaults) rather than miss F10.

## Post-run (humans, morning)
Read `reports/final.md`. Review `specs/decisions/*`, especially 000. Check the domain and the Devpost submission. Merge nothing overnight-generated that you haven't looked at into the event submission unless it's already on `main`.

## Launched follow-on: complete Southeast coverage

The user explicitly instructed Codex to continue until the entire Southeast is done. [C24](decisions/C24-southeast-launch.md)
assigns [F39](features/F39-southeast/spec.md) to this local session, separate from F38's New England checkpoint.
FL, GA, AL, MS, SC, NC, TN, KY, VA, WV, AR and LA remain the full objective. Florida is the publication pilot,
followed by Georgia and the remaining states. Original run gates are historical for this launch. No deadline or
token budget was requested; use resumable checkpoints without treating a checkpoint as completion.
Existing F38 and shared-contract claims retain their owners. F39 cannot publish until the applicable shared
contract and loader integration are accepted. Research can proceed independently during that integration.

| ID | Feature | Lane | Agent | Phase | Depends on | Cut |
|---|---|---|---|---|---|---|
| F39 | Verified Southeast project coverage and geographic delivery | A | data-researcher | 7 | F00, F30 | never |

## Launched follow-on: Texas

The user assigned Texas to this Codex local session, separate from the active Southeast and Great Lakes workers.
[F41](features/F41-texas/spec.md) starts a bounded public-source research checkpoint using the simplified official,
candidate and area-only display tiers in [C25](decisions/C25-main-demo-map.md). Existing feature assignments remain.

| ID | Feature | Lane | Agent | Phase | Depends on | Cut |
|---|---|---|---|---|---|---|
| F41 | Texas transmission project research and map delivery | A | data-researcher | 7 | F00, F30 | never |

## Launched follow-on: Great Lakes coverage

The user instructed Claude local to fill the map across the Great Lakes, starting with Minnesota, targeting ~5,000
points, and chose a labeled candidate-location tier over the F38 review bar for this rollout. [C26](decisions/C26-great-lakes-candidates.md)
assigns [F40](features/F40-great-lakes/spec.md): MN, WI, MI, IL, IN, OH, PA, NY. Candidates are never counted as verified.
Publication uses a fixed F40 release appended by F30's owner, following C29.

| ID | Feature | Lane | Agent | Phase | Depends on | Cut |
|---|---|---|---|---|---|---|
| F40 | Great Lakes project coverage with labeled candidate locations | A | data-researcher | 7 | F00, F30 | never |
