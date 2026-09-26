# F05 decisions (map + ranked list)

1. **Default view.** Open `future` if it has any overlaps; otherwise the first non-empty view (historical, then
   tentative), with a visible note that zero future overlaps is a valid result. Fixture mode therefore opens on the
   6 historical sample pairs. Undo: set `initialView` to `"future"` in `web/app/page.tsx`.
2. **MapLibre worker from jsDelivr.** maplibre-gl v6 finds its module worker relative to its own file, and the Next
   bundler moves that file, so the worker 404'd ("Worker failed to load"). F05 can't add files to `web/public/`, so
   `setWorkerUrl` points at `cdn.jsdelivr.net/npm/maplibre-gl@<installed version>/dist/maplibre-gl-worker.mjs`
   (maplibre wraps cross-origin worker URLs in a blob itself). If the CDN is blocked, the map shows its failure message
   and the list and project table still work. Undo: serve the worker same-origin (needs a `[C<n>]` for `web/public/`).
3. **Row interaction.** "Rows are buttons linking to /pair/[id]" and "clicking a row fits both projects" conflict for
   one element; the row is a button that selects the pair on the map, and each row carries an "Evidence →" link to
   `/pair/[id]` next to it (no nested interactive elements).
4. **Connector label** is a MapLibre popup at the midpoint ("5.65 mi center-to-center, not a route") rather than a
   symbol layer, so it doesn't depend on basemap glyphs.
5. **Distance order** sorts by unrounded `distance_mi`, which reproduces the sponsor sheet's OVL_1..6 order.
6. **Clicking a project** highlights it and every partner in the current view, draws a connector to each, and outlines
   those rows in the list.
