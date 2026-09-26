---
name: mongodb-atlas
description: MongoDB Atlas setup and query patterns for Gridlock - connection, collections, 2dsphere + $geoNear, Atlas Search, aggregation, safe query building from Next.js route handlers and Python.
---

# MongoDB Atlas

`MONGODB_URI` (`mongodb+srv://...`), database `gridlock`, free M0 cluster.
Two database users: `loader` (readWrite, pipeline only) and `web` (read, Vercel). Network access `0.0.0.0/0` for
the hackathon, because Vercel has no fixed egress IPs. Say so in the README.

## Loader (`pipeline/load_mongo.py`, pymongo)
- `bulk_write([ReplaceOne({"_id": d["_id"]}, d, upsert=True) ...])` per collection. Running it again changes nothing.
- Dates as `datetime`. GeoJSON `[lon, lat]`. Omit `center` when unknown (never `[0,0]`).
- Indexes: `projects.center` 2dsphere; `projects {utility:1, in_service_date:1}`; `pairs {tier:1, score:-1}`; `pairs {label:1}`.
- Insert one `quality` doc per run.

## Node (route handlers)
`mongodb` driver. `globalThis._mongo ??= new MongoClient(process.env.MONGODB_URI!)`. `export const runtime = "nodejs"`.

## Queries that show off Atlas
- Radius tool: `$geoNear` (must be the first stage) with `key: "center"`, `maxDistance: miles * 1609.344`, `spherical: true`, then `$limit`.
- Map viewport: `{center: {$geoWithin: {$box: [[w,s],[e,n]]}}}`.
- Zone page: `$lookup` from `zones.project_ids` to `projects`, plus `pairs` in the zone, in one aggregation.
- Text search: Atlas Search index `projects_text` (dynamic), `$search: {index: "projects_text", text: {query, path: ["name","description"], fuzzy: {}}}`.
- Data Quality page: latest `quality` doc plus `$facet` counts by utility x confidence.

## Safety
Never pass request JSON into a query. `/api/ask` receives Gemini's function-call args. Whitelist fields
(`label, tier, utility, kind, voltage_kv, distance_mi, time_gap_days, confidence, in_service_date, zone_id`)
and operators (`$lt $lte $gt $gte $eq $in`), clamp numbers, limit 50. Every parameter is validated at the route
boundary: radius <= 100 mi, limit <= 500, export <= 5000 rows. CSV cells starting with `= + - @` get a `'` prefix.
