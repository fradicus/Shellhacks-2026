# F39 independent publication implementation review

Scope: pipeline/southeast/publish.py, florida_crs.py and test_f39_publish.py in /private/tmp/gridbridge-f39-publication, against C27/F39. Read-only source review with synthetic runtime probes written only in temporary directories. No production data release reviewed or approved.

## Actionable findings

### P1: exact duplicate native identities can activate as two projects

Location: publish.py lines123–128 and163–180. Uniqueness checks only `_id`. Two new projects under the same source with identical native_id can use different southeast IDs and accepted row locators. Both pass source evidence/count validation and inflate canonical project totals. Reproduced with fixture source/native `fixture-source`/`fixture-1`: added `_id=southeast:fixture:second`, second accepted row and adjusted counts; `apply_release` accepted two projects.

Fix: enforce uniqueness of the primary `(source_id, native_id)` identity within the release. Explicitly distinct source-defined components need genuinely distinct native/component identity, not duplicated publisher identity under another internal ID. Retain existing canonical cross-source review; do not fuzzy-collapse names. Add a regression test where source totals/dispositions/hashes are otherwise valid.

### P2: identity review can predate included location evidence

Location: publish.py check_location lines87–105 and apply_release lines185–187. Source/project/event/enumeration evidence must predate identity_review, but point geometry_evidence and identity_evidence do not receive that whole-release timestamp check. check_location only compares acquisition time against a location review whose facts hash is current. With no location reviews or only stale reviews, newly acquired point evidence can be included under an older release identity review and still pass.

Reproduced: identity_review2025-02-02; point geometry_evidence retrieved2025-03-01; empty location reviews and expected confirmed_projects0; recalculated identity hash. apply_release accepted it. Center correctly stayed null, but the contract explicitly says the whole-release identity review cannot predate acquisition evidence being reviewed. This creates a false reviewed-evidence claim even though geometry is not promoted.

Fix: compare identity review time against every included point geometry/identity evidence retrieval, regardless of location decision, and retain per-location current-review checks. Add regressions for both missing and stale location reviews.

## Production CRS independent comparison

Reviewed florida_crs.py against my prior standalone reproduction and visually reviewed official Esri108354 parameters. Projection and inverse affine signs, coordinate-frame convention, GRS80/WGS84 ellipsoids, metre/arcsec/ppm conversions and2D height convention agree. Executed production function at pinned Hopkins native point:

`to_wgs84(361673.80200000107,716135.95380000025)` -> `(-84.39946533002666,30.452223774750678)`.

This exactly matches the independent stdlib script output and matches explicit ArcGIS output within6e-14degrees. The Albers domain guard is useful. Accuracy remains unknown; the operation's0.1m accuracy is not assigned as facility accuracy. No CRS implementation defect found for this bounded Hopkins operation. Add a pinned numeric regression for these native/output coordinates if not present elsewhere; current test_f39_publish only exercises EPSG4326 and unsupported/axes cases.

## Other reviewed boundaries

- Fixed-path activation and deepcopy preserve candidate isolation and base immutability.
- Schema enforces null pre-projection centers, independent event input path, typed evidence/geometry and Southeast-state presence.
- Missing/stale/rejected/insufficient/conflicting location reviews preserve null centers. Current self-reviews, malformed times, role/facility duplication and mismatched project hashes fail.
- Known acquired locator sets reconcile exactly; complete requires known matching count. Underlying source truth still requires actual independent source inspection, appropriately outside numeric validation.
- Calendar/precision checks and event native identity checks are present. Duplicate event IDs across location/project paths must match exactly; histories merge without double-display entries.
- Source hash and accepted locator are bound to project source_evidence. Review hashes cover changed release content.
- Continental bounds are only plausibility checks; exact state/project linkage remains independent source review. No claim that those bounds establish Florida identity.

## Verdict

Fix the two reproduced validation gaps before activation. No full-suite claim is made; root owns checks. This is implementation review, not final evidence/coordinate/release approval. Reproduction did not modify producer files.

## Fix verification

Read the revised implementation and dedicated regressions. Both reproduced gaps are resolved:

- Exact `(source_id, native_id)` duplicates now fail before row/source assembly, even with distinct internal IDs and otherwise reconciled counts.
- Every included point's geometry/identity evidence must predate the whole-release identity review, regardless of missing/stale location reviews.

Independently ran the focused duplicate-native, missing/stale evidence timing and DEP transformation tests: **4 passed,25 deselected**. The tests exercise both previously accepted invalid cases and the pinned numeric transform with reversed axes/unspecified-method rejection. Read the added event deduplication/source binding and mock database failure tests; did not independently run those or the full suite.

No remaining issue from this bounded implementation review. Root's full checks and final source/project/record-bound independent review remain required. This conclusion does not approve production data, coordinates or activation.
