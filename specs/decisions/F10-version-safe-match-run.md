# F10: version-safe full-corpus match run

## Decision

The production adapter binds each accepted F09 endpoint to exactly one active project version using `project_id`,
`source_id`, `project_key`, endpoint index and normalized endpoint name. It verifies F09's canonical DESC, GPC and OSM
input fingerprints against the current parsed inputs, rejects duplicate slots, stale bindings and source-gated accepted
evidence, excludes unknown owners, and ignores any pre-derived center. The complete location corpus must have one
globally unique record per actual filed endpoint slot, including rejected records. Accepted coordinates reject booleans,
non-finite numbers and values outside latitude/longitude ranges. Only the frozen `matches.core.center`, `overlaps` and
`priority_sort` functions calculate match results.

The summary separates every known-owner DESC×GPC combination from the subset whose centers can actually be evaluated,
then reports overlaps by view and distance band plus explicit exclusion counts. Every emitted pair begins as
`needs_review`; F13 alone can confirm it. The sponsor golden fixture uses the same adapter and must yield six overlaps,
19 spatial nonmatches and priority order OVL_2, OVL_3, OVL_1, OVL_4, OVL_5, OVL_6.

## Result

The accepted F09 corpus has 262 active project versions and 89 accepted endpoint locations. Seventy-nine projects
have centers, including 22 whose owner remains unknown; 16 DESC and 41 Georgia Power projects are eligible known-owner
centers. The summary therefore reports 7,452 active known-owner combinations, 656 centered pairs evaluated, 637
spatial nonmatches and 19 overlaps. Sixteen overlaps are historical and three tentative; one is band 0 and eighteen
are band 1. No future pair is claimed, and all 19 begin as `needs_review`.
