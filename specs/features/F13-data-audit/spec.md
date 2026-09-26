---
id: F13
name: Independent data audit - locations and featured pairs
lane: C
agent: qa-verifier
phase: 2
depends_on: [F10]
owns: [tests/pipeline/test_f13_, data/review/audit/, reports/audit/]
cut: allowed
---

# F13 Data audit

The sponsor guide warns that the common false match is a similarly named substation in the wrong county. Catch those.

## Plan
1. For the **top 15 matches** and every endpoint they use:
   - re-read the source page (DESC public PDF; Georgia table row by page number)
   - open the OSM feature: is it the right state, a plausible county for the DESC area or GPC zone, and the right operator where tagged?
   - recompute the distance from the stored coordinates using your own haversine
   - confirm both dates against the page
2. Write a verdict per pair and per endpoint to `data/review/audit/audit.json` (schema `review`: `confirmed` or `downgraded`, with the reason). The loader applies `confirmed` to `review_state`.
3. **Extraction spot check:** 12 DESC cards, where you read the page and compare it to F03's fields. Write the counts to `reports/audit/extraction_check.md` (F15 and F16 display them if present).
4. `reports/audit/summary.md`: pairs confirmed or downgraded, the common failure modes, and any `[FIX-]` issues filed.

## Validation
- `tests/pipeline/test_f13_*.py`: the audit file validates against the `review` schema, and every downgraded record has a reason.

## Defaults
- If you can't confirm a pair, don't mark it confirmed. A downgrade isn't a failure; it's the product working.
- A hash-verified cached OSM feature may support a conservative downgrade when a live feature-page inspection or county/project-area identity is unavailable. Record that limit explicitly; cache inspection does not establish positive location identity.
- Bind verdicts to current source/filing/endpoint facts through the safe F06 projection/hash helper. Reuse no production matcher or parser for independent numerical or source checks. Historical source observations must be distinguished from the refreshed accepted output.
