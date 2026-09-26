---
name: "map-workbench"
description: "Build the map, ranked list and evidence flow with visible uncertainty and accessible fallbacks."
---

# Map workbench

## Inputs
Shared API fixtures, accepted pair contract, design states and original source links. Start from fixtures while the real pipeline is being built.

## Procedure
1. Build one Next.js/React experience with overview, synchronized MapLibre map/table, evidence drawer and coordination card. Use OpenFreeMap with required attribution. Keep app secrets server-side.
2. Distinguish utility markers, selected centers and pair connectors without relying only on color. Explain that lines connect centers, not actual routes. Give keyboard users the full table/detail flow and visible focus.
3. Display analysis date, source versions, historical/future/tentative filters and the coverage denominator. Missing locations stay in the searchable table. Never silently drop unknown dates or imply a historical fixture is a future opportunity.
4. Show miles and day gap as separate facts. Expose distance band and rank drivers. In the evidence drawer link raw endpoint/owner/date claims to reviewed evidence and show one-endpoint limitations.
5. Make Gemini's product work visible: approved source page, structured response, validation/review state and grounded brief. Clearly label possibilities, unsupported-field rejection and cached generation timestamps.
6. Implement CSV/print handoff and empty/loading/error states. Map failure leaves the table useful. Gemini failure leaves match facts; Atlas failure has an honest unavailable state.
7. After core integration, add R2 source-change watchlist, coverage explorer and hypothetical-date drawer if the gate passes. Published facts and assumptions must be visually distinct with reset. Regional expansion toward 3–5 utilities is conditional R2; R3 is one second-region pilot or grouped agenda after CEO approval.

## National and Three.js requirements
Build U.S. discovery navigation with an eight-state Southeast lens and reviewed GA/SC data first. Regions without reviewed records display their coverage state, never invented project markers or zero-match claims. Use direct Three.js inside a MapLibre custom layer, client-only and with tested pinned versions. Keep real geographic anchors fixed while exact in-service dates rise on a shared date axis; use the project charter's date-height formula. Unknown/partial dates stay in a separate tray. Never calculate distance from display positions or interpret rendered lines as transmission routes.

The selected-pair date lift is R1; R2 adds assumed-date drag, published ghosts/reset and verified filing playback. Provide keyboard/date-input equivalence, reduced motion and context-loss fallback. Test 30 FPS and 250 ms feedback targets on the declared demo device with explicitly labeled performance fixtures. R3 chooses one extra regional pilot or agenda; R4–R5 describe national ingestion and later collaboration.

## Output and checks
A judge can go from utilities to a pair, verify both sources and export a card. QA tests this path by keyboard, zero matches, null fields, unavailable services and hypothetical reset. Cosmetic polish never outranks incorrect source or date labels.
