# F36: Route factors tab and client pipeline

## Context
The user asked to turn the site/route environmental evidence stack into a reusable pipeline and add a
**Factors** tab showing, for the assessed truck route, which factors apply and how much time/cost they add.

## Options
1. New top-level `/factors` route and shared nav entry (needs a contract change; nav is frozen).
2. Pure client pipeline under F36 plus a Factors tab on `/operations?view=factors` (no nav edit).
3. New F34 API that invents numeric delay/cost multipliers from weather/roadwork.

## Choice
Option 2. `deriveRouteFactors` / `applyFactorRates` in `web/components/operations/factors.ts` turn site + route
envelopes into evidence rows; user-entered minutes/USD only produce totals. Provider travel minutes may seed the
baseline travel row when left blank. Unknown stays null. No invented savings.

## Undo
Remove the Factors tab, `FactorsBoard`, `factors.ts`, its tests, and this decision; restore the previous
`/operations` page export.
