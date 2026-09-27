# F21 decisions

## 1. The time view is the main surface; `/` goes to the marketing page
- **Context:** the overlap map at `/` and the time view show the same pairs, tabs and evidence links. The time view
  adds the time axis and a 2D toggle; the old page adds only a sort toggle, a provenance strip and a full project
  table. Sponsors reviewed the time view and asked for nothing the old page has.
- **Choice:** marketing at `/`; the time view is labeled Overlaps and absorbs the provenance strip and project table.
  The sort toggle is dropped: priority order (`nearby-band-v1`) is the argued order.
- **Alternative:** keep both. Rejected: two maps of the same data invite "why are there two?"
- **Undo:** restore the nav labels; the old components stay in git history.

## 2. Fonts: Big Shoulders Display, Public Sans, Martian Mono
- **Context:** the time view used Instrument Serif. Editorial serifs read as a magazine and are overused in 2025–26
  landing pages; this product is for planners and foremen.
- **Choice:** signage and instrument type. Big Shoulders Display (condensed, made for civic signage) for headings and
  hero figures; Public Sans, the U.S. government's USWDS face, because every value here is public record; Martian
  Mono kept for numbers.
- **Alternative:** IBM Plex Sans Condensed + Plex Mono: coherent and safe, more corporate. Kept as fallback.
- **Undo:** the three families are tokens (`--font-display`, `--font-sans`, `--font-mono`).

## 3. How a cross-cutting restyle fits ownership
- **Context:** each route's CSS belongs to its feature; `ownership` forbids one PR touching all of them, and F21
  cannot own paths under another feature's prefix.
- **Choice:** frozen shared files via `[C18]`; each route via `[FIX-<ID>]` of its owner, visual only. Cross-lane FIX
  PRs (F15, F17) are authorized by the human's 2026-09-26 request; F31/F20 are left to their owner.
- **Undo:** each route is an independent PR and can be reverted alone.

## 4. Dark only
- **Context:** dark screens wash out in sunlight, and sponsors named field crews. The demo and the PM persona are
  indoors on laptops.
- **Choice:** dark only for now; everything is tokens so a daylight set is a later swap. Print uses a light set.

## 5. Contrast check (spec Validation)
WCAG 2.x ratios computed from the `:root` tokens in `globals.css`; translucent colors composited over the surface they sit on.
- **Body text passes everywhere (4.5:1).** `--text` is 13.8–17.5; `--muted` is 6.5–8.2; `--accent` is 12.3–15.6.
  Utility, band and state colors are 7.6–13.5 on every surface. Every badge's text on its own tint is 6.9–10.2.
  `--accent-ink` on `--accent` is 14.7.
- **One failure fixed.** `--text-3`, used for small mono labels, was `#7c7a76`: 4.68 on `--bg` but 4.42, 4.08 and 3.69 on
  `--surface`, `--surface-2` and `--surface-3`. It is now `#8c8a85` (5.81 / 5.49 / 5.07 / 4.58): the smallest step that
  passes on every surface while staying clearly dimmer than `--muted` (5.49 vs 7.73 on `--surface`), so the hierarchy holds.
- **Not covered here:** the time view's own translucent inks over the live map (a moving background). That is checked in F19.
