---
id: F19
name: Time view (Three.js)
lane: B
agent: frontend-engineer
phase: 3
depends_on: [F05, F06]
owns: [web/app/time/, web/components/time/]
cut: allowed
---

# F19 Time view

Added by the human after run 1's freeze (Plan E VIS-01..04, issue 23's 3D part only; no national scope).

## Plan
1. `/time`: the overlap map on a dark basemap with a Three.js custom MapLibre layer. Each located current project
   stands on its center; its height is its filed in-service date on a vertical time axis.
2. **Heights are display only.** Axis ground = 1 January of the earliest drawn year, declared on screen. Scale is
   pixels per year (user slider, shown), so it reads at any zoom. Height never feeds distance, overlap or rank.
3. Exact dates draw as a bead on a light pillar. Month- or year-only dates draw as a column over the whole span; no day
   is picked. Unknown dates stay on the ground and are listed. Unlocated projects are counted, not drawn.
4. A translucent sheet at the analysis date ("today", 10-mile grid) and a year ruler.
5. Selecting a pair turns the camera side-on and draws a drafting dimension between the two beads, labeled with the
   stored `time_gap_days`; the ground link is labeled with the stored `distance_mi` (2 dp). Null gap: no bracket.
6. 2D toggle flattens the axis; facts, IDs and list are unchanged. The pair list (keyboard) carries every fact shown.

## Requirements
- Only stored values are shown: no recomputed distance or gap, no imputed dates. Review state shown as stored.
- Reduced motion: no animation. WebGL or tile failure: explicit message; the pair list still works.

## Validation
- lint, typecheck, fixture build; screenshots of overview, a selected pair, 2D and phone width.
- In a fresh visible browser tab, navigate Home → Overlaps → National explorer → Overlaps.
  On both Overlaps visits, the map container fills the stage and the basemap, pillars and year ruler render.

## Defaults
- `three` pinned exactly via this feature's `[C9]`. Fonts via `next/font/google` scoped to the route.
