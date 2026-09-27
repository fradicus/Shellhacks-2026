# F34 free public water sources

## Context
Field context needs river/creek levels, tides, flood zone and wetlands at a
clicked point. C15 freezes the site contract as `{weather,soil,aef,roadwork}`
and conditions as `{weather,roadwork}`; widening either would break F36.

## Options
1. Fold water into `/api/operations/site` — rejected; changes the frozen C15 site shape.
2. Separate additive `GET /api/operations/water?lat&lon` — chosen.
3. Defer water until a C15 contract PR — larger delay; the four sources need no keys.

## Choice
One provider module `web/lib/operations/water.ts` mirrors the soil-style envelope
pattern and fan-outs four fixed HTTPS hosts:

| Part | Host / service | Scope |
|---|---|---|
| Rivers | `waterservices.usgs.gov` NWIS IV | ~17 mi bbox, gage height 00065, nearest 3 |
| Tides | `api.tidesandcurrents.noaa.gov` | nearest water-level station ≤25 mi; else inland skip |
| Flood | `hazards.fema.gov` NFHL layer 28 | zone code at point |
| Wetlands | `fwspublicservices.wim.usgs.gov` NWI | mapped wetland type at point |

Transport allowlists those hosts. Reference lists `water` with a 900-second
refresh hint. No credentials. Partial/out-of-coverage/unavailable stay visible;
absence is never treated as no hazard.

## Undo
Remove `water.ts`, the `/api/operations/water` route, Water* types,
transport host entries, reference row, focused tests and this note.
