---
name: map-ui
description: Build the Gridlock map interface with MapLibre GL in Next.js - layers, colors, interactions, ranked list, detail panel. Use for any web UI work on the map page.
---

# Map UI

Libraries: `maplibre-gl` only (no react-map-gl, no mapbox token). Basemap style `https://tiles.openfreemap.org/styles/positron`.
Render the map in a client component; load data from `/api/projects` and `/api/overlaps` once.

## Layers
- `projects-desc`, `projects-gpc`: circle layers on centers, two distinct colors (colorblind-safe, e.g. blue `#2563eb` / orange `#ea580c`); radius by confidence (low = hollow ring).
- Line from endpoint A to B for two-endpoint projects, same color, thin.
- `overlap-links`: line between the two centers of each overlap, width/opacity by score. Selected pair thick + labeled with distance.
- 25-mile ring (turf-free: `circle` of 64 points computed in 10 lines) around the selected project.

## Interactions
Click a project -> its overlaps light up, list scrolls to them. Click a list row -> `map.fitBounds` on the pair, open detail panel.
Detail panel: both projects (utility, name, date, cost or "redacted", confidence + match_note, PDF page), distance, gap, drivers, estimate card with assumptions, Gemini brief.
Filters (distance, gap, confidence) update layer filters with `map.setFilter`, no refetch.

## Layout and polish
Desktop: map 65% / list 35%. <= 768px: map 55vh, list below. Legend always visible. Keyboard: list rows are buttons, Esc closes panel.
Header: product name + one sentence of what it does + "Data: DESC SCRTP 2024-2028, Georgia Power 2025 IRP".
