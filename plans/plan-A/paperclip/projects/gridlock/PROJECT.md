---
name: Gridlock
description: Utility construction plan overlap detector - Dominion Energy SC vs Georgia Power
owner: ceo
---

# Gridlock - product spec

## What judges must see (Sperry Tech requirements)

1. **Interactive map** (pan / zoom / click) with both utilities' planned projects, overlaps visibly highlighted.
2. **Ranked list** of the top coordination opportunities.
3. **Bonus:** rough cost/impact estimate for at least one flagged opportunity.

Overlap rules (from the sponsor, non-negotiable):

- A project's **center** = midpoint of its two named endpoints; if only one endpoint is located, that point is the center.
- **Geographic overlap** = haversine distance between centers **< 25 miles**. This is the primary signal and the only thing that creates an overlap row.
- **Timeline** = gap between in-service dates **in days**. Secondary signal, used for ranking, never to create or drop a pair.
- Most pairs will not overlap. That is expected.

Sponsor golden sample (`docs/Sperry-Tech-Challenge/Projects_Overlaps.xlsx`) is the acceptance test: our
pipeline, fed those 10 projects, must reproduce OVL_1..OVL_6 (distance within 0.05 mi, gap exact) and no others.

## Architecture

```
docs/                         source PDFs + sponsor docs (read-only)
pipeline/   Python 3.12, uv   offline ETL, run once, re-runnable
  extract_desc.py             Dominion PDF (44 project cards) -> data/desc_projects.json
  extract_gpc.py              Georgia Power IRP Vol 3 Ten-Year Plan tables -> data/gpc_projects.json
  geocode.py                  OSM Overpass + Nominatim + Gemini adjudication -> data/projects.geojson
  overlaps.py                 haversine, time gap, score, estimate -> data/overlaps.json
  load_mongo.py               upsert both into Atlas, build indexes
  briefs.py                   Gemini coordination brief per top-N overlap -> overlaps.brief
  test_overlaps.py            golden-sample check (plain asserts, `uv run python pipeline/test_overlaps.py`)
data/                         committed pipeline outputs (the app never re-parses PDFs)
web/        Next.js (App Router, TypeScript), MapLibre GL, deployed on Vercel
  app/page.tsx                map + ranked list + detail panel
  app/api/projects            GET all projects (GeoJSON)
  app/api/overlaps            GET ranked overlaps (filters: max distance, max gap, min confidence)
  app/api/near                GET $geoNear around a clicked point, radius slider
  app/api/ask                 POST natural-language question -> Gemini function call -> Mongo query -> answer + highlighted map features
```

No auth, no user accounts, no ORM, no state library, no Docker. Map tiles from OpenFreeMap (no key).

## MongoDB Atlas data model (M0 free tier is enough)

`projects`
```
{ _id: "DESC_6807B" | "GPC_20277", utility: "DESC"|"GPC", state: "SC"|"GA",
  name, description, need, status, zone, sponsor,
  in_service_date: Date, cost_usd: Number|null,      # GPC costs are REDACTED -> null
  voltage_kv: [115], kind: "rebuild"|"new_line"|"reconductor"|"substation"|"reactor"|"other",
  endpoints: [{ name, loc: {type:"Point", coordinates:[lon,lat]}, osm_id, match_note }],
  center: {type:"Point", coordinates:[lon,lat]} | null,
  confidence: "high"|"medium"|"low"|"unlocated",
  source: { file, page } }
```
Index: `2dsphere` on `center`.

`overlaps`
```
{ _id: "DESC_6807B__GPC_20277", a, b, distance_mi, time_gap_days, score, rank,
  drivers: ["4.1 mi apart", "both 115 kV rebuilds", ...],
  estimate: { freight_savings_usd, shared_row_acres, assumptions: [...] },
  brief: { text, model, generated_at } }
```

## Milestones and issues (CEO creates these as Paperclip issues, in order)

| # | Issue | Owner | Blocked by |
|---|-------|-------|-----------|
| 1 | Scaffold repo: `pipeline/` (uv), `web/` (Next.js), `.env.example`, README, CI (lint + `test_overlaps.py`) | cto | - |
| 2 | Golden-sample test from the sponsor xlsx (fails until #6 lands) | qa-verifier | 1 |
| 3 | Extract Dominion projects -> `data/desc_projects.json` | data-engineer | 1 |
| 4 | Extract Georgia Power Ten-Year Plan projects -> `data/gpc_projects.json` (focus zones on the SC border first: Savannah / Augusta areas) | data-engineer | 1 |
| 5 | Geocode both utilities' endpoints, confidence per match | geo-engineer | 3, 4 |
| 6 | Overlap table, score, rank, cost/impact estimate | geo-engineer | 5 |
| 7 | Verify every high/medium match and every overlap against the PDFs; downgrade what can't be confirmed | qa-verifier | 5, 6 |
| 8 | Atlas cluster wiring, `load_mongo.py`, indexes, API routes | backend-engineer | 1, 6 |
| 9 | Gemini: PDF table extraction assist (#4), geocode adjudication (#5), coordination briefs, `/api/ask` | ai-engineer | 3, 5, 8 |
| 10 | Map UI: both utilities, overlap links, click panel, ranked list, filters, estimate card | frontend-engineer | 8 |
| 11 | Deploy to Vercel, attach GoDaddy Registry domain | cto | 10 + board registers domain |
| 12 | End-to-end QA on the live URL, mobile check | qa-verifier | 11 |
| 13 | Devpost write-up covering Sperry + Gemini + Atlas + GoDaddy tracks | ceo | 12 |

Definition of done for the project: live URL on the GoDaddy domain, golden test green, top-10 ranked
list each with a verified confidence label, at least one overlap with a cost/impact card and Gemini brief.
