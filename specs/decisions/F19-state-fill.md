# F19 state fill (2026-09-27)

## Decision
Fill the states under `/time` in one of two modes, **Map** (atlas colors, neighbors differ) by default and
**Density** (drawn projects per state), switched in the legend. Rebuild the legend around what is drawn.

## Why
- The overview was glowing points on a black map: the country's shape, and which state a cluster sits in, had to be
  read from faint basemap borders. A filled map is legible to a general judge at a glance.
- Map colors are the familiar atlas; Density argues something (Texas, New York and California carry the load). The
  Map mode has no meaning to explain, so the legend says outright that its colors only tell neighbors apart.
- Both palettes are cool (blues, teals, violets, one rose, one green) so the warm, mostly tentative gold points stay
  the brightest thing on the map and the two layers never share a hue.
- Density uses a square-root scale: on a linear one, Texas (569) leaves most states indistinguishable from zero.

## Data
Census TIGERweb generalized 1:20M states, shoreline-clipped (the non-generalized TIGERweb layer used for F09's
Georgia/South Carolina boundaries follows legal boundaries into the Great Lakes and coastal water, which reads wrong
as a fill). Stored unmodified so the SHA-256 in `usStates.source.json` verifies. Colors are derived in code from
shared border vertices, not stored, so the data file stays the Census response. 238 KB, loaded with the map chunk,
not the page.

## Legend
The old legend listed every legacy owner on every view and prose-length labels. It now lists only kinds with at
least one drawn project, with counts, and shows the pair-gap and out-of-scope glyphs only when they apply. Legacy
owner rows remain when legacy projects are drawn (they are, in the live data: 79).

## Not done
- No state toggle on phones: the legend is hidden below 860 px, as before; phones get the Map default.
- No grid-plan or operator fills: there are no committed plan boundaries, and drawing inferred territories would be
  inventing data.
- The choice is not in the URL; add `?states=density` if a shared link needs it.
