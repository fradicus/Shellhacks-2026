# FIX-F36: map click to site evidence

`/operations` gains a MapLibre worksite picker. A map click fills confirmed
coordinates (and a default label when empty). When an AEF year is already chosen,
the desk immediately calls `GET /api/operations/site` for weather, soil (incl.
horizon pH when published), AEF and roadwork. Without a year, the click only
captures the point and prompts for year + Check.

Optional `?lat&lon&label&year` query params seed the form. Soil panel shows
survey pH with centimeter depths and the 1:1 soil-water method. Coordinates remain
user-asserted; providers stay independent and never certify the site.
