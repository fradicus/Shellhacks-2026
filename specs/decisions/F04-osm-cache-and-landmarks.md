# F04: bounded cache and landmark evidence

## Context
The regional queries need to be reproducible without repeatedly loading the public Overpass service. A successful
response may still contain an Overpass runtime `remark`, and the unanchored spec query can match values beyond the
three normalized feature types. The live 2026-09-26 inventory also contains an unnamed substation at the Okatie
sample coordinate but no feature named Okatie.

## Choice
- Attempt the two full spec bboxes first. Split a query into four only after exhausted 504 retries or a response over
  25 MiB, with at most 32 HTTP attempts, three split levels, and 64 MiB of retained raw data.
- Bind every exact raw response to its exact query, bbox, SHA-256 and original retrieval timestamp. Reject a cached
  response when any binding differs. Treat an HTTP 200 payload with `remark` as unavailable, not complete.
- The owned `data/osm/.gitattributes` disables Git newline conversion for raw response JSON, preserving these
  SHA-256 bindings when a worker checks out the cache with Windows `core.autocrlf=true`.
- Normalize only exact `power=plant`, `power=substation`, and `power=switch` values. The live unanchored regex also
  returned 16 `power=switchgear` ways and 3 `power=pole;switch` nodes; they remain in the raw cache and their counts
  are explicit in the manifest instead of silently becoming endpoint candidates.
- Preserve the Okatie feature as unnamed. Landmark verification is `partial` (Thurmond and McIntosh matched; Okatie
  has a nearby unnamed feature) while retrieval status remains `complete`.

## Undo / morning check
Anchor the Overpass regex if the extra raw values are not useful, or deliberately add another normalized power type
after F09 reviews its endpoint semantics. If OSM later adds the Okatie name, rerun the cache and the deterministic
landmark report will become complete without a code change.
