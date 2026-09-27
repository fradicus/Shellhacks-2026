---
id: F54
name: History parity with Overlaps
lane: B
agent: frontend-engineer
phase: 7
depends_on: [F37, F19, F52]
owns: []
cut: allowed
---

# F54 History parity with Overlaps

Added by the user on 2026-09-27 ([C59](../../decisions/C59-history-parity.md)): "the history page is horribly
behind and is not at parity with overlaps". `/history` is `/time`'s sibling (F37: "looks and behaves very
similarly to the main time view"), but it was built before `/time`'s scope bar, year readout, state inks, quiet
rail and F52 pass, and it hasn't caught up. F54 brings it to rough parity. Like F52 and F53, F54 owns no code. It
ships as `[FIX-F37]` PRs in F37's paths and only imports from F19's paths.

## What's wrong (measured on `main` at 8883e12, live data, 1440 × 900)

1. **A gold wall.** Projects are colored by location tier, and 2,173 of the 2,821 in the default window are
   *tentative*, drawn in `#f0c36a`. That's the same amber as History's own chrome (plane, ledger, overline). One hue
   covers 77% of the ink, so there's no structure left to read. `/time` colors by state (`stateInk`) and shows the
   tier with the glyph.
2. **A barcode.** Every pillar runs from the axis ground (the window start, 2005) up to the plane. A project with one
   dated event in 2026 still gets a 21-year stem. So 2,821 stems of nearly equal height fill the frame, and the
   height carries no information.
3. **A rail of nine blocks.** Overline, title, lede, three stats, the verdict and its chart, the provenance lines
   (with the dataset hash), the contract note, Play, and then the list. The list starts 690 px down a 900 px
   screen. `/time`'s rail has five blocks and folds the provenance into "Data and sources".
4. **"Built 1,475" counts events** (`builtRows` is a list of `actual` events) and sits between two other counts,
   one of projects and one of events. F37 requires that counts separate projects and events.
5. **No scope and no year readout.** `/time` has the scope bar (state, region, grid plan, pin) and the big year
   numeral with "N of M … by then". History has a floating "PLANE · SEP 2026" tag, which slides under the nav
   when the camera moves.
6. **Dock clutter.** It has a "1 year = 14px" slider that `/time` doesn't show, and five fixed tier and owner color rows.
7. **Phones.** At 390 px the dock and the ledger sit on the scene, and the list starts below the fold.

## Requirements

In priority order. Cut from the bottom if time runs out.

1. **Stems span the record, not the window.** A project's lit stem runs from its earliest documented event to its
   latest event at or below the plane. Below its first event, a hairline drop to the ground marker anchors it.
   The drop uses the quiet-overview stem opacity × 0.3, and hovered and selected projects draw at full strength.
   The ghost above the plane, the glyphs, threads, spans, ripples and `calmAt` stay as they are. Heights still
   mean dates, and nothing moves.
2. **State inks for projects, amber for chrome.** A project's color is `/time`'s: `stateInk` for its stored state,
   `NO_STATE_INK` when none is stored, and the legacy DESC and GPC identity colors for legacy filings. The page
   reads the same `stateInks(usStates)` map that `/time`'s page reads. Amber is reserved for History's own chrome.
3. **Tier moves to the ground mark.** The ground marker uses `/time`'s tier glyph (confirmed ◉, owner-published ●,
   tentative ○). The pillar's beads keep F37's evidence-meaning shapes (actual solid, plan hollow, other square),
   so neither encoding has to share a shape with the other.
4. **The year readout replaces the plane tag.** At the top center, the scene shows the plane's year as a large
   numeral. It uses `/time`'s type and position, in History's amber. Beneath it is a line like
   `<n> of <m> projects documented in service by then`: the projects with a documented actual date at or before
   the plane, out of the projects in the window and filters. "Play the record" counts this numeral up. The floating
   "PLANE · <date>" tag goes. The exact plane date stays in the ledger's marker.
