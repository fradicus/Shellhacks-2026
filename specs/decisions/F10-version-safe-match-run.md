# F10: version-safe full-corpus match run

## Decision

The production adapter binds each accepted F09 endpoint to exactly one active project version using `project_id`,
`source_id`, `project_key`, endpoint index and normalized endpoint name. It verifies F09's canonical DESC, GPC and OSM
input fingerprints against the current parsed inputs, rejects duplicate accepted slots, stale bindings, source-gated
projects and unknown owners, and ignores any pre-derived center. Only the frozen `matches.core.center`, `overlaps` and
`priority_sort` functions calculate match results.

The summary separates every known-owner DESC×GPC combination from the subset whose centers can actually be evaluated,
then reports overlaps by view and distance band plus explicit exclusion counts. Every emitted pair begins as
`needs_review`; F13 alone can confirm it. The sponsor golden fixture uses the same adapter and must yield six overlaps,
19 spatial nonmatches and priority order OVL_2, OVL_3, OVL_1, OVL_4, OVL_5, OVL_6.
