# C53: map/routing provider policy and the contract-upload boundary

Recorded 2026-09-27 at the user's request while closing the audit's documentation finding (M11). This is policy;
it does not claim either integration is delivered. Feature ownership is unchanged.

## Provider policy

- **Overlaps (`/time`) keeps OSRM.** Its road-distance integration stays separate from Google and follows the
  drive-rule proposal (committed OSRM routes, open-data attribution), in review as
  [#241](https://github.com/fradicus/Shellhacks-2026/pull/241). Until it lands, Overlaps shows straight center-to-center connectors and says they are proximity, not road routes.
- **Every other map surface moves to Google mapping and routing**: `/map`, `/history`, `/explore`, `/operations` and
  pair evidence. Until that migration passes its acceptance, those surfaces keep MapLibre/OpenFreeMap and remain
  proximity views.
- Google route content is never drawn on MapLibre (C15, F34, F36). `/operations` keeps its attributed route-only panel
  until a configured Google map is approved.
- Truck routing requires `GOOGLE_ROUTES_API_KEY`, `GOOGLE_LVR_ENABLED=true` and separately provisioned LVR access, plus
  exact vehicle facts and a reviewed access point. There is no passenger-car fallback. Without all of them the route
  is `not_configured` and no numeric fallback is shown; the required acceptance suite checks this.
- Browser Google keys and map IDs are added to `.env.example` only when implemented, with their real names and
  referrer/API restrictions. No server key is ever browser-exposed.

## Contract upload: expansion and acceptance boundary

Upload widens the product from published filings to a planner-supplied contract. It is accepted only when one
authorized real document passes the whole sequence:

1. **Receipt.** Bytes, SHA-256, uploader, time and authorization are recorded. The raw document is not committed.
2. **Extraction.** Deterministic or schema-validated model extraction; every fact keeps page/row provenance, and
   unknown fields stay null.
3. **Evidence review.** A human accepts or rejects the extracted facts and location. Rejected or unreviewed facts
   never reach matching.
4. **Idempotent publication.** Re-publishing the same bytes is a no-op. A new version supersedes the old one without
   deleting it. Publication failures are reported as `publication_failed` and never activate a partial release.
5. **All consumers.** The published record appears with its release identity in the map, list, table, History,
   exports and matching, and `/api/health` reports it.

Out of scope until separately decided: a claim that a contract, saved dollar amount or available crew exists; OCR of
scanned documents without review; public (unauthenticated) upload.

The acceptance suite (`tests/acceptance`) keeps a visibly skipped "contract upload" test until this lands; it becomes
a required, unskipped test in the same PR that implements upload.

## Undo

Revert this record. Nothing in code depends on it.
