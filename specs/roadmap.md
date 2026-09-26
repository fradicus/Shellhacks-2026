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
  claude-local: [F00, F05, F11, F14, F16, F19, F21]
  codex-local: [F01, F02, F03, F04, F06, F07, F08, F09, F10, F12, F13, F15, F17, F18, F30, F31, F32]
frozen_paths:
  - schemas/
  - scripts/
  - .github/
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

## Authorized follow-on: national discovery

The user's 2026-09-26 follow-on authorizes C11/F30/F31 and a separate F32 branch after the first run. Read [C11](decisions/C11-national-follow-on.md) for the boundary: Plans B/D guide traceability and interaction, the existing sponsor math stays canonical, and Census geography is not nationwide project coverage. The original elapsed gates and run start remain historical; they do not cancel this new request. F30 and F31 may proceed in separate delegated worktrees against the frozen national schema contract; F31 cannot claim integrated data delivery until F30's validated snapshot is available. The root coordinator reviews shared integration and leaves the independent MongoDB/search/embedding worker's files alone. Old F08/F18 drafts remain paused.

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

## Original run critical path
F00 → F01 + F02 (+F04) → F09 → F10 → F12, with F05 → F11 and F06 in parallel. If F09 is late at 4:30, geo
narrows to the border-area projects (see F09 Defaults) rather than miss F10.

## Post-run (humans, morning)
Read `reports/final.md`. Review `specs/decisions/*`, especially 000. Check the domain and the Devpost submission. Merge nothing overnight-generated that you haven't looked at into the event submission unless it's already on `main`.
