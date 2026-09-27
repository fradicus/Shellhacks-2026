# F39 publication validation

C27 is merged. F39 implements its fixed-path pure assembler under `pipeline/southeast/`.
F30 still owns calling that assembler and final national coverage validation; this implementation
does not by itself activate data or complete geographic delivery.

For F39-produced records, `project.evidence.raw.source_evidence` contains C23 typed evidence entries.
At least one must bind the primary source hash, URL and that project's accepted row locator. Other
raw observations remain alongside these entries. This is an internal producer convention inside the
national schema's existing open raw object, not a new shared required field for other producers.
Independent whole-release review still verifies each normalized fact and the actual source enumeration.

The initial geometry validator supports identity WGS84 points, Web Mercator points, and DEP's EPSG:6439
points using the explicit inverse ESRI:108354 operation independently reproduced in
`reports/southeast/hopkins-location-review.md`. Other CRS fail closed until independently reproduced.
The Florida operation has a fixed method identifier, original coordinates and output reproduction;
neither its operation accuracy nor storage precision becomes a facility-position accuracy claim.
Continental bounds allow evidenced cross-border endpoints but never establish project/state identity.

The assembler preserves source-bounded unknowns, typed history without geometry, and unapproved location
records with null centers. Tests cover repeat assembly, source/row/hash/count/date failures, stale and
self reviews, unsupported geometry, event conflicts and the existing loader's failed-write behavior.
No production release is approved by those synthetic tests. Remove or replace this producer convention
through an F39 change; changes to shared contracts or other owners' hooks need their separate claims.
