---
name: map-ui
description: Build the Gridlock web UI with MapLibre GL in Next.js - map layers, Opportunities/Timeline/Zones views, evidence popovers, zone Gantt, pair memo print view, Data Quality page. Use for any web UI work.
---

# Map UI

Libraries: `maplibre-gl` only for the map (no react-map-gl, no Mapbox token). Basemap: `https://tiles.openfreemap.org/styles/positron`
(light) and `.../dark` (dark mode). Gantt and charts: plain SVG/CSS, no chart library. Load `/api/projects`, `/api/pairs` and `/api/zones` once; filter on the client.

## Home page
- Header: "Gridlock", one line ("Where Dominion Energy SC and Georgia Power are planning work near each other"), a Current/Snapshot toggle, and the analysis date.
- Layout: map (65%) plus a side panel with tabs **Opportunities | Timeline matches | Zones**. At <= 768 px: map at 55vh with the panel below.
- **Stat strip** above the tabs: `N projects · M located · K nearby pairs · Z zones`. Each number links to the Data Quality page.
- Opportunities: tier badge, both project names, distance, "in service N days apart", drivers, confidence badge. Click -> `fitBounds` the pair and open the pair drawer.
- Timeline matches: pairs with no tier, sorted by gap, visibly labeled "not nearby: timing only".
- Zones: cards with project count, date span, contention badge.
- Filters: max distance (default 25), T (default 180), min confidence, label, kind. Changing T recomputes label/tier on the client using the `overlap-scoring` rule.
- "Ask the grid" input: highlights the returned ids and shows filters as removable chips.

## Map layers
- Projects: circles at centers, DESC blue `#2563eb`, GPC orange `#ea580c`, other ITS owners grey with an outline. Low confidence = hollow ring. Past-dated = 50% opacity (Snapshot mode only).
- Project geometry: OSM line (solid) or a straight endpoint segment (dashed), in the utility color.
- Pair links between centers: width by score, color by tier (1 = deep red, 2 = amber, 3 = grey dashed). Shared-facility pairs get a small diamond marker on the shared substation.
- Selected project: 25-mi ring (a 64-point circle computed inline).
- Zones: a translucent hull or bbox when the Zones tab is active.

## Evidence everywhere
Every number in the drawer and on the pages is a button with a popover:
- distance -> formula, the two centers, and their endpoints
- date -> "DESC 2025-2029 list, p. 43" linking to `url#page=43`
- coordinate -> OSM feature link plus `match_note`
- cost -> source page; "redacted in filing" for GPC
- estimate input -> its source
This is the product's signature. Don't skip it.

## Pair page `/pair/[id]`
Both project cards, a mini map, a signal table (distance, shared facility, gap, window overlap, confidence), drivers,
the editable impact scenario (low/base/high inputs; the output updates live), the Gemini brief with open questions, and
"Print memo" (`window.print()` plus `@media print` CSS for one clean page with source citations). No PDF library.

## Zone page `/zone/[id]`
Zone map, SVG Gantt (known window = bar, in-service only = diamond, x axis in years), red contention bands, and
the sequence list ("crew could move X -> Y, N days apart"), plus the zone's pairs.

## Data Quality page `/quality`
Source manifest table (hash, filing date, status), counts by utility and confidence, check results (pass/fail with
counts), the unlocated projects list, extraction evaluation accuracy, and the last pipeline run time. Sperry's AI team hires for exactly this; make it look deliberate.

## Polish
Legend always visible. Keyboard: list rows are buttons, Esc closes the drawer, visible focus rings. Empty, loading and error
states for every panel. Map attribution for OSM/OpenFreeMap. Dark mode via `prefers-color-scheme`.
