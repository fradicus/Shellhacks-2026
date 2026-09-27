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
