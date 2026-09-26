# F06 decisions (Atlas loader + read API)

1. **Dataset-namespaced ids.** Upserting by record `_id` with a `dataset` field would overwrite the live documents
   before the pointer flips, so staging wouldn't be real. Stored `_id` is `<dataset>:<record _id>`, with `id` and
   `dataset` fields; the API returns `id` as `_id`, so responses match `lib/types.ts` exactly. The loader keeps the
   active and previous datasets and deletes older ones. Undo a bad load by setting `meta.active.dataset` back to
   `previous`.
2. **Writes are delete-this-dataset + `insert_many`**, not `bulk_write` upserts. Same result, one round trip per
   collection, and it runs under mongomock (whose bulk API doesn't match current pymongo). Reloading the *active*
   sha has a sub-second window where that dataset is being rewritten; a new sha (the normal case) doesn't.
3. **Viewport query is `$geoWithin` + `$geometry` Polygon** on a GeoJSON `geo` point with a `2dsphere` index, not
   `$box`: `$box` only works on legacy coordinate pairs. The bbox must not cross the antimeridian (400 otherwise).
   The 2dsphere index is on `geo`, not `center` (`center` is `{lat, lon}`, not GeoJSON).
4. **Locations are joined into `projects.endpoints`** and not stored as their own collection. `center` comes from
   `core.center`, `location_confidence` is the weakest confidence among the endpoints used, and projects with no
   locations keep any `center` they already had.
5. **Loaded folders:** `data/{sources,projects,locations,matches,briefs,extraction,review,coverage,versions}/`. A file
   is a JSON array of records or one object with `_id`; anything else (e.g. `data/matches/summary.json`) is skipped and
   listed. `data/fixtures/`, `data/osm/`, `data/owners/` are never loaded.
6. **Missing `MONGODB_URI_RW`**: the loader validates everything, prints a `::warning::`, and exits 0 if the data is
   valid. A red `load` run would read as "main is red" to every agent (`overnight.md` §6) and block all merges for a
   missing human secret. Invalid data still exits 1. Tracked in a `human-morning` issue.
7. **`/api/projects?view=`** is accepted but doesn't filter: projects aren't view-scoped (views belong to pairs).
8. **`/api/pairs/[id]`** returns the active filing's project for each key (`active: true` first), the newest
   `passed` brief only, version changes for either key, and reviews whose `record_id` is the pair id.
9. **Manual check ran against a local MongoDB 8 container**, not Atlas: no `MONGODB_URI_RO` or `MONGODB_URI_RW` exists
   on this machine or in visible repo secrets. Same driver, same indexes, same queries.
