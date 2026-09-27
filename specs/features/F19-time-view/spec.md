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
2. **Heights are display only.** Axis ground = 1 January of the year before the analysis date (or the earliest drawn
   year, if later), declared on screen. A filed date before the ground keeps its facts in every text and lies flat on
   the ground, counted in the Projects tray; it never stretches the planning axis (2026-09-27, see below). Scale is
   pixels per year, set by the zoom (no user slider, [F19-zoom-scale](../../decisions/F19-zoom-scale.md)). Height never feeds distance, overlap or rank.
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

## National map integration (issue #139)

The user's explicit follow-up assigns this bounded implementation to Codex under
`specs/decisions/F19-national-map.md`. Fetch the active national projection used by `/explore` and
render confirmed nonlegacy centers on `/time` by default. Preserve native IDs, actual owners,
source lifecycle status, milestone precision and site/complete/partial endpoint evidence. Exclude
national legacy projections and preserve stored pairs without calculating additional overlaps.

Expose source and independent review evidence when selecting a national project. Disclose national
unavailability and map truncation; link to the explorer for unlocated records. Default bounds include
the delivered points. Validate projection/deduplication and date precision, desktop/mobile selection,
2D/3D, navigation re-entry, fallback behavior and the repo-wide checks.

## Planning window (2026-09-27)

The user reported the axis running 2001–2035 after the national integration: 566 of the 612 drawn national records
are ones their publisher lists as in service, dated 2001–2025, which pushed "today" to the top of the axis. `/time`
plans and `/history` (F37) keeps the record, so `/time` now draws national records that are not in service; the
in-service count links to History. The ground rule in step 2 bounds the axis to about 2025–2035 on the current data.
Stored pairs, distances, gaps and rankings are unchanged. Each project card links to `/history?origin=<key>`.

## Scope and focus (2026-09-27)

The user reported that the national view is overwhelming: 1,400 near-identical cream pillars, all full height, in
five dense blobs. The user asked for a way to go from the national picture to the part a person cares about, by
region, by state, and by "everything within 25 miles of this point", without adding more clutter. Decisions:
[F19-scope-focus](../../decisions/F19-scope-focus.md).

**The one idea.** There is always one *scope*. The national view stays as the opening shot. Choosing a scope lifts
the projects inside it to their dates and lays everything else down as a faint ground trace. Height keeps
meaning one thing only: the filed in-service date of a project you are looking at.

15. **Scope bar.** A single control at the top centre of the map, between the side panels (top left on phones).
    Closed, it reads the current scope and its count: `United States · 1,414` or `Texas · 569 of 1,414 ×`. Opened, it
    is one search field over two tabs, each option with its drawn count:
    - **Places** (the default): `United States` first (clears the scope), then the four Census regions largest
      first (`census_region_code` of each state in the committed Census geography), then every state with at least
      one drawn project, A–Z, down two columns.
    - **Grid**: the stored `planning_region` of national projects, grouped case-insensitively, largest first, for
      the plans named in `scope.ts` only (ERCOT, NYISO, ATC 10-year …). Any other stored value (some imports stored
      a document's section heading there) is not a plan and is not listed. It is the plan a record was filed in,
      not an inferred operator. The tab ends by saying how many drawn projects have no plan on file; those are
      reachable under Places.
    Typing searches both tabs. Keyboard: ↑/↓ move, ←/→ switch tabs, Enter picks, Esc closes; `/` opens it. Only one
    scope is active; picking replaces it. The pin is not in the list: it is its own button beside the bar (item 19).
16. **Membership, from stored facts only.** A national project is in a state if the state is in its stored `states`
    (so a two-state line is in both). A legacy project is in the state of the filing it came from: `desc-*` is South
    Carolina, `gpc-*` is Georgia. Region follows state. A pin scope contains every drawn project whose stored centre
    is within 25 statute miles of the pin, by the matcher's own haversine (R = 3,958.8 mi). Nothing is recomputed
    for pairs; the pin is a lookup, not an overlap.
17. **Focus.** In scope: unchanged. Out of scope: no pillar, no bead, no halo; only a small neutral-grey ground ring
    at low brightness, so the national shape stays as context without competing. The grey is distinct from every
    data colour, so a grey ring never reads as "no date". Out-of-scope projects are not pickable. The today sheet,
    the year ruler and the sweep counter follow the scope. A selected or previewed pair still wins over scope.
18. **Arrival.** Choosing a scope flies the camera to the scope's drawn projects (pin: the 25-mile circle) and
    replays the timelapse for just that scope (1.6 s; reduced motion: at once), so a region rises in date order.
    **Overview** and the story return to `All projects`.
19. **Pin.** A round reticle button beside the scope bar (or `P`) arms the pin; the next map click drops it and
    the bar reads `Within 25 mi of pin`. The 25-mile circle is drawn around the pin with the pair view's ring, labelled `25 mi · N projects`.
    Every project card also offers **Within 25 mi →**, which pins its stored centre. The All projects drawer lists
    the scope's projects (for a pin, nearest first, with distance).
20. **Lists follow scope.** The pair tabs count and list pairs with both ends in scope; the empty state names the
    scope. The tray counts and the drawer list are the scope's.
21. **Shareable.** `?scope=region:3`, `state:48`, `plan:ercot` or `pin:29.7604,-95.3698` opens on that scope; the
    URL follows changes. An unknown plan, or any malformed value, is ignored.

### Requirements (scope)
- No inferred operator, state or location. Counts are counts of drawn projects; unlocated ones are never scoped.
- Scope never changes a pair, distance, gap, rank, date or tier. Clearing it restores the exact previous view.
- Accessible: the scope control is a labelled combobox/listbox; the chosen scope and its count are announced.

### Validation (scope)
- `node --import ./tests/web/operations-providers/loader.mjs --test web/components/time/scope.test.ts` (parse and
  format round trip, rejection of malformed values, haversine against the matcher, pin boundary, legacy states).
- Screenshots at 1440 and 390: national, a region, a state, a grid plan, a pin, a pair selected under a scope.
- Repo-wide checks.

### Deferred
- A cursor-following focus lens: it does the same job as the scope, reads worse on a trackpad, and would need a
  GPU path to stay cheap. Revisit only if a scoped view still feels crowded.
- Rebuilding GPU buffers on every hover change is fine at 1.4k projects; move emphasis to a shader attribute when
  the drawn count passes ~10k.
