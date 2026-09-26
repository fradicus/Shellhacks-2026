---
name: "Implement canonical overlaps and priority"
assignee: "geo-engineer"
project: "gridlock"
---

# Implement canonical overlaps and priority

Dependencies: resolve-locations, golden-reference, contracts

## Work
Implement all-pairs matching, strict haversine threshold, exact day gaps, null-date behavior, versioned canonical pair IDs and distance-band priority. Add optional R2 hypothetical-date/impact calculations only using documented formulas.

## Acceptance
Exact golden results plus 19 negatives; product order OVL_2, OVL_3, OVL_1, OVL_4, OVL_5, OVL_6; boundary tests; published inputs immutable under scenarios.

## Run discipline
Use the attached local skills. Confirm prerequisites and authorization, check out the issue, stay inside assigned paths and budget, and attach evidence plus remaining gaps to the handoff. Do not mark a future or unexecuted check as passed.
