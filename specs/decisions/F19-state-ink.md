# F19 state ink (2026-09-27)

## Decision
Color each point by its state, in six pen inks with neighbors never alike, and leave the map as it was. Carry the
C25 location tier by shape instead: ringed (confirmed), solid (owner-published, including legacy filings), hollow
(tentative). Replaces the state fills of #259, reverted in #264.

## Why
- The user asked for "every state a color, like a map". Filling the states (#259) competed with the points and
  was rejected on review; putting the color on the marks keeps the map minimal and still reads as an atlas.
- The old colors meant location tier, but 2,342 of 2,737 drawn points are tentative, so the map was one gold
  color that washed to white in dense areas. State inks separate clusters that sit side by side.
- C25 requires markers to show their evidence tier and forbids color alone carrying review state. Shape now does
  it, on the marker itself. Legacy filings draw solid, never ringed, so they are never shown as reviewed.
- Halos are halved and the bead's white core is smaller, so dense clusters keep their ink instead of blooming.

## Data
Census TIGERweb `Generalized_ACS2025/State_County` layer 9 (States 20M), stored unmodified; only adjacency is
used. Computed on the server in `app/time/page.tsx`, so the 238 KB file stays out of the browser bundle.

## Not done
- A line crossing states takes its first stored state's ink; no split coloring.
- No per-view palettes (region or grid plan); the scope already lifts its own points.
