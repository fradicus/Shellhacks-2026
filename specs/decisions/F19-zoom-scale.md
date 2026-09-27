# F19 Time view: year height follows the zoom (2026-09-27)

Supersedes the slider in [F19-time-view](F19-time-view.md) decision 1.

**Context.** A year was a fixed number of screen pixels at every zoom, set by a 16–96 px slider. At continental
zoom 1,719 pillars sit a pixel or two apart, so anything tall became a wall of light, and at 96 px an eight-year axis
ran off the top of the screen. The right height depends on how far apart pillars sit on screen, which the viewer
can't judge for us.

**Options.**
- Constant screen pixels (the old rule): pillars stay as tall zoomed out as zoomed in.
- Constant metres (Plan E): height doubles per zoom level; invisible when zoomed out, enormous at a pair.
- Height grows with the square root of the map scale (chosen): √2 taller per zoom level.

**Choice.** `yearPxAt(zoom, years, room) = clamp(8, room / years, 20 · 2^(0.5 · (zoom − 3.5)))`
in `web/components/time/timeScale.ts`, evaluated by the layer every frame. `years` is the whole axis, or the
selected pair's top so its day gap can fill the room; `room` is 75% of the canvas height. The slider and its
"1 year = N px" label are removed from `/time`; the year ruler shows the scale. A pair no longer jumps to a fixed
84 px: framing it zooms the map in, and the formula grows its pillars. 40% of the canvas was tried first and capped
every zoom at about 21 px/yr on a 17-year national axis, so zooming in never grew the pillars.

**Undo.** Pass a constant to `yearPxAt` in `timeLayer.ts` and restore the `SceneControls` slider props in `TimeView`.

## Revision (2026-09-27)
The base is 12 px at zoom 3.5 (was 20), for the quiet overview ([F19-quiet-overview](F19-quiet-overview.md)). The
√2-per-level growth, room cap and 8 px floor are unchanged.