5. **The quiet rail.** Keep the overline, title, lede (one sentence), verdict and slip chart, Play, and the list.
   - The Projects / Events / Built stats leave the rail. The readout carries the built count.
   - The window, analysis date, dataset, legacy availability and fixture badge fold into a
     `Data and sources · <n> located projects` disclosure, styled like `/time`'s. It is closed by default.
   - The contract note moves into that disclosure, word for word.
   - The verdict chart hides when fewer than 20 rows qualify. The sentence stays.

   The list should start above 450 px at 1440 × 900.
6. **Scope bar.** Reuse F19's `ScopeBar` and `scope.ts` (places, grid plans, pin) at the top center, above the
   readout. Scope filters the list, the readout, the verdict and the ledger the way the window already does. The
   camera flies to the scope with the same fit `/time` uses. URL state is `?scope=`, parsed by `parseScope`, and it
   survives reload and back. `?origin=` keeps working and wins over scope for the "Near this project" list.
7. **Dock parity.** The height slider leaves the dock (`SceneControls` without `yearPx`), and the automatic fit
   stays. The legend follows `/time`'s order. The glyph rows (actual, plan, other, plan → actual, the plane) come
   first. After them are "Color: the project's state" and one tier row using the ground glyphs, with each tier's
   count in the window (from #334, if it has merged). Then the hints, 2D/3D and Overview.
8. **Phones (≤ 700 px).** Use `/time`'s phone order: the scope bar, then the readout, the scene at ~45 vh, the list,
   and finally the ledger. The dock collapses to 2D/3D, Overview and the legend fold. Nothing overlaps the scene's
   controls. The masthead stays hidden, as it is now.
9. **Record mode for Play.** While "Play the record" runs, the rail and the dock fade out (0.5 s), as in F53's
   cinema mode, and the camera orbits −16° → +4°. The readout and the ledger stay. Esc, Stop, or any input ends
   it and everything comes back. Reduced motion jumps to the end state.

## Requirements carried from the mission and F37
- Display only. No data, API, schema, event meaning, date, precision or count definition changes, except that the
  readout counts projects where "Built" counted events (item 4).
- Unknown stays visible: undated located projects keep their explicit list section. Unlocated projects stay counted
  and linked, and a project with no stored state keeps the no-state ink.
- F37's evidence rules, URL state, 2D toggle, WebGL and tile failure behavior, and the 390 px support all stay.
  Accessible names used by tests stay: "Play the record", the tab labels, "Projects with documented history".
- No F19 file is edited. Importing F19 exports is allowed ([F37 shared scene cleanup](../../decisions/F37-shared-scene-cleanup.md)).
  If an F19 component needs a prop to be reused, that's a `[FIX-F19]` PR of its own.

## Validation
- Change-scoped checks in `specs/tech-stack.md`. Add a unit check for item 1's stem extent: first event to
  min(last, plane), and empty when no event is under the plane.
- On live data, take headless screenshots of `/history` and `/time` side by side at 1440 × 900 and 390 × 844. Do it
  before and after each PR, and describe them in the PR. Check that the eastern cluster no longer reads as a
  solid wall and that the basemap coastline shows through it.
- A scoped link (`/history?scope=state:51`) survives reload. Play → Esc brings back the rail and the dock.
- Reduced motion (emulated): Play jumps to the end, and nothing orbits.

## Defaults
- Keep the ledger. It's History's scrubber and its differentiator, and `/time` has nothing like it to match.
- Keep the warm basemap background (`#0d0b09`). It's the archive's palette, and the points carry all the color.
- Suggested PR order is 1–3 together (the scene), then 4–5 (the rail), 6, 7, 8 and 9. Each is a `[FIX-F37]` PR.
- Another local session is polishing F37 (#334, "legend lists the colors on screen"). Rebase onto whatever merges
  first. Don't open a competing PR on the same lines.
- The last part adds `changes/F54.md` in an `[F54]` PR that touches only F54's spec, decision and change files.
