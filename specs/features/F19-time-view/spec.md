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

## Polish pass (issue #119)
Motion and meaning, not more objects. Build order; each step ships only if the one before it is verified.
7. **Timelapse intro.** After the camera tilts, a sweep rises from the axis ground to the top year. Each pillar grows
   up to its own filed date and its bead flashes as the sweep passes it. A year counter reads the sweep year and
   "N of M filed in service by then" (exact dates, and month/year spans whose end is passed). Reduced motion: end state
   at once.
8. **The 25-mile rule on the ground.** Selecting a pair draws a 25-mile circle around each stored center in its
   utility's color, labeled "25 mi", growing in over about 0.7 s, and dims every other pillar further. The circles
   illustrate the rule (the other center lies inside); no overlap area is filled, because the rule is not an area.
9. **Glow and depth.** A soft halo behind each bead and a glow at each pillar's foot (sprites; the GL context is
   shared with MapLibre, so no post-processing). Points fade with camera distance.
10. **Booth mode.** After 25 s with no pointer, key or wheel input, the story plays on a loop with a slow orbit, and a
    chip says so. Any input stops it. Off under reduced motion.
11. **Time scrubber (stretch).** A dock control moves the sheet to any date between the axis ground and the top year.
    Pillars filed after it are ghosted, and the sheet and its label read "As of <date>", never "Today". Reset returns
    to the analysis date.
12. **Loading.** The two-ring mark draws itself while the basemap loads.
13. **List preview (issue #123).** Hovering or focusing a pair in the list lights its two pillars, draws its 25-mile
    circles and dims the rest before any click; a selected pair takes precedence.
14. **Provenance and every project (F21 site structure).** Under the stats: the analysis date and source ids. The
    "Projects" entry opens an All projects drawer: every current project, drawn ones selectable on the map and
    unlocated ones listed with a hatched "no located endpoint", filterable by name or ID. Without WebGL the view says
    so in one sentence, hides the 3D labels, and the pair list, detail card and drawer keep working.

## Requirements
- Only stored values are shown: no recomputed distance or gap, no imputed dates. Review state shown as stored.
- The sweep, scrubber and counts compare stored dates with a chosen date; they never change a pair, rank or fact.
- Reduced motion: no animation. WebGL or tile failure: explicit message; the pair list still works.

## Validation
- lint, typecheck, fixture build; screenshots of overview, a selected pair, 2D and phone width.
- Polish pass: screenshots mid-sweep, the selected pair with its rings, booth mode, and the scrubber; frame rate
  measured in real Chrome on the demo laptop's resolution (target: no sustained drop below 50 fps).
- In a fresh visible browser tab, navigate Home → Overlaps → National explorer → Overlaps.
  On both Overlaps visits, the map container fills the stage and the basemap, pillars and year ruler render.

## Defaults
- `three` pinned exactly via this feature's `[C9]`. Fonts via `next/font/google` scoped to the route.
