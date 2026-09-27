# C59: History parity with Overlaps (F54)

Recorded 2026-09-27. The user asked Claude local for a spec to bring `/history` to rough parity with `/time`, using
its best design judgement ("we're trying to place first for our track"). This contract adds
[F54](../features/F54-history-parity/spec.md) and assigns it to claude-local. Code ships as `[FIX-F37]` PRs.

## Evidence (read from `main` at 8883e12)
- `HistoryView.tsx` colors a project by `TIER_COLOR[p.tier]`. On live data the default window has tentative 2,173 ·
  confirmed 552 · owner-published 75 · DESC 10 · GPC 6 · no owner mapped 5 (counts from #334), so 77% of the ink is
  `#f0c36a`, the same amber as the plane and ledger.
- `historyLayer.ts` `rebuild()` pushes every lit stem from `z = 0` (the window start) to `min(top, plane)`.
- `builtRows` is a list of `actual` events, and it's shown as "Built" next to "Projects".
- `/time` has `ScopeBar` + `scope.ts`, a year numeral with "N of M … by then", state inks from `stateInks(usStates)`,
  a folded "Data and sources", and a dock without the height slider. History has none of these.

## Choices
- **Color by state, tier by glyph, meaning by bead.** Three encodings, three channels. Tier moves to the ground
  mark because F37 already uses the bead shape for evidence meaning. That's the page's core fact, and it can't be
  shared with tier.
- **Stems span the documented record.** Height is time, so a stem should cover only dates the record documents. The
  window start isn't a fact about any project. A faint drop keeps each bead anchored to its place.
- **Amber is chrome only.** The archive palette stays (plane, ledger, overline, warm background), but no data point
  shares its hue.
- **Keep the ledger and the slip chart.** They're History's own ideas. Parity means the shared frame (scope,
  readout, rail, dock, phones), not deleting what `/time` lacks.
- **Rejected:** drawing only beads without stems, which lose their ground and read as floating dust in 3D.
  Forking `timeLayer`, which F37's defaults forbid. A History film like F53, which is too much for the time left.
  Record mode (item 9) gets most of its value for demo footage.
