---
id: F05
name: Map + ranked list
lane: B
agent: frontend-engineer
phase: 1
depends_on: [F00]
owns: [web/app/page.tsx, web/components/map/, web/components/list/, web/components/landing/]
cut: never
---

# F05 Map + ranked list

## Plan
1. **Home page** `web/app/page.tsx` (marketing landing under `web/components/landing/`):
   - brand-first hero with GridBridge copy and a decorative right-to-left truck road scroll (illustrative only)
   - primary CTA into `/time` (Overlaps); fixture badge when `DATA_MODE=fixture`
   - the former map+list home moved to `/map` after the marketing page replaced `/`
2. **Map** (on `/map`): project centers as circles, DESC blue `#2563eb`, Georgia orange `#ea580c`, unknown-owner grey. Low-confidence locations as hollow rings.
   - Header strip with the view toggle (Future / Historical / Tentative), the analysis date, and source versions; map ~65% width with the ranked list alongside (list below at 390 px).
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
- Styling: night-instrument tokens from F21/C18. Marketing `/` may use a hero; map/list stay dense and planner-oriented.
