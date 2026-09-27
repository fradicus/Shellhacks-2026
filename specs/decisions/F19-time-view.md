# F19 Time view: decisions

1. **Height is pixels per year, not metres.** Plan E's `z = 1000 m × years` is invisible at regional zoom and huge at
   pair zoom. The layer multiplies years by `yearPx × metres-per-pixel` at the map centre each frame, so a year is the
   same height on screen at any zoom. The slider shows the scale in use; it rises to 84 px when a pair is selected so a
   day gap is legible, and returns to the fitted value on "Overview". Undo: fix `metresPerYear` to a constant.
   *Superseded 2026-09-27 by [F19-zoom-scale](F19-zoom-scale.md): the slider is gone and years grow with the zoom.*
2. **Axis ground = 1 January of the earliest drawn year**, declared in the masthead. It's an axis origin, not a date
   given to any project.
3. **Month/year dates draw as the whole span** (a column with ring caps). Today's data has none (261 exact, 1 unknown),
   so that legend row only appears when such a project is drawn. Unknown dates: ground ring only, listed in "Not drawn".
4. **Only stored numbers are printed.** The bracket label is `match.time_gap_days`; the ground label is
   `match.distance_mi` to 2 dp. Nothing is recomputed in the browser. A null gap draws no bracket.
5. **Three.js inside MapLibre** (custom layer, shared GL context, mercator projection forced). Fat lines
   (`LineSegments2`) and point sprites keep widths constant in screen pixels. All materials skip the depth test and are
   ordered explicitly: ground, below-today, the glass sheet, above-today, drafting marks, so the sheet veils only what's
   under it. Picking is done in screen space from the last frame's projected pillars.
6. **Dark OpenFreeMap style** for this route only, POI/transit labels hidden, others dimmed. The other routes keep
   Positron.
7. **Fonts** (Instrument Serif, Instrument Sans, Martian Mono) via `next/font/google`, scoped to this route's
   wrapper. The build fetches them once; CI has network.
8. **Checked with real data** in a loopback MongoDB (`python -m load` of main's `data/`), not Atlas; and in fixture mode.
   Screenshots were taken with headless Chromium (SwiftShader), not a GPU browser, so frame rate wasn't measured.
9. **"Play the story" picks its pairs from the data**: the top-ranked pair in the open view, then the pair with the
   widest stored day gap. Captions contain only stored distance and gap. Nothing is hard-coded, so the tour stays true
   when the corpus changes. Undo: remove the button; nothing else depends on it.
10. **`/time?pair=<id>`** opens on that pair (switching to its view). The incoming id is held in a ref until the intro
    consumes it, because syncing the URL first erased it (including under React's double-invoked dev effects).
    Arrow keys step through the ranked list unless focus is in an input or on the map canvas.
11. **Unmapped owners show their filed code** ("Owner code MEAG, not mapped") instead of "Owner unknown": the 70
    unmapped current projects carry GTC, MEAG or DU. Matching is unchanged (D3).

## 12. Polish pass (issue #119)
- **Sweep instead of a global grow.** The old intro scaled every pillar at once, so timing was invisible. Clipping each
  pillar at a rising sweep shows order in time, which is the view's point. Alternative: animate the camera only, but
  that says nothing about dates.
- **Rings, not a lens.** Two 25-mile circles show the rule as defined (a center inside the other's circle). A filled
  intersection would suggest an "overlap area" that the method does not compute. Rejected.
- **Fake bloom.** EffectComposer needs its own render targets. The layer draws into MapLibre's framebuffer, so glow
  is additive halo sprites. The cost is that glow doesn't bleed across lines, which is acceptable.
- **Booth mode reuses the story.** A second scripted camera path would drift from the facts the story already derives
  from stored values.
- **Scrubber labels itself.** Moving the sheet off the analysis date relabels it "As of"; showing "Today" at another
  date would be false.
