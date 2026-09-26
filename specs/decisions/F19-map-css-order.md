# F19: keep the time map positioned when another route loads MapLibre CSS

## Context

Issue [116](https://github.com/fradicus/Shellhacks-2026/issues/116) is reproducible with
Home → Overlaps → National explorer → Overlaps. On the second visit, the time map's
container computes to `position: relative` and zero height. Its canvas defaults to
300px tall, with the year labels near the top and the basemap and pillars clipped.
Browser stylesheet inspection shows a later MapLibre stylesheet overriding the
route's `.map { position: absolute }` with `.maplibregl-map { position: relative }`.
Both selectors have equal specificity. No stale build or lost context is needed.

## Choice

Scope the time-map positioning selector under `.stage`, so its required absolute
position does not depend on the order in which route CSS loads. This stays within
F19 ownership and uses the existing CSS module. Keep vendor CSS imports and map
lifecycle unchanged. Validate the failing route sequence before and after the fix.

## Alternatives and reversal

Moving all vendor CSS into the shared layout would require a contract change.
Context recovery and map remounts do not correct the measured CSS override.
Revert the selector change to undo this fix; the navigation regression would return.
