---
name: mongodb-atlas
description: MongoDB Atlas setup and query patterns for Gridlock - connection, schema, 2dsphere and $geoNear, Atlas Search, safe query building from Next.js route handlers and Python.
---

# MongoDB Atlas

Connection string in `MONGODB_URI` (`mongodb+srv://...`), database `gridlock`. Atlas cluster: free M0.
Network access: `0.0.0.0/0` is acceptable for the hackathon (Vercel has no fixed IPs); DB user with readWrite on `gridlock` only.

## Python loader (`pipeline/load_mongo.py`)
`pymongo`: `replace_one({"_id": doc["_id"]}, doc, upsert=True)` per doc (idempotent). Dates as `datetime`.
Indexes: `db.projects.create_index([("center", "2dsphere")])`, `db.overlaps.create_index("rank")`.
Projects with `center: null` are still stored (2dsphere indexes skip null/missing).

## Node (Next.js route handlers)
`mongodb` driver, one cached client: `globalThis._mongo ??= new MongoClient(process.env.MONGODB_URI!)`. Route handlers run on the Node runtime (`export const runtime = "nodejs"`).

## Geo query (`/api/near`)
```js
db.collection("projects").aggregate([
  { $geoNear: { near: { type: "Point", coordinates: [lon, lat] }, key: "center",
      distanceField: "distance_m", maxDistance: miles * 1609.344, spherical: true } },
  { $limit: 200 }
])
```
`$geoNear` must be the first stage. Coordinates are `[lon, lat]`.

## Atlas Search (text box / ask fallback)
Create search index `projects_text` in the Atlas UI (dynamic mapping) and query with `$search: { index: "projects_text", text: { query, path: ["name","description"] , fuzzy: {} } }`.

## Safety
Never pass user JSON straight into a query. `/api/ask` gets a Gemini function-call object: whitelist fields
(`utility, kind, voltage_kv, distance_mi, time_gap_days, confidence, in_service_date`), whitelist operators
(`$lt $lte $gt $gte $eq $in`), clamp numbers, limit 50.
