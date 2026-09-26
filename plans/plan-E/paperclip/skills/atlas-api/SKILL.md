---
name: "atlas-api"
description: "Build the Atlas data layer and bounded application API with provenance, idempotency and secret isolation."
---

# Atlas and API

## Inputs
Shared schemas, source/record versions, canonical matcher output and scoped connection credentials. MongoDB Atlas is required application storage.

## Procedure
1. Create collections for sources, projects, matches, runs, reviews and briefs. Preserve raw evidence and normalized fields. Add unique source-hash, project/version and match-input keys. Index known center geometry with 2dsphere; use ordinary owner/date/version indexes for tables.
2. Use GeoJSON longitude/latitude order and omit unknown geometry. Do not rely on the spatial index to return unlocated records. Run canonical all-pairs matching for the initial corpus; indexed viewport queries serve the map.
3. Load data idempotently into a staged run. Validate counts and references, then switch the active dataset version. A partial run must not appear as the current complete dataset. Preserve old versions for changes and reproducibility.
4. Use a pooled native MongoDB driver connection on the server. Provide bounded, schema-validated read routes for projects, matches, details and CSV. Do not accept arbitrary database operators, unbounded queries or source URLs.
5. Keep read and write credentials separate. Bind RW only to controlled ingestion/protected persistence and RO to browse paths/QA. Restrict users to the app database and configure actual host egress through Atlas's access list.
6. Implement protected brief generation from approved stored pair IDs, with rate limits and a cache keyed by inputs. Validate the server-side OPERATOR_API_TOKEN from a local operator CLI bearer header; reject missing/invalid credentials without logging them. The public browser never holds this token. Public browse can read accepted cached briefs. Never expose keys in NEXT_PUBLIC variables, logs or client bundles.
7. Escape spreadsheet formula prefixes in CSV. Test unknown IDs, invalid filters, missing geometry, interrupted imports, repeated imports and unavailable Atlas/Gemini.

## Output and checks
Documented JSON contracts, indexes and live query evidence behind an integrated UI interaction. QA verifies two identical imports do not duplicate records and stale briefs invalidate after a source change. A static JSON screen does not satisfy the Atlas track.
