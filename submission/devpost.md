# GridBridge — submission draft

Draft only. Live deployment, team eligibility, production URL and submission deadline are unverified. No event submission has been made.

Evidence baseline: main `18da907`, 2026-09-26. See [status](../reports/status.md) for pending PRs and separate automated,
live and user acceptance. Refresh this draft against the actual demo revision before submission.

## Inspiration
Transmission planners need to find nearby projects across utility boundaries without losing the evidence behind them. FERC's 2024 Order No. 1920 put long-term regional transmission planning in focus ([official announcement](https://ferc.gov/news-events/news/ferc-takes-long-term-planning-historic-transmission-rule)). The sponsor's freight-cost anecdote motivated the coordination question; its dollar figures are [unverified] context, not a savings estimate. GridBridge helps a planner start an informed conversation. It does not certify compliance or promise shared construction windows.

## What it does
GridBridge turns public DESC filings and permitted Georgia planning-table metadata into versioned project records, an evidence map, a ranked overlap list, source-linked coordination cards, CSV/print exports, filing changes, and coverage reporting. A geographic overlap requires different verified utilities and centers strictly less than 25 miles apart. Exact in-service dates rank the leads; missing or partial dates stay unknown. Historical, future, and tentative results remain distinct.

The Three.js time view makes the filed milestones visible above the map without changing the matcher. The national
explorer adds source-linked regional records and state/county/region reference filters, with unknown locations and
actual import coverage explicit. Source-wide totals include historical and cancelled records.

Sponsor feedback sharpened the primary follow-up task: a desktop project manager investigates a real project,
checks nearby work and changes, and prepares evidence for a conversation. The guided demo received positive
feedback; independent user-task success and savings have not been measured.

## How we built it
A deterministic Python pipeline preserves source hashes, filing versions, owner codes, raw milestone text, and
uncertain endpoint decisions. One canonical matcher computes centers, distances, date gaps, and priority. The
MongoDB loader stages versioned records and promotes an active dataset; Next.js reads stored data through bounded
read-only APIs. National discovery has a separate dataset namespace and activation pointer. Local database checks
are separate from Atlas acceptance. Gemini extraction and briefs validate structured responses, provenance and
current-fact bindings. Main's committed artifacts still record unavailable live results; PR91 reports new live
briefs on its branch. Verify merged/deployed evidence before claiming them. Fixture/snapshot modes are explicit
and disabled in production.

The team used separate feature worktrees, draft pull requests as cross-computer ownership claims, shared JSON contracts, independent source/math review, and CI gates. Codex selected Astra for coordination, Gemini validation and independent QA; Sol high handled bounded data, geospatial, release and coverage implementation. The remote Claude worker owned shared contracts and the main application features; the Mac Codex worker owned browser QA. Coding-agent models are distinct from the application's Gemini model.

## Challenges
The Georgia source contains mixed disclosure markings. We retained only the sponsor-authorized deterministic table fields and did not send those pages to Gemini or publish page images. A document's publisher is not necessarily a project's owner, so unresolved codes stay unknown and cannot enter cross-utility matching. A nearby OSM name is insufficient to confirm a filed endpoint, and an in-service milestone does not identify a construction window. Source corrections and audit decisions remain visible instead of becoming silent assumptions.

## Accomplishments
The committed location report covers **262 active projects and 400 filed endpoints**: **89 medium-confidence locations and 311 unresolved endpoints**. The full-corpus matcher evaluated **656 centered pairs** from **7,452 known-owner combinations**, finding **19 candidate overlaps: 16 historical, three tentative and zero future**. None is independently confirmed; the source-bound audit conservatively downgrades the featured pairs where location identity remains unverified. These are coordination candidates, not confirmed construction opportunities. The matcher records **79 centered projects**, of which **57 have a known eligible utility**; uncertain owners remain excluded. See [location coverage](../data/locations/coverage.json) and [match summary](../data/matches/summary.json).

The [independent audit](../reports/audit/summary.md) and [coverage page implementation](../changes/F15.md) are complete.
The [national snapshot](../data/national/coverage.json) contains 1,286 records with 69 exposed needs-review points;
the rest have no displayed location. These are import counts, not nationwide completeness or verified future work.
Final live integration and observed PM-task acceptance remain pending. Main's [extraction evaluation](../data/extraction/eval.json)
records zero calls/processed responses and null accuracy. Main's [brief summary](../data/briefs/summary.json) also
records zero calls; [PR91](https://github.com/fradicus/Shellhacks-2026/pull/91) reports 15 live calls and 15 passed briefs
on its unmerged branch. No synthetic test or unmerged artifact is presented as a deployed result.

## What's next
Evaluate the PM investigation-to-evidence-packet workflow with a real user. Improve bounded location evidence,
make source freshness and available filing changes understandable, and verify the configured live data path.
Expand sources according to evidence quality and user relevance. Equipment rental/subleasing, automatic dispatch,
new field-account workflows and published predictive claims are potential ideas requiring separate decisions;
they are not promised features. Existing separately authorized operations research keeps its own scope. See
[C16 / PR99](https://github.com/fradicus/Shellhacks-2026/pull/99). Team names, event eligibility, exact submission
deadline and production URL are [unverified].
