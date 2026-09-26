# F09: conservative endpoint location review

## Context

The F04 inventory contains strong public OSM evidence but little fine-area metadata: exact-name candidates generally
have voltage, some have operator, and none of the unique exact candidates has an OSM county tag. Georgia filing zone
numbers have no cited public geometry. The location schema permits evidence details, but downstream reviews need a
durable version-specific identity rather than an array position or `project_key` alone.

The active source set also contains 23 deliberately zero-endpoint ambiguous projects, one Georgia source-status
conflict, and a newly verified DESC title/description scope conflict. The sponsor workbook is a regression input and
cannot supply production coordinates.

## Decision

1. Use the recorded F04 inventory with no new Overpass requests. Cache two state polygons from the U.S. Census Bureau
   TIGERweb State_County layer 4 using this exact query:
   `where=STATE IN ('13','45')`, `outFields=STATE,GEOID,STUSAB,BASENAME`, `returnGeometry=true`, `outSR=4326`,
   `f=geojson`. Cache the layer metadata too, verify the stated **January 1, 2026** vintage, retain retrieval time and
   exact raw SHA-256 hashes, and reject replay when the query binding or bytes change.
2. Use state and the 10-mile opposite-state border rule only as coarse eligibility. Do not infer a zone map from
   numeric GPC zones. With no positive fine-area proof in this run, a unique exact candidate that also passes feature
   type, state/border, operator and voltage review is at most `medium` and carries `project_area_unverified`. Missing
   operator is retained as a limitation. An unverified owner never turns an OSM operator into corroboration. A fuzzy
   name without fine-area evidence is rejected. `high` remains implemented and tested for future cited area evidence.
3. Reject candidates when several remain contextually viable; never average or choose by input order. A voltage tag
   describes the mapped substation feature and may be incomplete, so a mismatch is recorded as a conflict rather than
   proof about every circuit. For a cross-utility tie, a different operator may be plausible, but it still blocks
   automatic acceptance without independent tie evidence.
4. Keep the 15 DESC and 8 Georgia `endpoint_ambiguous` active projects at zero endpoints. Reject both actual endpoints
   of `GPC:20482@gpc-2025` for `source_status_conflict`. Reject Fairfax and Yemassee for
   `DESC:6238 H@desc-2025`: page 44 titles the project Fairfax–Yemassee, while its description limits work to the
   DESCSQ #1151–Yemassee portion. Preserve both filed names and candidates for later review without changing F01.
5. For `DESC:6888`, reject McIntosh pending review of the DESC/Georgia Power and 115/230 kV conflicts. Okatie remains
   unlocated because no named OSM candidate exists. Preserve unnamed `way/1064022697` only in the sanity diagnostic as
   `candidate_only_not_asserted_as_okatie`; do not use the sponsor point to name it.
6. A location `_id` is `location:v1:` plus a SHA-256 prefix over the active version `_id`, endpoint index, endpoint
   norm and selected OSM id (or `unlocated`). Each record also carries `project_id`, `project_key`, and `source_id`.
   Changing selected evidence creates a new identity; unrelated ordering does not. Review ids bind to this location id
   and verdict. Project and normalized inventory inputs use canonical parsed-JSON SHA-256 fingerprints; Census raw
   responses use byte hashes and `-text` Git attributes.

## Consequences and reversal

The full run favors visible unresolved records over broad name-only coverage, and no endpoint receives `high` without
fine-area proof. F13 may independently confirm featured endpoints and pairs. To increase confidence later, add a cited
public area source or a reviewed zone mapping, rerun the deterministic builder, and retain the changed location ids as
new evidence decisions rather than retargeting old reviews.
