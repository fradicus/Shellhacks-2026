---
name: "overlap-analysis"
description: "Compute exact sponsor overlaps, transparent priority, versioned pairs and explicitly hypothetical scenarios."
---

# Overlap analysis

## Inputs
Active project versions, accepted endpoint centers, verified owners, analysis date and rule versions. Golden mode instead uses the sponsor workbook's original labels verbatim.

## Procedure
1. Compare distinct projects from different verified utilities. Compute every cross-utility pair in the small initial corpus; do not let a database candidate-radius mismatch discard boundary cases.
2. Use the sponsor midpoint/single-endpoint rule. Convert degrees to radians and calculate haversine with radius 3958.8 miles; clamp its intermediate value to [0,1]. Eligibility is unrounded distance strictly below 25 miles. Exactly 25 is excluded.
3. For two exact in-service dates compute their absolute calendar-day difference. Missing/month/year-only dates yield null exact gaps. Do not treat in-service proximity as construction overlap or drop a spatial pair because a date is missing.
4. Rank selected-view pairs by distance band (0 under 10 miles, 1 from 10 to under 25), then gap with unknown last, then unrounded distance and canonical IDs. Ten miles is a product assumption, not a new eligibility rule. Keep workbook IDs independent from product rank.
5. Persist both project versions, analysis date and rule/rank versions in the match key. Keep historical, future and tentative views distinct. Canonicalize ID order to avoid duplicate reverse pairs.
6. If the R2 scenario feature is enabled, copy published facts into a separate hypothetical state. User-entered dates reuse the same gap formula and are visibly assumptions; reset restores published dates. They cannot mutate source records or prove construction feasibility.
7. Optional savings arithmetic is avoided mobilizations times sourced unit cost minus coordination/transfer cost. Any missing input produces null. Keep negative outcomes, cite all factual inputs and label user scenarios. Never extrapolate the contractor anecdote as a ratio.

## Output and checks
Exact OVL_1–OVL_6, 19 nonmatches, expected gaps and rounded distances; rank order OVL_2, OVL_3, OVL_1, OVL_4, OVL_5, OVL_6. Test the strict threshold, missing geometry/dates, ties, leap dates, input order and null impact. Atlas/UI consume these canonical results, not independent competing math.
