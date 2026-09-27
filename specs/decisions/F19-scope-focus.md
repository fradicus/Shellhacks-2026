# F19: scope and focus on Overlaps

2026-09-27. The user reported the national `/time` view as overwhelming and asked for region, state and 25-mile
views without more clutter, and handed the design to this local Claude Code session.

## Ownership
`web/components/time/` and `web/app/time/` belong to F19. Codex holds the C34 cleanup claim through #200
(`[FIX-F19]`) and #202 (`[FIX-F37]`). This work is stacked on #202's branch and opens as `[FIX-F19]` only after
both merge, so F19 never has two open PRs or two active writers.

## Choices
- **One scope, one control** instead of separate region/state/pin widgets: they answer the same question (which
  part of the map), so one slot keeps the chrome from growing. Undo: remove the bar; nothing else depends on it.
- **Fade out-of-scope to grey ground rings, don't shorten them.** Height means the filed date. A shortened pillar
  would misstate a date; a grey ground trace makes no date claim. Grey (not a tier or utility colour) keeps it
  distinct from in-scope undated projects, which draw coloured ground rings.
- **Not recoloured by region.** Position already separates regions, and colour must keep carrying the C25 location
  tier. The contrast between the lifted scope and the grey trace is what breaks up the single colour.
- **Grid plans are stored labels, not operators.** The live data (Atlas `8610d91`, 1,356 drawn national records)
  stores `planning_region` as each source filed it: `ercot` 569, `nyiso` 239, `frcc` 129, `atc-tya` 123, `miso` 60,
  `mn-biennial` 43, `PJM` 26, `iso-ne` 16, `NYPSC` 3, and none on 148. Mapping states or utilities to an ISO
  would invent a fact (Michigan alone is split between MISO and PJM). Labels are grouped case-insensitively (the
  source catalogue uses both `PJM` and `pjm`) and given readable names only.
- **Regions are Census regions** from the committed Census geography, as F31's explorer filter already uses.
- **Legacy state from the filing:** DESC's register is its South Carolina filing and the Georgia ITS Ten-Year Plan
  is Georgia's (F01, F02), so `desc-*` → SC and `gpc-*` → GA. The `sample` fixture has no state.
- **Pin radius = the overlap rule's 25 statute miles, by the matcher's haversine.** The pin lists neighbours;
  it creates no pair and no rank.
- **No cursor lens** (see the spec's Deferred list).

## Revision: Places, Grid and a pin button (2026-09-27)
The user reviewed the first scope bar: the grid-plan group was flooded, there was no way back to the whole country
from the list, and the list was long. They chose to keep both Census regions (legible to a general judge) and grid
plans (for sponsor judges), and to make the pin its own quick control.
- **Two tabs, not one long list.** Places (United States, regions, states) and Grid (plans) share one search, so
  typing still finds anything, but neither audience scrolls past the other's rows.
- **Grid lists only named plans.** F42's Pacific Northwest import stores PDF section headings in
  `planning_region` (`pipeline/pnw/build.py`: 83 distinct values such as `terminal facilities; bpa` on 312
  records). Those are not plans. F19 lists the plans it names and says how many drawn projects have none, rather
  than editing F42's data; the heading is also kept in the record's evidence, so F42 can null the field later.
- **Names as filed, not merged into operators.** ATC 10-year and Minnesota biennial stay separate from MISO:
  merging them would be our inference.
- **States A–Z down two columns.** People look a state up by name; two columns halve the height.
- **Pin is a button (`P`), not the last row.** It is picked on the map, not from a list.

## Superseded (2026-09-27)
"Not recoloured by region" is superseded by [F19 state ink](F19-state-ink.md): color is now the state, and the C25
tier is carried by shape.
