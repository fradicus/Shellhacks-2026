# Mission: GridBridge

## Why
Neighboring electric utilities plan transmission construction years ahead, mostly in isolation. When their projects
are near each other, they could coordinate crews, equipment, freight and outage windows. When they aren't
coordinated, a contractor quoted $1.5M of freight on a single $5M job, and line crews (a scarce, state-bound pool)
get fought over. FERC Order No. 1920 (2024) reformed long-term regional planning because of this isolation.
GridBridge is a **coordination discovery tool**. It finds leads worth a planner's conversation; it doesn't certify
compliance or promise savings.

## Who
Primary: a transmission planner or regional planning analyst preparing for a coordination meeting. Judges: Sperry
Tech's AI team (they value extraction pipelines, validation, and tracing any number back to its source), plus MLH
track judges.

## What (the product)
A web app that compares **Dominion Energy South Carolina (DESC)** and **Georgia Power / Georgia ITS** planned
transmission projects from public filings:
1. **Map + ranked list:** both utilities' projects, with geographic overlaps highlighted and ranked.
2. **Evidence drawer:** every value traced to its source document and page, location evidence, raw text, unknowns shown as unknown.
3. **Coordination card:** deterministic pair facts, a Gemini brief grounded in cited facts, possible shared activities, open questions, CSV and print export.
4. **Filing-change view:** the same DESC project across two filing versions (e.g. project `0139 M,N` moved from 2024-12-31 to 2026-05-31).
5. **Coverage view:** how much of each source was extracted, located and reviewed, with denominators.
6. **Gemini workbench:** a judge sees the source page text, Gemini's structured extraction, and which fields were accepted or rejected against validation.

## Non-negotiable rules (sponsor: Sperry Tech "Gridlock")
- Project **center** = arithmetic mean lat/lon of its two located endpoints; one located endpoint -> that point; none -> no center, no spatial matching.
- **Overlap** = different utilities AND both centers known AND haversine distance (R = 3958.8 mi) **< 25 miles**. Exactly 25 is not an overlap. Classify on unrounded values; round to 2 dp for display only.
- **Time gap** = |in-service date A − in-service date B| in days, exact dates only. Otherwise null (keep the raw text and precision). Never impute Jan 1 or Dec 31.
- Geography decides overlap. Time only ranks. An in-service date is a milestone, not a construction window.
- **Golden test:** the sponsor workbook `docs/Sperry-Tech-Challenge/Projects_Overlaps.xlsx` must yield exactly OVL_1..OVL_6 (distances to 2 dp, gaps exact) and exclude the other 19 cross-utility pairs.
- **Priority** (`nearby-band-v1`): band 0 (< 10 mi) before band 1 (10–25 mi), then exact gap ascending (unknown last), then unrounded distance, then canonical pair id. No composite score, no invented probability.
- Public sources only, CEII handled per `specs/decisions/000-overnight-defaults.md`. Never invent coordinates, dates, costs or owners.
- Impact dollars only from cited or user-entered inputs. Absent inputs mean null dollars. The $1.5M/$5M anecdote is context, not a ratio.

## Tracks and what proves each
| Track | Proof |
|---|---|
| Sperry Tech Gridlock | Map + ranked list of two utilities, golden test green, real public data beyond the sample, evidence drawer, coordination card with impact inputs |
| MLH Best Use of Gemini API | Gemini extraction visible in the workbench with measured accuracy; grounded briefs with citations; model id and timestamps shown |
| MLH Best Use of MongoDB Atlas | The deployed UI reads from Atlas: GeoJSON + `2dsphere`, viewport `$geoWithin`, versioned collections. No static JSON pretending to be the database |
| MLH Best Domain (GoDaddy Registry) | Live over HTTPS on the qualifying domain the human registered |

## Tone
Plain, precise, evidence-first. Say "in service 152 days apart", never "built at the same time". Say "possible shared activity", never "savings".

## Out of scope tonight
Auth and accounts, live Gemini calls from the public site, a third utility, route or corridor geometry, schedule optimization, notifications.

## National follow-on authorized by the user
The first-run limits above are historical. C11/F30/F31 extend discovery to verified public national sources and state/county/Census-region/planning-region filters, starting with an actual regional import plus the reviewed legacy corpus. Government geography and a source directory must not imply imported project coverage everywhere. Preserve the sponsor's strict distance rule, source evidence, unknown locations and milestone precision. F32 is a separate potential-feature branch for a controlled natural-language side panel; it does not activate a public live model. Plans B and D supply source-audit and map/table/Ask-the-grid guidance within the current stack.
