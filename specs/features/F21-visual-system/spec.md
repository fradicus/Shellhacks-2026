---
id: F21
name: Visual system and frontend pass
lane: B
agent: frontend-engineer
phase: 5
depends_on: [F19]
owns: [web/components/brand/]
cut: allowed
---

# F21 Visual system and frontend pass

Added by the human on 2026-09-26 after the sponsor reviews. The judges singled out the time view ("that user
interface is phenomenal"); every other page still wears the provisional F00 light theme. F21 makes the whole app
one product in the time view's language. Background: [C16 sponsor context](../../decisions/C16-sponsor-context.md)
(when merged) and [F21 decisions](../../decisions/F21-visual-system.md).

## Site structure
1. `/` becomes the marketing page, built by another contributor. **F21 never edits `web/app/page.tsx`.**
2. The time view (`/time`) is the app's main surface. The nav calls it **Overlaps** and lists it first among app
   routes; `/pair/[id]` marks it active. The URL stays `/time`, so `?pair=` links and tests keep working.
3. `/` is labeled **Home** in the nav until the marketing page ships its own header.
4. When the marketing page replaces `/`, the old overlap map (`web/components/map/`, `web/components/list/`) has no
   importer left. F05 deletes it in a `[FIX-F05]` after `grep` shows no imports; not before.
5. Folded into the time view (FIX-F19): a provenance strip (analysis date, source ids, fixture badge), a
   **Projects** drawer listing every current project including unlocated ones and unknown dates, and a no-WebGL
   fallback that keeps the ranked pair list and the drawer usable.

## Visual system
- **Night instrument.** Dark surfaces everywhere, warm off-white ink at four opacities, one cool accent (sky) for
  selection, focus and "today". The two utility colors are the only saturated hues; bands and states are
  desaturated and always carry a text label.
- **Type.** Big Shoulders Display for headings and hero figures; Public Sans (the U.S. Web Design System face) for
  body and UI; Martian Mono for numbers, ids, units and coordinates. Loaded once via `next/font/google` in the root
  layout. No serif.
- **Surfaces.** Glass panels with hairline edges and a faint top highlight; no drop-shadow cards on white.
- **Readouts.** A figure is a display-font number plus a mono unit and source line, e.g. `4.31` `mi · stored`.
- **Unknown is drawn.** Null values get a faint diagonal hatch plus the word "unknown", never an empty cell or
  a grey that disappears on dark.
- **Motifs.** The 25-mile ring and the "today" line recur as dividers, empty states and progress marks.
- **Documents stay lit.** PDFs and source text sit on a light page inside the dark shell.
- **Print is light.** `@media print` swaps to a light token set; exported cards never print dark.
- **Motion.** One staged rise per page load, hover light-ups, no loops; `prefers-reduced-motion` removes all of it.

## Per-route moments
| Route | Owner PR | Moment |
|---|---|---|
| `/time` | FIX-F19 | Shared tokens and fonts; serif replaced; items from Site structure 5 |
| `/pair/[id]` | FIX-F11 | Case file: A and B side by side with utility stripes, distance and gap readouts, evidence as lit pages |
| `/changes` | FIX-F14 | Each change as a before→after bar on a date axis, stored dates only |
| `/coverage` | FIX-F15 | Extracted → located → reviewed as gauges, numerator and denominator always printed |
| `/gemini` | FIX-F16 | Code-review layout: source, Gemini, parse; a match/mismatch gutter like a diff |
| `/impact` | FIX-F17 | Inputs panel; null dollars hatched as unknown |
| `/explore`, `/search` | owners | Inherit tokens; bespoke work only with the owner's agreement |

## Requirements
- Visual only. No data, API, schema or ranking change. Headings, labels, roles and accessible names stay as they
  are, except the nav labels in Site structure 2–3, so e2e selectors keep matching.
- Only stored values are shown (mission rules); unknown stays visible and labeled.
- Contrast: WCAG AA (4.5:1 body text, 3:1 large text and UI boundaries) on the dark tokens. Visible focus on every
  control. Color never carries meaning alone.
- No new npm dependencies. Three font families at most.
- Every MapLibre basemap in F21-touched routes uses the dark style with POI labels hidden.

## Delivery
1. `[C17]` this spec, the roadmap row and the decision record.
2. `[C18]` foundation: `globals.css` tokens (color, type scale, space, radius, glass, motion, print), fonts in
   `layout.tsx`, nav restyle and labels, `ui/` primitives restyled plus `Readout` and `Unknown`, and the `Mark` (two overlapping service rings) exported from
   `nav/` so the marketing page can reuse it. `web/components/brand/` holds later shared motifs, if any.
3. One `[FIX-<ID>]` per route in the table's order: F19, F11, F14, F16, F15, F17. Each touches only that feature's
   `owns`. If a route already has an open PR from its owner, F21 waits for it and rebases instead of competing.

## Validation
- Per PR: the tech-stack Checks, e2e smoke, and screenshots at 1440 and 390 px of each touched route.
- A contrast check of the token pairs, recorded in the decision file.

## Defaults
- Dark only. A light "daylight/field" token set is later work, not F21.
- If time runs out, stop at the end of a route: tokens already make untouched routes coherent.
- Work in a separate worktree and preview port; the demo server stays on `main` until the foundation is verified.
