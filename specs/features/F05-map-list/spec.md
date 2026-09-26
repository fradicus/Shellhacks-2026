---
id: F05
name: Map + ranked list
lane: B
agent: frontend-engineer
phase: 1
depends_on: [F00]
owns: [web/app/page.tsx, web/components/map/, web/components/list/]
cut: never
---

# F05 Map + ranked list

## Plan
1. **Home page** `web/app/page.tsx`:
   - a header strip with the view toggle (Future / Historical / Tentative), the analysis date, and source versions
   - a MapLibre map (OpenFreeMap `positron` style) taking about 65% of the width
   - the ranked overlap list alongside it; at 390 px, the list sits below the map
2. **Map:** project centers as circles, DESC blue `#2563eb`, Georgia orange `#ea580c`, unknown-owner grey. Low-confidence locations as hollow rings.
   - Clicking a project highlights its overlaps.
   - Clicking a list row fits both projects and draws a straight connector, labeled "center-to-center, not a route".
   - A legend and OSM/OpenFreeMap attribution are always visible.
3. **List rows:** both project names, utility badges, miles (2 dp), "in service N days apart" (or "date unknown"), a band badge (<10 mi / 10–25 mi), a review state badge. Rows are buttons linking to `/pair/[id]`. Add a "distance order" toggle, which reproduces the sponsor sheet order.
4. **Accessible fallback:** if the tiles fail, the list still works, and a table of projects is available.
5. Use `lib/data.ts` only (fixtures in dev/CI, the API in production). Build empty, loading and unavailable states.

## Requirements
- No new dependencies. Don't edit frozen files (`layout`, `nav`, `ui`, `lib/*`); request a `[C<n>]` if needed.
- The UI never decides eligibility; it only displays matches from the data.

## Validation
- `npm run lint && npm run typecheck && DATA_MODE=fixture npm run build`.
- Screenshots at 1440 px and 390 px in fixture mode (`DATA_MODE=fixture npm run dev`), attached to the PR, showing the 6 golden pairs in priority order.

## Defaults
- Styling: whatever F00 set up (CSS modules or Tailwind). Clean and dense, planner-oriented; no hero sections.
