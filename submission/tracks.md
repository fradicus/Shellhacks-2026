# Track evidence — draft, not eligibility confirmation

Checkpoint: main `ac2c506`, 2026-09-26. Recheck against the selected deployed revision before submission.

The [official MLH ShellHacks prize page](https://www.mlh.com/events/shellhacks-b9/prizes) lists Gemini API, MongoDB Atlas and GoDaddy Registry domain categories. This does not establish team eligibility or completed integration. Exact event submission rules/deadline and team details are [unverified].

| Track | Implemented evidence | Outstanding evidence |
|---|---|---|
| Sperry Tech Gridlock | Map/list, pair evidence/export, filing changes, coverage and time view; [golden fixture](../data/fixtures/golden/overlaps.json), [full-corpus summary](../data/matches/summary.json), [national coverage](../data/national/coverage.json) | [Independent audit](../reports/audit/summary.md) complete; no real pair confirmed. Final live/user acceptance pending. Mobile time-heading defect remains on main; see status. Optional impact scenario is not included. |
| Gemini API | [Extraction evaluation](../data/extraction/eval.json), structured validation/workbench; [grounded-brief validation and offline results](../data/briefs/README.md) | Main artifacts: zero extraction/brief calls and null extraction accuracy. [PR91](https://github.com/fradicus/Shellhacks-2026/pull/91) reports live brief results on its branch. Merge and verify the served artifacts, model and timestamps before claiming delivered integration. Coding with AI is not Gemini API proof. |
| MongoDB Atlas | [Versioned loader and index definitions](../pipeline/load/__main__.py), [viewport query](../web/lib/server/queries.ts), local MongoDB QA | Atlas and deployed UI query evidence deferred; a local database or green workflow is not Atlas proof. |
| GoDaddy Registry domain | [Release verification tool](../release/verify-deployment.mjs) | Domain registration, qualification and live HTTPS are unavailable. No purchase, registration or terms acceptance performed. |

## Routes and deployment

Production URL: **not verified in the committed release evidence**. Route identifiers `/`, `/pair/<id>`, `/changes`,
`/coverage`, `/gemini`, `/time` and `/explore` are application routes, not verified live links. Do not present fixture
or localhost evidence as a public deployment. Domain: **not verified**. Devpost event submission URL: **unverified**;
do not substitute a prior year's event. See [current checkpoint](../reports/status.md) and [release log](../release/deploys.md).

## Defined database indexes

The committed loader defines a unique `(dataset,id)` index on stored collections; project indexes on `(dataset,geo:2dsphere)`, `(dataset,utility,active)` and `(dataset,project_key)`; match indexes on `(dataset,view,band,time_gap_days,distance_mi)` and `(dataset,rank)`; brief index `(dataset,match_id)`; and filing-change index `(dataset,project_key)`. These are code definitions, not a claim of live Atlas installation.

An earlier 2026-09-26 checkpoint reported ten successful HTTP link checks. That result is historical and does not
verify this revised document's destinations or a production deployment. Final product acceptance is pending;
record fresh link and deployment results before submission.
