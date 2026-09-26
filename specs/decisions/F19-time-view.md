# F19 Time view: decisions

1. **Height is pixels per year, not metres.** Plan E's `z = 1000 m × years` is invisible at regional zoom and huge at
   pair zoom. The layer multiplies years by `yearPx × metres-per-pixel` at the map centre each frame, so a year is the
   same height on screen at any zoom. The slider shows the scale in use; it rises to 84 px when a pair is selected so a
   day gap is legible, and returns to the fitted value on "Overview". Undo: fix `metresPerYear` to a constant.
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
