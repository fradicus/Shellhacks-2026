---
name: hackathon-submission
description: ShellHacks 2026 judging criteria, the four target tracks and their proof, mentor checkpoints, pitch structure and the Devpost write-up for Gridlock. Use for scope decisions and the final submission.
---

# Hackathon submission

## General judging
Completion, Originality, Design, Technology, Practicality. Judges spend minutes per project, so the first 30 seconds decide it.

## Who judges Sperry: their AI team
Their intern listing prizes extraction pipelines, validation checks, automated refresh, tracing a number back to its
source, Python and pandas, and document parsing. Our proof: the Data Quality page, evidence popovers, the source-watch
workflow, the extraction evaluation, and the golden test in CI.

## Tracks and proof
| Track | Proof a judge must see |
|---|---|
| Sperry Tech - Gridlock | Map of both utilities' full lists, highlighted pairs (< 25 mi), ranked Opportunities, Timeline tab, zones, estimate card, golden sample reproduced |
| MLH Gemini API | GPC row joining, geocode adjudication, number-checked briefs, Ask the grid driving the map; model ID and eval accuracy stated |
| MLH MongoDB Atlas | GeoJSON + 2dsphere, `$geoNear` radius tool, Atlas Search, `$lookup`/`$facet` aggregations; a screenshot of indexes in Atlas |
| MLH GoDaddy Registry domain | App live on the qualifying domain; a line on why the name fits |

## Mentor checkpoints (board does these)
- Hour 1: Sperry mentor. Is using the GPC table fields OK given the CEII banner? What makes an opportunity useful? Is 180 days a reasonable timing window?
- Hour 20: show the ranked list and a zone page; ask what's missing. Feed the answers into the score weights and copy.

## Pitch (2 minutes, pick the strongest verified examples)
1. Problem (15 s): the $1.5M-of-$5M freight quote; utilities plan in isolation; FERC Order 1920.
2. Scale (15 s): "We parsed every project in both utilities' public filings: N projects, M located, every number traceable."
3. Best lead (30 s): the top Tier 1 pair. If QA verifies it, the Okatie-McIntosh tie shares McIntosh with Georgia Power's McIntosh work.
4. Counterexample (15 s): the 4.09-mi Hooks/Evans-Thurmond pair is 3,074 days apart, so the tool ranks evidence, not just proximity.
5. Zone + sequencing (20 s): the contention band and "a crew could move X -> Y in N days".
6. Trust (15 s): click a number, see the page. Data Quality page. Golden test in CI.
7. Close (10 s): the domain, and "Gridlock finds the leads; planners make the call."

## Devpost write-up
Inspiration - What it does - How we built it (pipeline diagram, the stack per track, Paperclip agent team) -
Challenges (redacted GPC costs, ambiguous substation names, in-service vs construction dates) - Accomplishments
(measured numbers only, verified by QA) - What we learned - What's next (Santee Cooper and more utility pairs, SERTP
data, corridor-geometry overlap). Include the live URL, repo, and screenshots of the map, pair memo, zone Gantt and Data Quality page.
Select all four tracks. A human submits; the CEO drafts.
