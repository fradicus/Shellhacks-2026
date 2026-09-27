# F31: cache national map data by active dataset

## Ownership and scope

The user assigned this performance change to this Codex local session on 2026-09-27.
This is an F31 follow-up in the frontend-engineer role, implemented entirely within
F31's existing ownership. Original run gates are historical for this bounded task.
F19's active presentation work retains its owner. No map renderer, animation, visual,
point eligibility, evidence, count, export or database-writer contract changes.

## Problem and implementation

`/time` and `/history` both call `loadNationalExplorer({page: 1, limit: 1})`.
Every visit currently repeats the same national project/source/count/facet reads
and validation. Cache that successful Atlas result by the active dataset ID.

- Read `meta.national_active` on every request, outside the cache. Pin every query
  in a fill to that ID. New publications and rollbacks must use the selected ID.
- Cache only this unfiltered map request. Filtered/paginated explorer requests and
  exports keep their current behavior. Explicit snapshot mode bypasses the cache.
- Keep one entry per warm server instance, bounded to five minutes. Reuse an
  in-flight promise for simultaneous requests. Replace it on a dataset change.
  Failed queries/validation must not remain cached or fall back to an older dataset.
- A late failure for a superseded entry must not evict a newer successful entry.
- Preserve the complete payload, including evidence and uncertainty; no API shape
  changes. An unavailable active-pointer read still returns unavailable.
- Use the existing runtime; no dependency, shared cache service, framework-wide
  cache setting, or additional credential. Cold instances perform the normal load.

## Validation and acceptance

Test the actual loader with explicit database fixtures: cold/warm equality and
query reduction; concurrent requests; dataset switch and rollback; failure/retry
including validation failure and a superseded failed fill; pointer failure; filter,
page and snapshot isolation; expiry. Existing national tests and required CI pass.
Measure read-only Atlas cold/warm loader times and payload size when credentials
are available; report them as local loader measurements, not end-user page latency.
A diff review verifies the renderer and animation files are untouched.

## Limitations / undo

The cache is per server instance, so a cold start or deployment refills it. Dataset
contents are immutable under the existing loader; the five-minute bound limits
memory retention and refreshes metadata under the same ID. Serialization, legacy
queries, basemap loading, GPU work and the opening animation are unaffected.
Remove the small cache wrapper to restore uncached behavior.

## Measurements on 2026-09-27

Local read-only Atlas loader, active dataset `4aa0691b3154beacaba7d6e377813c703a26c8a8`:
3,472 map records; full explorer payload 14,178,406 serialized bytes. Four uncached
loads took 5,374 / 7,236 / 3,924 / 5,171 ms. With the cache, the cold load took
8,206 ms and three warm loads took 89 / 75 / 86 ms. Each measurement includes JSON
serialization; all four cached-run outputs were identical. These are small local
samples with variable network latency, not hosted page-load or frame-rate claims.
The installed Next Data Cache has a 2 MB entry limit, so this complete payload uses
the bounded in-process cache instead of silently exceeding that limit.
