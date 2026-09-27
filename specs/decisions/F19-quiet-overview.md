# F19 quiet overview (2026-09-27)

## Decision
In the national overview (no scope), draw unfocused points quietly: thin dim stems, dimmer dots, no halos. Light
them back up as the map zooms toward a region (`calmAt`: 0.25 at zoom ≤2.5, 0.4 at 4.2, 1 at ≥6.5), for a scope,
and for anything hovered or selected. Keep the intro sweep bright and settle afterwards. Year height at zoom 3.5
drops from 20 to 12 px and the overview tilt from 58° to 50°.

## Why
- 2,870 points each drew a pillar, bead, ground ring and two additive halos at full strength. Additive light sums,
  so dense states (Texas, Florida, the Northeast) turned white regardless of ink, and the overview read as noise.
- At 20 px/yr a 2041 filing stood about 340 px tall on a 17-year axis; tilted 58°, the pillars walled off each
  other. 12 px/yr with √2 growth per zoom only changes zooms below ~7; the room cap still governs scopes and pairs.
- Dimming by zoom rather than hiding keeps every project on the map (no invented clustering, nothing dropped), and
  keeps the per-point encoding (ink = state, shape = C25 tier) intact.
- The sweep stays at full glow so the opening still lands; the 1.2 s settle hands over to the readable resting view.

## Alternatives
- Switch to normal alpha blending: fixes the white-out but loses the lit look everywhere, including selections.
- Cluster or aggregate at low zoom: hides individual filings and needs a counting rule the spec doesn't have.

## Known limit
On a phone (zoom ~1.5) 2,870 fixed-size dots in ~300 px still saturate at the centre. Scaling dot size with zoom
is the next lever.

## Undo
`calmAt` returning 1 restores the old brightness; `yearPxAt` base 20 and `OVERVIEW_PITCH` 58 restore height and tilt.
