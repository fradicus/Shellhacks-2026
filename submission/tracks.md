# Track evidence — draft, not eligibility confirmation

The [official MLH ShellHacks prize page](https://www.mlh.com/events/shellhacks-b9/prizes) lists Gemini API, MongoDB Atlas and GoDaddy Registry domain categories. This does not establish team eligibility or completed integration. Exact event submission rules/deadline and team details are [unverified].

| Track | Implemented evidence | Outstanding evidence |
|---|---|---|
| Sperry Tech Gridlock | Map/list, source-linked pair cards, CSV/print and filing changes; [golden fixture](../data/fixtures/golden/overlaps.json), [full-corpus summary](../data/matches/summary.json), [independent browser QA](../reports/qa/evidence-export.md) | [Independent audit](../reports/audit/summary.md) complete; F15 and final integration pending. No real pair confirmed. Optional impact scenario is not included. |
| Gemini API | [Extraction evaluation](../data/extraction/eval.json), structured validation/workbench; [grounded-brief validation and offline results](../data/briefs/README.md) | Live service deferred. Model ID and execution timestamp unavailable; zero real calls/outputs, accuracy null. Coding with AI is not Gemini API proof. |
| MongoDB Atlas | [Versioned loader and index definitions](../pipeline/load/__main__.py), [viewport query](../web/lib/server/queries.ts), local MongoDB QA | Atlas and deployed UI query evidence deferred; a local database or green workflow is not Atlas proof. |
| GoDaddy Registry domain | [Release verification tool](../release/verify-deployment.mjs) | Domain registration, qualification and live HTTPS are unavailable. No purchase, registration or terms acceptance performed. |

## Routes and deployment

Production URL: **not working / not provided**. Route identifiers `/`, `/pair/<id>`, `/changes`, `/coverage` and `/gemini` are application routes, not live links. Do not present fixture or localhost evidence as a public deployment. Domain: **not working / not provided**. Devpost event submission URL: **unverified / not working**; do not substitute a prior year's event.

## Defined database indexes

The committed loader defines a unique `(dataset,id)` index on stored collections; project indexes on `(dataset,geo:2dsphere)`, `(dataset,utility,active)` and `(dataset,project_key)`; match indexes on `(dataset,view,band,time_gap_days,distance_mi)` and `(dataset,rank)`; brief index `(dataset,match_id)`; and filing-change index `(dataset,project_key)`. These are code definitions, not a claim of live Atlas installation.

Link check on 2026-09-26: all ten linked evidence destinations returned HTTP 200 using curl with redirects, and every relative file exists locally. Unprovided production, domain and event-submission URLs remain explicitly marked above. Final product acceptance is pending.

