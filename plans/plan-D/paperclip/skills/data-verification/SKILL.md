---
name: data-verification
description: Verify Gridlock data and behavior - golden and boundary tests, extraction evaluation, location-match and pair verification against sources, verification log, live-site and failure drills. Use for QA of data or the app.
---

# Data verification

## Golden + boundary test (`pipeline/test_overlaps.py`)
Load the 10 sample projects from `docs/Sperry-Tech-Challenge/Projects_Overlaps.xlsx` (sheet `projects`, `openpyxl`;
convert Excel serial dates). Run them through the real `overlaps.py` functions. Assert:
- exactly OVL_1..OVL_6 are nearby; the other 19 pairs aren't
- `abs(distance - expected) <= 0.05`; gaps are exact
- boundaries: 24.999 nearby; 25.000 and 25.001 not; zero distance; same utility excluded; missing center never pairs; T=180 timely, 181 not; window touching at one day = overlap; leap-year gap
Plain asserts. `uv run python pipeline/test_overlaps.py` exits non-zero on failure. CI runs it.

## Match verification (sponsor guide, Part 2)
For every `high`/`medium` endpoint:
1. Open `source.url#page=N` and re-read the name, zone, description and landmarks.
2. Open the OSM feature: right state, plausible county for the GPC zone or DESC area, operator consistent where tagged.
3. A similar name in the wrong county -> downgrade with a reason.
Log each check to `data/verification_log.csv`: `project_id, endpoint, verdict (confirmed|downgraded), reason, checked_at`.

## Pair verification
For every Tier 1-2 pair: recompute the distance from the stored coordinates, confirm both dates on the source pages,
confirm the shared-facility claim (same physical substation, not just the same name), and read the Gemini brief for any number that isn't in the record.

## Live-site checks (issue 15)
- Every judge requirement is visible without instructions: map with both utilities, highlighted pairs, ranked list, estimate card.
- Every evidence popover link resolves to the right page.
- 390 px: usable, nothing overflows. Keyboard: tab through the list, Esc closes the drawer.
- Console: no errors. Secrets: `GEMINI_API_KEY` and `MONGODB_URI` absent from `web/.next/static` and API responses.
- Gemini-down drill: on a preview deploy with an invalid key, the map, list and zones still work, and briefs/Ask show their fallbacks.
- Use `webapp-testing` (Playwright) for a scripted smoke test: load, click the first opportunity, open the pair page, print preview.

## Submission claims
Every number in the Devpost write-up or pitch (counts, distances, estimates) is re-checked against the live app on the day it's written.
