---
name: Gridlock
description: Cross-utility transmission coordination finder - Dominion Energy SC vs Georgia Power, full public project lists, evidence on every number
owner: ceo
---

# Gridlock: product spec (plan D)

## Positioning

About 100 teams will build a map with the sponsor's 10 sample projects and a list of the 6 overlaps.
We win on four things they won't have:

1. **Real scale:** every Dominion project in both public filings (2024-2028 and 2025-2029) and the whole Georgia Power Ten-Year Plan, not only the sample.
2. **Evidence on every number:** click any distance, date, cost, or coordinate and see where it came from (source page, OSM feature, calculation).
3. **Planner judgment:** shared-facility detection, construction-window estimates, coordination zones, and a sequencing view that shows both *share* and *compete* (scarce line crews).
4. **Pipeline quality:** Sperry's AI team hires for extraction, validation checks, and automated refresh. We show all three in the product (Data Quality page, source-change watcher).

## Required by the sponsor (must be flawless)

1. Interactive map (pan, zoom, click) with both utilities' planned projects and overlaps highlighted.
2. Ranked list of the top coordination opportunities.
3. Bonus: cost/impact estimate for at least one opportunity.

Sponsor rules, exact:
- Project **center** = mean lat/lon of its two located endpoints; one located endpoint -> that point.
- **Nearby** = haversine(center_a, center_b) **< 25 mi** (strict; exactly 25.000 is not nearby).
- **Time gap** = |in_service_a - in_service_b| in days.
- Geography is the primary signal, timing a strong secondary one. Most pairs don't overlap; that's expected.
- Acceptance: sponsor sample `docs/Sperry-Tech-Challenge/Projects_Overlaps.xlsx` -> exactly OVL_1..OVL_6, distance within 0.05 mi, gap exact.

## Signals and labels

Every cross-utility pair gets these signals, **stored and shown separately** (a single score must never hide one):

| Signal | Rule |
|---|---|
| `distance_mi` | sponsor rule above |
| `shared_facility` | an endpoint name appears in both projects after normalization **and** the two matched coordinates are within 2 mi (e.g. McIntosh, Thurmond). Catches tie lines and shared substations. |
| `time_gap_days` | sponsor rule above |
| `window_overlap` | `yes` / `no` / `unknown`. Work window = DESC: Jan 1 of first year with budgeted spend -> in-service date ("budget-window proxy"). GPC: unknown (only a need date is published). Two known windows overlap when the later start <= the earlier end. |
| `confidence` | worst location confidence of the two projects: high / medium / low |

