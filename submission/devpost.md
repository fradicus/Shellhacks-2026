# GridBridge — submission draft

Draft only. Live deployment, team eligibility, production URL and submission deadline are unverified. No event submission has been made.

## Inspiration
Transmission planners need to find nearby projects across utility boundaries without losing the evidence behind them. FERC's 2024 Order No. 1920 put long-term regional transmission planning in focus ([official announcement](https://ferc.gov/news-events/news/ferc-takes-long-term-planning-historic-transmission-rule)). The sponsor's freight-cost anecdote motivated the coordination question; its dollar figures are [unverified] context, not a savings estimate. GridBridge helps a planner start an informed conversation. It does not certify compliance or promise shared construction windows.

## What it does
GridBridge turns public DESC filings and permitted Georgia planning-table metadata into versioned project records, an evidence map, a ranked overlap list, source-linked coordination cards, CSV/print exports, filing changes, and coverage reporting. A geographic overlap requires different verified utilities and centers strictly less than 25 miles apart. Exact in-service dates rank the leads; missing or partial dates stay unknown. Historical, future, and tentative results remain distinct.

## How we built it
A deterministic Python pipeline preserves source hashes, filing versions, owner codes, raw milestone text, and uncertain endpoint decisions. One canonical matcher computes centers, distances, date gaps, and priority. The MongoDB loader stages versioned records and promotes an active dataset; Next.js reads the stored data through bounded read-only APIs. Local MongoDB integration is checked separately from Atlas. The Gemini extraction pipeline validates structured responses and caches its evidence; grounded-brief implementation is in progress; live Gemini calls, Atlas deployment, and domain setup are deferred at the user's request. The workbench shows unavailable outputs honestly. Fixture mode is explicit and disabled in production.

The team used separate feature worktrees, draft pull requests as cross-computer ownership claims, shared JSON contracts, independent source/math review, and CI gates. Codex selected Astra for coordination, Gemini validation and independent QA; Sol high handled bounded data, geospatial, release and coverage implementation. The remote Claude worker owned shared contracts and the main application features; the Mac Codex worker owned browser QA. Coding-agent models are distinct from the application's Gemini model.

## Challenges
The Georgia source contains mixed disclosure markings. We retained only the sponsor-authorized deterministic table fields and did not send those pages to Gemini or publish page images. A document's publisher is not necessarily a project's owner, so unresolved codes stay unknown and cannot enter cross-utility matching. A nearby OSM name is insufficient to confirm a filed endpoint, and an in-service milestone does not identify a construction window. Source corrections and audit decisions remain visible instead of becoming silent assumptions.

## Accomplishments
The committed location report covers **262 active projects and 400 filed endpoints**: **89 medium-confidence locations and 311 unresolved endpoints**. The full-corpus matcher evaluated **656 centered pairs** from **7,452 known-owner combinations**, finding **19 candidate overlaps: 16 historical, three tentative and zero future**. All are still `needs_review`. These are coordination candidates, not confirmed construction opportunities. The matcher records **79 centered projects**, of which **57 have a known eligible utility**; uncertain owners remain excluded. See [location coverage](../data/locations/coverage.json) and [match summary](../data/matches/summary.json).

Independent audit artifacts, the coverage page and final integrated acceptance are pending. Real Gemini calls and outputs remain **zero**, and extraction accuracy is **null**, as recorded in [extraction evaluation](../data/extraction/eval.json). We do not substitute synthetic tests for live model evidence.

## What's next
Obtain planner-reviewed county/project-area evidence for unresolved endpoints, then rerun the version-bound audit. Configure Gemini, Atlas and HTTPS hosting when credentials and a domain are available; record actual model, timestamps and deployment evidence before claiming those integrations. User-entered impact scenarios remain optional stretch work. Team names, event eligibility, exact submission deadline and production URL are [unverified].

