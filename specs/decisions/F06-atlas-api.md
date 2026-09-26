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
   locations get `center: null` (decision 14).
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
10. **Ambiguous accepted endpoints block activation (#35).** `collect()` reports an error for more than one
    non-rejected location per `(project_key, endpoint_index)` and for a non-rejected `endpoint_index` other than 0/1.
    `core.center` averages whatever it gets, so picking one candidate or averaging would both invent a center.
    Rejected candidates stay allowed (F09 keeps them as evidence).
11. **Audit verdicts set `match.review_state` at staging (#38).** Reviews whose `record_id` is the pair id count;
    `confirmed` -> confirmed, `downgraded`/`rejected` -> rejected, newest timezone-aware `at` wins, and at the same
    instant a downgrade wins. Other verdicts, endpoint reviews and undated reviews change nothing; with no decision the
    producer's state stays. All reviews are stored. Not done: the subject-fingerprint proposal in #38's comment
    (a confirmation that survives changed facts); it needs an agreed review contract first.
12. **Passed briefs must prove their `input_hash` is current (#43).** Staging recomputes it with a `brief_hash`
    function; a mismatch, an unknown match, or no function at all stores the brief as `validation: rejected` with the
    reason and `source_validation: passed`, so neither the pair route nor `/api/briefs` shows it as approved. F12's
    builder doesn't exist yet, so today every passed brief fails closed; wire it in as the default when F12 lands.
13. **`/api/briefs` and `/api/runs` (C5, #41).** Briefs: all in the active dataset, sorted `match_id, generated_at,
    id`. Runs: not dataset-namespaced, so read as stored via `handleDb` (no active dataset needed, so a failed first
    load still shows); latest by `started_at` desc then `_id` desc; public fields only (never `errors`); 404 when
    none. `started_at` has one-second resolution, so two runs in the same second fall back to `_id` order.
14. **A location is evidence for one filing version (#47).** `join_projects` grouped locations by `project_key`, so a
    superseded filing (`DESC:0167C-D@desc-2024`) inherited coordinates reviewed only for the current one. Now
    `bind_locations` binds each location to `project_id`, or `<project_key>@<source_id>` when only `source_id` is
    given (the project `_id` convention), and only that version gets the endpoint. The version must exist and agree
    with `project_key`/`source_id`; a location naming neither (today's fixtures) binds to the key's *only* active
    version. Zero or several active versions, an unknown version, or a contradiction are `collect()` errors and block
    activation (no silent drop, no enrichment of every version). Accepted-candidate uniqueness (#35) is now per
    `(project_id, endpoint_index)`, so two versions may each carry their own reviewed endpoint. Unlocated projects
    now store `center: null` explicitly. Alternative rejected: join by key and only mark `active` versions, which
    still lets an inactive version own evidence produced for another filing.