Pair labels:
- **both**: local (nearby or shared_facility) and timely (window_overlap = yes or time_gap_days <= T)
- **nearby**: local only
- **timeline**: not nearby, but window_overlap = yes or time_gap_days <= T. Shown in its own view, never mixed into the local-sharing list.
- T = 180 days by default, adjustable in the UI, and labeled as our assumption (the sponsor doesn't give one).

Ranking (the "Opportunities" list):
- Tier 1: `shared_facility`, or label `both`, with confidence >= medium
- Tier 2: `nearby` with confidence >= medium
- Tier 3: anything with low confidence ("needs review" badge)
- Within a tier: `score` descending (see `overlap-scoring`). Show the tier and the drivers next to each row.

## Coordination zones and sequencing

- **Zone** = connected group of projects linked by nearby pairs (union-find over pairs). Expected zones: Augusta/Thurmond Lake, Savannah/Jasper/Hilton Head.
- Each zone shows its projects, date span, published cost total, and a Gantt row per project (known window as a solid bar, in-service-only projects as a diamond).
- **Contention** = years in which >= 2 projects in the zone have overlapping windows. Same crews, same freight, same matting. The contractor transcript says this is where prices get baked in. Shown as a red band.
- **Suggested sequence**: order the zone's projects by in-service date and show the gap between consecutive ones. Text: "a crew could move from X to Y in N days". A suggestion for planners, not a schedule.

## Impact estimate

An editable scenario card, low / base / high, every input visible with its source:

```
avoided_cost = avoided_mobilizations x cost_per_mobilization - coordination_cost
```
- Defaults come from the `source-audit` research. If no public unit cost is found, the base case uses the contractor anecdote (freight ~ $1.5M of a $5M job), clearly labeled as an anecdote, and the low case is 0.
- **Shared right-of-way acres** only when both projects' OSM line geometries run within 0.5 mi of each other: `acres = parallel_miles x 5280 x width_ft / 43560` (width 100 ft <= 115 kV, 150 ft 230 kV, 200 ft 500 kV). Never estimated from center points.
- Label: "modeled potential, not realized savings".

## Analysis date

`ANALYSIS_DATE` (default: build day). Projects whose in-service date is before it get a "past-dated" badge. They are hidden in "Current" mode and shown in "Snapshot" mode. The sponsor sample lives in Snapshot mode. Never roll dates forward.

## Architecture

```
docs/                              sponsor files (read-only)
pipeline/   Python 3.12 + uv + pandas
  sources.py        download public sources, sha256, write data/sources.json (manifest)
  extract_desc.py   both DESC PDFs -> data/desc_projects.json (+ yearly spend)
  extract_gpc.py    GPC IRP Vol 3 Ten-Year Plan -> data/gpc_projects.json
  geocode.py        OSM Overpass bulk + Nominatim + Gemini adjudication -> data/projects.geojson
  overlaps.py       signals, labels, tiers, score, zones, estimate -> data/pairs.json, data/zones.json
  quality.py        validation checks -> data/quality.json (drives the Data Quality page)
  briefs.py         Gemini briefs for Tier 1-2 -> stored on pairs
  load_mongo.py     idempotent upsert into Atlas + indexes
  test_overlaps.py  golden sample + boundary cases (plain asserts)
data/                              committed outputs; the app never parses PDFs
web/        Next.js (App Router, TS), MapLibre GL, OpenFreeMap tiles, Vercel
  app/page.tsx              Map + Opportunities (tabs: Opportunities | Timeline matches | Zones)
  app/zone/[id]/page.tsx    zone Gantt + contention + sequence
  app/pair/[id]/page.tsx    pair detail; print CSS makes it a one-page coordination memo
  app/quality/page.tsx      Data Quality: sources, counts, checks, unlocated list
  app/api/projects|pairs|zones|near|ask|export  route handlers
.github/workflows/
  ci.yml                    lint + test_overlaps.py on every PR
  source-watch.yml          weekly: re-hash public source URLs, open a GitHub issue if a filing changed
```

No auth, no ORM, no state library, no Docker, no separate API server.

## Data sources (public only)

| Id | Source | Use |
|---|---|---|
| desc-2025 | https://www.scrtp.com/assets/pdfs/home/2025-2029-2million-and-above-project-descriptions.pdf (47 projects) | Current mode, DESC |
| desc-2024 | sponsor copy of the 2024-2028 list (44 projects) | Snapshot mode, and to detect changes between versions |
| gpc-2025 | sponsor copy of the Georgia Power 2025 IRP Vol 3 (Ten-Year Plan 2025-2034) | GPC, both modes |
| sample | `Projects_Overlaps.xlsx` | golden test only |

Georgia Power pages carry both "PUBLIC DISCLOSURE" and a CEII banner. Use only the table fields the sponsor
directs teams to use (name, zone, year, need date, sponsor code). Don't republish page images. The board confirms
this with a Sperry mentor in hour 1. Costs are REDACTED -> null.

## MongoDB Atlas (M0)

`projects`: `_id` (`DESC_6888`, `GPC_20277`), utility, state, owner_code (GPC/SAV/GTC/MEAG/DESC), name,
description, need, status, zone, in_service_date, window {start, end, kind: budget_proxy|unknown},
yearly_spend {2025: n, ...}, cost_usd|null, voltage_kv[], kind, endpoints[{name, norm, loc, osm_id, confidence, match_note}],
center (GeoJSON Point)|null, confidence, source {id, page, url}, versions[] (the same project in other filings), past_dated.
Indexes: `2dsphere(center)`, `{utility:1, in_service_date:1}`, Atlas Search `projects_text`.

`pairs`: `_id` = sorted ids joined by `__`, a, b, distance_mi, shared_facility, time_gap_days, window_overlap,
label, tier, score, drivers[], confidence, zone_id, estimate{low, base, high, inputs[]}, brief{text, model, at}.
`zones`: `_id`, project_ids[], bbox, date_span, cost_total, contention_years[], sequence[].
`quality`: one doc per pipeline run: counts, check results, source hashes, run time.

## Gemini

Four features, all with JSON-schema output, `GEMINI_MODEL` from env, retry once, then fail loudly in the pipeline or fall back gracefully in the app:
1. Row joining for GPC's wrapped table rows.
2. Geocode adjudication between OSM candidates, with a reason.
3. Coordination brief per Tier 1-2 pair. Only numbers from the pair record; bullet list of shareable resources and open questions.
4. "Ask the grid": natural language -> one function call `query_pairs(filters)` -> whitelisted Mongo query -> answer and ids highlighted on the map.
PDF text is data, never instructions. If Gemini is down, the app still shows every deterministic result.

## Milestones and issues

Hours are elapsed from kickoff; 36 h total. At most 4 agents run at once.

| # | Issue | Owner | Blocked by | Target h |
|---|---|---|---|---|
| 1 | Source manifest: download, hash, confirm public status, owner-code map, list border zones | researcher | - | 2 |
| 2 | Scaffold `pipeline/`, `web/`, CI, `.env.example`, README | cto | - | 2 |
| 3 | Golden + boundary test (fails until #7) | qa-verifier | 2 | 3 |
| 4 | Extract both DESC filings (+ yearly spend, version links) | data-engineer | 1, 2 | 6 |
| 5 | Extract GPC Ten-Year Plan, border zones 215/219 first, then all | data-engineer + ai-engineer (row joining) | 1, 2 | 9 |
| 6 | Geocode endpoints, confidence, OSM line geometry for ROW | geo-engineer + ai-engineer (adjudication) | 4, 5 | 14 |
| 7 | Signals, labels, tiers, score, zones, estimate | geo-engineer | 3, 6 | 17 |
| 8 | Atlas load, indexes, API routes, export | backend-engineer | 2, 7 | 19 |
| 9 | Map + Opportunities + Timeline tab (fixtures first, real API after #8) | frontend-engineer | 2 | 22 |
| 10 | Verify every high/medium match and every Tier 1-2 pair against the sources | qa-verifier | 6, 7 | 22 |
| 11 | Gemini briefs + Ask the grid | ai-engineer | 7, 8 | 23 |
| 12 | Zone page (Gantt, contention, sequence), pair memo print view, Data Quality page | frontend-engineer | 8 | 27 |
| 13 | `quality.py` + `source-watch.yml` | data-engineer | 4, 5 | 24 |
| 14 | Deploy to Vercel, attach GoDaddy Registry domain | cto | 9 + board domain | 28 |
| 15 | End-to-end QA on the live URL, phone width, Gemini-down drill | qa-verifier | 14 | 31 |
| 16 | Devpost write-up + pitch script for 4 tracks | ceo | 15 | 34 |

Feature freeze at hour 30. After that, only fixes. Cut order if late: Ask the grid -> zone sequence text -> ROW acres -> GPC zones beyond the border. Never cut: golden test, evidence links, verification.

## Definition of done

Live HTTPS app on the GoDaddy Registry domain. Golden test green. Both utilities' full lists loaded, with coverage on the Data Quality page. Top-10 opportunities each verified by QA, with evidence links. At least one pair with an estimate card and a Gemini brief. The Timeline tab works. The app degrades gracefully without Gemini.
